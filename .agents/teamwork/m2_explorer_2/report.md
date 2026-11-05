# kutomoto Workflow Execution Engine Architecture Blueprint

**Module Target**: `src/kutomoto/engine/`  
**Copyright**: Copyrights reserved to 90Studio  
**Milestone**: M2 — Win32 Automation Core & Workflow Engine  
**Author**: `m2_explorer_2`  
**Date**: 2026-11-04  

---

## 1. Executive Summary & Architectural Context

The kutomoto Workflow Execution Engine (`src/kutomoto/engine/`) is the central orchestrator responsible for executing automated form-filling pipelines across open web browser tabs and Windows desktop applications. It operates as an asynchronous, non-blocking runtime that bridges high-level workflow definitions (whether authored via the Visual Form Designer or manual step-by-step editor) to hardware-level Win32 automation primitives.

### 1.1 Architectural Responsibilities

The engine subsystem comprises four core modules:
1. `src/kutomoto/engine/schema.py`: Canonical Pydantic V2 models defining the Unified Action Workflow Schema (Draft 2020-12), encapsulating all 10 atomic action specifications, target application binding, variable resolution, and 90Studio copyright enforcement.
2. `src/kutomoto/engine/fsm.py`: A formal 7-State Finite State Machine enforcing the 18 state transitions (T01–T18) with strict guard conditions, invalid transition rejection, and lifecycle event callbacks.
3. `src/kutomoto/engine/runner.py`: The asynchronous workflow executor (`WorkflowRunner`) driving the step execution loop, inter-step delays, parameter binding, loss-of-focus pre-step checks, retry policies, and real-time telemetry streaming over WebSockets.
4. `src/kutomoto/engine/audit.py`: The 90Studio compliance audit logger emitting immutable, tamper-evident structured JSON audit records compliant with Section 10.1, complete with credential masking for sensitive fields (`is_secret=True`).

```
+--------------------------------------------------------------------------------------------------+
|                                    KUTOMOTO EXECUTION RUNTIME                                    |
+--------------------------------------------------------------------------------------------------+
|                                                                                                  |
|   +------------------------------------+          +------------------------------------------+   |
|   |   Unified Action Schema Models     |          |       7-State Finite State Machine       |   |
|   |   (schema.py - Pydantic V2)        |          |       (fsm.py - Transitions T01-T18)     |   |
|   |   - KutomotoWorkflow (Root)        |          |   IDLE -> VALIDATING -> COUNTDOWN ->     |   |
|   |   - 10 Atomic Actions              |          |   RUNNING <-> PAUSED                     |   |
|   |   - Recovery Policies (ABORT/RETRY)|          |   RUNNING -> ERROR_RECOVERY / STOPPING   |   |
|   |   - 90Studio Copyright Default     |          |   STOPPED / COMPLETED / ERROR            |   |
|   +-----------------+------------------+          +--------------------+---------------------+   |
|                     |                                                  |                         |
|                     +------------------------+-------------------------+                         |
|                                              |                                                   |
|                                              v                                                   |
|                   +----------------------------------------------------------+                   |
|                   |           WorkflowRunner (runner.py - Async)             |                   |
|                   |  - Async execution loop & step dispatchers (10 actions)   |                   |
|                   |  - Pre-step Loss-of-Focus Guardian verification          |                   |
|                   |  - Variable interpolation & dynamic expression solver    |                   |
|                   |  - Event emitter for WebSocket streaming & UI console    |                   |
|                   |  - Multi-tier error recovery (Retry, Skip, Abort)        |                   |
|                   +--------------------------+-------------------------------+                   |
|                                              |                                                   |
|                     +------------------------+-------------------------+                         |
|                     |                                                  |                         |
|                     v                                                  v                         |
|   +------------------------------------+          +------------------------------------------+   |
|   |    90Studio Compliance Logger      |          |        Win32 Automation Driver Core      |   |
|   |    (audit.py - Section 10.1)       |          |        (src/kutomoto/automation/)        |   |
|   |    - Structured JSON Audit Trail   |          |    - SetForegroundWindow & AttachThread  |   |
|   |    - Credential Masking (is_secret)|          |    - SendInput Keyboard & Mouse Core     |   |
|   |    - Step Latency & Telemetry      |          |    - Per-Monitor V2 DPI Awareness        |   |
|   +------------------------------------+          +------------------------------------------+   |
+--------------------------------------------------------------------------------------------------+
```

---

## 2. Module Blueprint 1: `src/kutomoto/engine/schema.py`

### 2.1 Design Objectives
- Full compliance with `docs/SPECIFICATION.md` Section 7.3 (Unified Action Workflow Formal JSON Schema Draft 2020-12).
- Native Pydantic V2 syntax with strict type validation, field constraints, default factories, and custom validators.
- Enforce mandatory 90Studio legal copyright notice: `"Copyrights reserved to 90Studio"`.
- Support all 10 atomic action specifications with specialized parameter models and a unified discriminated union or polymorphic container.

### 2.2 Complete Enumerations & Constants
```python
"""
Unified Action Workflow Schema Models (Pydantic V2).
Copyrights reserved to 90Studio
"""
from enum import Enum
from typing import List, Optional, Union, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
import uuid
from datetime import datetime, timezone

class ActionType(str, Enum):
    FOCUS_WINDOW = "focus_window"
    CLICK = "click"
    TYPE_TEXT = "type_text"
    KEY_PRESS = "key_press"
    HOTKEY = "hotkey"
    CLEAR_FIELD = "clear_field"
    DELAY = "delay"
    SUBMIT = "submit"
    SCROLL = "scroll"
    PROMPT_USER_INPUT = "prompt_user_input"

class ErrorRecoveryPolicy(str, Enum):
    ABORT = "abort"
    RETRY_STEP = "retry_step"
    PROMPT_USER = "prompt_user"
    SKIP_STEP = "skip_step"

class TargetAppType(str, Enum):
    WEB_BROWSER = "web_browser"
    WINDOWS_DESKTOP = "windows_desktop"
    ANY = "any"

class MatchMode(str, Enum):
    EXACT = "exact"
    CONTAINS = "contains"
    REGEX = "regex"

class CoordinateMode(str, Enum):
    SCREEN = "screen"
    WINDOW_CLIENT = "window_client"
    NORMALIZED = "normalized"

class MouseButton(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"

class ClearStrategy(str, Enum):
    SELECT_ALL_BACKSPACE = "select_all_backspace"
    TRIPLE_CLICK_DELETE = "triple_click_delete"
    BACKSPACE_REPEAT = "backspace_repeat"

class SubmitMethod(str, Enum):
    ENTER_KEY = "enter_key"
    BUTTON_CLICK = "button_click"

class SourceMode(str, Enum):
    VISUAL_DESIGNER_GENERATED = "visual_designer_generated"
    MANUAL_STEP_FLOW = "manual_step_flow"
    HYBRID = "hybrid"

class VariableType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    SECRET = "secret"
```

