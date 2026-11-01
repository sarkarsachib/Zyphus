"""
DEVmind Fusion PORT System
Protocol Operations Runtime Terminal - Unified interface for all language ports and system connections
"""

import asyncio
import json
import logging
import py_compile
import shutil
import signal
import subprocess
import sys
import os
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod
import importlib.util
import tempfile
import threading
import queue
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PortType(Enum):
    """Types of PORTs in the Fusion system"""
    LANGUAGE = "language"
    SYSTEM = "system"
    NETWORK = "network"
    QUANTUM = "quantum"
    DEVICE = "device"
    METAVERSE = "metaverse"

class PortStatus(Enum):
    """Status of a PORT"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"

@dataclass
class PortConfig:
    """Configuration for a PORT"""
    name: str
    port_type: PortType
    capabilities: List[str]
    connection_params: Dict[str, Any]
    security_level: str = "standard"
    auto_reconnect: bool = True
    timeout: float = 30.0

@dataclass
class PortMessage:
    """Message structure for PORT communication"""
    id: str
    source_port: str
    target_port: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    priority: int = 1

# --- real validators and compilers -------------------------------------------
#
# These are plain synchronous functions so both the PORT classes below and the
# agent's tools can use them without an event loop. When a toolchain is absent
# the result says `available: False` - it never reports a fake success.

def _tool(name: str) -> Optional[str]:
    return shutil.which(name)


def validate_code(code: str, language: str = "python") -> Dict[str, Any]:
    """Validate source code with the language's own checker.

    Python is compiled in-process; JavaScript goes through `node --check`;
    Rust through `rustc --emit=metadata`; Go through `gofmt -e`. A language
    whose toolchain is missing returns `available: False` and `valid: None`.
    """
    language = (language or "python").strip().lower()
    code = code or ""
    if not code.strip():
        return {"valid": False, "available": True, "language": language,
                "message": "no code to validate"}

    if language in ("python", "py"):
        try:
            compile(code, "<fusion-port>", "exec")
        except SyntaxError as exc:
            return {"valid": False, "available": True, "language": "python",
                    "message": f"{exc.msg} (line {exc.lineno}, column {exc.offset})",
                    "line": exc.lineno, "column": exc.offset}
        return {"valid": True, "available": True, "language": "python",
                "message": "syntax ok"}

    if language in ("javascript", "js", "node", "mjs"):
        node = _tool("node")
        if not node:
            return {"valid": None, "available": False, "language": "javascript",
                    "message": "node is not installed"}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "check.mjs")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(code)
            proc = subprocess.run([node, "--check", path], capture_output=True,
                                  text=True, timeout=30)
        return {"valid": proc.returncode == 0, "available": True,
                "language": "javascript", "message": (proc.stderr or "syntax ok").strip(),
                "stderr": proc.stderr.strip()}

    if language in ("rust", "rs"):
        rustc = _tool("rustc")
        if not rustc:
            return {"valid": None, "available": False, "language": "rust",
                    "message": "rustc is not installed"}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "check.rs")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(code)
            proc = subprocess.run(
                [rustc, "--edition", "2021", "--crate-type", "lib", "--emit=metadata",
                 "-o", os.path.join(tmp, "check.rmeta"), path],
                capture_output=True, text=True, timeout=120)
        return {"valid": proc.returncode == 0, "available": True, "language": "rust",
                "message": (proc.stderr or "compiles").strip(),
                "stderr": proc.stderr.strip()}

    if language in ("go", "golang"):
        gofmt = _tool("gofmt")
        if not gofmt:
            return {"valid": None, "available": False, "language": "go",
                    "message": "gofmt is not installed"}
        proc = subprocess.run([gofmt, "-e"], input=code, capture_output=True,
                              text=True, timeout=30)
        return {"valid": proc.returncode == 0, "available": True, "language": "go",
                "message": (proc.stderr or "syntax ok").strip(),
                "stderr": proc.stderr.strip()}

    return {"valid": None, "available": False, "language": language,
            "message": f"no validator for {language}"}


def compile_code(code: str, language: str = "python",
                 out_dir: Optional[str] = None) -> Dict[str, Any]:
    """Build code with the language's own compiler and report the artifact."""
    language = (language or "python").strip().lower()
    code = code or ""
    out_dir = out_dir or tempfile.mkdtemp(prefix="fusion-port-")
    os.makedirs(out_dir, exist_ok=True)

    if language in ("python", "py"):
        source = os.path.join(out_dir, "compiled_source.py")
        with open(source, "w", encoding="utf-8") as handle:
            handle.write(code)
        artifact = os.path.join(out_dir, "compiled_source.pyc")
        try:
            py_compile.compile(source, cfile=artifact, doraise=True)
        except py_compile.PyCompileError as exc:
            return {"compiled": False, "available": True, "language": "python",
                    "message": str(exc)}
        return {"compiled": True, "available": True, "language": "python",
                "artifact": artifact, "bytes": os.path.getsize(artifact),
                "message": "bytecode written"}

    if language in ("javascript", "js", "node", "mjs"):
        checked = validate_code(code, "javascript")
        return {"compiled": checked.get("valid"), "available": checked["available"],
                "language": "javascript", "artifact": None,
                "message": "JavaScript is interpreted - syntax checked with node --check"
                           if checked["available"] else checked["message"]}

    if language in ("rust", "rs"):
        cargo = _tool("cargo")
        if not cargo:
            return {"compiled": None, "available": False, "language": "rust",
                    "message": "cargo is not installed"}
        project = os.path.join(out_dir, "rust_project")
        os.makedirs(os.path.join(project, "src"), exist_ok=True)
        with open(os.path.join(project, "Cargo.toml"), "w", encoding="utf-8") as handle:
            handle.write('[package]\nname = "fusion_check"\nversion = "0.1.0"\n'
                         'edition = "2021"\n\n[dependencies]\n')
        with open(os.path.join(project, "src", "main.rs"), "w", encoding="utf-8") as handle:
            handle.write(code)
        proc = subprocess.run([cargo, "build", "--offline"], cwd=project,
                              capture_output=True, text=True, timeout=300)
        binary = os.path.join(project, "target", "debug", "fusion_check")
        return {"compiled": proc.returncode == 0, "available": True, "language": "rust",
                "artifact": binary if os.path.exists(binary) else None,
                "message": (proc.stderr or "built").strip()[-2000:]}

    if language in ("go", "golang"):
        go = _tool("go")
        if not go:
            return {"compiled": None, "available": False, "language": "go",
                    "message": "go is not installed"}
        source = os.path.join(out_dir, "main.go")
        with open(source, "w", encoding="utf-8") as handle:
            handle.write(code)
        binary = os.path.join(out_dir, "main")
        proc = subprocess.run([go, "build", "-o", binary, source], cwd=out_dir,
                              capture_output=True, text=True, timeout=300)
        return {"compiled": proc.returncode == 0, "available": True, "language": "go",
                "artifact": binary if os.path.exists(binary) else None,
                "message": (proc.stderr or "built").strip()[-2000:]}

    return {"compiled": None, "available": False, "language": language,
            "message": f"no compiler for {language}"}


