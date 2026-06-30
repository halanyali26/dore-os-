"""
Dore OS v2.0 — State Machine
Release lifecycle finite state machine with transition validation.
"""
from enum import Enum
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timezone


class State(str, Enum):
    IDEA = "IDEA"
    PRODUCTION = "PRODUCTION"
    MASTERED = "MASTERED"
    PACKAGED = "PACKAGED"
    DISTRIBUTED = "DISTRIBUTED"
    LIVE = "LIVE"
    MONETIZED = "MONETIZED"
    ARCHIVED = "ARCHIVED"


@dataclass
class Transition:
    from_state: State
    to_state: State
    description: str
    required_files: List[str] = field(default_factory=list)
    auto_actions: List[str] = field(default_factory=list)


# Define all valid transitions with requirements
TRANSITIONS: List[Transition] = [
    # Creative phase
    Transition(State.IDEA, State.PRODUCTION,
              "Start production: lyrics written, genre decided",
              ["lyrics.txt", "concept.md"]),

    # Production → Mastering
    Transition(State.PRODUCTION, State.MASTERED,
              "Audio mastered: WAV file ready, normalized",
              ["master.wav", "stems/"],
              ["normalize_audio", "generate_waveform"]),

    # Mastering → Packaging
    Transition(State.MASTERED, State.PACKAGED,
              "Packaging complete: ISRC assigned, metadata ready, artwork created",
              ["cover.jpg", "metadata.json"],
              ["generate_isrc", "generate_upc", "create_ddex"]),

    # Packaging → Distribution
    Transition(State.PACKAGED, State.DISTRIBUTED,
              "Uploaded to platforms: YouTube, DistroKid, Spotify",
              ["distribution_report.json"]),

    # Distribution → Live
    Transition(State.DISTRIBUTED, State.LIVE,
              "Confirmed live on streaming platforms",
              []),
    # Allow rollback from DISTRIBUTED to PACKAGED if needed
    Transition(State.DISTRIBUTED, State.PACKAGED,
              "Rollback: distribution failed, needs repackaging",
              []),

    # Live → Monetized
    Transition(State.LIVE, State.MONETIZED,
              "First royalty payment received",
              []),

    # Monetized → Archived
    Transition(State.MONETIZED, State.ARCHIVED,
              "Release archived (no longer actively promoted)",
              []),

    # Allow rollback
    Transition(State.PRODUCTION, State.IDEA,
              "Rollback: production restart needed",
              []),
    Transition(State.MASTERED, State.PRODUCTION,
              "Rollback: mastering failed, redo production",
              []),
    Transition(State.PACKAGED, State.MASTERED,
              "Rollback: packaging incorrect",
              []),
]


class StateMachine:
    """Manages state transitions with validation and hooks."""

    def __init__(self):
        self.transitions = {t.from_state: {} for t in TRANSITIONS}
        for t in TRANSITIONS:
            self.transitions[t.from_state][t.to_state] = t
        self.hooks: Dict[str, List[Callable]] = {
            "before": [],
            "after": [],
            "on_error": [],
        }

    def can_transition(self, from_state: State, to_state: State) -> bool:
        return to_state in self.transitions.get(from_state, {})

    def get_transition(self, from_state: State, to_state: State) -> Optional[Transition]:
        return self.transitions.get(from_state, {}).get(to_state)

    def get_valid_next_states(self, current: State) -> List[State]:
        return list(self.transitions.get(current, {}).keys())

    def add_hook(self, event: str, callback: Callable):
        if event in self.hooks:
            self.hooks[event].append(callback)

    def transition(self, from_state: State, to_state: State,
                   context: Dict = None) -> Dict:
        """Execute a state transition with hooks."""
        context = context or {}
        transition = self.get_transition(from_state, to_state)

        if not transition:
            return {
                "success": False,
                "error": f"Invalid transition: {from_state.value} → {to_state.value}",
                "valid_next": [s.value for s in self.get_valid_next_states(from_state)],
            }

        # Before hooks
        for hook in self.hooks["before"]:
            try:
                hook(from_state, to_state, context)
            except Exception as e:
                for eh in self.hooks["on_error"]:
                    eh("before", str(e))
                return {"success": False, "error": f"Before hook failed: {e}"}

        # Execute
        result = {
            "success": True,
            "from": from_state.value,
            "to": to_state.value,
            "description": transition.description,
            "required_files": transition.required_files,
            "auto_actions": transition.auto_actions,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }
        context.update(result)

        # After hooks
        for hook in self.hooks["after"]:
            try:
                hook(from_state, to_state, context)
            except Exception as e:
                for eh in self.hooks["on_error"]:
                    eh("after", str(e))

        return result
