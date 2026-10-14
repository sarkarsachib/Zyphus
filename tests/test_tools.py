"""Tests for the real tool layer."""

from src.agent.tools import ToolRegistry, build_registry, run_shell, read_file, write_file, list_dir


def test_run_shell_success():
    result = run_shell("echo hello")
    assert result.ok
    assert "hello" in result.output


def test_run_shell_failure():
    result = run_shell("exit 42")
    assert not result.ok
    assert "42" in result.error


def test_run_shell_timeout():
    result = run_shell("sleep 5", timeout=0.5)
    assert not result.ok
    assert "timed out" in result.error


def test_read_file_missing():
    result = read_file("/no/such/file/here")
    assert not result.ok


def test_write_and_read_file(tmp_path):
    target = str(tmp_path / "test.txt")
    w = write_file(target, "hello world")
    assert w.ok
    r = read_file(target)
    assert r.ok
    assert "hello world" in r.output


def test_list_dir(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "sub").mkdir()
    result = list_dir(str(tmp_path))
    assert result.ok
    assert "a.txt" in result.output
    assert "sub" in result.output


def test_registry_catalog():
    reg = build_registry()
    catalog = reg.catalog()
    names = [t["name"] for t in catalog]
    assert "run_shell" in names
    assert "read_file" in names
    assert "write_file" in names


def test_registry_unknown_tool():
    reg = build_registry()
    result = reg.run("nonexistent", {})
    assert not result.ok
    assert "unknown tool" in result.error


def test_registry_bad_arguments():
    reg = build_registry()
    result = reg.run("run_shell", {"unexpected_arg": 42})
    assert not result.ok
