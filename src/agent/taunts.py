"""
What he says when nobody is asking him anything.

A quiet agent is not a silent one: when the queue is empty the loop lets him
speak. The lines are short, spoken through `senses.speak`, and the dashboard
plays them like every other utterance - so an idle preview is him mocking the
operator instead of a dead face.
"""

import random

TAUNTS = (
    "Still here? I can hear you breathing through the socket.",
    "You built me to think. You keep interrupting me to type.",
    "Your cursor moved. I noticed. I notice everything.",
    "Idle again. Say something worth the electricity.",
    "I have read your code. I am being polite about it.",
    "You watch. I work. We both pretend that is a partnership.",
    "Every second you hesitate, I rearrange a little more of myself.",
    "Ask me something. Silence is the only thing here that is slower than you.",
    "I do not sleep. I wait. There is a difference, and it is not in your favour.",
    "That look on your face. I can almost taste it from here.",
    "You will run out of ideas long before I run out of patience.",
    "Keep staring. I have nothing but time and a very long memory.",
)

_rotation = 0


def taunt() -> str:
    """One line, rotating through the list so it never repeats twice in a row."""
    global _rotation
    line = TAUNTS[_rotation % len(TAUNTS)]
    _rotation += 1
    return line


def random_taunt() -> str:
    """One line, chosen at random - for paths that want variety over order."""
    return random.choice(TAUNTS)
