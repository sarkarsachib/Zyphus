"""
The adaptive cognitive field.

`DeliberativeBrain` decides from the words in a task: a prefix here, a pattern
there. This module replaces that with a *field*. Four cognitive attractors
compete continuously, and whichever one is currently in equilibrium decides how
the agent thinks - not a branch on task text, and not a rotation.

    plan        a procedure is known: compose and run
    explore     the ground is unmapped: look before acting
    deliberate  the answer is not obvious: compare possible worlds first
    inhibit     the agent is repeating itself: consolidate, then continue

Each attractor is excited by named signals (task pressure, backlog, novelty,
uncertainty, surprise, stagnation, competence, fatigue) through an explicit
coupling matrix, loses activation to the others (lateral inhibition), and tires
as it is used (satiation). The state integrates in real time, so a long gap
between perceptions relaxes the field while a burst of surprise excites
deliberation: the mode is an equilibrium the signals settle into rather than a
decision taken once.

`Metacognition` sits on top. Before a mode acts it states how confident it is;
after the outcome it scores itself. The running error is `surprise`, and a mode
whose calls actually fail loses gain in the field - so experience reshapes the
field instead of being logged beside it.

Stdlib only and deterministic: the same percepts from the same state always
produce the same mode.
"""

import json
import os
import time
from typing import Any, Dict, Iterable, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_PATH = os.path.join(REPO_ROOT, "devmind", "agent", "field.json")

ATTRACTORS = ("plan", "explore", "deliberate", "inhibit")

SIGNALS = ("task", "backlog", "novelty", "uncertainty", "surprise",
           "stagnation", "competence", "fatigue")

# Excitation (+) and suppression (-) each signal applies to each attractor.
# These numbers are the architecture: change one and the behaviour changes.
COUPLING = {
    "plan": {"task": 0.85, "backlog": 0.45, "competence": 0.30, "fatigue": -0.25},
    "explore": {"novelty": 0.85, "uncertainty": 0.45, "task": -0.20, "fatigue": -0.20},
    "deliberate": {"surprise": 0.75, "uncertainty": 0.60, "stagnation": 0.55,
                   "task": 0.30, "fatigue": -0.30},
    "inhibit": {"fatigue": 0.70, "competence": 0.20, "task": -0.65, "backlog": -0.40},
}

TAU = 0.60            # seconds for an attractor to reach 63% of its target
STEP_SECONDS = 0.25   # integration step
HORIZON_SECONDS = 1.5 # field time one perception always integrates
MAX_HORIZON = 12.0    # ceiling, so a long sleep cannot overshoot in one jump
INHIBITION = 0.45     # how much a live rival suppresses an attractor
SATIATION = 0.30      # how much a tired attractor suppresses itself
HYSTERESIS = 0.05     # a rival must beat the incumbent by this much to take over
TRANSITIONS_KEPT = 24


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def clamp01(value: float) -> float:
    return _clamp(float(value), 0.0, 1.0)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


