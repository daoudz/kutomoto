# Empirical Challenge Handoff Report: Milestone M2

**Agent**: `m2_challenger_2`  
**Date**: 2026-11-04T23:27:00Z  
**Verdict**: **FAIL**  
**Overall Risk Assessment**: **HIGH**  

---

## 1. Observation

Direct code observations from inspection and execution of empirical test harness `tests/test_m2_empirical_challenge.py`:

### Observation 1: Contract Inconsistency Between `win32_window.get_client_rect` and `runner._execute_click`
In `src/kutomoto/automation/win32_window.py` (lines 367–377):
```python
def get_client_rect(hwnd: int) -> Tuple[int, int, int, int]:
    """
    Returns (screen_left, screen_top, width, height) of the window client area.
    """
    if user32 is None:
        return (0, 0, 0, 0)
    crc = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(crc))
    pt = POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return (pt.x, pt.y, crc.right - crc.left, crc.bottom - crc.top)
```
The returned tuple is `(screen_left, screen_top, width, height)`.

However, in `src/kutomoto/engine/runner.py` (lines 267–276):
```python
            if hasattr(self._driver, "get_client_rect"):
                rect = self._driver.get_client_rect(ctx.target_hwnd)
            else:
                rect = self._driver.get_window_bounds(ctx.target_hwnd)

            client_w = rect[2] - rect[0]
            client_h = rect[3] - rect[1]
            client_x = int(round(p.norm_x * client_w))
            client_y = int(round(p.norm_y * client_h))
```
The runner computes `client_w = rect[2] - rect[0]` and `client_h = rect[3] - rect[1]`.
Because `rect[2]` is `width` (not `right`), `client_w` evaluates to `width - screen_left`.
- If a target window is located at `screen_left = 300, screen_top = 200` with `width = 800, height = 600`, `runner` calculates `client_w = 800 - 300 = 500` (error of 300px), causing a click targeting `(norm_x=0.5, norm_y=0.5)` to land at `(550, 400)` instead of `(700, 500)` — a targeting error of 150px on X and 100px on Y.
- If a target window is on a secondary monitor or right side of a display where `screen_left = 1200 > 800`, `client_w = 800 - 1200 = -400` (negative width!), causing clicks to occur inverted and completely outside the target application.
- In `src/kutomoto/engine/safety.py` (lines 452–455), `MockWin32Driver` implemented:
```python
    def get_client_rect(self, hwnd: int) -> Tuple[int, int, int, int]:
        bounds = self.get_window_bounds(hwnd)
        # Returns (left, top, right, bottom)
        return (bounds[0], bounds[1], bounds[0] + bounds[2], bounds[1] + bounds[3])
```
Because the mock returned `(left, top, right, bottom)`, it masked this targeting bug during existing unit tests.
Empirically reproduced in `tests/test_m2_empirical_challenge.py::TestAdversarialChallenges::test_adversarial_client_rect_contract_mismatch`.

### Observation 2: Emergency Escape Abort Trapped in Retry Loop Under `RETRY_STEP` Policy
In `src/kutomoto/engine/runner.py` (lines 474–521):
```python
                    # Perform safety checks
                    if step.action_type != ActionType.FOCUS_WINDOW:
                        self._safety_guard.pre_step_check(ctx.target_hwnd)

                    await self._dispatch_action(step, ctx)
                    ...
                except Exception as ex:
                    ...
                    policy = workflow.execution_settings.error_recovery_policy
                    policy_val = policy.value if hasattr(policy, "value") else str(policy)

                    # T12: RUNNING -> ERROR_RECOVERY
                    await self._fsm.trigger(FSMEvent.STEP_EXCEPTION)

                    if policy_val == ErrorRecoveryPolicy.RETRY_STEP.value and retries_remaining > 0:
                        retries_remaining -= 1
                        ctx.step_retry_count += 1
                        ...
                        await asyncio.sleep(0.05 if os.environ.get("KUTOMOTO_TEST_FAST") else 0.5)
                        await self._fsm.trigger(FSMEvent.POLICY_RETRY)  # T15
                        continue
```
When an operator presses Escape, `pre_step_check()` raises `EscapeAbortTriggered`.
Because `runner.py` catches all exceptions uniformly under `except Exception as ex:`, when `error_recovery_policy == ErrorRecoveryPolicy.RETRY_STEP`, `EscapeAbortTriggered` is retried `max_step_retries` times rather than immediately aborting. When retries expire, the execution summary records `final_status == "FAILED"` rather than `"ABORTED"`.
Empirically reproduced in `tests/test_m2_empirical_challenge.py::TestAdversarialChallenges::test_adversarial_escape_abort_retried_under_retry_policy`.

