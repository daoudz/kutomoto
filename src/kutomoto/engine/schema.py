"""
kutomoto.engine.schema
Unified Action Workflow Schema Models (Pydantic V2).
Copyrights reserved to 90Studio
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Literal, Optional
import uuid

from pydantic import BaseModel, Field, field_validator, model_validator


# ==============================================================================
# 1. ENUMERATIONS
# ==============================================================================

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


# ==============================================================================
# 2. ATOMIC ACTION PARAMETER MODELS
# ==============================================================================

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
    use_clipboard_threshold: int = Field(default=40, ge=0)
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
    is_password: bool = Field(default=False)


# ==============================================================================
# 3. WORKFLOW STEP & APPLICATION CONFIG MODELS
# ==============================================================================

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
        description="Mandatory 90Studio copyright watermark",
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