### 2.3 Atomic Action Parameter Models

Each atomic action corresponds to a dedicated parameter structure, while a consolidated `StepParameters` model provides unified JSON deserialization matching Section 7.3:

```python
class FocusWindowParameters(BaseModel):
    window_title_pattern: str = Field(..., min_length=1, description="Regex or substring matching target window title")
    process_name: Optional[str] = Field(None, description="Optional executable name e.g. msedge.exe")
    match_mode: MatchMode = Field(default=MatchMode.CONTAINS)

class ClickParameters(BaseModel):
    x: Optional[float] = Field(None, description="Absolute screen or client X coordinate")
    y: Optional[float] = Field(None, description="Absolute screen or client Y coordinate")
    norm_x: Optional[float] = Field(None, ge=0.0, le=1.0, description="Normalized horizontal coordinate [0.0..1.0]")
    norm_y: Optional[float] = Field(None, ge=0.0, le=1.0, description="Normalized vertical coordinate [0.0..1.0]")
    coordinate_mode: CoordinateMode = Field(default=CoordinateMode.NORMALIZED)
    button: MouseButton = Field(default=MouseButton.LEFT)
    click_count: int = Field(default=1, ge=1, le=3)

class TypeTextParameters(BaseModel):
    text: str = Field(default="", description="Text payload or variable template {{var}}")
    is_secret: bool = Field(default=False, description="If True, payload is masked in logs")
    keystroke_delay_ms: int = Field(default=20, ge=0, description="Delay between consecutive keystrokes in ms")
    use_clipboard_threshold: int = Field(default=40, ge=0, description="Payload length threshold to trigger clipboard fallback")

class KeyPressParameters(BaseModel):
    key: str = Field(default="tab", description="Key name e.g. tab, enter, escape, backspace, space")
    repeat_count: int = Field(default=1, ge=1, description="Number of times key is pressed")

class HotkeyParameters(BaseModel):
    keys: List[str] = Field(default_factory=list, min_length=1, description="Keys in chord e.g. ['ctrl', 'a']")

class ClearFieldParameters(BaseModel):
    clear_strategy: ClearStrategy = Field(default=ClearStrategy.SELECT_ALL_BACKSPACE)
    repeat_backspace_count: int = Field(default=50, ge=1)

class DelayParameters(BaseModel):
    duration_ms: int = Field(..., ge=0, description="Settling delay duration in milliseconds")

class SubmitParameters(BaseModel):
    submit_method: SubmitMethod = Field(default=SubmitMethod.ENTER_KEY)
    norm_x: Optional[float] = Field(None, ge=0.0, le=1.0)
    norm_y: Optional[float] = Field(None, ge=0.0, le=1.0)
    x: Optional[float] = None
    y: Optional[float] = None

class ScrollParameters(BaseModel):
    delta_x: int = Field(default=0, description="Horizontal scroll wheel delta")
    delta_y: int = Field(default=0, description="Vertical scroll wheel delta (negative for down)")

class PromptUserInputParameters(BaseModel):
    variable_name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$", description="Variable to bind")
    prompt_message: str = Field(..., min_length=1, description="Message displayed to operator")
    is_password: bool = Field(default=False, description="Whether to mask user input in prompt dialog")

class StepParameters(BaseModel):
    """
    Unified parameters model compatible with Section 7.3 formal schema.
    Contains optional fields for all 10 actions to allow direct JSON serialization.
    """
    window_title_pattern: Optional[str] = None
    process_name: Optional[str] = None
    match_mode: Optional[MatchMode] = None
    x: Optional[float] = None
    y: Optional[float] = None
    norm_x: Optional[float] = Field(None, ge=0.0, le=1.0)
    norm_y: Optional[float] = Field(None, ge=0.0, le=1.0)
    coordinate_mode: CoordinateMode = Field(default=CoordinateMode.NORMALIZED)
    button: MouseButton = Field(default=MouseButton.LEFT)
    click_count: int = Field(default=1, ge=1, le=3)
    text: Optional[str] = None
    is_secret: bool = Field(default=False)
    keystroke_delay_ms: int = Field(default=20, ge=0)
    key: Optional[str] = None
    repeat_count: int = Field(default=1, ge=1)
    keys: Optional[List[str]] = None
    clear_strategy: ClearStrategy = Field(default=ClearStrategy.SELECT_ALL_BACKSPACE)
    duration_ms: Optional[int] = Field(None, ge=0)
    submit_method: SubmitMethod = Field(default=SubmitMethod.ENTER_KEY)
    delta_x: int = Field(default=0)
    delta_y: int = Field(default=0)
    variable_name: Optional[str] = None
    prompt_message: Optional[str] = None
```

### 2.4 Workflow Step & Target Application Models