### Observation 3: Safety Guardrails Bypassed Under `SKIP_STEP` Policy
In `src/kutomoto/engine/runner.py` (lines 522–531):
```python
                    elif policy_val == ErrorRecoveryPolicy.SKIP_STEP.value:
                        if self._audit_logger:
                            self._audit_logger.record_skipped(
                                step_index=idx + 1,
                                action_type=step.action_type.value,
                                label=step.label,
                                error_details=str(ex),
                            )
                        await self._fsm.trigger(FSMEvent.POLICY_SKIP)   # T16
                        step_success = True
```
When `error_recovery_policy == ErrorRecoveryPolicy.SKIP_STEP`, if `CornerFailsafeTriggered`, `EscapeAbortTriggered`, or `MouseDisturbanceDetected` is raised, `runner.py` treats the safety violation as a skippable step error, sets `step_success = True`, and continues automating subsequent workflow steps on the desktop. The audit log then reports `final_status == "SUCCESS"`.
Empirically reproduced in `tests/test_m2_empirical_challenge.py::TestAdversarialChallenges::test_adversarial_corner_failsafe_bypassed_under_skip_policy`.

### Observation 4: Stuck Modifier Keys on Step Failure Under `RETRY_STEP` and `SKIP_STEP` Policies
In `src/kutomoto/engine/runner.py` (lines 509–545):
`await self._cleanup_after_abort()` is exclusively called on the terminal `ABORT` path (line 543).
Neither `ErrorRecoveryPolicy.RETRY_STEP` nor `ErrorRecoveryPolicy.SKIP_STEP` calls `emergency_cleanup()` or `release_all_modifiers()`.
If a step fails while a modifier key is pressed down, or if an action was interrupted, modifier keys remain pressed, corrupting operator input and subsequent steps.
Empirically reproduced in `tests/test_m2_empirical_challenge.py::TestAdversarialChallenges::test_adversarial_modifier_leak_on_skip_policy`.

### Observation 5: Unicode and Surrogate Pair Decomposition Robustness
In `src/kutomoto/automation/win32_input.py` (lines 298–316):
`send_text` properly unpacks UTF-16LE code units and dispatches them via `KEYEVENTF_UNICODE`.
Empirical round-trip decoding across 14 test sets (emojis with ZWJ and skin tones, Egyptian hieroglyphs, CJK Extension B, Arabic with tashkeel, Devanagari, Hebrew, Thai, ASCII combinations) achieved 100% character fidelity across 6,000+ code units.

---

## 2. Logic Chain