# --- real process management -------------------------------------------------

_CLOCK_TICKS = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
_PAGE_SIZE = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096


def _proc_stat(pid: int) -> Optional[Dict[str, Any]]:
    try:
        with open(f"/proc/{pid}/stat", "r", encoding="utf-8", errors="replace") as handle:
            raw = handle.read()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None
    close = raw.rfind(")")
    if close < 0:
        return None
    name = raw[raw.find("(") + 1:close]
    fields = raw[close + 2:].split()
    if len(fields) < 22:
        return None
    return {
        "pid": pid,
        "name": name,
        "state": fields[0],
        "cpu_ticks": int(fields[11]) + int(fields[12]),
        "threads": int(fields[17]),
        "starttime": int(fields[19]),
        "rss_bytes": int(fields[21]) * _PAGE_SIZE,
    }


def _proc_cmdline(pid: int) -> List[str]:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as handle:
            raw = handle.read()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return []
    return [part.decode("utf-8", "replace") for part in raw.split(b"\0") if part]


def _uptime() -> float:
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as handle:
            return float(handle.read().split()[0])
    except (FileNotFoundError, ValueError, IndexError):
        return 0.0


def list_processes(limit: int = 25, sort: str = "rss") -> Dict[str, Any]:
    """List live processes from /proc, largest memory footprint first by default."""
    processes = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        snapshot = _proc_stat(int(entry))
        if snapshot is None:
            continue
        snapshot["cmdline"] = " ".join(_proc_cmdline(int(entry)))[:300]
        snapshot["memory_mb"] = round(snapshot["rss_bytes"] / (1024 * 1024), 2)
        processes.append(snapshot)

    if sort in ("pid",):
        processes.sort(key=lambda item: item["pid"])
    elif sort in ("cpu", "ticks"):
        processes.sort(key=lambda item: item["cpu_ticks"], reverse=True)
    elif sort in ("name",):
        processes.sort(key=lambda item: item["name"])
    else:
        processes.sort(key=lambda item: item["rss_bytes"], reverse=True)

    limit = max(1, int(limit))
    return {"ok": True, "count": len(processes), "returned": min(limit, len(processes)),
            "processes": processes[:limit]}