```python
class WorkflowStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sequence_index: int = Field(..., ge=1, description="Contiguous 1-based order")
    label: Optional[str] = Field(None, description="Human-readable step description")
    action_type: ActionType = Field(..., description="One of the 10 atomic actions")
    enabled: bool = Field(default=True)
    pre_delay_ms: int = Field(default=0, ge=0)
    post_delay_ms: int = Field(default=0, ge=0)
    parameters: StepParameters = Field(default_factory=StepParameters)

class TargetApplication(BaseModel):
    type: TargetAppType = Field(default=TargetAppType.WINDOWS_DESKTOP)
    window_title_pattern: str = Field(..., min_length=1)
    process_name: Optional[str] = None
    browser_url_pattern: Optional[str] = None
    match_mode: MatchMode = Field(default=MatchMode.CONTAINS)

class ExecutionSettings(BaseModel):
    countdown_seconds: int = Field(default=3, ge=0, le=30)
    default_step_delay_ms: int = Field(default=120, ge=10, le=10000)
    typing_speed_ms: int = Field(default=20, ge=1, le=500)
    stop_on_error: bool = Field(default=True)
    error_recovery_policy: ErrorRecoveryPolicy = Field(default=ErrorRecoveryPolicy.ABORT)
    max_step_retries: int = Field(default=2, ge=0, le=5)
    failsafe_corner_enabled: bool = Field(default=True)
    abort_hotkey: str = Field(default="Escape")

class WorkflowVariable(BaseModel):
    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    description: Optional[str] = None
    default_value: str = Field(default="")
    type: VariableType = Field(default=VariableType.STRING)
    required: bool = Field(default=False)

class DesignerMetadata(BaseModel):
    canvas_width: Optional[float] = None
    canvas_height: Optional[float] = None
    background_image_path: Optional[str] = None
    box_count: Optional[int] = None

class KutomotoWorkflow(BaseModel):
    schema_version: Literal["1.0.0"] = Field(default="1.0.0")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=1024)
    author: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    copyright: Literal["Copyrights reserved to 90Studio"] = Field(
        default="Copyrights reserved to 90Studio",
        description="Mandatory 90Studio copyright watermark"
    )
    source_mode: SourceMode = Field(default=SourceMode.MANUAL_STEP_FLOW)
    target_application: TargetApplication
    execution_settings: ExecutionSettings = Field(default_factory=ExecutionSettings)
    variables: List[WorkflowVariable] = Field(default_factory=list)
    designer_metadata: Optional[DesignerMetadata] = None
    steps: List[WorkflowStep] = Field(..., min_length=1)

    @field_validator("copyright")
    @classmethod
    def validate_copyright(cls, v: str) -> str:
        if v != "Copyrights reserved to 90Studio":
            raise ValueError("Invalid copyright. Must be exactly 'Copyrights reserved to 90Studio'")
        return v

    @model_validator(mode="after")
    def validate_steps_sequence(self) -> "KutomotoWorkflow":
        indices = [s.sequence_index for s in self.steps]
        if len(indices) != len(set(indices)):
            raise ValueError("Step sequence indices must be unique")
        return self
```

---

## 3. Module Blueprint 2: `src/kutomoto/engine/fsm.py`

### 3.1 Design Objectives
- Implement the formal 7-State Finite State Machine (`IDLE`, `VALIDATING`, `COUNTDOWN`, `RUNNING`, `PAUSED`, `STOPPING`, `COMPLETED`, `ERROR`) alongside intermediate/transient states (`ERROR_RECOVERY`, `STOPPED`).
- Strictly encode all 18 transitions (T01–T18) specified in Section 9.2.
- Provide transition validation: attempting any invalid transition raises `InvalidTransitionError`.
- Support synchronous and asynchronous state change listeners for WebSocket broadcasting and UI HUD updates.
- Include a safe `RESET` transition to return to `IDLE` after workflow termination.

### 3.2 State & Event Enumerations
```python
"""
Finite State Machine for kutomoto Workflow Execution.
Copyrights reserved to 90Studio
"""
from enum import Enum
from typing import Dict, Tuple, List, Callable, Any, Optional
import inspect
import asyncio

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
```

### 3.3 Formal State Transition Table (T01–T18 + Reset)

| Transition ID | Current State | Trigger Event | Next State | Guard / Required Condition |
|:---:|:---|:---|:---|:---|
| **T01** | `IDLE` | `EXECUTE_START` | `VALIDATING` | Workflow payload present |
| **T02** | `VALIDATING` | `VALIDATION_OK` | `COUNTDOWN` | Workflow schema valid & variables bound |
| **T03** | `VALIDATING` | `VALIDATION_FAILED` | `ERROR` | Schema validation error or missing required variable |
| **T04** | `COUNTDOWN` | `COUNTDOWN_TICK` | `COUNTDOWN` | Countdown timer $> 0$ |
| **T05** | `COUNTDOWN` | `COUNTDOWN_DONE` | `RUNNING` | Countdown reaches 0 |
| **T06** | `COUNTDOWN` | `ABORT_TRIGGERED` | `STOPPED` | Operator cancels during countdown |
| **T07** | `RUNNING` | `STEP_SUCCESS` | `RUNNING` | Step succeeded, steps remaining |
| **T08** | `RUNNING` | `ALL_STEPS_DONE` | `COMPLETED` | Final step finished |
| **T09** | `RUNNING` | `USER_PAUSE` | `PAUSED` | User clicks pause or hotkey |
| **T10** | `RUNNING` | `FOCUS_LOST` | `PAUSED` | `GetForegroundWindow() != target_hwnd` |
| **T11** | `RUNNING` | `ABORT_TRIGGERED` | `STOPPING` | `Escape` pressed or $(0,0)$ corner slam |
| **T12** | `RUNNING` | `STEP_EXCEPTION` | `ERROR_RECOVERY` | Step execution threw an exception |
| **T13** | `PAUSED` | `USER_RESUME` | `RUNNING` | User clicks resume & window re-focused |
| **T14** | `PAUSED` | `ABORT_TRIGGERED` | `STOPPED` | User clicks abort while paused |
| **T15** | `ERROR_RECOVERY` | `POLICY_RETRY` | `RUNNING` | `retry_count < max_retries` |
| **T16** | `ERROR_RECOVERY` | `POLICY_SKIP` | `RUNNING` | Recovery policy is `skip_step` |
| **T17** | `ERROR_RECOVERY` | `POLICY_ABORT` | `ERROR` | Recovery policy is `abort` or retries exhausted |
| **T18** | `STOPPING` | `CLEANUP_DONE` | `STOPPED` | Modifiers released, inputs flushed |
| **T19** | `STOPPED` | `RESET` | `IDLE` | Workflow reset requested |
| **T20** | `COMPLETED` | `RESET` | `IDLE` | Workflow reset requested |
| **T21** | `ERROR` | `RESET` | `IDLE` | Workflow reset requested |

### 3.4 Python FSM Implementation Structure
```python
class InvalidTransitionError(Exception):
    def __init__(self, from_state: ExecutionState, event: FSMEvent):
        super().__init__(
            f"Invalid FSM transition: cannot transition from state '{from_state.value}' "
            f"via event '{event.value}'."
        )
        self.from_state = from_state
        self.event = event

class ExecutionFSM:
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
            ExecutionState.STOPPING
        )

    @property
    def is_terminal(self) -> bool:
        return self._state in (ExecutionState.COMPLETED, ExecutionState.STOPPED, ExecutionState.ERROR)
```

---

## 4. Module Blueprint 3: `src/kutomoto/engine/runner.py`

### 4.1 Design Objectives
- Coordinate end-to-end asynchronous workflow execution loop using `asyncio`.
- Dispatch all 10 atomic actions to Win32 automation primitives with appropriate coordinate conversion and delay timing.
- Enforce the Pre-Step Loss-of-Focus Guardian: verify `GetForegroundWindow() == target_hwnd` before injecting mouse/keystrokes; trigger auto-pause on discrepancy.
- Support real-time pause/resume signals and emergency abort interrupt (< 50ms).
- Stream granular step telemetry events (`step_started`, `step_completed`, `countdown_tick`, etc.) to WebSocket clients.
- Implement error recovery policies (`abort`, `retry_step`, `prompt_user`, `skip_step`).

