"""
Shared pytest fixtures for kutomoto specification and compiler testing.
Copyrights reserved to 90Studio
"""
import json
import re
from pathlib import Path
import pytest

SPEC_PATH = Path(__file__).resolve().parent.parent / "docs" / "SPECIFICATION.md"

@pytest.fixture(scope="session")
def spec_content() -> str:
    assert SPEC_PATH.exists(), f"SPECIFICATION.md not found at {SPEC_PATH}"
    return SPEC_PATH.read_text(encoding="utf-8")

@pytest.fixture(scope="session")
def visual_layout_schema(spec_content: str) -> dict:
    match = re.search(r"### 7\.2 VisualFormLayout Formal JSON Schema.*?```json\s*(.*?)\s*```", spec_content, re.DOTALL)
    assert match, "Could not extract VisualFormLayout schema from Section 7.2"
    return json.loads(match.group(1))

@pytest.fixture(scope="session")
def workflow_schema(spec_content: str) -> dict:
    match = re.search(r"### 7\.3 Unified Action Workflow Formal JSON Schema.*?```json\s*(.*?)\s*```", spec_content, re.DOTALL)
    assert match, "Could not extract Unified Action Workflow schema from Section 7.3"
    return json.loads(match.group(1))

@pytest.fixture(scope="session")
def compiler_func(spec_content: str):
    lines = spec_content.splitlines()
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if "### 8.1 Reference Compilation Implementation" in line:
            for j in range(i + 1, i + 10):
                if lines[j].strip().startswith("```python"):
                    start_idx = j + 1
                    break
        elif start_idx is not None and line.strip().startswith("```") and i > start_idx:
            end_idx = i
            break
    assert start_idx is not None and end_idx is not None, "Could not locate compiler code block boundaries"
    code = "\n".join(lines[start_idx:end_idx])
    scope = {}
    exec(code, scope)
    assert "compile_visual_boxes_to_workflow" in scope, "compile_visual_boxes_to_workflow not defined in code"
    return scope["compile_visual_boxes_to_workflow"]

@pytest.fixture(scope="session")
def win32_input_struct(spec_content: str):
    match = re.search(r"### 6\.2 64-bit ABI Memory Layout.*?```python\s*(.*?)\s*```", spec_content, re.DOTALL)
    assert match, "Could not locate ctypes struct definitions in Section 6.2"
    code = match.group(1)
    scope = {}
    exec(code, scope)
    assert "INPUT" in scope, "INPUT struct not found in ctypes block"
    return scope["INPUT"]