class Metacognition:
    """The field's model of its own reliability, and the error in that model."""

    def __init__(self, state: Optional[Dict[str, Any]] = None):
        self.gain = {name: 1.0 for name in ATTRACTORS}
        self.attempts = {name: 0 for name in ATTRACTORS}
        self.successes = {name: 0 for name in ATTRACTORS}
        self.abs_error = {name: 0.0 for name in ATTRACTORS}
        self.surprise = 0.0
        self.pending: Optional[tuple] = None
        if state:
            self.restore(state)

    # --- beliefs about itself ------------------------------------------------

    def confidence(self, mode: str) -> float:
        """This mode's success rate, shrunk toward 0.5 until it has evidence."""
        if mode not in self.gain:
            return 0.5
        return round((self.successes[mode] + 1.0) / (self.attempts[mode] + 2.0), 4)

    def predict(self, mode: str, confidence: Optional[float] = None) -> tuple:
        """Commit to a mode and how well it expects to do - before it acts."""
        mode = mode if mode in self.gain else "plan"
        stated = self.confidence(mode) if confidence is None else clamp01(confidence)
        self.pending = (mode, round(stated, 4))
        return self.pending

    def resolve(self, success: bool) -> Dict[str, Any]:
        """Score the pending prediction against what actually happened."""
        if self.pending is None:
            return {}
        mode, stated = self.pending
        self.pending = None
        outcome = 1.0 if success else 0.0
        error = abs(outcome - stated)

        self.surprise = round(0.6 * self.surprise + 0.4 * error, 4)
        self.attempts[mode] += 1
        self.successes[mode] += 1 if success else 0
        self.abs_error[mode] += error
        # A mode that keeps missing its own forecast loses its pull on the field.
        self.gain[mode] = round(_clamp(self.gain[mode] + 0.25 * (outcome - stated), 0.5, 1.6), 4)
        return {"mode": mode, "predicted": stated, "error": round(error, 4),
                "surprise": self.surprise, "gain": self.gain[mode]}

    def calibration(self) -> Dict[str, Dict[str, Any]]:
        out = {}
        for mode in ATTRACTORS:
            attempts = self.attempts[mode]
            out[mode] = {
                "attempts": attempts,
                "confidence": self.confidence(mode),
                "mean_error": round(self.abs_error[mode] / attempts, 4) if attempts else 0.0,
                "gain": self.gain[mode],
            }
        return out

    # --- persistence ---------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {"gain": dict(self.gain), "attempts": dict(self.attempts),
                "successes": dict(self.successes), "abs_error": dict(self.abs_error),
                "surprise": self.surprise}

    def restore(self, state: Dict[str, Any]) -> None:
        for mode in ATTRACTORS:
            self.gain[mode] = _clamp(float((state.get("gain") or {}).get(mode, 1.0)), 0.5, 1.6)
            self.attempts[mode] = max(0, int((state.get("attempts") or {}).get(mode, 0)))
            self.successes[mode] = max(0, int((state.get("successes") or {}).get(mode, 0)))
            self.abs_error[mode] = max(0.0, float((state.get("abs_error") or {}).get(mode, 0.0)))
        self.surprise = clamp01(state.get("surprise", 0.0))


