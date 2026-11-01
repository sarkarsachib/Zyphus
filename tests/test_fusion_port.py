"""Tests for the fusion PORT validators, compilers and process management."""

import asyncio
import os
import subprocess
import sys

import pytest

from src import fusion_port


def _port(language: str, runtime: str = "") -> "fusion_port.LanguagePORT":
    config = fusion_port.PortConfig(name=f"{language}_port",
                                    port_type=fusion_port.PortType.LANGUAGE,
                                    capabilities=[], connection_params={})
    return fusion_port.LanguagePORT(config, language, runtime or language)


def test_python_validation_reports_real_syntax_error():
    assert fusion_port.validate_code("print('ok')", "python")["valid"] is True
    broken = fusion_port.validate_code("def broken(:\n    pass", "python")
    assert broken["valid"] is False
    assert broken["line"] == 1


def test_javascript_validation_when_node_is_available():
    if not fusion_port._tool("node"):
        pytest.skip("node is not installed")
    assert fusion_port.validate_code("export const x = 1;", "javascript")["valid"] is True
    assert fusion_port.validate_code("export const = ;", "javascript")["valid"] is False


def test_missing_toolchain_is_unavailable_not_a_fake_pass():
    result = fusion_port.validate_code("fn main() {}", "rust")
    if fusion_port._tool("rustc"):
        assert result["available"] is True
    else:
        assert result["available"] is False
        assert result["valid"] is None
        assert "not installed" in result["message"]


def test_unknown_language_is_reported_not_assumed_valid():
    result = fusion_port.validate_code("whatever", "brainfuck")
    assert result["available"] is False
    assert result["valid"] is None


def test_compile_python_writes_bytecode(tmp_path):
    result = fusion_port.compile_code("value = 1\n", "python", str(tmp_path))
    assert result["compiled"] is True
    assert os.path.exists(result["artifact"])
    assert result["bytes"] > 0


def test_compile_python_reports_syntax_error(tmp_path):
    result = fusion_port.compile_code("def nope(:\n", "python", str(tmp_path))
    assert result["compiled"] is False


def test_language_port_uses_the_real_checker():
    result = asyncio.run(_port("python")._validate_code("x = 1"))
    assert result["valid"] is True


def test_list_processes_contains_this_process():
    data = fusion_port.list_processes(limit=500)
    assert data["ok"] is True
    assert data["count"] > 0
    assert os.getpid() in [entry["pid"] for entry in data["processes"]]


def test_process_info_for_self():
    info = fusion_port.process_info(os.getpid())
    assert info["ok"] is True
    assert info["pid"] == os.getpid()
    assert info["memory_mb"] > 0
    assert info["state"]


def test_process_info_for_missing_pid():
    assert fusion_port.process_info(999999)["ok"] is False


def test_monitor_process_samples_cpu():
    result = fusion_port.monitor_process(os.getpid(), interval=0.1)
    assert result["ok"] is True
    assert result["cpu_percent"] >= 0.0


def test_signal_process_terminates_a_child():
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        result = fusion_port.signal_process(child.pid, "TERM")
        assert result["ok"] is True
        assert result["running"] is False
    finally:
        if child.poll() is None:
            child.kill()
        child.wait()


def test_process_management_dispatches_and_rejects_unknown():
    assert fusion_port.process_management({"action": "info", "pid": os.getpid()})["pid"] == os.getpid()
    assert fusion_port.process_management({"action": "nope"})["ok"] is False


def test_system_port_process_management_is_wired():
    config = fusion_port.PortConfig(name="system_port", port_type=fusion_port.PortType.SYSTEM,
                                    capabilities=[], connection_params={})
    port = fusion_port.SystemPORT(config)
    result = asyncio.run(port._process_management({"action": "info", "pid": os.getpid()}))
    assert result["ok"] is True