def process_info(pid: int) -> Dict[str, Any]:
    """Details for one process: state, memory, threads, command and age."""
    pid = int(pid)
    snapshot = _proc_stat(pid)
    if snapshot is None:
        return {"ok": False, "error": f"no process with pid {pid}"}
    try:
        cwd = os.readlink(f"/proc/{pid}/cwd")
    except OSError:
        cwd = ""
    try:
        exe = os.readlink(f"/proc/{pid}/exe")
    except OSError:
        exe = ""
    elapsed = max(0.0, _uptime() - snapshot["starttime"] / _CLOCK_TICKS)
    return {
        "ok": True,
        "pid": pid,
        "name": snapshot["name"],
        "state": snapshot["state"],
        "threads": snapshot["threads"],
        "memory_mb": round(snapshot["rss_bytes"] / (1024 * 1024), 2),
        "cpu_seconds": round(snapshot["cpu_ticks"] / _CLOCK_TICKS, 3),
        "elapsed_seconds": round(elapsed, 1),
        "cmdline": " ".join(_proc_cmdline(pid))[:2000],
        "cwd": cwd,
        "exe": exe,
    }


def monitor_process(pid: int, interval: float = 0.2) -> Dict[str, Any]:
    """Sample a live process twice and report CPU use over that interval."""
    pid = int(pid)
    interval = max(0.05, min(5.0, float(interval)))
    first = _proc_stat(pid)
    if first is None:
        return {"ok": False, "error": f"no process with pid {pid}"}
    time.sleep(interval)
    second = _proc_stat(pid)
    if second is None:
        return {"ok": False, "error": f"process {pid} exited during the sample"}
    delta_ticks = max(0, second["cpu_ticks"] - first["cpu_ticks"])
    cpu_percent = (delta_ticks / _CLOCK_TICKS) / interval * 100.0
    return {"ok": True, "pid": pid, "name": second["name"], "state": second["state"],
            "cpu_percent": round(cpu_percent, 1),
            "memory_mb": round(second["rss_bytes"] / (1024 * 1024), 2),
            "threads": second["threads"], "interval_seconds": interval}


def signal_process(pid: int, signal_name: str = "TERM") -> Dict[str, Any]:
    """Send a signal to a process and report whether it is still running."""
    pid = int(pid)
    if pid <= 0:
        return {"ok": False, "error": "pid must be positive"}
    name = signal_name.strip().upper()
    if not name.startswith("SIG"):
        name = f"SIG{name}"
    if not hasattr(signal, name):
        return {"ok": False, "error": f"unknown signal: {signal_name}"}
    try:
        os.kill(pid, getattr(signal, name))
    except ProcessLookupError:
        return {"ok": False, "error": f"no process with pid {pid}"}
    except PermissionError as exc:
        return {"ok": False, "error": f"not permitted: {exc}"}

    time.sleep(0.2)
    snapshot = _proc_stat(pid)
    still_running = snapshot is not None and snapshot["state"] != "Z"
    return {"ok": True, "pid": pid, "signal": name, "running": still_running}


