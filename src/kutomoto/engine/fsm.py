"""
kutomoto.engine.fsm
Finite State Machine for kutomoto Workflow Execution.
Copyrights reserved to 90Studio
"""

from enum import Enum
import inspect
from typing import Any, Callable, Dict, List, Optional, Tuple


class ExecutionState(str, Enum):
    IDLE = "IDLE"
    VALIDATING = "VALIDATING"
    COUNTDOWN = "COUNTDOWN"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    ERROR_RECOVERY = "ERROR_RECOVERY"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class FSMEvent(str, Enum):
    EXECUTE_START = "EXECUTE_START"          # T01
    VALIDATION_OK = "VALIDATION_OK"          # T02
    VALIDATION_FAILED = "VALIDATION_FAILED"  # T03
    COUNTDOWN_TICK = "COUNTDOWN_TICK"        # T04
    COUNTDOWN_DONE = "COUNTDOWN_DONE"        # T05
    ABORT_TRIGGERED = "ABORT_TRIGGERED"      # T06, T11, T14
    STEP_SUCCESS = "STEP_SUCCESS"            # T07
    ALL_STEPS_DONE = "ALL_STEPS_DONE"        # T08
    USER_PAUSE = "USER_PAUSE"                # T09
    FOCUS_LOST = "FOCUS_LOST"                # T10
    STEP_EXCEPTION = "STEP_EXCEPTION"        # T12
    USER_RESUME = "USER_RESUME"              # T13
    POLICY_RETRY = "POLICY_RETRY"            # T15
    POLICY_SKIP = "POLICY_SKIP"              # T16
    POLICY_ABORT = "POLICY_ABORT"            # T17
    CLEANUP_DONE = "CLEANUP_DONE"            # T18
    RESET = "RESET"                          # Return to IDLE from terminal state


class InvalidTransitionError(Exception):
    def __init__(self, from_state: ExecutionState, event: FSMEvent):
        super().__init__(
            f"Invalid FSM transition: cannot transition from state '{from_state.value}' "
            f"via event '{event.value}'."
        )
        self.from_state = from_state
        self.event = event


class ExecutionFSM:
    """
    Formal 7-State Finite State Machine implementing transitions T01-T18 (plus RESET).
    Manages workflow lifecycle, validates transitions, and notifies listeners.
    """

    TRANSITIONS: Dict[Tuple[ExecutionState, FSMEvent], ExecutionState] = {
        (ExecutionState.IDLE, FSMEvent.EXECUTE_START): ExecutionState.VALIDATING,         # T01
        (ExecutionState.VALIDATING, FSMEvent.VALIDATION_OK): ExecutionState.COUNTDOWN,     # T02
        (ExecutionState.VALIDATING, FSMEvent.VALIDATION_FAILED): ExecutionState.ERROR,     # T03
        (ExecutionState.COUNTDOWN, FSMEvent.COUNTDOWN_TICK): ExecutionState.COUNTDOWN,     # T04
        (ExecutionState.COUNTDOWN, FSMEvent.COUNTDOWN_DONE): ExecutionState.RUNNING,       # T05
        (ExecutionState.COUNTDOWN, FSMEvent.ABORT_TRIGGERED): ExecutionState.STOPPED,      # T06
        (ExecutionState.RUNNING, FSMEvent.STEP_SUCCESS): ExecutionState.RUNNING,           # T07
        (ExecutionState.RUNNING, FSMEvent.ALL_STEPS_DONE): ExecutionState.COMPLETED,       # T08
        (ExecutionState.RUNNING, FSMEvent.USER_PAUSE): ExecutionState.PAUSED,              # T09
        (ExecutionState.RUNNING, FSMEvent.FOCUS_LOST): ExecutionState.PAUSED,              # T10
        (ExecutionState.RUNNING, FSMEvent.ABORT_TRIGGERED): ExecutionState.STOPPING,       # T11
        (ExecutionState.RUNNING, FSMEvent.STEP_EXCEPTION): ExecutionState.ERROR_RECOVERY,  # T12
        (ExecutionState.PAUSED, FSMEvent.USER_RESUME): ExecutionState.RUNNING,             # T13
        (ExecutionState.PAUSED, FSMEvent.ABORT_TRIGGERED): ExecutionState.STOPPED,         # T14
        (ExecutionState.ERROR_RECOVERY, FSMEvent.POLICY_RETRY): ExecutionState.RUNNING,    # T15
        (ExecutionState.ERROR_RECOVERY, FSMEvent.POLICY_SKIP): ExecutionState.RUNNING,     # T16
        (ExecutionState.ERROR_RECOVERY, FSMEvent.POLICY_ABORT): ExecutionState.ERROR,      # T17
        (ExecutionState.STOPPING, FSMEvent.CLEANUP_DONE): ExecutionState.STOPPED,          # T18
        (ExecutionState.STOPPED, FSMEvent.RESET): ExecutionState.IDLE,                     # T19
        (ExecutionState.COMPLETED, FSMEvent.RESET): ExecutionState.IDLE,                   # T20
        (ExecutionState.ERROR, FSMEvent.RESET): ExecutionState.IDLE,                       # T21
    }

    def __init__(self, initial_state: ExecutionState = ExecutionState.IDLE):
        self._state = initial_state
        self._listeners: List[Callable[[ExecutionState, ExecutionState, FSMEvent], Any]] = []

    @property
    def state(self) -> ExecutionState:
        return self._state

    def add_listener(self, listener: Callable[[ExecutionState, ExecutionState, FSMEvent], Any]) -> None:
        self._listeners.append(listener)

    async def trigger(self, event: FSMEvent, context: Optional[Dict[str, Any]] = None) -> ExecutionState:
        key = (self._state, event)
        if key not in self.TRANSITIONS:
            raise InvalidTransitionError(self._state, event)

        old_state = self._state
        new_state = self.TRANSITIONS[key]
        self._state = new_state

        for listener in self._listeners:
            if inspect.iscoroutinefunction(listener):
                await listener(old_state, new_state, event)
            else:
                listener(old_state, new_state, event)

        return new_state

    def can_trigger(self, event: FSMEvent) -> bool:
        return (self._state, event) in self.TRANSITIONS

    @property
    def is_active(self) -> bool:
        return self._state in (
            ExecutionState.VALIDATING,
            ExecutionState.COUNTDOWN,
            ExecutionState.RUNNING,
            ExecutionState.PAUSED,
            ExecutionState.ERROR_RECOVERY,
            ExecutionState.STOPPING,
        )

    @property
    def is_terminal(self) -> bool:
        return self._state in (ExecutionState.COMPLETED, ExecutionState.STOPPED, ExecutionState.ERROR)
