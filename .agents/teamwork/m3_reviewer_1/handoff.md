# Milestone 3 Review 1: Schema & Geometry Review Report

**Reviewer**: `m3_reviewer_1` (Role: Milestone 3 Reviewer 1 - Schema & Geometry Review)  
**Parent Agent**: `ce2dd708-d288-4e8f-9834-dfdb673a5856`  
**Working Directory**: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_reviewer_1`  
**Date**: 2026-11-05T00:36:30Z  

---

## 1. Review Summary

**Verdict**: **APPROVE**  
**Integrity Attestation**: **VERIFIED CLEAN** (Zero integrity violations; no hardcoded test shortcuts, no facade implementations, no dummy logic, no fabricated outputs).  
**Overall Risk Assessment**: **LOW**

---

## 2. Review Findings & Observations

### Observation 1: Schema & Validation Rigor (`src/kutomoto/designer/schema.py`)
- **CanvasDimensions Validation**:
  - `CanvasDimensions` in `schema.py:82-84`:
    ```python
    width: float = Field(..., gt=0, description="Canvas width in pixels (> 0)")
    height: float = Field(..., gt=0, description="Canvas height in pixels (> 0)")
    scale: float = Field(default=1.0, gt=0, description="Canvas display scale factor")
    ```
    Verified: Strictly enforces `gt=0` for width and height. Canvas dimensions <= 0 fail with Pydantic `ValidationError`.
- **BoxGeometry Properties**:
  - `BoxGeometry` in `schema.py:98-113`:
    ```python
    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center_x(self) -> float:
        return self.x + (self.width / 2.0)

    @property
    def center_y(self) -> float:
        return self.y + (self.height / 2.0)
    ```
    Verified: Bounding box properties are computed correctly using standard cartesian planar geometry.
- **Boundary Containment & Tolerance Epsilon**:
  - `VisualFormLayout.validate_layout_integrity` in `schema.py:335-344`:
    ```python
    if geom.right > cw + 1e-4:
        raise ValueError(
            f"Box '{b.id}' (name='{b.name}') right edge ({geom.right:.2f}) exceeds canvas width ({cw:.2f})"
        )
    if geom.bottom > ch + 1e-4:
        raise ValueError(
            f"Box '{b.id}' (name='{b.name}') bottom edge ({geom.bottom:.2f}) exceeds canvas height ({ch:.2f})"
        )
    ```
    Verified: Enforces strict boundary containment with `1e-4` epsilon, preventing floating-point precision jitter while rejecting genuine boundary overshoots.
- **Duplicate Box ID Rejection**:
  - `VisualFormLayout.validate_layout_integrity` in `schema.py:323-326`:
    ```python
    box_ids = [b.id for b in self.boxes]
    if len(box_ids) != len(set(box_ids)):
        dups = [bid for bid in box_ids if box_ids.count(bid) > 1]
        raise ValueError(f"VisualFormLayout contains duplicate box IDs: {set(dups)}")
    ```
    Verified: Multiple boxes sharing an ID are rejected with `ValueError` (or `DuplicateBoxIdError` during Pass 1 compilation).
- **Mandatory Copyright Watermark**:
  - `VisualFormLayout` in `schema.py:284-287, 310-316`:
    ```python
    copyright: Literal["Copyrights reserved to 90Studio"] = Field(
        default="Copyrights reserved to 90Studio",
        description="Mandatory 90Studio copyright watermark",
    )
    @field_validator("copyright")
    @classmethod
    def validate_copyright(cls, v: str) -> str:
        if v != "Copyrights reserved to 90Studio":
            raise ValueError("Invalid copyright. Must be exactly 'Copyrights reserved to 90Studio'")
        return v
    ```
    Verified: Alteration or omission of `"Copyrights reserved to 90Studio"` fails validation.

---

### Observation 2: Compilation Passes 1 - 3 (`src/kutomoto/designer/compiler.py`)
- **Pass 1: Structural & Geometry Validation**:
  - In `compiler.py:224-288` (for raw dictionary input) and `compiler.py:302-339` (for model input):
    - Empty layouts (`boxes` empty or None) raise `EmptyLayoutError`.
    - Zero/negative canvas dimensions raise `GeometryError`.
    - Negative box coordinates or zero/negative box dimensions raise `GeometryError`.
    - Box coordinates exceeding canvas boundaries raise `GeometryError`.
    - Duplicate box IDs raise `DuplicateBoxIdError`.
    - Note that `EmptyLayoutError`, `GeometryError`, and `DuplicateBoxIdError` inherit from both `CompilationError` and `ValueError` (`exceptions.py:14-28`), preserving both domain exception semantics and standard Python value error handling.
- **Pass 2: 2D Spatial Band Sorting & Determinism**:
  - In `compiler.py:47-85` (`_spatial_band_sort`):
    - Default band tolerance is `24.0` px (`tolerance = band_tolerance_px`).
    - If `tolerance <= 0`, dynamically computes adaptive tolerance `max(10.0, 0.5 * avg_h)`.
    - Deterministic primary sorting: `sorted(boxes, key=lambda b: (b.geometry.y, b.geometry.x))`.
    - Band partitioning: groups items whose Y-distance to band `anchor_y` is `<= tolerance`.
    - Deterministic horizontal ordering within bands: `sorted(band, key=lambda b: (b.geometry.x, b.geometry.y))`.
  - In `compiler.py:368-395`:
    - Boxes with explicit `sequence_index > 0` strictly override spatial ordering.
    - For hybrid layouts, explicit sequence boxes execute first (ordered by `sequence_index`), followed by unindexed boxes sorted via 2D spatial band sorting.
    - If duplicate sequence indices occur, secondary tie-breakers `(y, x)` maintain deterministic ordering.
- **Pass 3: Coordinate Normalization**:
  - In `schema.py:348-373` (`get_normalized_box`) and `compiler.py:399`:
    - `center_norm_x = max(0.0, min(1.0, round((geom.x + (geom.width / 2.0)) / cw, 4)))`
    - `center_norm_y = max(0.0, min(1.0, round((geom.y + (geom.height / 2.0)) / ch, 4)))`
    - Clamped strictly to `[0.0, 1.0]` and rounded to 4 decimal places.
    - `norm_w` and `norm_h` are bounded to `1.0 - norm_x` and `1.0 - norm_y` to guarantee bounds preservation.

---

### Observation 3: Verification Commands & Outputs
The following commands were executed independently:

1. **Compiler Test Suite**:
   - Command: `python -m pytest tests/test_compiler.py -v`
   - Result: **61 passed in 4.10s** (Exit code: 0)
   - Covered classes:
     - `TestVisualLayoutSchema` (12 tests) — PASSED
     - `TestCompilerPass1Validation` (7 tests) — PASSED
     - `TestCompilerPass2SpatialBandSorting` (8 tests) — PASSED
     - `TestCompilerPass3CoordinateNormalization` (5 tests) — PASSED
     - `TestCompilerPass4ActionStepSynthesis` (9 tests) — PASSED
     - `TestCompilerPass5PeepholeOptimizer` (11 tests) — PASSED
     - `TestCompilerIntegrationAndEdgeCases` (9 tests) — PASSED
2. **Full Workspace Test Suite**:
   - Command: `python -m pytest tests/ -v`
   - Result: **193 passed in 8.51s** (Exit code: 0)
   - Zero regressions across specification, engine, safety, driver, and compiler tests.
3. **Linter**:
   - Command: `python -m ruff check src/ tests/`
   - Result: **All checks passed!** (Exit code: 0)

---

## 3. Adversarial Challenges & Stress Testing

### Challenge 1: Anchor-Based Band Partitioning vs. Staggered Cascades
- **Assumption Challenged**: Fixed `anchor_y` for clustering does not trigger runaway band chaining, but could split visually close fields if a band's anchor is at the extreme top.
- **Stress Scenario**: Field A at Y=100, Field B at Y=122 (within 24px of A), Field C at Y=126 (26px from A, but only 4px from B).
- **Behavior Observed**: Field C is placed in band 2. Because Field C is > 24px from anchor A, it starts the next band. This strictly caps the vertical thickness of any single visual band to `band_tolerance_px`.
- **Verdict/Mitigation**: Robust behavior. It prevents vertical drift chaining (where fields at 100, 120, 140, 160 would collapse into a single giant row). Users can also adjust `band_tolerance_px` or specify explicit `sequence_index`.

### Challenge 2: Duplicate Sequence Indices
- **Assumption Challenged**: What happens if a user assigns identical `sequence_index` values to multiple visual boxes?
- **Stress Scenario**: Two boxes with `sequence_index=1`.
- **Behavior Observed**: The compiler's sort key `(b.sequence_index, b.geometry.y, b.geometry.x)` cleanly tie-breaks using physical Y and X coordinates, producing stable, deterministic ordering. Verified in `test_duplicate_sequence_indices_stable_order`.
- **Verdict**: Handled deterministically.

### Challenge 3: Boundary Precision with Floating Point Coordinates
- **Assumption Challenged**: Does `1e-4` epsilon allow significant out-of-bounds bleed?
- **Stress Scenario**: A box at `x=999.0001` on a `1000px` canvas.
- **Behavior Observed**: `1e-4` is `0.0001` pixels (less than 1/1000th of a single pixel). It protects against IEEE 754 floating point arithmetic imprecision (e.g., `0.1 + 0.2 != 0.3`) while catching any true pixel overflow.
- **Verdict**: Optimal engineering decision for floating point geometric tolerances.

---

## 4. Logic Chain

1. **From Schema Definitions to Validation Guarantees**:
   `CanvasDimensions` and `BoxGeometry` use Pydantic `gt=0` and `ge=0` constraints, which guarantees that negative or zero dimensions cannot be instantiated through the schema. Pass 1 of `compiler.py` mirrors this check for raw dictionaries, ensuring that all entry points are defended.
2. **From Geometry Properties to Normalization Precision**:
   `BoxGeometry.center_x` and `center_y` compute exact center coordinates. `VisualFormLayout.get_normalized_box` normalizes against canvas dimensions, applies `round(..., 4)`, and explicitly clamps values with `max(0.0, min(1.0, ...))`. This guarantees that normalized coordinates passed to downstream Win32 automation steps never exceed `[0.0, 1.0]`.
3. **From Spatial Banding to Deterministic Western Reading Order**:
   `_spatial_band_sort` sorts primarily by Y, clusters within vertical tolerance, and sorts within bands by X. Python's Timsort combined with composite tuple keys `(y, x)` and `(x, y)` guarantees identical ordering on every execution. Explicit `sequence_index` overrides spatial order, satisfying enterprise requirement R2.
4. **From Integrity Inspection to Verification Verdict**:
   Inspected all files for facade implementations, mock results, or shortcuts. Real implementations exist for all 5 compiler passes, exception classes, and schema validators. All 61 compiler tests and 193 workspace tests pass with 0 lint errors. Therefore, approval is warranted.

---

## 5. Caveats

- **Live GUI Visual Rendering**: Review covered schema, exceptions, mathematical geometry, and compiler Passes 1-3 (and end-to-end compiler integration via MockWin32Driver). The physical interactive canvas GUI widget is part of Milestones 4/5.
- **Canvas Scaling**: Canvas scaling property (`scale: float = Field(default=1.0, gt=0)`) is captured in schema; high-DPI scaling translation is handled by the Win32 driver coordinate resolution layer.

---

## 6. Conclusion

The schema, exception hierarchy, and Passes 1-3 of the Kutomoto Visual Form Designer Compiler strictly fulfill all requirements, edge cases, and safety constraints specified in the prompt and `ORIGINAL_REQUEST.md`:
- `CanvasDimensions` strictly enforces `gt=0`.
- `BoxGeometry` properly calculates `center_x`, `center_y`, `right`, and `bottom`.
- `VisualFormLayout` validates boundary containment with epsilon `1e-4`.
- Duplicate box IDs are rejected with `DuplicateBoxIdError` / `ValueError`.
- `copyright="Copyrights reserved to 90Studio"` is strictly enforced.
- Pass 1 validation reliably rejects empty layouts and invalid geometries.
- Pass 2 spatial band clustering and explicit sequence overrides are deterministic and robust.
- Pass 3 dual-coordinate normalization guarantees clamping to `[0.0, 1.0]` and 4-decimal precision.
- Zero integrity violations detected.
- 100% test pass rate (193/193 tests) and 0 linter errors.

**Verdict**: **APPROVE**

---

## 7. Independent Verification Method

To independently reproduce this verification:
```powershell
# 1. Run compiler unit & integration tests
python -m pytest tests/test_compiler.py -v

# 2. Run entire test suite across all subsystems
python -m pytest tests/ -v

# 3. Run ruff linter
python -m ruff check src/ tests/
```
Files to inspect:
- `src/kutomoto/designer/schema.py`
- `src/kutomoto/designer/exceptions.py`
- `src/kutomoto/designer/compiler.py`
- `tests/test_compiler.py`
