"""Tests for the agent's durable store: task queue + action log."""

import os
import tempfile

from src.agent.store import AgentStore


def _fresh_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return AgentStore(path=path, lease_seconds=1.0), path


def test_enqueue_and_claim():
    store, _ = _fresh_store()
    task_id = store.enqueue("test", "shell: echo hi")
    task = store.claim_next()
    assert task is not None
    assert task["id"] == task_id
    assert task["status"] == "pending"  # row status before claim was pending
    assert task["attempts"] == 1  # claimed bumps attempts


def test_claim_returns_none_when_empty():
    store, _ = _fresh_store()
    assert store.claim_next() is None


def test_complete_task():
    store, _ = _fresh_store()
    task_id = store.enqueue("done test", "vitals")
    store.claim_next()
    store.complete(task_id, "all good")
    counts = store.counts()
    assert counts["done"] == 1
    assert counts["pending"] == 0


def test_fail_then_retry_then_exhaust():
    store, _ = _fresh_store()
    task_id = store.enqueue("fail test", "shell: false")
    # default max_attempts is 3; need to claim+fail 3 times.
    # Use retry_delay=0 so the task is immediately re-claimable.
    for _ in range(3):
        store.claim_next()
        result = store.fail(task_id, "boom", retry_delay=0.0)
    assert result == "failed"
    assert store.counts()["failed"] == 1


def test_log_action():
    store, _ = _fresh_store()
    store.log_action(None, "run_shell", {"command": "echo hi"}, True, "hi\n", "", 5)
    actions = store.recent_actions(5)
    assert len(actions) == 1
    assert actions[0]["tool"] == "run_shell"
    assert actions[0]["ok"] == 1


def test_counts():
    store, _ = _fresh_store()
    store.enqueue("a", "vitals")
    store.enqueue("b", "vitals")
    counts = store.counts()
    assert counts["pending"] == 2
    assert counts["done"] == 0
