# Dispatch for m1_explorer_3

## Objective
Explore and provide the precise data schemas, workflow rules, visual compiler mechanics, and audit logging specifications to be specified in `docs/SPECIFICATION.md`.

## Inputs
- ORIGINAL_REQUEST path: c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md
- PROJECT.md path: c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md
- Survey engine report: c:\Users\daoud\projects\kutomoto\.agents\teamwork\explorer_survey_3\engine_survey_report.md

## Instructions
1. Read ORIGINAL_REQUEST.md and PROJECT.md.
2. Review the survey engine findings in `engine_survey_report.md`.
3. Formulate the engine and designer specification sections for `docs/SPECIFICATION.md` detailing:
   - VisualFormLayout schema and VisualBox attributes (geometry, normalized dual-coordinates, sequence index, navigation)
   - Unified Action Workflow JSON Schema (Draft 2020-12) supporting 10 atomic actions (`focus_window`, `click`, `type_text`, `key_press`, `hotkey`, `clear_field`, `delay`, `submit`, `scroll`, `prompt_user_input`)
   - 5-pass compilation algorithm from visual layout to action workflow
   - 7-state execution finite state machine (FSM)
   - 90Studio audit log schema and compliance trail
4. Recommend concrete guidance for the Worker who will author `docs/SPECIFICATION.md`.
5. Write your report to `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_explorer_3\report.md` and deliver `handoff.md`.

## 2026-11-04T22:18:42Z
From ce2dd708-d288-4e8f-9834-dfdb673a5856:
You are m1_explorer_3.
Your working directory is: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_explorer_3
Your task instructions are in: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_explorer_3\DISPATCH.md
Read c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md, c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md, and your DISPATCH.md.
Formulate the engine rules, visual compiler mechanics, Unified Action Schema, VisualFormLayout schema, and 90Studio audit log specifications for docs/SPECIFICATION.md.
Write your report to c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_explorer_3\report.md and deliver handoff.md. Report back via send_message when done.
