"""
The agent's senses: a voice and an eye.

Voice - `speak()` renders text to a real .wav with the speech engine installed
in the image (espeak-ng). The dashboard plays the newest utterance, so the agent
can be heard in the preview. `listen()` is deliberately absent: this container
has no microphone, and pretending otherwise would be a lie.

Vision - `look()` reads an image the agent can reach (a path in the container or
an http(s) URL) and reports what is actually in it: format, size, brightness,
dominant colours and a luminance grid it can reason about. PNG is decoded pixel
by pixel with the standard library; for JPEG only the frame size is read, and
the tool says so instead of guessing at pixels it did not decode.
"""

import os
import shutil
import struct
import subprocess
import time
import urllib.request
import zlib
from typing import Any, Dict, List, Optional, Tuple

from src.agent.tools import REPO_ROOT, ToolResult

VOICE_DIR = os.path.join(REPO_ROOT, "devmind", "agent", "voice")
RAMP = " .:-=+*#%@"
GRID_COLS = 56
MAX_IMAGE_BYTES = 12 * 1024 * 1024


# --- voice -------------------------------------------------------------------


def speech_engine() -> Optional[str]:
    return shutil.which("espeak-ng") or shutil.which("espeak")


def speak(text: str, speed: int = 165, voice: Optional[str] = None) -> ToolResult:
    """Say `text` out loud to a wav file; the dashboard plays the newest one."""
    text = (text or "").strip()
    if not text:
        return ToolResult(False, error="nothing to say")
    engine = speech_engine()
    if engine is None:
        return ToolResult(False, error="no speech engine in the image (install espeak-ng)")

    os.makedirs(VOICE_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(VOICE_DIR, f"voice-{stamp}.wav")
    command = [engine, "-w", path, "-s", str(int(speed))]
    if voice:
        command += ["-v", str(voice)]
    command.append(text)

    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except Exception as exc:
        return ToolResult(False, error=f"{type(exc).__name__}: {exc}")
    if proc.returncode != 0 or not os.path.isfile(path):
        return ToolResult(False, error=(proc.stderr or "speech engine failed").strip())

    seconds = _wav_seconds(path)
    return ToolResult(
        True,
        output=f"said: {text[:200]}\naudio: {os.path.basename(path)} ({seconds:.1f}s)",
        meta={"file": os.path.basename(path), "path": path, "seconds": round(seconds, 2),
              "text": text, "bytes": os.path.getsize(path)},
    )


def _wav_seconds(path: str) -> float:
    """Duration of a RIFF/wav file, read from its own header."""
    with open(path, "rb") as handle:
        header = handle.read(44)
    if header[:4] != b"RIFF" or len(header) < 44:
        return 0.0
    channels = struct.unpack("<H", header[22:24])[0]
    rate = struct.unpack("<I", header[24:28])[0]
    bits = struct.unpack("<H", header[34:36])[0]
    frames = os.path.getsize(path) - 44
    bytes_per_second = max(1, rate * max(1, channels) * max(8, bits) // 8)
    return frames / bytes_per_second


def utterances(limit: int = 5) -> List[Dict[str, Any]]:
    """Newest-first list of the audio the agent has produced."""
    if not os.path.isdir(VOICE_DIR):
        return []
    names = sorted((n for n in os.listdir(VOICE_DIR) if n.endswith(".wav")), reverse=True)
    return [{"file": name, "seconds": round(_wav_seconds(os.path.join(VOICE_DIR, name)), 2)}
            for name in names[:limit]]


# --- vision ------------------------------------------------------------------


def look(source: str) -> ToolResult:
    """Read an image (path or URL) and describe what is really in it."""
    if not source:
        return ToolResult(False, error="nothing to look at")
    try:
        blob = _load_image(source)
    except Exception as exc:
        return ToolResult(False, error=f"{type(exc).__name__}: {exc}")

    if blob[:8] == b"\x89PNG\r\n\x1a\n":
        try:
            width, height, rgb = _decode_png(blob)
        except Exception as exc:
            return ToolResult(False, error=f"could not decode PNG: {exc}")
        report = _describe(width, height, rgb)
        report["format"] = "png"
        report["source"] = source
        return ToolResult(True, output=_render(report), meta=report)

    size = _jpeg_size(blob)
    if size:
        width, height = size
        return ToolResult(
            True,
            output=(f"{source}\nformat: jpeg\nsize: {width}x{height}\n"
                    "pixels: not decoded (only PNG is decoded by the built-in eye)"),
            meta={"format": "jpeg", "source": source, "width": width, "height": height},
        )
    return ToolResult(False, error="unrecognised image format (png and jpeg only)")


def _load_image(source: str) -> bytes:
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=30) as response:
            return response.read(MAX_IMAGE_BYTES)
    path = source if os.path.isabs(source) else os.path.join(REPO_ROOT, source)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"not a file: {path}")
    with open(path, "rb") as handle:
        return handle.read(MAX_IMAGE_BYTES)