def process_management(payload: Dict[str, Any]) -> Dict[str, Any]:
    """The shared body of SystemPORT._process_management."""
    action = str(payload.get("process_operation") or payload.get("action") or "list").lower()
    if action in ("list", "ps"):
        return list_processes(limit=int(payload.get("limit") or 25),
                              sort=str(payload.get("sort") or "rss"))
    if action in ("info", "stat", "status"):
        return process_info(int(payload.get("pid") or 0))
    if action in ("monitor", "sample"):
        return monitor_process(int(payload.get("pid") or 0),
                               float(payload.get("interval") or 0.2))
    if action in ("kill", "signal", "terminate"):
        return signal_process(int(payload.get("pid") or 0),
                              str(payload.get("signal") or "TERM"))
    return {"ok": False, "error": f"unknown process operation: {action}"}


class BasePORT(ABC):
    """Base class for all PORTs"""
    
    def __init__(self, config: PortConfig):
        self.config = config
        self.status = PortStatus.INACTIVE
        self.connection = None
        self.message_queue = queue.Queue()
        self.event_handlers = {}
        self.metrics = {
            'messages_sent': 0,
            'messages_received': 0,
            'errors': 0,
            'uptime': 0,
            'last_activity': None
        }
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the target system"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the target system"""
        pass
    
    @abstractmethod
    async def send_message(self, message: PortMessage) -> Dict[str, Any]:
        """Send message through this PORT"""
        pass
    
    @abstractmethod
    async def receive_message(self) -> Optional[PortMessage]:
        """Receive message from this PORT"""
        pass
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler for specific event types"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit event to registered handlers"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"Event handler error: {str(e)}")
    
    def update_metrics(self, metric_type: str, value: Any = None):
        """Update PORT metrics"""
        if metric_type in self.metrics:
            if value is not None:
                self.metrics[metric_type] = value
            else:
                self.metrics[metric_type] += 1
        
        self.metrics['last_activity'] = datetime.now()