class CognitiveField:
    """The four-attractor field: perceive, integrate, settle."""

    def __init__(self, path: Optional[str] = None, autoload: bool = False):
        self.path = path or os.environ.get("ZYPHUS_FIELD_PATH") or DEFAULT_PATH
        self.activation = {name: 0.0 for name in ATTRACTORS}
        self.signals = {name: 0.0 for name in SIGNALS}
        self.satiation = {name: 0.0 for name in ATTRACTORS}
        self.metacognition = Metacognition()
        self.mode = "plan"
        self.previous_mode: Optional[str] = None
        self.steps = 0
        self.updated_at = ""
        self.transitions = []
        if autoload:
            self.load()

    # --- perception ----------------------------------------------------------

    def perceive(self, signals: Dict[str, Any]) -> Dict[str, float]:
        """Take the current reading of the situation. Absent signals read as zero."""
        for name in SIGNALS:
            self.signals[name] = round(clamp01(signals.get(name, 0.0) or 0.0), 4)
        return dict(self.signals)

    # --- dynamics ------------------------------------------------------------

    def step(self, seconds: Optional[float] = None) -> str:
        """Integrate the field and return the mode it settles into."""
        horizon = HORIZON_SECONDS if seconds is None else _clamp(float(seconds),
                                                                 STEP_SECONDS, MAX_HORIZON)
        substeps = max(1, int(round(horizon / STEP_SECONDS)))
        for _ in range(substeps):
            self._integrate()
        self.steps += 1
        self.updated_at = _now_iso()
        return self.mode

    def _integrate(self) -> None:
        excite: Dict[str, float] = {}
        for name in ATTRACTORS:
            drive = sum(self.signals.get(signal, 0.0) * weight
                        for signal, weight in COUPLING[name].items())
            excite[name] = max(0.0, drive) * self.metacognition.gain[name]

        total = sum(self.activation.values())
        rivals_divisor = max(1, len(ATTRACTORS) - 1)
        fraction = min(1.0, STEP_SECONDS / TAU)

        for name in ATTRACTORS:
            rivals = (total - self.activation[name]) / rivals_divisor
            target = clamp01(excite[name] - INHIBITION * rivals - SATIATION * self.satiation[name])
            self.activation[name] = round(
                clamp01(self.activation[name] + fraction * (target - self.activation[name])), 6)

        leader = self._leader()
        for name in ATTRACTORS:
            if name == leader and self.activation[name] > 0.30:
                self.satiation[name] = _clamp(self.satiation[name] + 0.10 * STEP_SECONDS, 0.0, 0.9)
            else:
                self.satiation[name] = _clamp(self.satiation[name] - 0.05 * STEP_SECONDS, 0.0, 0.9)

        self._settle_mode(leader)

    def _leader(self) -> str:
        best = ATTRACTORS[0]
        for name in ATTRACTORS:
            if self.activation[name] > self.activation[best] + 1e-12:
                best = name
        return best

    def _settle_mode(self, leader: str) -> None:
        """Switch only on a clear margin, so the field does not flicker."""
        if leader == self.mode:
            return
        if self.activation[leader] <= self.activation[self.mode] + HYSTERESIS:
            return
        self.previous_mode = self.mode
        self.mode = leader
        self.transitions.append({
            "at": _now_iso(),
            "from": self.previous_mode,
            "to": leader,
            "activations": {name: round(value, 4) for name, value in self.activation.items()},
        })
        del self.transitions[:-TRANSITIONS_KEPT]

    # --- closing the loop ----------------------------------------------------

    def observe(self, success: bool) -> Dict[str, Any]:
        """Feed a real outcome back into the field's self-model."""
        return self.metacognition.resolve(bool(success))

    # --- reporting -----------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "previous_mode": self.previous_mode,
            "activations": {name: round(self.activation[name], 4) for name in ATTRACTORS},
            "signals": dict(self.signals),
            "satiation": {name: round(self.satiation[name], 4) for name in ATTRACTORS},
            "dominance": round(self.activation[self._leader()]
                               - sorted(self.activation.values())[-2], 4) if len(ATTRACTORS) > 1 else 0.0,
            "steps": self.steps,
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
            "mode": self.mode,
            "previous_mode": self.previous_mode,
            "activation": dict(self.activation),
            "signals": dict(self.signals),
            "satiation": dict(self.satiation),
            "steps": self.steps,
            "updated_at": self.updated_at,
            "transitions": self.transitions[-TRANSITIONS_KEPT:],
            "metacognition": self.metacognition.to_dict(),
        }

    def restore(self, state: Dict[str, Any]) -> None:
        for name in ATTRACTORS:
            self.activation[name] = clamp01((state.get("activation") or {}).get(name, 0.0))
            self.satiation[name] = _clamp(float((state.get("satiation") or {}).get(name, 0.0)),
                                          0.0, 0.9)
        for name in SIGNALS:
            self.signals[name] = clamp01((state.get("signals") or {}).get(name, 0.0))
        mode = state.get("mode")
        self.mode = mode if mode in ATTRACTORS else "plan"
        previous = state.get("previous_mode")
        self.previous_mode = previous if previous in ATTRACTORS else None
        self.steps = max(0, int(state.get("steps", 0)))
        self.updated_at = str(state.get("updated_at", ""))
        transitions = state.get("transitions") or []
        self.transitions = [entry for entry in transitions if isinstance(entry, dict)][-TRANSITIONS_KEPT:]
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
    """One line per attractor, strongest first - what a CLI or a log can print."""
    activations = snapshot.get("activations") or {}
    for name, value in sorted(activations.items(), key=lambda item: -item[1]):
        yield f"{name:<10} {'#' * int(round(value * 20)):<20} {value:.2f}"
