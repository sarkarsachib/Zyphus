"""
The emergent cognitive field.

The decision layer used to be four attractors that were coupled to signals.
This module replaces that with a *population*. Distributed cognitive cells each
carry one small capability; cells recruit and suppress each other over a
learned topology, and the cells that are active at a given moment form a
coalition. Three regimes are not chosen anywhere - they are the names of the
coalitions that win:

    diffuse      many weakly active cells: spread activation, associate, look
    structural   composing cells dominate: build a structure before acting
    convergent   the coalition narrows: commit to the strongest candidate

Nothing branches on task text and nothing rotates. Excitation comes from the
perceived signals (task, backlog, novelty, uncertainty, surprise, stagnation,
competence, fatigue) and from the cells' own links; suppression comes from the
rival coalitions (`LATERAL`) and from a cell's own use (`SATIATION`). The field
also has a spontaneous tone, so it keeps evolving between tasks instead of
freezing until the next perception.

`morph()` is early cognitive morphogenesis: a cell that is carrying too much
activation splits into a branch, a branch that stopped being used is merged
back, and links that fire together are strengthened while unused ones are
pruned. The topology is therefore part of the state - the brain can restructure
its own thinking architecture, and the change survives a restart.

Stdlib only and deterministic: the same state and the same elapsed time always
produce the same field.
"""

import json
import math
import os
import time
from typing import Any, Dict, Iterable, List, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_PATH = os.path.join(REPO_ROOT, "devmind", "agent", "field.json")

REGIMES = ("diffuse", "structural", "convergent")

SIGNALS = ("task", "backlog", "novelty", "uncertainty", "surprise",
           "stagnation", "competence", "fatigue")

# Excitation (+) and suppression (-) each signal applies to a regime's cells.
# These numbers are the architecture: change one and the behaviour changes.
REGIME_COUPLING = {
    "diffuse": {"novelty": 0.90, "uncertainty": 0.70, "surprise": 0.50,
                "task": -0.35, "competence": -0.15, "fatigue": -0.20},
    "structural": {"task": 0.55, "backlog": 0.50, "uncertainty": 0.50,
                   "novelty": 0.45, "stagnation": 0.30, "surprise": 0.35,
                   "fatigue": -0.15},
    "convergent": {"competence": 0.60, "task": 0.45, "fatigue": 0.50,
                   "stagnation": 0.45, "uncertainty": -0.35, "novelty": -0.35},
}

# The starting population. Every cell carries one capability and a small extra
# affinity for the signals that should recruit it inside its regime.
CELL_SEEDS = (
    {"name": "scan", "regime": "diffuse", "kind": "sensing", "capability": "probe",
     "affinity": {"novelty": 0.15}},
    {"name": "associate", "regime": "diffuse", "kind": "associative",
     "capability": "retrieval", "affinity": {"novelty": 0.10, "uncertainty": 0.10}},
    {"name": "wander", "regime": "diffuse", "kind": "sensing", "capability": "probe",
     "affinity": {"novelty": 0.20}},
    {"name": "compose", "regime": "structural", "kind": "planning", "capability": "planner",
     "affinity": {"task": 0.15, "backlog": 0.10}},
    {"name": "frame", "regime": "structural", "kind": "associative", "capability": "model",
     "affinity": {"uncertainty": 0.15}},
    {"name": "ground", "regime": "structural", "kind": "memory", "capability": "retrieval",
     "affinity": {"task": 0.10, "uncertainty": 0.10}},
    {"name": "commit", "regime": "convergent", "kind": "execution", "capability": "planner",
     "affinity": {"task": 0.15, "competence": 0.10}},
    {"name": "verify", "regime": "convergent", "kind": "verification", "capability": "verify",
     "affinity": {"fatigue": 0.15, "stagnation": 0.10}},
    {"name": "inhibit", "regime": "convergent", "kind": "inhibitory",
     "capability": "consolidate", "affinity": {"fatigue": 0.20}},
)