### 4.2 Class Architecture & Win32 Driver Interface Contract

The runner interacts with the Win32 automation driver via a well-defined interface:
```python
class IWin32Driver:
    """Protocol / Interface expected from src/kutomoto/automation/"""
    def set_dpi_awareness(self) -> bool: ...
    def find_window(self, title_pattern: str, match_mode: str = "contains", process_name: Optional[str] = None) -> Optional[int]: ...
    def focus_window(self, hwnd: int) -> bool: ...
    def get_foreground_window(self) -> int: ...
    def get_client_rect(self, hwnd: int) -> Tuple[int, int, int, int]: ... # left, top, right, bottom
    def client_to_screen(self, hwnd: int, x: int, y: int) -> Tuple[int, int]: ...
    def send_click(self, x: int, y: int, button: str = "left", click_count: int = 1) -> None: ...
    def send_text(self, text: str, delay_between_keys_ms: int = 20, use_clipboard_threshold: int = 40) -> None: ...
    def send_key_press(self, key_name: str, repeat_count: int = 1) -> None: ...
    def send_hotkey(self, modifiers: List[str], key: str) -> None: ...
    def clear_field(self, strategy: str = "select_all_backspace") -> None: ...
    def send_scroll(self, delta_x: int, delta_y: int) -> None: ...
    def release_all_modifiers(self) -> None: ...
```

### 4.3 Execution Context Model
```python
@dataclass
class ExecutionContext:
    workflow: KutomotoWorkflow
    execution_id: str
    target_hwnd: Optional[int] = None
    target_bounds: Optional[Tuple[int, int, int, int]] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    current_step_index: int = 0
    step_retry_count: int = 0
    is_paused: bool = False
    abort_requested: bool = False
    pause_event: asyncio.Event = field(default_factory=asyncio.Event)
    start_time: float = 0.0
    operator_username: str = ""
    host_machine: str = ""
```

### 4.4 Step Dispatchers Implementation Blueprint

The runner implements 10 dedicated private methods for atomic actions:

#### 1. `_execute_focus_window(step, context)`
```python
async def _execute_focus_window(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
    pattern = step.parameters.window_title_pattern or ctx.workflow.target_application.window_title_pattern
    mode = step.parameters.match_mode or ctx.workflow.target_application.match_mode
    proc = step.parameters.process_name or ctx.workflow.target_application.process_name

    hwnd = self._driver.find_window(pattern, match_mode=mode.value, process_name=proc)
    if not hwnd:
        raise RuntimeError(f"Target window matching '{pattern}' (process: {proc}) not found.")
    
    ctx.target_hwnd = hwnd
    success = self._driver.focus_window(hwnd)
    if not success:
        raise RuntimeError(f"Failed to bring target window 0x{hwnd:08X} to foreground.")
    
    ctx.target_bounds = self._driver.get_client_rect(hwnd)
```

#### 2. `_execute_click(step, context)`
```python
async def _execute_click(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
    p = step.parameters
    if p.coordinate_mode == CoordinateMode.NORMALIZED:
        if p.norm_x is None or p.norm_y is None:
            raise ValueError(f"Normalized click requires norm_x and norm_y in step {step.sequence_index}")
        if not ctx.target_hwnd:
            raise RuntimeError("Cannot compute normalized coordinates: target_hwnd not resolved.")
        
        rect = self._driver.get_client_rect(ctx.target_hwnd) # (left, top, right, bottom)
        client_w = rect[2] - rect[0]
        client_h = rect[3] - rect[1]
        client_x = int(round(p.norm_x * client_w))
        client_y = int(round(p.norm_y * client_h))
        screen_x, screen_y = self._driver.client_to_screen(ctx.target_hwnd, client_x, client_y)
    elif p.coordinate_mode == CoordinateMode.WINDOW_CLIENT:
        screen_x, screen_y = self._driver.client_to_screen(ctx.target_hwnd, int(p.x or 0), int(p.y or 0))
    else: # Screen coordinates
        screen_x, screen_y = int(p.x or 0), int(p.y or 0)

    self._driver.send_click(screen_x, screen_y, button=p.button.value, click_count=p.click_count)
```

#### 3. `_execute_type_text(step, context)`
```python
async def _execute_type_text(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
    raw_text = step.parameters.text or ""
    # Variable resolution: replace {{var_name}} with runtime value
    resolved_text = self._interpolate_variables(raw_text, ctx.variables)
    
    # Edge case E14: Blank or empty string payload bypass typing loop
    if not resolved_text:
        return

    delay = step.parameters.keystroke_delay_ms or ctx.workflow.execution_settings.typing_speed_ms
    self._driver.send_text(
        resolved_text,
        delay_between_keys_ms=delay,
        use_clipboard_threshold=getattr(step.parameters, 'use_clipboard_threshold', 40)
    )
```

#### 4. `_execute_key_press(step, context)`
```python
async def _execute_key_press(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
    key = step.parameters.key or "tab"
    repeat = step.parameters.repeat_count or 1
    self._driver.send_key_press(key, repeat_count=repeat)
```

#### 5. `_execute_hotkey(step, context)`
```python
async def _execute_hotkey(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
    keys = step.parameters.keys or []
    if not keys:
        return
    modifiers = [k.lower() for k in keys[:-1]]
    key = keys[-1].lower()
    self._driver.send_hotkey(modifiers, key)
```

#### 6. `_execute_clear_field(step, context)`
```python
async def _execute_clear_field(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
    strategy = step.parameters.clear_strategy.value if step.parameters.clear_strategy else "select_all_backspace"
    self._driver.clear_field(strategy=strategy)
```

#### 7. `_execute_delay(step, context)`
```python
async def _execute_delay(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
    duration_ms = step.parameters.duration_ms or 0
    # Interruptible sleep in 50ms increments to allow instant abort
    remaining = duration_ms / 1000.0
    while remaining > 0:
        if ctx.abort_requested:
            break
        chunk = min(0.05, remaining)
        await asyncio.sleep(chunk)
        remaining -= chunk
```

