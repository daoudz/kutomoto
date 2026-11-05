# Dispatch for explorer_survey_3

## Objective
Survey the visual form designer mechanics, workflow representation data structures, translation engine, and execution loop for kutomoto.

## Inputs
- ORIGINAL_REQUEST path: c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md
- Read ORIGINAL_REQUEST.md thoroughly before starting.

## Instructions
1. Design the Visual Form Designer interaction model:
   - Drawing bounding boxes representing form fields (click-and-drag or point-based box definition).
   - Assigning properties per box: field name/label, field type (text, number, date, select, checkbox, submit button), execution sequence index (order 1, 2, 3...), input text value or dynamic variable, navigation action (Tab, Enter, Click).
   - Visual reordering and visual preview.
2. Design the Workflow Engine & Action Schema:
   - Unified Action Workflow JSON/data schema supporting actions: `click`, `type_text`, `key_press` (Tab, Enter, Escape, etc.), `delay`, `focus_window`, `submit`.
   - The translation algorithm from visual box sequence to executable action workflow.
   - Support for manual custom fill flows (creating steps step-by-step) as well as auto-generated flows from visual boxes.
3. Design the Execution & Error Handling Engine:
   - Target application attachment (by window title, process, or countdown/hotkey trigger to allow user to focus target).
   - Execution state machine: Idle, Countdown, Running, Paused, Completed, Error.
   - Step execution loop with configurable inter-action delays, error recovery, and execution logs.
4. Write your report to `c:\Users\daoud\projects\kutomoto\.agents\teamwork\explorer_survey_3\engine_survey_report.md` and deliver `handoff.md`.