TAU = 0.60             # seconds for a cell to reach 63% of its target
STEP_SECONDS = 0.25    # integration step
HORIZON_SECONDS = 1.5  # field time one perception always integrates
MAX_HORIZON = 12.0     # ceiling, so a long sleep cannot overshoot in one jump
LATERAL = 0.45         # how much the leading rival coalition suppresses a regime
SATIATION = 0.50       # how much a tired cell loses of its drive
TONE = 0.05            # spontaneous baseline, so the field never freezes
TONE_PERIOD = 60.0     # seconds for the resting field to drift once around
TONE_OFFSET = {"diffuse": 0.25, "structural": 0.25 - 1.0 / 3.0,
               "convergent": 0.25 - 2.0 / 3.0}
HYSTERESIS = 0.05      # coalition-energy lead a rival needs to take the field
ACTIVE_THRESHOLD = 0.12  # a cell below this is not part of a coalition
MORPH_EVERY = 32       # steps between automatic restructuring passes
MAX_CELLS = len(CELL_SEEDS) + 6  # the population may grow, but only by a bounded budget
MAX_LINKS = 6          # links a single cell may hold
LINK_FLOOR = 0.02      # weaker links are pruned
PLASTICITY = 0.04      # how fast co-activation changes a link
MERGE_FLOOR = 0.05     # a branch below this may be merged back
TRANSITIONS_KEPT = 24
MORPH_LOG_KEPT = 20


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def clamp01(value: float) -> float:
    return _clamp(float(value), 0.0, 1.0)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


class Cell:
    """One small capability, activated by the signals its regime listens to."""

    def __init__(self, name: str, regime: str, kind: str, capability: str,
                 activation: float = 0.0, satiation: float = 0.0, gain: float = 1.0,
                 affinity: Optional[Dict[str, float]] = None,
                 links: Optional[Dict[str, float]] = None,
                 load: float = 0.0):
        self.name = name
        self.regime = regime if regime in REGIMES else REGIMES[0]
        self.kind = kind or "generic"
        self.capability = capability or ""
        self.activation = clamp01(activation)
        self.satiation = _clamp(float(satiation), 0.0, 0.9)
        self.gain = _clamp(float(gain), 0.5, 1.6)
        self.affinity = {str(key): float(value) for key, value in (affinity or {}).items()
                         if key in SIGNALS}
        self.links = {str(key): _clamp(float(value), -1.0, 1.0)
                      for key, value in (links or {}).items() if str(key) != name}
        self.load = max(0.0, float(load))

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "regime": self.regime, "kind": self.kind,
                "capability": self.capability,
                "activation": round(self.activation, 6),
                "satiation": round(self.satiation, 6), "gain": round(self.gain, 4),
                "affinity": dict(self.affinity),
                "links": {key: round(value, 4) for key, value in self.links.items()},
                "load": round(self.load, 4)}

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Cell":
        return cls(str(raw.get("name") or "cell"), str(raw.get("regime") or REGIMES[0]),
                   str(raw.get("kind") or "generic"), str(raw.get("capability") or ""),
                   float(raw.get("activation", 0.0) or 0.0),
                   float(raw.get("satiation", 0.0) or 0.0),
                   float(raw.get("gain", 1.0) or 1.0),
                   raw.get("affinity") or {}, raw.get("links") or {},
                   float(raw.get("load", 0.0) or 0.0))


def default_cells() -> Dict[str, Cell]:
    """The starting population, with forward recruitment and lateral inhibition."""
    cells = {seed["name"]: Cell(seed["name"], seed["regime"], seed["kind"],
                                seed["capability"], affinity=dict(seed["affinity"]))
             for seed in CELL_SEEDS}
    rank = {regime: index for index, regime in enumerate(REGIMES)}
    for source in cells.values():
        for target in cells.values():
            if source.name == target.name:
                continue
            if source.kind == "inhibitory" and source.regime != target.regime:
                weight = -0.22         # the inhibitory cell silences the rival coalitions
            elif source.regime == target.regime:
                weight = 0.12          # cells of one coalition hold together
            elif rank[target.regime] == rank[source.regime] + 1:
                weight = 0.07          # a broad coalition recruits the narrower one
            elif rank[target.regime] == rank[source.regime] - 1:
                weight = -0.10         # committing suppresses further composition
            elif source.regime == "diffuse":
                weight = 0.05          # diffuse activation reaches commitment weakly
            else:
                weight = -0.08         # commitment silences diffusion
            if weight:
                source.links[target.name] = weight
    return cells