#### 8. `_execute_submit(step, context)`
```python
async def _execute_submit(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
    method = step.parameters.submit_method or SubmitMethod.ENTER_KEY
    if method == SubmitMethod.ENTER_KEY:
        self._driver.send_key_press("enter", repeat_count=1)
    elif method == SubmitMethod.BUTTON_CLICK:
        # Re-use click logic with button coordinates
        await self._execute_click(step, ctx)
```

#### 9. `_execute_scroll(step, context)`
```python
async def _execute_scroll(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
    dx = step.parameters.delta_x
    dy = step.parameters.delta_y
    self._driver.send_scroll(delta_x=dx, delta_y=dy)
```

#### 10. `_execute_prompt_user_input(step, context)`
```python
async def _execute_prompt_user_input(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
    var_name = step.parameters.variable_name
    msg = step.parameters.prompt_message or f"Enter value for {var_name}:"
    
    # Broadcast prompt event over WebSocket / callback
    await self._emit_telemetry("user_prompt_requested", {
        "variable_name": var_name,
        "prompt_message": msg,
        "step_index": step.sequence_index
    })
    
    # Await response from prompt handler or UI resolver
    value = await self._prompt_resolver.request_input(var_name, msg, step.parameters.is_secret)
    ctx.variables[var_name] = value
```

### 4.5 Pre-Step Loss-of-Focus Guardian Check
```python
async def _check_loss_of_focus(self, ctx: ExecutionContext) -> None:
    """Edge Case E13: Active Browser Tab or Window Switching Guardian."""
    if not ctx.target_hwnd:
        return
    
    current_fg = self._driver.get_foreground_window()
    if current_fg != ctx.target_hwnd:
        # Trigger Loss-of-Focus FSM transition to PAUSED (T10)
        await self._fsm.trigger(FSMEvent.FOCUS_LOST)
        await self._emit_telemetry("focus_lost_warning", {
            "expected_hwnd": ctx.target_hwnd,
            "actual_hwnd": current_fg,
            "message": "Target application lost active focus. Execution automatically paused."
        })
        # Wait until operator refocuses target window or clicks resume
        await ctx.pause_event.wait()
```

### 4.6 Complete Execution Loop & Error Recovery

```python
class WorkflowRunner:
    def __init__(
        self,
        driver: IWin32Driver,
        audit_logger: "AuditLogger",
        telemetry_callback: Optional[Callable[[str, Dict[str, Any]], Any]] = None
    ):
        self._driver = driver
        self._audit_logger = audit_logger
        self._telemetry_cb = telemetry_callback
        self._fsm = ExecutionFSM()
        self._ctx: Optional[ExecutionContext] = None

    async def execute(
        self,
        workflow: KutomotoWorkflow,
        runtime_variables: Optional[Dict[str, Any]] = None
    ) -> "KutomotoAuditLog":
        # T01: IDLE -> VALIDATING
        await self._fsm.trigger(FSMEvent.EXECUTE_START)
        
        # Initialize Context
        ctx = ExecutionContext(
            workflow=workflow,
            execution_id=str(uuid.uuid4()),
            variables={v.name: v.default_value for v in workflow.variables},
            start_time=asyncio.get_running_loop().time(),
            operator_username=os.getlogin() if hasattr(os, "getlogin") else "enterprise_user",
            host_machine=platform.node()
        )
        if runtime_variables:
            ctx.variables.update(runtime_variables)
        self._ctx = ctx

        # Validation Guard Check
        missing_vars = [v.name for v in workflow.variables if v.required and not ctx.variables.get(v.name)]
        if missing_vars:
            await self._fsm.trigger(FSMEvent.VALIDATION_FAILED)
            raise ValueError(f"Workflow execution blocked: missing required variables: {missing_vars}")

        # T02: VALIDATING -> COUNTDOWN
        await self._fsm.trigger(FSMEvent.VALIDATION_OK)
        
        # Countdown Phase
        cd_secs = workflow.execution_settings.countdown_seconds
        for rem in range(cd_secs, 0, -1):
            if ctx.abort_requested:
                await self._fsm.trigger(FSMEvent.ABORT_TRIGGERED) # T06
                return self._finalize_audit(ctx, "ABORTED")
            await self._emit_telemetry("countdown_tick", {"remaining": rem})
            await self._fsm.trigger(FSMEvent.COUNTDOWN_TICK) # T04
            await asyncio.sleep(1.0)

        # T05: COUNTDOWN -> RUNNING
        await self._fsm.trigger(FSMEvent.COUNTDOWN_DONE)
        
        # Set DPI Awareness
        self._driver.set_dpi_awareness()

        # Step Execution Loop
        total_steps = len(workflow.steps)
        for idx, step in enumerate(workflow.steps):
            ctx.current_step_index = idx + 1
            if not step.enabled:
                self._audit_logger.record_skipped(idx + 1, step.action_type.value, step.label)
                continue

            # Check abort request
            if ctx.abort_requested:
                await self._fsm.trigger(FSMEvent.ABORT_TRIGGERED) # T11
                await self._cleanup_after_abort()
                await self._fsm.trigger(FSMEvent.CLEANUP_DONE)   # T18
                return self._finalize_audit(ctx, "ABORTED")

            # Pre-step Focus Guardian
            if step.action_type != ActionType.FOCUS_WINDOW:
                await self._check_loss_of_focus(ctx)

            # Pre-delay
            if step.pre_delay_ms > 0:
                await asyncio.sleep(step.pre_delay_ms / 1000.0)

            # Step dispatch with retry loop
            step_success = False
            retries_remaining = workflow.execution_settings.max_step_retries
            
            while not step_success:
                t0 = asyncio.get_running_loop().time()
                try:
                    await self._emit_telemetry("step_started", {
                        "step_index": idx + 1,
                        "action_type": step.action_type.value,
                        "label": step.label
                    })
                    
                    await self._dispatch_action(step, ctx)
                    
                    latency = (asyncio.get_running_loop().time() - t0) * 1000.0
                    self._audit_logger.record_success(
                        step_index=idx + 1,
                        action_type=step.action_type.value,
                        label=step.label,
                        parameters_summary=self._summarize_parameters(step),
                        latency_ms=latency
                    )
                    await self._emit_telemetry("step_completed", {
                        "step_index": idx + 1,
                        "latency_ms": latency
                    })
                    step_success = True
                    # T07: RUNNING -> RUNNING
                    await self._fsm.trigger(FSMEvent.STEP_SUCCESS)

                except Exception as ex:
                    latency = (asyncio.get_running_loop().time() - t0) * 1000.0
                    policy = workflow.execution_settings.error_recovery_policy
                    
                    # T12: RUNNING -> ERROR_RECOVERY
                    await self._fsm.trigger(FSMEvent.STEP_EXCEPTION)
                    
                    if policy == ErrorRecoveryPolicy.RETRY_STEP and retries_remaining > 0:
                        retries_remaining -= 1
                        ctx.step_retry_count += 1
                        self._audit_logger.record_retried(
                            step_index=idx + 1,
                            action_type=step.action_type.value,
                            label=step.label,
                            error_details=str(ex)
                        )
                        await asyncio.sleep(0.5) # Backoff
                        await self._fsm.trigger(FSMEvent.POLICY_RETRY) # T15
                        continue
                    elif policy == ErrorRecoveryPolicy.SKIP_STEP:
                        self._audit_logger.record_skipped(
                            step_index=idx + 1,
                            action_type=step.action_type.value,
                            label=step.label,
                            error_details=str(ex)
                        )
                        await self._fsm.trigger(FSMEvent.POLICY_SKIP) # T16
                        step_success = True
                    else: # ABORT
                        self._audit_logger.record_failure(
                            step_index=idx + 1,
                            action_type=step.action_type.value,
                            label=step.label,
                            parameters_summary=self._summarize_parameters(step),
                            latency_ms=latency,
                            error_details=str(ex)
                        )
                        await self._fsm.trigger(FSMEvent.POLICY_ABORT) # T17
                        return self._finalize_audit(ctx, "FAILED")

            # Post-delay
            post_delay = step.post_delay_ms or workflow.execution_settings.default_step_delay_ms
            if post_delay > 0:
                await asyncio.sleep(post_delay / 1000.0)

        # T08: RUNNING -> COMPLETED
        await self._fsm.trigger(FSMEvent.ALL_STEPS_DONE)
        return self._finalize_audit(ctx, "SUCCESS")

    async def pause(self) -> None:
        if self._fsm.state == ExecutionState.RUNNING:
            await self._fsm.trigger(FSMEvent.USER_PAUSE) # T09
            if self._ctx:
                self._ctx.pause_event.clear()
            await self._emit_telemetry("execution_paused", {})

    async def resume(self) -> None:
        if self._fsm.state == ExecutionState.PAUSED:
            if self._ctx and self._ctx.target_hwnd:
                self._driver.focus_window(self._ctx.target_hwnd)
                self._ctx.pause_event.set()
            await self._fsm.trigger(FSMEvent.USER_RESUME) # T13
            await self._emit_telemetry("execution_resumed", {})

    async def abort(self) -> None:
        if self._ctx:
            self._ctx.abort_requested = True
            if self._ctx.pause_event:
                self._ctx.pause_event.set()
```

