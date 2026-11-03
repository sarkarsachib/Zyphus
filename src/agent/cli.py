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


@agent.command("field")
def field_cmd():
    """Show the cognitive field: regimes, coalitions, cells and self-model."""
    from src.agent.field import summarize

    brain = get_loop().brain
    snapshot = brain.snapshot() if hasattr(brain, "snapshot") else None
    if not snapshot:
        click.echo(f"brain {brain.name} keeps no field")
        return
    click.echo(click.style("--- Cognitive field ---", fg="cyan"))
    click.echo(f"regime:      {snapshot['regime']}"
               + (f" (from {snapshot['previous_regime']})"
                  if snapshot.get("previous_regime") else ""))
    click.echo(f"dominance:   {snapshot['dominance']:.2f}")
    click.echo(f"cells:       {snapshot['cell_count']}  generation "
               f"{snapshot['morphogenesis']['generation']}  steps {snapshot['steps']}")
    for line in summarize(snapshot):
        click.echo("  " + line)
    click.echo(click.style("\ncompeting coalitions", fg="cyan"))
    for coalition in snapshot["coalitions"]:
        members = ", ".join(coalition["cells"]) or "none active"
        click.echo(f"  {coalition['regime']:<12} energy {coalition['energy']:.2f}  mean "
                   f"{coalition['mean']:.2f}  {members}")
    click.echo(click.style("\nsignals", fg="cyan"))
    for name, value in snapshot["signals"].items():
        click.echo(f"  {name:<12} {value:.2f}")
    meta = snapshot["metacognition"]
    click.echo(click.style(f"\nmetacognition (surprise {meta['surprise']:.2f})", fg="cyan"))
    for regime, stats in meta["calibration"].items():
        click.echo(f"  {regime:<12} attempts {stats['attempts']:<3} confidence "
                   f"{stats['confidence']:.2f} gain {stats['gain']:.2f} "
                   f"error {stats['mean_error']:.2f}")
    events = snapshot["morphogenesis"]["events"]
    if events:
        click.echo(click.style("\nlast morphogenesis", fg="cyan"))
        for event in events:
            detail = event.get("from") or event.get("into") or ""
            click.echo(f"  {event.get('at', '')}  {event.get('type', ''):<6} "
                       f"{event.get('cell', '')} {detail}".rstrip())


@agent.command("morph")
def morph_cmd():
    """Restructure the field now: split overloaded cells, merge unused branches."""
    brain = get_loop().brain
    field = getattr(brain, "field", None)
    if field is None:
        click.echo(f"brain {brain.name} keeps no field")
        return
    report = field.morph()
    field.save()
    click.echo(click.style(f"--- Morphogenesis (generation {report['generation']}) ---", fg="cyan"))
    click.echo(f"cells: {report['cells']}")
    for event in report["events"]:
        detail = event.get("from") or event.get("into") or ""
        click.echo(f"  {event.get('type', ''):<6} {event.get('cell', '')} {detail}".rstrip())
    if not report["events"]:
        click.echo("  no structural change warranted")


@agent.command("consolidate")
@click.option("--window", default=60, type=int, help="Recent tool calls to replay.")
@click.option("--dry-run", is_flag=True, help="Compute the pass without writing anything.")
def consolidate_cmd(window, dry_run):
    """Replay measured experience and promote what it measured into structure."""
    phase = get_loop().consolidation()
    report = phase.run(window=window, dry_run=dry_run)
    click.echo(click.style("--- Consolidation " + ("(dry run) ---" if dry_run else "---"), fg="cyan"))
    click.echo(f"replayed:   {report['replayed']} tool call(s), window {report['window']}")
    click.echo(f"promoted:   {', '.join(report['promoted']) or 'none'}")
    click.echo(f"weak:       {', '.join(report['weak']) or 'none'}")
    for record in report["tools"]:
        click.echo(f"  {record['tool']:<14} {record['successes']}/{record['attempts']} ok"
                   f"  rate {record['success_rate']:.2f}  {record['mean_ms']:.0f}ms")
    if dry_run:
        click.echo(click.style("nothing written", fg="yellow"))
    else:
        click.echo(f"pass {phase.passes()} recorded in {phase.path} "
                   f"({report['duration_ms']}ms)")


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