1. **Premise**: Enterprise forms filling automation relies on exact spatial pixel targeting from normalized coordinates `(norm_x, norm_y)`.
2. **From Observation 1**: In `runner._execute_click`, the calculation `client_w = rect[2] - rect[0]` assumes `rect` has format `(left, top, right, bottom)`. However, `win32_window.get_client_rect` returns `(screen_left, screen_top, width, height)`.
3. **Inference 1**: Any execution against a real Win32 window located at `screen_left > 0` produces distorted normalized coordinates. On any display where `screen_left > width`, `client_w` becomes negative. This will cause clicks to miss form elements completely in real Windows environments.
4. **Premise**: Safety guardrails (Emergency Escape, Screen-Corner Failsafe) are non-negotiable emergency stops designed to protect user environments from unintended automation actions.
5. **From Observations 2 & 3**: `WorkflowRunner.execute()` wraps step execution in a generic `try...except Exception:` block without intercepting `SafetyException` subclasses (`EscapeAbortTriggered`, `CornerFailsafeTriggered`, `MouseDisturbanceDetected`).
6. **Inference 2**: Under `ErrorRecoveryPolicy.RETRY_STEP`, an emergency stop request is treated as a transient fault and retried up to `max_step_retries` times with sleep delays, violating the emergency stop contract. Under `ErrorRecoveryPolicy.SKIP_STEP`, safety exceptions are suppressed and the robot continues executing subsequent actions.
7. **From Observation 4**: In the retry and skip exception handling paths, modifier release routines are omitted. Any failure during a modifier-involved operation leaves keys logically stuck down.
8. **Deduction**: Because the automation runner fails coordinate targeting on real Win32 windows and allows safety guardrails to be bypassed or delayed by workflow policies, Milestone M2 does not pass empirical verification.

---

## 3. Caveats

- Win32 DPI awareness mode (`SetProcessDpiAwarenessContext(-4)`) was validated via API signatures and ladder fallback, but live multi-monitor DPI scaling testing requires multi-monitor hardware connected to the runner.
- Clipboard copy/paste fallback (`send_text_clipboard`) was verified via unit tests; clipboard locks from external applications (e.g. Office or clipboard managers) can cause transient delays, which kutomoto mitigates via 5-attempt retry loop.

---

## 4. Conclusion

**Verdict: FAIL**

The implementation of Milestone M2 contains a Critical coordinate targeting defect due to an interface contract mismatch between `win32_window.py` and `runner.py`, along with High-severity safety guardrail bypasses under non-default error recovery policies (`RETRY_STEP` and `SKIP_STEP`).

### Required Mitigations Before Milestone Approval:

1. **Fix Coordinate Contract in `runner.py` / `win32_window.py`**:
   Align the return signature of `get_client_rect`. In `runner.py` line 272–273, use:
   ```python
   # If rect is (screen_left, screen_top, width, height):
   client_w = rect[2]
   client_h = rect[3]
   # Or standardize get_client_rect across driver and mock to return (left, top, right, bottom)
   ```
2. **Prioritize Safety Exceptions Over Error Recovery Policies in `runner.py`**:
   Before handling `ErrorRecoveryPolicy`, catch `SafetyException` (or `EscapeAbortTriggered`, `CornerFailsafeTriggered`) explicitly:
   ```python
   except SafetyException as sex:
       await self._fsm.trigger(FSMEvent.ABORT_TRIGGERED)
       await self._cleanup_after_abort()
       return self._finalize_audit(ctx, "ABORTED")
   except Exception as ex:
       # Standard error recovery policy logic...
   ```
3. **Release Modifiers on Step Retries and Skips**:
   In `runner.py`, invoke `self._driver.release_all_modifiers()` in both `RETRY_STEP` and `SKIP_STEP` branches to prevent stuck modifier keys.

---

## 5. Verification Method

### Test Execution Commands
Execute the empirical challenge test suite:
```powershell
python -m pytest tests/test_m2_empirical_challenge.py -v
```

Execute the complete project test suite:
```powershell
python -m pytest -v
```

### Specific Files to Inspect
- `tests/test_m2_empirical_challenge.py` (36 test cases reproducing defects and verifying Unicode/coordinates)
- `src/kutomoto/automation/win32_window.py` (lines 367–377)
- `src/kutomoto/engine/runner.py` (lines 267–281, 474–545)
- `src/kutomoto/engine/safety.py` (lines 452–455)

### Invalidation Conditions
This challenge report is invalidated if:
1. `win32_window.get_client_rect` is documented and proven to return `(left, top, right, bottom)` matching `runner.py`'s subtraction, and all dependent callers are verified.
2. Safety exceptions are shown to bypass the step retry/skip loop through an alternative uninspected mechanism.