---

## 5. Module Blueprint 4: `src/kutomoto/engine/audit.py`

### 5.1 Design Objectives
- Strict compliance with `docs/SPECIFICATION.md` Section 10.1 (Structured Audit Log JSON Schema Draft 2020-12).
- Automatic embedding of mandatory intellectual property watermark: `"Copyrights reserved to 90Studio"`.
- Credential Masking Algorithm: any payload associated with `is_secret=True`, password fields, or secret variables is redacted as `********`.
- Output immutable JSON audit trail records to disk (`~/.kutomoto/audit/` or designated directory).

### 5.2 Audit Schema Models (Pydantic V2)
```python
"""
90Studio Compliance Audit Trail Models & Logger.
Copyrights reserved to 90Studio
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timezone

class AuditTargetApplication(BaseModel):
    title: str = Field(..., description="Target window caption")
    hwnd: int = Field(..., description="Win32 Window Handle integer")
    process_name: str = Field(..., description="Target process executable name")
    pid: Optional[int] = Field(None, description="Process ID")

class AuditExecutionSummary(BaseModel):
    total_steps: int = Field(..., ge=0)
    successful_steps: int = Field(..., ge=0)
    failed_steps: int = Field(..., ge=0)
    retried_steps: int = Field(..., ge=0)
    duration_seconds: float = Field(..., ge=0.0)
    final_status: Literal["SUCCESS", "FAILED", "ABORTED"]

class AuditStepEvent(BaseModel):
    step_index: int = Field(..., ge=1)
    action_type: str = Field(...)
    label: Optional[str] = None
    timestamp_offset_ms: int = Field(..., ge=0)
    parameters_summary: str = Field(...)
    latency_ms: float = Field(..., ge=0.0)
    status: Literal["SUCCESS", "ERROR", "SKIPPED", "RETRIED"]
    error_details: Optional[str] = None

class KutomotoAuditLog(BaseModel):
    audit_version: Literal["1.0.0"] = "1.0.0"
    system: Literal["kutomoto"] = "kutomoto"
    copyright: Literal["Copyrights reserved to 90Studio"] = "Copyrights reserved to 90Studio"
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = Field(...)
    workflow_name: str = Field(...)
    source_mode: Optional[Literal["visual_designer_generated", "manual_step_flow", "hybrid"]] = "manual_step_flow"
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    operator_username: str = Field(...)
    host_machine: str = Field(...)
    os_version: str = Field(...)
    target_application: AuditTargetApplication
    execution_summary: AuditExecutionSummary
    step_events: List[AuditStepEvent]
```

### 5.3 Credential Masking Implementation
```python
class CredentialMasker:
    """Masks secret values in audit summaries and execution logs."""
    MASK_STRING = "********"

    @classmethod
    def mask_parameter_summary(cls, action_type: str, params: Any, is_secret: bool = False) -> str:
        if action_type == "type_text":
            if is_secret or getattr(params, "is_secret", False):
                char_count = len(getattr(params, "text", "") or "")
                return f"text='{cls.MASK_STRING}' ({char_count} chars, masked), pacing={getattr(params, 'keystroke_delay_ms', 20)}ms"
            return f"text='{getattr(params, 'text', '')}', pacing={getattr(params, 'keystroke_delay_ms', 20)}ms"
        
        elif action_type == "click":
            mode = getattr(params, "coordinate_mode", "normalized")
            if mode == "normalized":
                return f"norm_coords=({getattr(params, 'norm_x', 0):.4f}, {getattr(params, 'norm_y', 0):.4f}), button={getattr(params, 'button', 'left')}"
            return f"screen_coords=({getattr(params, 'x', 0)}, {getattr(params, 'y', 0)}), button={getattr(params, 'button', 'left')}"

        elif action_type == "focus_window":
            return f"pattern='{getattr(params, 'window_title_pattern', '')}', process='{getattr(params, 'process_name', '')}'"

        elif action_type == "key_press":
            return f"key={getattr(params, 'key', 'tab')}, repeat={getattr(params, 'repeat_count', 1)}"

        elif action_type == "hotkey":
            return f"keys={getattr(params, 'keys', [])}"

        elif action_type == "clear_field":
            return f"strategy={getattr(params, 'clear_strategy', 'select_all_backspace')}"

        elif action_type == "delay":
            return f"duration_ms={getattr(params, 'duration_ms', 0)}"

        elif action_type == "submit":
            return f"method={getattr(params, 'submit_method', 'enter_key')}"

        elif action_type == "prompt_user_input":
            var = getattr(params, "variable_name", "")
            if is_secret or getattr(params, "is_password", False):
                return f"prompt for variable '{var}' (secret input)"
            return f"prompt for variable '{var}'"

        return str(params)
```