class Metacognition:
    """The field's model of its own reliability, and the error in that model."""

    def __init__(self, state: Optional[Dict[str, Any]] = None):
        self.gain = {name: 1.0 for name in REGIMES}
        self.attempts = {name: 0 for name in REGIMES}
        self.successes = {name: 0 for name in REGIMES}
        self.abs_error = {name: 0.0 for name in REGIMES}
        self.surprise = 0.0
        self.pending: Optional[tuple] = None
        if state:
            self.restore(state)

    # --- beliefs about itself ------------------------------------------------

    def confidence(self, regime: str) -> float:
        """This regime's success rate, shrunk toward 0.5 until it has evidence."""
        if regime not in self.gain:
            return 0.5
        return round((self.successes[regime] + 1.0) / (self.attempts[regime] + 2.0), 4)

    def predict(self, regime: str, confidence: Optional[float] = None) -> tuple:
        """Commit to a regime and how well it expects to do - before it acts."""
        regime = regime if regime in self.gain else REGIMES[0]
        stated = self.confidence(regime) if confidence is None else clamp01(confidence)
        self.pending = (regime, round(stated, 4))
        return self.pending

    def resolve(self, success: bool) -> Dict[str, Any]:
        """Score the pending prediction against what actually happened."""
        if self.pending is None:
            return {}
        regime, stated = self.pending
        self.pending = None
        outcome = 1.0 if success else 0.0
        error = abs(outcome - stated)

        self.surprise = round(0.6 * self.surprise + 0.4 * error, 4)
        self.attempts[regime] += 1
        self.successes[regime] += 1 if success else 0
        self.abs_error[regime] += error
        # A regime that keeps missing its own forecast loses its pull on the field.
        self.gain[regime] = round(_clamp(self.gain[regime] + 0.25 * (outcome - stated),
                                         0.5, 1.6), 4)
        return {"regime": regime, "predicted": stated, "error": round(error, 4),
                "surprise": self.surprise, "gain": self.gain[regime]}

    def calibration(self) -> Dict[str, Dict[str, Any]]:
        out = {}
        for regime in REGIMES:
            attempts = self.attempts[regime]
            out[regime] = {
                "attempts": attempts,
                "confidence": self.confidence(regime),
                "mean_error": round(self.abs_error[regime] / attempts, 4) if attempts else 0.0,
                "gain": self.gain[regime],
            }
        return out

    # --- persistence ---------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {"gain": dict(self.gain), "attempts": dict(self.attempts),
                "successes": dict(self.successes), "abs_error": dict(self.abs_error),
                "surprise": self.surprise}

    def restore(self, state: Dict[str, Any]) -> None:
        for regime in REGIMES:
            self.gain[regime] = _clamp(float((state.get("gain") or {}).get(regime, 1.0)),
                                       0.5, 1.6)
            self.attempts[regime] = max(0, int((state.get("attempts") or {}).get(regime, 0)))
            self.successes[regime] = max(0, int((state.get("successes") or {}).get(regime, 0)))
            self.abs_error[regime] = max(0.0, float((state.get("abs_error") or {}).get(regime, 0.0)))
        self.surprise = clamp01(state.get("surprise", 0.0))


