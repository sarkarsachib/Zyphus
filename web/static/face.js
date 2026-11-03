/* The face: an ASCII sculpture on a canvas.
 *
 * A skull is described as a scalar field over the stage (tapered cranium, angry
 * brows, hollow sockets, cheekbones, teeth) and sampled onto a monospace grid.
 * Each cell picks a glyph by density, so the portrait is really text; the eyes,
 * the teeth and the throat are drawn again in hot ink so they burn through the
 * bone.
 */
(function () {
  const GLYPHS = " .`',:;~+*=#%@";
  const BONE_TOP = [222, 214, 194];
  const BONE_BOTTOM = [116, 110, 99];
  const HOT_LIMIT = 900;

  const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);
  const gauss = (x, s) => Math.exp(-(x * x) / (2 * s * s));
  const smooth = (a, b, x) => {
    const t = clamp((x - a) / (b - a), 0, 1);
    return t * t * (3 - 2 * t);
  };
  const hash = (n) => {
    const s = Math.sin(n * 127.1) * 43758.5453;
    return s - Math.floor(s);
  };

  class EvilFace {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.voice = 0;
      this.speaking = false;
      this.regime = "diffuse";
      this.look = { x: 0, y: 0 };
      this.target = { x: 0, y: 0 };
      this.t = 0;
      this.last = performance.now();
      this.resize();
      window.addEventListener("resize", () => this.resize());
      requestAnimationFrame((ts) => this.loop(ts));
    }

    resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      const w = this.canvas.clientWidth || 800;
      const h = this.canvas.clientHeight || 480;
      this.canvas.width = Math.round(w * dpr);
      this.canvas.height = Math.round(h * dpr);
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.w = w;
      this.h = h;
      this.cellH = clamp(h / 42, 8, 18);
      this.cellW = this.cellH * 0.54;
      this.cols = Math.ceil(w / this.cellW) + 1;
      this.rows = Math.ceil(h / this.cellH) + 1;
      this.ctx.font = `${Math.round(this.cellH * 1.06)}px ui-monospace, "SF Mono", Menlo, Consolas, monospace`;
      this.ctx.textBaseline = "top";
    }

    setPointer(nx, ny) {
      this.target.x = clamp(nx, -1, 1);
      this.target.y = clamp(ny, -1, 1);
    }

    setVoice(level) {
      this.voice = clamp(level, 0, 1);
    }

    setSpeaking(on) {
      this.speaking = Boolean(on);
    }

    setRegime(regime) {
      this.regime = String(regime || "diffuse");
    }

    /** The skull as density (0..1) plus heat (0..1, what burns red). */
    sample(u, v, t) {
      const vv = v + 0.02;

      // skull silhouette: wide cranium, jaw tapering to a chin
      let halfW = 0.8;
      if (vv > 0.02) halfW *= 1 - 0.42 * Math.pow(Math.min(1, (vv - 0.02) / 1.0), 1.7);
      const R = Math.hypot(u / halfW, vv / 1.04);
      if (R > 1.16) return null;

      let val = 0;
      let heat = 0;

      // bone: brighter cranium, heavier jaw
      val += 0.44 - 0.22 * smooth(-0.25, 0.9, vv);
      val += 0.13 * Math.max(0, -u * 0.8 - vv * 0.5 + 0.2);

      // contour: lit only where the light falls, so it reads as a skull and not a ball
      const rimLight = Math.max(0, -u * 0.55 - vv * 0.8 + 0.42);
      val += gauss(R - 0.965, 0.026) * (0.12 + 0.75 * rimLight);

      for (const s of [-1, 1]) {
        const ex = 0.30 * s;
        const ey = -0.10;

        // angry brow: the inner end sits lower, angled at the nose
        const browY = ey - 0.175 + (u - ex) * 0.22 * (s < 0 ? 1 : -1);
        val -= 0.9 * gauss(u - ex, 0.205) * gauss(vv - browY, 0.042);

        // deep socket
        val -= 1.4 * gauss(u - ex, 0.145) * gauss(vv - ey, 0.108);

        // the pupil that follows the pointer
        const px = ex + this.look.x * 0.05;
        const py = ey + this.look.y * 0.04;
        const pupil = gauss(u - px, 0.042) * gauss(vv - py, 0.04);
        val += 1.35 * pupil;
        heat += 1.55 * pupil;

        // cheekbone, then the hollow beneath it
        val += 0.2 * gauss(u - 0.4 * s, 0.1) * gauss(vv + 0.06, 0.09);
        val -= 0.55 * gauss(u - 0.52 * s, 0.13) * gauss(vv - 0.3, 0.13);
      }

      // brow furrow between the brows
      val -= 0.4 * (gauss(u - 0.055, 0.017) + gauss(u + 0.055, 0.017)) * gauss(vv + 0.3, 0.09);

      // nose: bridge, then two slit nostrils
      val += 0.2 * gauss(u, 0.04) * gauss(vv + 0.02, 0.17);
      for (const s of [-1, 1]) {
        val -= 0.75 * gauss(u - 0.075 * s, 0.03) * gauss(vv - 0.235, 0.024);
      }

      // the mouth: always a jagged line of teeth, opening as he speaks
      const my = 0.5;
      const mw = 0.27;
      const span = Math.exp(-Math.pow(Math.abs(u) / mw, 6));
      const open = 0.017 + this.voice * 0.2;
      const aperture = span * Math.exp(-Math.pow((vv - my) / open, 4));
      val -= 1.3 * aperture;
      if (Math.sin(u * 62) > -0.1) {
        val += (0.5 + this.voice * 0.55) * span * Math.exp(-Math.pow((vv - my) / (open * 1.05), 6));
      }
      heat += 0.7 * aperture * (0.22 + this.voice * 1.6);

      // chin crease
      val -= 0.3 * gauss(u, 0.22) * gauss(vv - 0.78, 0.035);

      // grain, so the skull never looks printed
      val += (hash(u * 12.9898 + vv * 78.233 + t * 0.7) - 0.5) * 0.12;

      const inside = 1 - smooth(0.99, 1.1, R);
      if (inside <= 0.002) return null;
      return { v: clamp(val * inside, 0, 1), h: clamp(heat * inside, 0, 1) };
    }

    loop(ts) {
      const dt = Math.min(0.06, (ts - this.last) / 1000 || 0.016);
      this.last = ts;
      this.t += dt;

      // the pupils drift toward the pointer instead of snapping
      this.look.x += (this.target.x - this.look.x) * Math.min(1, dt * 3.2);
      this.look.y += (this.target.y - this.look.y) * Math.min(1, dt * 3.2);

      this.draw();
      requestAnimationFrame((next) => this.loop(next));
    }

    draw() {
      const ctx = this.ctx;
      const t = this.t;
      ctx.clearRect(0, 0, this.w, this.h);

      const breath = 1 + Math.sin(t * 0.33) * 0.008;
      const R0 = Math.min(this.w, this.h) * 0.43 * breath;
      const cx = this.w / 2;
      const cy = this.h * 0.49 + Math.sin(t * 0.42) * this.h * 0.011;

      // the aura behind the skull
      const aura = ctx.createRadialGradient(cx, cy, R0 * 0.15, cx, cy, R0 * 1.55);
      const ember = 0.13 + this.voice * 0.2 + (this.speaking ? 0.05 : 0);
      aura.addColorStop(0, `rgba(178, 16, 20, ${ember.toFixed(3)})`);
      aura.addColorStop(0.5, `rgba(110, 8, 14, ${(ember * 0.45).toFixed(3)})`);
      aura.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = aura;
      ctx.fillRect(0, 0, this.w, this.h);

      this.drawRunes(cx, cy, R0 * 1.16, t);

      const hot = [];
      const cols = this.cols;
      const rows = this.rows;
      ctx.globalAlpha = 0.96;

      for (let ry = 0; ry < rows; ry++) {
        let line = "";
        let has = false;
        for (let rx = 0; rx < cols; rx++) {
          const x = rx * this.cellW + this.cellW * 0.5;
          const y = ry * this.cellH + this.cellH * 0.5;
          const s = this.sample((x - cx) / R0, (y - cy) / R0, t);
          if (!s) { line += " "; continue; }
          const idx = Math.round(s.v * (GLYPHS.length - 1));
          const glyph = GLYPHS[idx];
          line += glyph;
          if (glyph !== " ") has = true;
          if (s.h > 0.14) hot.push({ rx, ry, glyph, heat: s.h });
        }
        if (!has) continue;
        const k = ry / Math.max(1, rows - 1);
        const r = Math.round(BONE_TOP[0] + (BONE_BOTTOM[0] - BONE_TOP[0]) * k);
        const g = Math.round(BONE_TOP[1] + (BONE_BOTTOM[1] - BONE_TOP[1]) * k);
        const b = Math.round(BONE_TOP[2] + (BONE_BOTTOM[2] - BONE_TOP[2]) * k);
        ctx.fillStyle = `rgb(${r},${g},${b})`;
        ctx.fillText(line, 0, ry * this.cellH);
      }

      ctx.globalAlpha = 1;
      ctx.save();
      ctx.shadowColor = "rgba(255, 34, 40, 0.85)";
      ctx.shadowBlur = this.cellH * 0.7;
      for (let i = 0; i < hot.length && i < HOT_LIMIT; i++) {
        const cell = hot[i];
        const alpha = clamp(0.25 + cell.heat * 0.9, 0, 1);
        ctx.fillStyle = `rgba(255, ${Math.round(52 + cell.heat * 60)}, 48, ${alpha.toFixed(3)})`;
        ctx.fillText(cell.glyph, cell.rx * this.cellW, cell.ry * this.cellH);
      }
      ctx.restore();
    }

    drawRunes(cx, cy, radius, t) {
      const ctx = this.ctx;
      const glyphs = "⟁⟟⟠⧉◈▚▞†‡◬";
      const count = 44;
      const spin = t * 0.06;
      ctx.save();
      ctx.font = `${Math.round(this.cellH * 0.85)}px ui-monospace, Menlo, monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      for (let i = 0; i < count; i++) {
        const a = spin + (i / count) * Math.PI * 2;
        const pulse = 0.05 + 0.045 * Math.sin(t * 0.8 + i * 0.7);
        ctx.fillStyle = `rgba(198, 26, 30, ${pulse.toFixed(3)})`;
        ctx.fillText(glyphs[(i * 7) % glyphs.length], cx + Math.cos(a) * radius, cy + Math.sin(a) * radius * 1.02);
      }
      ctx.restore();
    }
  }

  window.EvilFace = EvilFace;
})();