### 5.4 AuditLogger Class Structure
```python
class AuditLogger:
    def __init__(self, execution_id: str, workflow: "KutomotoWorkflow"):
        self.execution_id = execution_id
        self.workflow = workflow
        self.start_perf = asyncio.get_running_loop().time()
        self.step_events: List[AuditStepEvent] = []
        self._target_app_info = AuditTargetApplication(
            title=workflow.target_application.window_title_pattern,
            hwnd=0,
            process_name=workflow.target_application.process_name or "unknown",
            pid=0
        )

    def set_target_app_details(self, hwnd: int, title: str, process_name: str, pid: Optional[int] = None) -> None:
        self._target_app_info = AuditTargetApplication(
            title=title,
            hwnd=hwnd,
            process_name=process_name,
            pid=pid
        )

    def _offset_ms(self) -> int:
        return int((asyncio.get_running_loop().time() - self.start_perf) * 1000)

    def record_success(self, step_index: int, action_type: str, label: Optional[str], parameters_summary: str, latency_ms: float) -> None:
        self.step_events.append(AuditStepEvent(
            step_index=step_index,
            action_type=action_type,
            label=label,
            timestamp_offset_ms=self._offset_ms(),
            parameters_summary=parameters_summary,
            latency_ms=round(latency_ms, 2),
            status="SUCCESS"
        ))

    def record_failure(self, step_index: int, action_type: str, label: Optional[str], parameters_summary: str, latency_ms: float, error_details: str) -> None:
        self.step_events.append(AuditStepEvent(
            step_index=step_index,
            action_type=action_type,
            label=label,
            timestamp_offset_ms=self._offset_ms(),
            parameters_summary=parameters_summary,
            latency_ms=round(latency_ms, 2),
            status="ERROR",
            error_details=error_details
        ))

    def record_skipped(self, step_index: int, action_type: str, label: Optional[str], error_details: Optional[str] = None) -> None:
        self.step_events.append(AuditStepEvent(
            step_index=step_index,
            action_type=action_type,
            label=label,
            timestamp_offset_ms=self._offset_ms(),
            parameters_summary="Step skipped",
            latency_ms=0.0,
            status="SKIPPED",
            error_details=error_details
        ))

    def record_retried(self, step_index: int, action_type: str, label: Optional[str], error_details: str) -> None:
        self.step_events.append(AuditStepEvent(
            step_index=step_index,
            action_type=action_type,
            label=label,
            timestamp_offset_ms=self._offset_ms(),
            parameters_summary="Step execution retried",
            latency_ms=0.0,
            status="RETRIED",
            error_details=error_details
        ))

    def generate_log(self, final_status: Literal["SUCCESS", "FAILED", "ABORTED"]) -> KutomotoAuditLog:
        duration = round(asyncio.get_running_loop().time() - self.start_perf, 2)
        successful = sum(1 for e in self.step_events if e.status == "SUCCESS")
        failed = sum(1 for e in self.step_events if e.status == "ERROR")
        retried = sum(1 for e in self.step_events if e.status == "RETRIED")
        
        return KutomotoAuditLog(
            workflow_id=self.workflow.id,
            workflow_name=self.workflow.name,
            source_mode=self.workflow.source_mode.value,
            operator_username=os.getlogin() if hasattr(os, "getlogin") else "enterprise_user",
            host_machine=platform.node(),
            os_version=f"{platform.system()} {platform.release()} ({platform.version()})",
            target_application=self._target_app_info,
            execution_summary=AuditExecutionSummary(
                total_steps=len(self.workflow.steps),
                successful_steps=successful,
                failed_steps=failed,
                retried_steps=retried,
                duration_seconds=duration,
                final_status=final_status
            ),
            step_events=self.step_events
        )

    def write_to_disk(self, log: KutomotoAuditLog, base_dir: Optional[Path] = None) -> Path:
        target_dir = base_dir or (Path.home() / ".kutomoto" / "audit")
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"audit_{log.workflow_id}_{log.execution_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        out_path = target_dir / filename
        out_path.write_text(log.model_dump_json(indent=2), encoding="utf-8")
        return out_path
```

---

## 6. Unit & Integration Test Strategy

The verification strategy encompasses both unit testing of discrete engine components and integration testing of end-to-end execution sequences.

### 6.1 Test Suites Organization
```
tests/
├── test_schema.py      # Schema models, 10 actions, validation errors, 90Studio copyright
├── test_fsm.py         # 7-State FSM, 18 transitions (T01-T18), invalid transitions, callbacks
├── test_runner.py      # WorkflowRunner async loop, variable binding, retry, pause/resume, abort
└── test_audit.py       # 90Studio audit JSON schema conformance, credential masking (is_secret)
```