class LanguagePORT(BasePORT):
    """PORT for programming language runtime integration"""
    
    def __init__(self, config: PortConfig, language: str, runtime_path: str):
        super().__init__(config)
        self.language = language
        self.runtime_path = runtime_path
        self.process = None
        self.temp_dir = None
    
    async def connect(self) -> bool:
        """Connect to language runtime"""
        try:
            self.status = PortStatus.CONNECTING
            
            # Create temporary directory for code execution
            self.temp_dir = tempfile.mkdtemp(prefix=f"devmind_{self.language}_")
            
            # Initialize language-specific runtime
            if self.language.lower() == 'python':
                await self._init_python_runtime()
            elif self.language.lower() == 'javascript':
                await self._init_javascript_runtime()
            elif self.language.lower() == 'rust':
                await self._init_rust_runtime()
            elif self.language.lower() == 'go':
                await self._init_go_runtime()
            else:
                await self._init_generic_runtime()
            
            self.status = PortStatus.ACTIVE
            self.emit_event('connected', {'language': self.language})
            logger.info(f"Language PORT connected: {self.language}")
            return True
            
        except Exception as e:
            self.status = PortStatus.ERROR
            logger.error(f"Failed to connect Language PORT {self.language}: {str(e)}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from language runtime"""
        try:
            if self.process:
                self.process.terminate()
                self.process = None
            
            if self.temp_dir and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
            
            self.status = PortStatus.DISCONNECTED
            self.emit_event('disconnected', {'language': self.language})
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting Language PORT {self.language}: {str(e)}")
            return False
    
    async def send_message(self, message: PortMessage) -> Dict[str, Any]:
        """Execute code through language runtime"""
        try:
            payload = message.payload
            code = payload.get('code', '')
            execution_mode = payload.get('mode', 'execute')
            
            if execution_mode == 'execute':
                result = await self._execute_code(code)
            elif execution_mode == 'validate':
                result = await self._validate_code(code)
            elif execution_mode == 'compile':
                result = await self._compile_code(code)
            else:
                result = {'error': f'Unknown execution mode: {execution_mode}'}
            
            self.update_metrics('messages_sent')
            return result
            
        except Exception as e:
            self.update_metrics('errors')
            return {'error': str(e)}
    
    async def receive_message(self) -> Optional[PortMessage]:
        """Receive message from language runtime"""
        # For language PORTs, this would typically be used for
        # receiving runtime events, errors, or output
        try:
            if not self.message_queue.empty():
                return self.message_queue.get_nowait()
        except queue.Empty:
            pass
        return None
    
    async def _execute_code(self, code: str) -> Dict[str, Any]:
        """Execute code in the language runtime"""
        if self.language.lower() == 'python':
            return await self._execute_python(code)
        elif self.language.lower() == 'javascript':
            return await self._execute_javascript(code)
        elif self.language.lower() == 'rust':
            return await self._execute_rust(code)
        elif self.language.lower() == 'go':
            return await self._execute_go(code)
        else:
            return {'error': f'Execution not implemented for {self.language}'}
    
    async def _execute_python(self, code: str) -> Dict[str, Any]:
        """Execute Python code"""
        try:
            # Create temporary Python file
            code_file = os.path.join(self.temp_dir, 'temp_code.py')
            with open(code_file, 'w') as f:
                f.write(code)
            
            # Execute Python code
            process = await asyncio.create_subprocess_exec(
                sys.executable, code_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.temp_dir
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                'success': process.returncode == 0,
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8'),
                'return_code': process.returncode,
                'language': 'python'
            }
            
        except Exception as e:
            return {'error': str(e), 'language': 'python'}
    
    async def _execute_javascript(self, code: str) -> Dict[str, Any]:
        """Execute JavaScript code"""
        try:
            # Create temporary JavaScript file
            code_file = os.path.join(self.temp_dir, 'temp_code.js')
            with open(code_file, 'w') as f:
                f.write(code)
            
            # Execute JavaScript code with Node.js
            process = await asyncio.create_subprocess_exec(
                'node', code_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.temp_dir
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                'success': process.returncode == 0,
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8'),
                'return_code': process.returncode,
                'language': 'javascript'
            }
            
        except Exception as e:
            return {'error': str(e), 'language': 'javascript'}
    
    async def _execute_rust(self, code: str) -> Dict[str, Any]:
        """Execute Rust code"""
        try:
            # Create Rust project structure
            src_dir = os.path.join(self.temp_dir, 'src')
            os.makedirs(src_dir, exist_ok=True)
            
            # Create Cargo.toml
            cargo_toml = """[package]
name = "devmind_temp"
version = "0.1.0"
edition = "2021"

[dependencies]
"""
            with open(os.path.join(self.temp_dir, 'Cargo.toml'), 'w') as f:
                f.write(cargo_toml)
            
            # Create main.rs
            with open(os.path.join(src_dir, 'main.rs'), 'w') as f:
                f.write(code)
            
            # Compile and run
            process = await asyncio.create_subprocess_exec(
                'cargo', 'run',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.temp_dir
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                'success': process.returncode == 0,
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8'),
                'return_code': process.returncode,
                'language': 'rust'
            }
            
        except Exception as e:
            return {'error': str(e), 'language': 'rust'}
    
    async def _execute_go(self, code: str) -> Dict[str, Any]:
        """Execute Go code"""
        try:
            # Create temporary Go file
            code_file = os.path.join(self.temp_dir, 'main.go')
            with open(code_file, 'w') as f:
                f.write(code)
            
            # Execute Go code
            process = await asyncio.create_subprocess_exec(
                'go', 'run', code_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.temp_dir
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                'success': process.returncode == 0,
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8'),
                'return_code': process.returncode,
                'language': 'go'
            }
            
        except Exception as e:
            return {'error': str(e), 'language': 'go'}
    
    async def _init_python_runtime(self):
        """Initialize Python runtime"""
        # Check if Python is available
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            if process.returncode != 0:
                raise Exception("Python runtime not available")
        except Exception as e:
            raise Exception(f"Failed to initialize Python runtime: {str(e)}")
    
    async def _init_javascript_runtime(self):
        """Initialize JavaScript runtime"""
        try:
            process = await asyncio.create_subprocess_exec(
                'node', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            if process.returncode != 0:
                raise Exception("Node.js runtime not available")
        except Exception as e:
            raise Exception(f"Failed to initialize JavaScript runtime: {str(e)}")
    
    async def _init_rust_runtime(self):
        """Initialize Rust runtime"""
        try:
            process = await asyncio.create_subprocess_exec(
                'cargo', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            if process.returncode != 0:
                raise Exception("Rust/Cargo runtime not available")
        except Exception as e:
            raise Exception(f"Failed to initialize Rust runtime: {str(e)}")
    
    async def _init_go_runtime(self):
        """Initialize Go runtime"""
        try:
            process = await asyncio.create_subprocess_exec(
                'go', 'version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            if process.returncode != 0:
                raise Exception("Go runtime not available")
        except Exception as e:
            raise Exception(f"Failed to initialize Go runtime: {str(e)}")
    
    async def _init_generic_runtime(self):
        """Initialize generic runtime"""
        # For unsupported languages, we'll just mark as connected
        # but execution will return not implemented errors
        pass
    
    async def _validate_code(self, code: str) -> Dict[str, Any]:
        """Validate code syntax with this PORT's language toolchain"""
        return await asyncio.to_thread(validate_code, code, self.language)
    
    async def _compile_code(self, code: str) -> Dict[str, Any]:
        """Compile code with this PORT's language toolchain"""
        return await asyncio.to_thread(compile_code, code, self.language, self.temp_dir)

class SystemPORT(BasePORT):
    """PORT for system-level operations"""
    
    def __init__(self, config: PortConfig):
        super().__init__(config)
        self.os_type = os.name
        self.platform = sys.platform
    
    async def connect(self) -> bool:
        """Connect to system interfaces"""
        try:
            self.status = PortStatus.CONNECTING
            
            # Initialize system connections
            self.connection = {
                'os': self.os_type,
                'platform': self.platform,
                'capabilities': self._get_system_capabilities()
            }
            
            self.status = PortStatus.ACTIVE
            self.emit_event('connected', {'system': self.platform})
            return True
            
        except Exception as e:
            self.status = PortStatus.ERROR
            logger.error(f"Failed to connect System PORT: {str(e)}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from system interfaces"""
        self.status = PortStatus.DISCONNECTED
        self.connection = None
        return True
    
    async def send_message(self, message: PortMessage) -> Dict[str, Any]:
        """Execute system operation"""
        try:
            payload = message.payload
            operation = payload.get('operation', '')
            
            if operation == 'execute_command':
                return await self._execute_command(payload.get('command', ''))
            elif operation == 'file_operation':
                return await self._file_operation(payload)
            elif operation == 'process_management':
                return await self._process_management(payload)
            elif operation == 'system_info':
                return await self._get_system_info()
            else:
                return {'error': f'Unknown system operation: {operation}'}
                
        except Exception as e:
            self.update_metrics('errors')
            return {'error': str(e)}
    
    async def receive_message(self) -> Optional[PortMessage]:
        """Receive system events"""
        try:
            if not self.message_queue.empty():
                return self.message_queue.get_nowait()
        except queue.Empty:
            pass
        return None
    
    def _get_system_capabilities(self) -> List[str]:
        """Get available system capabilities"""
        capabilities = ['command_execution', 'file_operations', 'system_info']
        
        if self.os_type == 'posix':
            capabilities.extend(['unix_commands', 'shell_access'])
        elif self.os_type == 'nt':
            capabilities.extend(['windows_commands', 'powershell_access'])
        
        return capabilities
    
    async def _execute_command(self, command: str) -> Dict[str, Any]:
        """Execute system command"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                'success': process.returncode == 0,
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8'),
                'return_code': process.returncode,
                'command': command
            }
            
        except Exception as e:
            return {'error': str(e), 'command': command}
    
    async def _file_operation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform file operations"""
        operation = payload.get('file_operation', '')
        path = payload.get('path', '')
        
        try:
            if operation == 'read':
                with open(path, 'r') as f:
                    content = f.read()
                return {'success': True, 'content': content}
            
            elif operation == 'write':
                content = payload.get('content', '')
                with open(path, 'w') as f:
                    f.write(content)
                return {'success': True, 'message': 'File written'}
            
            elif operation == 'exists':
                exists = os.path.exists(path)
                return {'success': True, 'exists': exists}
            
            elif operation == 'list':
                if os.path.isdir(path):
                    files = os.listdir(path)
                    return {'success': True, 'files': files}
                else:
                    return {'error': 'Path is not a directory'}
            
            else:
                return {'error': f'Unknown file operation: {operation}'}
                
        except Exception as e:
            return {'error': str(e)}
    
    async def _process_management(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Manage system processes: list, inspect, sample or signal one"""
        return await asyncio.to_thread(process_management, payload)
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        import platform
        
        return {
            'success': True,
            'system_info': {
                'platform': platform.platform(),
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version()
            }
        }

class NetworkPORT(BasePORT):
    """PORT for network communications"""
    
    def __init__(self, config: PortConfig):
        super().__init__(config)
        self.session = None
    
    async def connect(self) -> bool:
        """Connect to network interfaces"""
        try:
            import aiohttp
            self.session = aiohttp.ClientSession()
            self.status = PortStatus.ACTIVE
            return True
        except Exception as e:
            logger.error(f"Failed to connect Network PORT: {str(e)}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from network interfaces"""
        if self.session:
            await self.session.close()
        self.status = PortStatus.DISCONNECTED
        return True
    
    async def send_message(self, message: PortMessage) -> Dict[str, Any]:
        """Send network request"""
        try:
            payload = message.payload
            method = payload.get('method', 'GET').upper()
            url = payload.get('url', '')
            headers = payload.get('headers', {})
            data = payload.get('data', {})
            
            if not self.session:
                return {'error': 'Network session not initialized'}
            
            async with self.session.request(method, url, headers=headers, json=data) as response:
                response_data = await response.text()
                
                return {
                    'success': response.status < 400,
                    'status_code': response.status,
                    'headers': dict(response.headers),
                    'data': response_data,
                    'url': url,
                    'method': method
                }
                
        except Exception as e:
            return {'error': str(e)}
    
    async def receive_message(self) -> Optional[PortMessage]:
        """Receive network message"""
        # For network PORTs, this could be used for webhooks or real-time data
        return None

class FusionPORTManager:
    """Manager for all Fusion PORTs"""
    
    def __init__(self):
        self.ports = {}
        self.port_configs = {}
        self.message_router = {}
        self.global_metrics = {
            'total_ports': 0,
            'active_ports': 0,
            'total_messages': 0,
            'total_errors': 0
        }
    
    def register_port(self, port_name: str, port: BasePORT):
        """Register a new PORT"""
        self.ports[port_name] = port
        self.port_configs[port_name] = port.config
        self.global_metrics['total_ports'] += 1
        
        # Register event handlers
        port.register_event_handler('connected', self._on_port_connected)
        port.register_event_handler('disconnected', self._on_port_disconnected)
        port.register_event_handler('error', self._on_port_error)
        
        logger.info(f"PORT registered: {port_name}")
    
    async def connect_port(self, port_name: str) -> bool:
        """Connect a specific PORT"""
        if port_name in self.ports:
            success = await self.ports[port_name].connect()
            if success:
                self.global_metrics['active_ports'] += 1
            return success
        return False
    
    async def disconnect_port(self, port_name: str) -> bool:
        """Disconnect a specific PORT"""
        if port_name in self.ports:
            success = await self.ports[port_name].disconnect()
            if success and self.ports[port_name].status == PortStatus.ACTIVE:
                self.global_metrics['active_ports'] -= 1
            return success
        return False
    
    async def connect_all_ports(self) -> Dict[str, bool]:
        """Connect all registered PORTs"""
        results = {}
        for port_name in self.ports:
            results[port_name] = await self.connect_port(port_name)
        return results
    
    async def disconnect_all_ports(self) -> Dict[str, bool]:
        """Disconnect all PORTs"""
        results = {}
        for port_name in self.ports:
            results[port_name] = await self.disconnect_port(port_name)
        return results
    
    async def send_message(self, port_name: str, message: PortMessage) -> Dict[str, Any]:
        """Send message through specific PORT"""
        if port_name in self.ports:
            port = self.ports[port_name]
            if port.status == PortStatus.ACTIVE:
                result = await port.send_message(message)
                self.global_metrics['total_messages'] += 1
                return result
            else:
                return {'error': f'PORT {port_name} is not active'}
        else:
            return {'error': f'PORT {port_name} not found'}
    
    async def broadcast_message(self, message: PortMessage, port_types: List[PortType] = None) -> Dict[str, Any]:
        """Broadcast message to multiple PORTs"""
        results = {}
        
        for port_name, port in self.ports.items():
            if port_types and port.config.port_type not in port_types:
                continue
            
            if port.status == PortStatus.ACTIVE:
                results[port_name] = await port.send_message(message)
            else:
                results[port_name] = {'error': 'PORT not active'}
        
        return results
    
    def get_port_status(self, port_name: str = None) -> Dict[str, Any]:
        """Get status of specific PORT or all PORTs"""
        if port_name:
            if port_name in self.ports:
                port = self.ports[port_name]
                return {
                    'name': port_name,
                    'type': port.config.port_type.value,
                    'status': port.status.value,
                    'capabilities': port.config.capabilities,
                    'metrics': port.metrics
                }
            else:
                return {'error': f'PORT {port_name} not found'}
        else:
            status = {}
            for name, port in self.ports.items():
                status[name] = {
                    'type': port.config.port_type.value,
                    'status': port.status.value,
                    'capabilities': port.config.capabilities,
                    'metrics': port.metrics
                }
            return status
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global PORT system metrics"""
        return {
            **self.global_metrics,
            'port_details': {name: port.metrics for name, port in self.ports.items()}
        }
    
    def _on_port_connected(self, data: Dict[str, Any]):
        """Handle PORT connected event"""
        logger.info(f"PORT connected: {data}")
    
    def _on_port_disconnected(self, data: Dict[str, Any]):
        """Handle PORT disconnected event"""
        logger.info(f"PORT disconnected: {data}")
    
    def _on_port_error(self, data: Dict[str, Any]):
        """Handle PORT error event"""
        logger.error(f"PORT error: {data}")
        self.global_metrics['total_errors'] += 1

# Global Fusion PORT Manager instance
fusion_port_manager = FusionPORTManager()

# Initialize default PORTs
def initialize_default_ports():
    """Initialize default PORTs for common languages and systems"""
    
    # Language PORTs
    languages = [
        ('python', sys.executable),
        ('javascript', 'node'),
        ('rust', 'cargo'),
        ('go', 'go')
    ]
    
    for lang, runtime in languages:
        config = PortConfig(
            name=f"{lang}_port",
            port_type=PortType.LANGUAGE,
            capabilities=[f"{lang}_execution", "code_validation", "syntax_checking"],
            connection_params={'runtime': runtime}
        )
        port = LanguagePORT(config, lang, runtime)
        fusion_port_manager.register_port(f"{lang}_port", port)
    
    # System PORT
    system_config = PortConfig(
        name="system_port",
        port_type=PortType.SYSTEM,
        capabilities=["command_execution", "file_operations", "process_management"],
        connection_params={}
    )
    system_port = SystemPORT(system_config)
    fusion_port_manager.register_port("system_port", system_port)
    
    # Network PORT
    network_config = PortConfig(
        name="network_port",
        port_type=PortType.NETWORK,
        capabilities=["http_requests", "api_calls", "web_scraping"],
        connection_params={}
    )
    network_port = NetworkPORT(network_config)
    fusion_port_manager.register_port("network_port", network_port)

# Initialize default PORTs when module is imported
initialize_default_ports()