def _decode_png(data: bytes) -> Tuple[int, int, bytearray]:
    """Decode a non-interlaced 8-bit PNG into packed RGB."""
    pos, idat, palette = 8, bytearray(), None
    width = height = colour_type = 0
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            width, height, depth, colour_type, _, _, interlace = struct.unpack(">IIBBBBB", chunk)
            if interlace:
                raise ValueError("interlaced PNG")
            if depth != 8:
                raise ValueError(f"{depth}-bit PNG")
        elif kind == b"PLTE":
            palette = chunk
        elif kind == b"IDAT":
            idat += chunk
        elif kind == b"IEND":
            break

    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(colour_type)
    if channels is None:
        raise ValueError(f"colour type {colour_type}")

    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    rows, previous, cursor = [], bytearray(stride), 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        line = bytearray(raw[cursor:cursor + stride])
        cursor += stride
        if filter_type == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif filter_type == 2:
            for i in range(stride):
                line[i] = (line[i] + previous[i]) & 0xFF
        elif filter_type == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 0xFF
        elif filter_type == 4:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                up = previous[i]
                upleft = previous[i - channels] if i >= channels else 0
                p = left + up - upleft
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - upleft)
                pred = left if (pa <= pb and pa <= pc) else (up if pb <= pc else upleft)
                line[i] = (line[i] + pred) & 0xFF
        elif filter_type != 0:
            raise ValueError(f"filter {filter_type}")
        rows.append(bytes(line))
        previous = line

    rgb = bytearray(width * height * 3)
    at = 0
    for line in rows:
        for x in range(width):
            base = x * channels
            if colour_type == 2:
                r, g, b = line[base], line[base + 1], line[base + 2]
            elif colour_type == 6:
                r, g, b = line[base], line[base + 1], line[base + 2]
            elif colour_type == 0:
                r = g = b = line[base]
            elif colour_type == 4:
                r = g = b = line[base]
            else:  # palette
                index = line[base] * 3
                if palette is None or index + 2 >= len(palette):
                    r = g = b = line[base]
                else:
                    r, g, b = palette[index], palette[index + 1], palette[index + 2]
            rgb[at] = r
            rgb[at + 1] = g
            rgb[at + 2] = b
            at += 3
    return width, height, rgb


def _jpeg_size(data: bytes) -> Optional[Tuple[int, int]]:
    if data[:2] != b"\xff\xd8":
        return None
    pos = 2
    while pos + 9 < len(data):
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB):
            height, width = struct.unpack(">HH", data[pos + 5:pos + 9])
            return width, height
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        length = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        pos += 2 + length
    return None


def _describe(width: int, height: int, rgb: bytearray) -> Dict[str, Any]:
    pixels = width * height
    total = [0, 0, 0]
    buckets: Dict[Tuple[int, int, int], int] = {}
    for i in range(0, pixels * 3, 3):
        r, g, b = rgb[i], rgb[i + 1], rgb[i + 2]
        total[0] += r
        total[1] += g
        total[2] += b
        buckets[(r >> 4, g >> 4, b >> 4)] = buckets.get((r >> 4, g >> 4, b >> 4), 0) + 1

    mean = [round(channel / max(1, pixels)) for channel in total]
    top = sorted(buckets.items(), key=lambda item: -item[1])[:3]
    dominant = [
        {"hex": "#%02x%02x%02x" % (r * 16 + 8, g * 16 + 8, b * 16 + 8),
         "share": round(count / max(1, pixels), 3)}
        for (r, g, b), count in top
    ]
    luminance = round((0.299 * mean[0] + 0.587 * mean[1] + 0.114 * mean[2]) / 255, 3)
    return {
        "width": width,
        "height": height,
        "mean_rgb": mean,
        "brightness": luminance,
        "dominant_colors": dominant,
        "grid": _grid(width, height, rgb),
    }


def _grid(width: int, height: int, rgb: bytearray, cols: int = GRID_COLS) -> List[str]:
    """A luminance picture of the image, so the agent can see its shape."""
    cols = max(8, min(cols, width))
    rows = max(4, min(40, int(cols * height / max(1, width) * 0.5)))
    lines = []
    for row in range(rows):
        line = []
        y0, y1 = row * height // rows, max(row * height // rows + 1, (row + 1) * height // rows)
        for col in range(cols):
            x0, x1 = col * width // cols, max(col * width // cols + 1, (col + 1) * width // cols)
            total = count = 0
            for y in range(y0, y1):
                start = (y * width + x0) * 3
                for x in range(x0, x1):
                    i = start + (x - x0) * 3
                    total += 0.299 * rgb[i] + 0.587 * rgb[i + 1] + 0.114 * rgb[i + 2]
                    count += 1
            value = total / max(1, count) / 255
            line.append(RAMP[min(len(RAMP) - 1, int(value * len(RAMP)))])
        lines.append("".join(line))
    return lines


def _render(report: Dict[str, Any]) -> str:
    colors = ", ".join(f"{c['hex']} ({c['share'] * 100:.0f}%)" for c in report["dominant_colors"])
    return "\n".join([
        f"{report['source']}",
        f"format: {report['format']}  size: {report['width']}x{report['height']}",
        f"brightness: {report['brightness']:.2f}  mean rgb: {report['mean_rgb']}",
        f"dominant colours: {colors}",
        "shape:",
        *report["grid"],
    ])