### 6.2 Test Matrix for FSM Transitions (T01–T18)
Each transition is tested independently in `tests/test_fsm.py`:
- `test_t01_idle_to_validating`: `EXECUTE_START` moves `IDLE` -> `VALIDATING`.
- `test_t02_validating_to_countdown`: `VALIDATION_OK` moves `VALIDATING` -> `COUNTDOWN`.
- `test_t03_validating_to_error`: `VALIDATION_FAILED` moves `VALIDATING` -> `ERROR`.
- `test_t04_countdown_tick`: `COUNTDOWN_TICK` keeps state at `COUNTDOWN`.
- `test_t05_countdown_done_to_running`: `COUNTDOWN_DONE` moves `COUNTDOWN` -> `RUNNING`.
- `test_t06_countdown_abort`: `ABORT_TRIGGERED` moves `COUNTDOWN` -> `STOPPED`.
- `test_t07_running_step_success`: `STEP_SUCCESS` keeps state at `RUNNING`.
- `test_t08_running_all_steps_done`: `ALL_STEPS_DONE` moves `RUNNING` -> `COMPLETED`.
- `test_t09_running_user_pause`: `USER_PAUSE` moves `RUNNING` -> `PAUSED`.
- `test_t10_running_focus_lost`: `FOCUS_LOST` moves `RUNNING` -> `PAUSED`.
- `test_t11_running_abort`: `ABORT_TRIGGERED` moves `RUNNING` -> `STOPPING`.
- `test_t12_running_step_exception`: `STEP_EXCEPTION` moves `RUNNING` -> `ERROR_RECOVERY`.
- `test_t13_paused_user_resume`: `USER_RESUME` moves `PAUSED` -> `RUNNING`.
- `test_t14_paused_abort`: `ABORT_TRIGGERED` moves `PAUSED` -> `STOPPED`.
- `test_t15_error_recovery_retry`: `POLICY_RETRY` moves `ERROR_RECOVERY` -> `RUNNING`.
- `test_t16_error_recovery_skip`: `POLICY_SKIP` moves `ERROR_RECOVERY` -> `RUNNING`.
- `test_t17_error_recovery_abort`: `POLICY_ABORT` moves `ERROR_RECOVERY` -> `ERROR`.
- `test_t18_stopping_cleanup_done`: `CLEANUP_DONE` moves `STOPPING` -> `STOPPED`.
- `test_invalid_transitions`: Verify that unmapped state-event pairs (e.g. `COMPLETED` -> `RUNNING`, `IDLE` -> `PAUSED`, `STOPPED` -> `RUNNING`) raise `InvalidTransitionError`.
- `test_fsm_listeners`: Verify asynchronous and synchronous listener callbacks are called in order with `(old_state, new_state, event)`.

### 6.3 Test Matrix for WorkflowRunner
A `MockWin32Driver` records all synthetic input calls without touching the operating system:
```python
class MockWin32Driver(IWin32Driver):
    def __init__(self):
        self.calls = []
        self.foreground_window = 12345
        self.client_rect = (0, 0, 1000, 800)
    
    def find_window(self, title_pattern, match_mode="contains", process_name=None):
        self.calls.append(("find_window", title_pattern, process_name))
        return 12345
    
    def focus_window(self, hwnd):
        self.calls.append(("focus_window", hwnd))
        return True
    
    def send_click(self, x, y, button="left", click_count=1):
        self.calls.append(("send_click", x, y, button, click_count))

    def send_text(self, text, delay_between_keys_ms=20, use_clipboard_threshold=40):
        self.calls.append(("send_text", text, delay_between_keys_ms))

    def send_key_press(self, key_name, repeat_count=1):
        self.calls.append(("send_key_press", key_name, repeat_count))

    def send_hotkey(self, modifiers, key):
        self.calls.append(("send_hotkey", modifiers, key))

    def clear_field(self, strategy="select_all_backspace"):
        self.calls.append(("clear_field", strategy))
```

Key test scenarios for runner:
- `test_runner_all_10_actions`: Workflow containing all 10 actions executes in order and dispatches correct driver calls.
- `test_runner_variable_interpolation`: `{{username}}` in `type_text` payload is substituted with runtime variable value.
- `test_runner_empty_text_edge_case`: Step with `text=""` executes navigation/focus but skips typing loop (Edge Case E14).
- `test_runner_loss_of_focus_guardian`: Simulating `get_foreground_window() != target_hwnd` transitions FSM to `PAUSED` and waits for resume.
- `test_runner_retry_policy`: Step failure triggers up to `max_step_retries` before transitioning to `RUNNING` or `ERROR`.
- `test_runner_skip_policy`: Step failure with `policy=skip_step` records skipped status and continues to next step.
- `test_runner_emergency_abort`: Setting `abort_requested` terminates sleep loops and transitions to `STOPPING` -> `STOPPED`.

### 6.4 Test Matrix for AuditLogger
- `test_audit_schema_conformance`: Output of `generate_log()` validates against Section 10.1 formal JSON Schema.
- `test_audit_90studio_watermark`: Copyright field strictly equals `"Copyrights reserved to 90Studio"`.
- `test_audit_credential_masking`: When `is_secret=True`, password text is redacted as `"********"` in `parameters_summary`.
- `test_audit_latency_tracking`: Each step records non-negative `latency_ms` and cumulative execution duration.

---

## 7. Package Exports & Interface Contracts

In `src/kutomoto/engine/__init__.py`:
```python
"""
kutomoto Workflow Execution Engine Subsystem.
Copyrights reserved to 90Studio
"""

from .schema import (
    KutomotoWorkflow,
    WorkflowStep,
    StepParameters,
    TargetApplication,
    ExecutionSettings,
    WorkflowVariable,
    DesignerMetadata,
    ActionType,
    ErrorRecoveryPolicy,
    TargetAppType,
    MatchMode,
    CoordinateMode,
    MouseButton,
    ClearStrategy,
    SubmitMethod,
    SourceMode,
    VariableType,
)

from .fsm import (
    ExecutionState,
    FSMEvent,
    ExecutionFSM,
    InvalidTransitionError,
)

from .runner import (
    WorkflowRunner,
    ExecutionContext,
    IWin32Driver,
)

from .audit import (
    AuditLogger,
    KutomotoAuditLog,
    AuditStepEvent,
    AuditExecutionSummary,
    AuditTargetApplication,
    CredentialMasker,
)

__all__ = [
    # Schema
    "KutomotoWorkflow",
    "WorkflowStep",
    "StepParameters",
    "TargetApplication",
    "ExecutionSettings",
    "WorkflowVariable",
    "DesignerMetadata",
    "ActionType",
    "ErrorRecoveryPolicy",
    "TargetAppType",
    "MatchMode",
    "CoordinateMode",
    "MouseButton",
    "ClearStrategy",
    "SubmitMethod",
    "SourceMode",
    "VariableType",
    # FSM
    "ExecutionState",
    "FSMEvent",
    "ExecutionFSM",
    "InvalidTransitionError",
    # Runner
    "WorkflowRunner",
    "ExecutionContext",
    "IWin32Driver",
    # Audit
    "AuditLogger",
    "KutomotoAuditLog",
    "AuditStepEvent",
    "AuditExecutionSummary",
    "AuditTargetApplication",
    "CredentialMasker",
]
```

---

## 8. Conclusion

This blueprint provides an exhaustive, production-grade architectural specification for `src/kutomoto/engine/`. It guarantees full fidelity with the Master Specification (`docs/SPECIFICATION.md`), provides complete Pydantic V2 type safety, establishes the 18-transition FSM lifecycle, coordinates async execution across web and desktop forms, and mandates 90Studio intellectual property compliance throughout.
