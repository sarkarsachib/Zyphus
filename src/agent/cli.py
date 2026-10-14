"""CLI for the agent layer: `python src/main.py agent ...`."""

import json
import time

import click

from src.agent.loop import get_loop
from src.agent.tools import build_registry


@click.group()
def agent():
    """Autonomous agent: real tools plus a durable task loop."""


@agent.command("status")
def status_cmd():
    """Show loop state, queue counts and the most recent tool calls."""
    state = get_loop().status()
    queue = state["queue"]
    click.echo(click.style("--- Zyphus agent ---", fg="cyan"))
    click.echo(f"running:      {state['running']}")
    click.echo(f"brain:        {state['brain']}")
    click.echo(f"ticks:        {state['ticks']} (last {state['last_tick_at']})")
    click.echo(f"interval:     {state['interval_seconds']:.0f}s, self-directed every "
               f"{state['self_interval_seconds']:.0f}s")
    click.echo(f"queue:        {queue['pending']} pending, {queue['running']} running, "
               f"{queue['done']} done, {queue['failed']} failed")
    click.echo(f"state file:   {state['queue_path']}")
    click.echo(f"tools:        {', '.join(t['name'] for t in state['tools'])}")
    click.echo(click.style("\n--- Recent tool calls ---", fg="cyan"))
    for action in state["recent_actions"]:
        flag = click.style("ok  ", fg="green") if action["ok"] else click.style("fail", fg="red")
        args = json.dumps(action["arguments"], default=str)
        click.echo(f"{action['created_at']}  {flag} {action['tool']:<14} {args[:110]}")


@agent.command("tools")
def tools_cmd():
    """List the tools the agent can call."""
    for tool in build_registry().catalog():
        click.echo(click.style(tool["name"], fg="cyan") + f" - {tool['description']}")
        for name, note in tool["parameters"].items():
            click.echo(f"    {name}: {note}")


@agent.command("tasks")
def tasks_cmd():
    """List queued and finished tasks."""
    for task in get_loop().store.list_tasks(30):
        click.echo(f"{task['id']}  {task['status']:<8} {task['origin']:<8} {task['title']}")


@agent.command("run")
@click.argument("instructions")
@click.option("--title", default=None, help="Label for the task (defaults to the instructions).")
def run_cmd(instructions, title):
    """Queue a task and run one tick on it."""
    loop = get_loop()
    task_id = loop.store.enqueue(title or instructions[:60], instructions)
    result = loop.tick()
    click.echo(f"task {task_id}: {json.dumps(result, indent=2, default=str)}")


@agent.command("tick")
def tick_cmd():
    """Run a single tick of the loop."""
    click.echo(json.dumps(get_loop().tick(), indent=2, default=str))


@agent.command("forever")
@click.option("--interval", default=None, type=float, help="Seconds between ticks.")
def forever_cmd(interval):
    """Run the loop until interrupted."""
    loop = get_loop()
    if interval:
        loop.interval = interval
    click.echo(f"agent loop running every {loop.interval:.0f}s - Ctrl-C to stop")
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.stop()
        click.echo("agent loop stopped")