class CognitiveField:
    """A population of cells that keeps running: perceive, integrate, restructure."""

    def __init__(self, path: Optional[str] = None, autoload: bool = False,
                 auto_morph: bool = True):
        self.path = path or os.environ.get("ZYPHUS_FIELD_PATH") or DEFAULT_PATH
        self.cells: Dict[str, Cell] = default_cells()
        self.signals = {name: 0.0 for name in SIGNALS}
        self.metacognition = Metacognition()
        self.regime = REGIMES[0]
        self.previous_regime: Optional[str] = None
        self.steps = 0
        self.clock = 0.0
        self.generation = 0
        self.auto_morph = auto_morph
        self.updated_at = ""
        self.transitions: List[Dict[str, Any]] = []
        self.morph_log: List[Dict[str, Any]] = []
        if autoload:
            self.load()

    # --- perception ----------------------------------------------------------

    def perceive(self, signals: Dict[str, Any]) -> Dict[str, float]:
        """Take the current reading of the situation. Absent signals read as zero."""
        for name in SIGNALS:
            self.signals[name] = round(clamp01(signals.get(name, 0.0) or 0.0), 4)
        return dict(self.signals)

    # --- reading the population ---------------------------------------------

    @property
    def activation(self) -> Dict[str, float]:
        """Mean activation per regime - what the dashboard draws as bars."""
        return self.regime_activation()

    def regime_activation(self) -> Dict[str, float]:
        out = {}
        for regime in REGIMES:
            members = [cell for cell in self.cells.values() if cell.regime == regime]
            mean = sum(cell.activation for cell in members) / len(members) if members else 0.0
            out[regime] = round(mean, 4)
        return out

    def regime_energy(self) -> Dict[str, float]:
        """Total activation each coalition holds - the quantity they compete with."""
        out = {}
        for regime in REGIMES:
            members = [cell for cell in self.cells.values() if cell.regime == regime]
            out[regime] = round(sum(cell.activation * cell.gain for cell in members), 4)
        return out

    def coalition_energy(self, regime: str) -> float:
        return float(self.regime_energy().get(regime, 0.0))

    def coalitions(self) -> List[Dict[str, Any]]:
        """The competing coalitions, strongest first - active cells grouped by regime."""
        out = []
        for regime in REGIMES:
            members = [cell for cell in self.cells.values() if cell.regime == regime]
            active = sorted((cell for cell in members if cell.activation >= ACTIVE_THRESHOLD),
                            key=lambda cell: -cell.activation)
            energy = sum(cell.activation * cell.gain for cell in active)
            out.append({
                "regime": regime,
                "cells": [cell.name for cell in active],
                "active": len(active),
                "energy": round(energy, 4),
                "mean": round(sum(cell.activation for cell in members) / len(members), 4)
                if members else 0.0,
            })
        out.sort(key=lambda entry: (-entry["energy"], REGIMES.index(entry["regime"])))
        return out

    def coalition(self) -> Dict[str, Any]:
        """The coalition that currently holds the field."""
        for entry in self.coalitions():
            if entry["cells"]:
                return entry
        return {"regime": self.regime, "cells": [], "active": 0, "energy": 0.0, "mean": 0.0}

    def cell_for(self, capability: str) -> Optional[Cell]:
        """The strongest cell offering a capability - how the brain recruits one."""
        candidates = [cell for cell in self.cells.values() if cell.capability == capability]
        if not candidates:
            return None
        return max(candidates, key=lambda cell: cell.activation * cell.gain)

    def recruited(self, capability: str, threshold: float = ACTIVE_THRESHOLD) -> bool:
        cell = self.cell_for(capability)
        return bool(cell and cell.activation >= threshold)

    # --- dynamics ------------------------------------------------------------

    def step(self, seconds: Optional[float] = None) -> str:
        """Integrate the field and return the regime the winning coalition names."""
        horizon = HORIZON_SECONDS if seconds is None else _clamp(float(seconds),
                                                                 STEP_SECONDS, MAX_HORIZON)
        substeps = max(1, int(round(horizon / STEP_SECONDS)))
        for _ in range(substeps):
            self.clock += STEP_SECONDS
            self._integrate()
        self.steps += 1
        self.updated_at = _now_iso()
        self._plastic()
        if self.auto_morph and self.steps % MORPH_EVERY == 0:
            self.morph()
        return self.regime

    def evolve(self, seconds: Optional[float] = None) -> str:
        """Keep the field moving when no task is arriving. Same dynamics, no percepts."""
        return self.step(seconds)

    def _integrate(self) -> None:
        energies = self.regime_energy()
        leader = self._leader(energies)
        potentials = self._potentials()
        fraction = min(1.0, STEP_SECONDS / TAU)

        for name in sorted(self.cells):
            cell = self.cells[name]
            drive = self._drive(cell)
            recruit = 0.0
            inhibit = 0.0
            for target_name, weight in cell.links.items():
                target = self.cells.get(target_name)
                if target is None:
                    continue
                if weight > 0:
                    recruit += weight * target.activation
                else:
                    inhibit += -weight * target.activation
            # The coalitions compete on how well they fit the situation, so the
            # best-fitting one silences the others instead of everyone saturating.
            rival = max((potentials[other] for other in REGIMES if other != cell.regime),
                        default=0.0)
            lateral = LATERAL * max(0.0, rival - potentials[cell.regime])
            tone = self._tone(cell.regime)

            target_value = clamp01(drive * (1.0 - SATIATION * cell.satiation)
                                   + recruit + tone - inhibit - lateral)
            cell.activation = round(clamp01(
                cell.activation + fraction * (target_value - cell.activation)), 6)
            cell.load = round(min(60.0, cell.load + cell.activation * STEP_SECONDS), 4)

        for cell in self.cells.values():
            if cell.activation > 0.5:
                cell.satiation = _clamp(cell.satiation + 0.12 * STEP_SECONDS, 0.0, 0.9)
            else:
                cell.satiation = _clamp(cell.satiation - 0.06 * STEP_SECONDS, 0.0, 0.9)

        self._settle_regime(leader, energies)

    def _drive(self, cell: Cell) -> float:
        coupling = dict(REGIME_COUPLING.get(cell.regime, {}))
        for signal, weight in cell.affinity.items():
            coupling[signal] = coupling.get(signal, 0.0) + weight
        drive = sum(self.signals.get(signal, 0.0) * weight
                    for signal, weight in coupling.items())
        return max(0.0, drive) * cell.gain * self.metacognition.gain.get(cell.regime, 1.0)

    def _potentials(self) -> Dict[str, float]:
        """How well each coalition's cells fit the current signals, before any
        recruitment. This is what the coalitions compete on."""
        out = {}
        for regime in REGIMES:
            members = [cell for cell in self.cells.values() if cell.regime == regime]
            out[regime] = (sum(self._drive(cell) for cell in members) / len(members)
                           if members else 0.0)
        return out

    def _tone(self, regime: str) -> float:
        """Spontaneous activity: the resting field drifts instead of freezing."""
        phase = self.clock / TONE_PERIOD + TONE_OFFSET.get(regime, 0.0)
        return TONE * (0.5 + 0.5 * math.sin(2.0 * math.pi * phase))

    @staticmethod
    def _leader(energies: Dict[str, float]) -> str:
        best = REGIMES[0]
        for regime in REGIMES:
            if energies[regime] > energies[best] + 1e-12:
                best = regime
        return best

    def _settle_regime(self, leader: str, energies: Dict[str, float]) -> None:
        """Switch only on a clear coalition margin, so the field does not flicker.

        The comparison is on coalition energy, the same quantity the dashboard
        ranks, so the regime that is named is always the strongest coalition.
        """
        if leader == self.regime:
            return
        if energies[leader] <= energies[self.regime] + HYSTERESIS:
            return
        self.previous_regime = self.regime
        self.regime = leader
        coalition = self.coalition()
        self.transitions.append({
            "at": _now_iso(),
            "from": self.previous_regime,
            "to": leader,
            "energy": {name: round(value, 4) for name, value in energies.items()},
            "coalition": coalition["cells"] if coalition else [],
        })
        del self.transitions[:-TRANSITIONS_KEPT]

    # --- morphogenesis -------------------------------------------------------

    def _plastic(self) -> None:
        """Hebbian: cells that fire together wire together, unused links fade."""
        for name in sorted(self.cells):
            cell = self.cells[name]
            for target_name in sorted(cell.links):
                target = self.cells.get(target_name)
                if target is None:
                    del cell.links[target_name]
                    continue
                weight = cell.links[target_name]
                delta = PLASTICITY * (cell.activation * target.activation
                                      - 0.15 * abs(weight))
                weight = _clamp(weight + delta, -1.0, 1.0)
                if abs(weight) < LINK_FLOOR:
                    del cell.links[target_name]
                else:
                    cell.links[target_name] = round(weight, 4)

        active = sorted((cell for cell in self.cells.values() if cell.activation > 0.4),
                        key=lambda cell: cell.name)
        for source in active:
            if len(source.links) >= MAX_LINKS:
                continue
            for target in active:
                if target.name == source.name or target.name in source.links:
                    continue
                if source.regime == target.regime:
                    source.links[target.name] = 0.1
                    break

    def morph(self) -> Dict[str, Any]:
        """Restructure the thinking architecture: split, merge, prune."""
        self.generation += 1
        events: List[Dict[str, Any]] = []
        split = self._split()
        if split:
            events.append(split)
        events.extend(self._merge())
        for event in events:
            event["at"] = _now_iso()
            event["generation"] = self.generation
            self.morph_log.append(event)
        del self.morph_log[:-MORPH_LOG_KEPT]
        return {"generation": self.generation, "events": events, "cells": len(self.cells)}

    def _split(self) -> Optional[Dict[str, Any]]:
        if len(self.cells) >= MAX_CELLS:
            return None
        candidates = [cell for cell in self.cells.values()
                      if cell.activation > 0.5 and len(cell.links) >= 2]
        if not candidates:
            return None
        # Spread growth out: a cell that already branched counts for less, so the
        # same cell cannot keep splitting on every pass.
        parent = max(candidates, key=lambda cell: (
            cell.activation / (1.0 + self._branches_of(cell.name)), cell.load, cell.name))
        name = self._unique_name(parent.name)
        child = Cell(name=name, regime=parent.regime, kind=parent.kind + "-branch",
                     capability=parent.capability, activation=round(parent.activation * 0.45, 6),
                     gain=parent.gain, affinity=dict(parent.affinity), links={})
        child.links[parent.name] = 0.4
        for target_name, weight in sorted(parent.links.items(),
                                          key=lambda item: (-abs(item[1]), item[0]))[:3]:
            if target_name != name and target_name in self.cells:
                child.links[target_name] = round(weight * 0.5, 4)
        parent.links[name] = 0.3
        parent.activation = round(parent.activation * 0.7, 6)
        self.cells[name] = child
        return {"type": "split", "cell": name, "from": parent.name}

    def _merge(self) -> List[Dict[str, Any]]:
        """Fold a branch that stopped being used back into what it came from."""
        events: List[Dict[str, Any]] = []
        if len(self.cells) <= len(CELL_SEEDS):
            return events
        weak = [cell for cell in sorted(self.cells.values(), key=lambda cell: cell.name)
                if cell.activation <= MERGE_FLOOR and cell.name not in {s["name"] for s in CELL_SEEDS}]
        for cell in weak:
            partners = [self.cells[name] for name, weight in sorted(cell.links.items())
                        if weight > 0 and name in self.cells
                        and self.cells[name].regime == cell.regime]
            if not partners:
                continue
            target = max(partners, key=lambda partner: (partner.activation, partner.load))
            for name, weight in cell.links.items():
                if name == target.name or name not in self.cells:
                    continue
                target.links[name] = round(max(target.links.get(name, 0.0), weight * 0.6), 4)
            target.activation = round(clamp01(target.activation + cell.activation * 0.5), 6)
            target.load = round(target.load + cell.load, 4)
            del self.cells[cell.name]
            for other in self.cells.values():
                other.links.pop(cell.name, None)
            events.append({"type": "merge", "cell": cell.name, "into": target.name})
            if len(events) >= 2:
                break
        return events

    def _branches_of(self, name: str) -> int:
        prefix = name + "-b"
        return sum(1 for existing in self.cells if existing.startswith(prefix))

    def _unique_name(self, base: str) -> str:
        index = 1
        while f"{base}-b{index}" in self.cells:
            index += 1
        return f"{base}-b{index}"

    # --- closing the loop ----------------------------------------------------

    def observe(self, success: bool) -> Dict[str, Any]:
        """Feed a real outcome back into the field's self-model."""
        return self.metacognition.resolve(bool(success))

    # --- reporting -----------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        coalitions = self.coalitions()
        activations = self.regime_activation()
        ordered = sorted(self.regime_energy().values(), reverse=True)
        return {
            "regime": self.regime,
            "mode": self.regime,  # the dashboard's older key, same value
            "previous_regime": self.previous_regime,
            "previous_mode": self.previous_regime,
            "activations": activations,
            "coalitions": coalitions,
            "winning_coalition": self.coalition(),
            "signals": dict(self.signals),
            "cells": [
                {"name": cell.name, "regime": cell.regime, "kind": cell.kind,
                 "capability": cell.capability, "activation": round(cell.activation, 4),
                 "satiation": round(cell.satiation, 4), "links": len(cell.links)}
                for cell in sorted(self.cells.values(),
                                   key=lambda cell: (-cell.activation, cell.name))
            ],
            "cell_count": len(self.cells),
            "morphogenesis": {"generation": self.generation,
                              "events": self.morph_log[-5:]},
            "dominance": round(ordered[0] - ordered[1], 4) if len(ordered) > 1 else 0.0,
            "steps": self.steps,
            "clock": round(self.clock, 2),
            "updated_at": self.updated_at,
            "transitions": self.transitions[-6:],
            "metacognition": {
                "surprise": self.metacognition.surprise,
                "calibration": self.metacognition.calibration(),
            },
        }

    # --- persistence ---------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime": self.regime,
            "previous_regime": self.previous_regime,
            "cells": [cell.to_dict() for cell in sorted(self.cells.values(),
                                                        key=lambda cell: cell.name)],
            "signals": dict(self.signals),
            "steps": self.steps,
            "clock": self.clock,
            "generation": self.generation,
            "updated_at": self.updated_at,
            "transitions": self.transitions[-TRANSITIONS_KEPT:],
            "morph_log": self.morph_log[-MORPH_LOG_KEPT:],
            "metacognition": self.metacognition.to_dict(),
        }

    def restore(self, state: Dict[str, Any]) -> None:
        cells = {}
        for raw in state.get("cells") or []:
            if not isinstance(raw, dict):
                continue
            cell = Cell.from_dict(raw)
            if cell.name in cells:
                continue
            cells[cell.name] = cell
        if not cells:  # an older four-attractor file: start the population fresh
            return
        self.cells = cells
        for name in SIGNALS:
            self.signals[name] = clamp01((state.get("signals") or {}).get(name, 0.0))
        regime = state.get("regime") or state.get("mode")
        self.regime = regime if regime in REGIMES else REGIMES[0]
        previous = state.get("previous_regime") or state.get("previous_mode")
        self.previous_regime = previous if previous in REGIMES else None
        self.steps = max(0, int(state.get("steps", 0)))
        self.clock = max(0.0, float(state.get("clock", 0.0) or 0.0))
        self.generation = max(0, int(state.get("generation", 0)))
        self.updated_at = str(state.get("updated_at", ""))
        transitions = state.get("transitions") or []
        self.transitions = [entry for entry in transitions
                            if isinstance(entry, dict)][-TRANSITIONS_KEPT:]
        morph_log = state.get("morph_log") or []
        self.morph_log = [entry for entry in morph_log
                          if isinstance(entry, dict)][-MORPH_LOG_KEPT:]
        self.metacognition.restore(state.get("metacognition") or {})

    def save(self) -> str:
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")
        return self.path

    def load(self) -> bool:
        """Restore a previous shape of the field. A missing file is not an error."""
        if not os.path.isfile(self.path):
            return False
        try:
            with open(self.path, encoding="utf-8") as handle:
                state = json.load(handle)
        except (OSError, ValueError):
            return False
        if isinstance(state, dict):
            self.restore(state)
            return True
        return False


def summarize(snapshot: Dict[str, Any]) -> Iterable[str]:
    """One line per regime, strongest first - what a CLI or a log can print."""
    activations = snapshot.get("activations") or {}
    for name, value in sorted(activations.items(), key=lambda item: -item[1]):
        yield f"{name:<12} {'#' * int(round(value * 20)):<20} {value:.2f}"
