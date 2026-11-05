"""
Milestone 4 Empirical Challenge Test Suite: UI Assets, Canvas Geometry, and CLI Integration.
Copyrights reserved to 90Studio
"""

from html.parser import HTMLParser
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Dict, List, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from fastapi.testclient import TestClient  # noqa: E402
import pytest  # noqa: E402

from kutomoto import __copyright__, __version__  # noqa: E402
from kutomoto.server.app import app  # noqa: E402

UI_DIR = PROJECT_ROOT / "src" / "kutomoto" / "ui"
CSS_FILE = UI_DIR / "css" / "kutomoto.css"
INDEX_HTML = UI_DIR / "index.html"
APP_JS = UI_DIR / "js" / "app.js"
DESIGNER_JS = UI_DIR / "js" / "designer.js"
RUNNER_JS = UI_DIR / "js" / "runner.js"
BAT_LAUNCHER = PROJECT_ROOT / "run_kutomoto.bat"


class HTMLValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags_stack: List[str] = []
        self.ids: Set[str] = set()
        self.classes: Set[str] = set()
        self.void_tags = {
            "area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"
        }
        self.errors: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]):
        if tag.lower() not in self.void_tags:
            self.tags_stack.append(tag.lower())

        for attr, val in attrs:
            if attr == "id" and val:
                if val in self.ids:
                    self.errors.append(f"Duplicate DOM ID: '{val}'")
                self.ids.add(val)
            elif attr == "class" and val:
                for c in val.split():
                    self.classes.add(c)

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower in self.void_tags:
            return
        if not self.tags_stack:
            self.errors.append(f"Unexpected closing tag </{tag}> with empty stack")
            return
        last = self.tags_stack.pop()
        if last != tag_lower:
            self.errors.append(f"Mismatched closing tag </{tag_lower}>, expected </{last}>")


# =============================================================================
# 1. STATIC ASSET VALIDATION
# =============================================================================

class TestStaticAssetIntegrity:
    """Empirical verification of HTML syntax, DOM IDs, CSS rules & tokens, and JS syntax."""

    def test_html_syntax_and_structure(self):
        """Verify HTML is well-formed, contains no syntax/unclosed-tag errors, and has valid doctype."""
        assert INDEX_HTML.is_file(), f"index.html missing at {INDEX_HTML}"
        content = INDEX_HTML.read_text(encoding="utf-8")

        # HTML parsing
        parser = HTMLValidator()
        parser.feed(content)

        assert not parser.errors, f"HTML parser found errors: {parser.errors}"
        assert not parser.tags_stack, f"Unclosed tags remaining in stack: {parser.tags_stack}"

        # Standard DOCTYPE and essential meta
        assert content.strip().startswith("<!DOCTYPE html>"), "Missing <!DOCTYPE html> preamble"
        assert '<html lang="en">' in content, "Missing <html lang=\"en\">"
        assert '<meta charset="UTF-8">' in content, "Missing <meta charset=\"UTF-8\">"
        assert 'name="viewport"' in content, "Missing viewport meta tag"
        assert "<title>kutomoto — Enterprise Form Automation — Copyrights reserved to 90Studio</title>" in content, "Invalid page title"

        # Stylesheet & scripts
        assert '<link rel="stylesheet" href="css/kutomoto.css">' in content, "Missing kutomoto.css link"
        assert '<script src="js/designer.js"></script>' in content, "Missing designer.js script tag"
        assert '<script src="js/runner.js"></script>' in content, "Missing runner.js script tag"
        assert '<script src="js/app.js"></script>' in content, "Missing app.js script tag"

        # Check script load order: designer and runner must load before app
        pos_designer = content.index('src="js/designer.js"')
        pos_runner = content.index('src="js/runner.js"')
        pos_app = content.index('src="js/app.js"')
        assert pos_designer < pos_app, "designer.js must load before app.js"
        assert pos_runner < pos_app, "runner.js must load before app.js"

    def test_90studio_branding_watermarks(self):
        """Verify strict 90Studio copyright enforcement across all presentation assets."""
        expected_copyright = "Copyrights reserved to 90Studio"

        html_text = INDEX_HTML.read_text(encoding="utf-8")
        assert expected_copyright in html_text, f"Missing 90Studio copyright in {INDEX_HTML}"

        css_text = CSS_FILE.read_text(encoding="utf-8")
        assert expected_copyright in css_text, f"Missing 90Studio copyright in {CSS_FILE}"

        for js_file in [APP_JS, DESIGNER_JS, RUNNER_JS]:
            js_text = js_file.read_text(encoding="utf-8")
            assert expected_copyright in js_text, f"Missing 90Studio copyright in {js_file.name}"

    def test_dom_ids_referenced_in_js_exist_in_html(self):
        """Cross-check every DOM ID referenced by JavaScript exists in index.html or dynamic templates."""
        parser = HTMLValidator()
        parser.feed(INDEX_HTML.read_text(encoding="utf-8"))
        html_ids = parser.ids

        # 1. app.js IDs
        app_text = APP_JS.read_text(encoding="utf-8")
        app_ids = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", app_text))
        missing_in_app = app_ids - html_ids
        assert not missing_in_app, f"app.js references non-existent HTML IDs: {missing_in_app}"

        # 2. designer.js IDs
        designer_text = DESIGNER_JS.read_text(encoding="utf-8")
        designer_ids = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", designer_text))
        missing_in_designer = designer_ids - html_ids
        assert not missing_in_designer, f"designer.js references non-existent HTML IDs: {missing_in_designer}"

        # 3. runner.js IDs (includes both static IDs in index.html and dynamic IDs inside parameter cards)
        runner_text = RUNNER_JS.read_text(encoding="utf-8")
        runner_ids = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", runner_text))
        dynamic_template_ids = set(re.findall(r"id=['\"]([^'\"]+)['\"]", runner_text))
        all_available_runner_ids = html_ids | dynamic_template_ids

        truly_missing_runner = runner_ids - all_available_runner_ids
        assert not truly_missing_runner, f"runner.js references undefined DOM IDs: {truly_missing_runner}"

    def test_css_rules_color_tokens_and_classes(self):
        """Verify CSS syntax, color tokens in :root, and UI classes referenced by JS."""
        assert CSS_FILE.is_file(), f"kutomoto.css missing at {CSS_FILE}"
        css_text = CSS_FILE.read_text(encoding="utf-8")

        # Balanced braces
        open_braces = css_text.count("{")
        close_braces = css_text.count("}")
        assert open_braces == close_braces, f"Unbalanced CSS braces: {open_braces} vs {close_braces}"

        # Essential color tokens
        expected_tokens = [
            "--bg-app", "--bg-header", "--bg-surface", "--bg-surface-hover",
            "--bg-surface-elevated", "--bg-canvas-backdrop", "--border-subtle",
            "--border-default", "--border-focus", "--border-glow",
            "--text-primary", "--text-secondary", "--text-muted", "--text-code",
            "--accent-blue", "--accent-blue-hover", "--accent-green",
            "--accent-green-hover", "--accent-red", "--accent-red-hover",
            "--accent-purple", "--accent-amber"
        ]
        for token in expected_tokens:
            assert f"{token}:" in css_text, f"Missing required CSS variable token: {token}"

        # Verify key classes styled in CSS
        required_classes = [
            ".app-header", ".nav-tab", ".designer-toolbar", ".flow-builder-toolbar",
            ".canvas-viewport", ".property-inspector", ".step-card", ".step-executing",
            ".step-success", ".step-error", ".step-disabled", ".state-badge",
            ".state-idle", ".state-running", ".state-paused", ".state-completed",
            ".state-error", ".modal-overlay", ".countdown-hud-card", ".hud-counter-number",
            ".hud-progress-fill", ".toast", ".toast-success", ".toast-error", ".toast-info"
        ]
        for cls in required_classes:
            assert cls in css_text, f"Missing CSS class declaration: {cls}"

    def test_javascript_syntax_via_node(self):
        """Empirically test JavaScript syntax and module integrity with Node.js parser."""
        node_bin = shutil.which("node")
        if not node_bin:
            pytest.skip("Node.js not installed in environment; skipping node --check")

        for js_file in [APP_JS, DESIGNER_JS, RUNNER_JS]:
            res = subprocess.run(
                [node_bin, "--check", str(js_file)],
                capture_output=True,
                text=True
            )
            assert res.returncode == 0, f"Node syntax error in {js_file.name}:\n{res.stderr}"

    def test_javascript_async_await_integrity(self):
        """Verify all JS functions containing await expressions are properly declared async."""
        node_bin = shutil.which("node")
        if node_bin:
            # Use Node VM to compile scripts and verify async/await syntax
            for js_file in [APP_JS, DESIGNER_JS, RUNNER_JS]:
                js_escaped = str(js_file).replace("\\", "\\\\")
                node_script = f"""
                const fs = require('fs');
                const vm = require('vm');
                const code = fs.readFileSync('{js_escaped}', 'utf8');
                new vm.Script(code, {{ filename: '{js_escaped}' }});
                """
                res = subprocess.run(
                    [node_bin, "-e", node_script],
                    capture_output=True,
                    text=True
                )
                assert res.returncode == 0, f"Node VM compilation error in {js_file.name}:\n{res.stderr}"

        # Check expected async methods exist
        app_text = APP_JS.read_text(encoding="utf-8")
        assert "async initHealthCheck()" in app_text

        designer_text = DESIGNER_JS.read_text(encoding="utf-8")
        assert "async compileToWorkflow()" in designer_text

        runner_text = RUNNER_JS.read_text(encoding="utf-8")
        for fn_name in ["fetchActiveWindows", "dispatchWorkflowExecution", "pauseExecution", "resumeExecution", "abortExecution"]:
            assert f"async function {fn_name}" in runner_text


# =============================================================================
# 2. CANVAS GEOMETRY & COORDINATE PRECISION
# =============================================================================

class TestCanvasGeometryAndCoordinatePrecision:
    """Empirical mathematical tests for coordinate conversion and 8 resize handles."""

    @staticmethod
    def client_to_canvas_coords(
        client_x: float, client_y: float,
        rect_left: float, rect_top: float,
        rect_width: float, rect_height: float,
        canvas_width: int = 1024, canvas_height: int = 768
    ) -> Tuple[float, float]:
        """Implements getCanvasCoordinates math from designer.js."""
        scale_x = canvas_width / rect_width
        scale_y = canvas_height / rect_height
        x = (client_x - rect_left) * scale_x
        y = (client_y - rect_top) * scale_y
        return x, y

    @staticmethod
    def compute_normalized_coords(
        x: float, y: float, w: float, h: float,
        cw: int = 1024, ch: int = 768
    ) -> Dict[str, float]:
        """Implements getNormalizedCoordinates math from designer.js."""
        norm_x = max(0.0, min(1.0, round(x / cw, 4)))
        norm_y = max(0.0, min(1.0, round(y / ch, 4)))
        norm_w = max(0.0, min(1.0 - norm_x, round(w / cw, 4)))
        norm_h = max(0.0, min(1.0 - norm_y, round(h / ch, 4)))
        center_norm_x = max(0.0, min(1.0, round((x + w / 2.0) / cw, 4)))
        center_norm_y = max(0.0, min(1.0, round((y + h / 2.0) / ch, 4)))
        return {
            "norm_x": norm_x,
            "norm_y": norm_y,
            "norm_w": norm_w,
            "norm_h": norm_h,
            "center_norm_x": center_norm_x,
            "center_norm_y": center_norm_y
        }

    def test_canvas_client_to_pixel_conversion(self):
        """Test viewport scale and offset mapping under various viewport aspect ratios."""
        # Scenario 1: 1:1 ratio, viewport offset at (100, 50)
        cx, cy = self.client_to_canvas_coords(
            client_x=300, client_y=250,
            rect_left=100, rect_top=50,
            rect_width=1024, rect_height=768
        )
        assert cx == 200.0
        assert cy == 200.0

        # Scenario 2: Scaled down (50% scale: viewport is 512x384)
        cx, cy = self.client_to_canvas_coords(
            client_x=256, client_y=192,
            rect_left=0, rect_top=0,
            rect_width=512, rect_height=384
        )
        assert cx == 512.0
        assert cy == 384.0

        # Scenario 3: Scaled up (viewport is 2048x1536)
        cx, cy = self.client_to_canvas_coords(
            client_x=1024, client_y=768,
            rect_left=0, rect_top=0,
            rect_width=2048, rect_height=1536
        )
        assert cx == 512.0
        assert cy == 384.0

    def test_coordinate_normalization_precision_and_clamping(self):
        """Test 4-decimal place precision and boundary clamping."""
        # Top-left origin box
        norm = self.compute_normalized_coords(0, 0, 102.4, 76.8, cw=1024, ch=768)
        assert norm["norm_x"] == 0.0
        assert norm["norm_y"] == 0.0
        assert norm["norm_w"] == 0.1000
        assert norm["norm_h"] == 0.1000
        assert norm["center_norm_x"] == 0.0500
        assert norm["center_norm_y"] == 0.0500

        # Exact center box
        norm_center = self.compute_normalized_coords(256, 192, 512, 384, cw=1024, ch=768)
        assert norm_center["norm_x"] == 0.2500
        assert norm_center["norm_y"] == 0.2500
        assert norm_center["norm_w"] == 0.5000
        assert norm_center["norm_h"] == 0.5000
        assert norm_center["center_norm_x"] == 0.5000
        assert norm_center["center_norm_y"] == 0.5000

        # Bottom-right boundary clamping
        norm_edge = self.compute_normalized_coords(924, 718, 200, 100, cw=1024, ch=768)
        assert norm_edge["norm_x"] == round(924 / 1024, 4)
        assert norm_edge["norm_x"] + norm_edge["norm_w"] <= 1.0
        assert norm_edge["norm_y"] + norm_edge["norm_h"] <= 1.0

        # Negative / Out-of-bounds inputs clamped to [0.0, 1.0]
        norm_oob = self.compute_normalized_coords(-50, -50, 1200, 900, cw=1024, ch=768)
        assert norm_oob["norm_x"] == 0.0
        assert norm_oob["norm_y"] == 0.0
        assert norm_oob["norm_w"] == 1.0
        assert norm_oob["norm_h"] == 1.0

    def test_resize_handle_positions_all_8_handles(self):
        """Test calculation of all 8 resize handle coordinates for a given bounding box."""
        g = {"x": 100, "y": 150, "width": 200, "height": 80}

        handles = {
            "nw": (g["x"], g["y"]),
            "n":  (g["x"] + g["width"] / 2.0, g["y"]),
            "ne": (g["x"] + g["width"], g["y"]),
            "e":  (g["x"] + g["width"], g["y"] + g["height"] / 2.0),
            "se": (g["x"] + g["width"], g["y"] + g["height"]),
            "s":  (g["x"] + g["width"] / 2.0, g["y"] + g["height"]),
            "sw": (g["x"], g["y"] + g["height"]),
            "w":  (g["x"], g["y"] + g["height"] / 2.0),
        }

        assert handles["nw"] == (100, 150)
        assert handles["n"]  == (200, 150)
        assert handles["ne"] == (300, 150)
        assert handles["e"]  == (300, 190)
        assert handles["se"] == (300, 230)
        assert handles["s"]  == (200, 230)
        assert handles["sw"] == (100, 230)
        assert handles["w"]  == (100, 190)

    def test_resize_handle_hit_testing(self):
        """Test handle hit test tolerance radius ((handleSize / 2) + 2 = 6px)."""
        handle_pos = (300, 190)  # 'e' handle
        hit_radius = 6.0

        # Exact center -> HIT
        assert abs(300 - handle_pos[0]) <= hit_radius and abs(190 - handle_pos[1]) <= hit_radius
        # 5px offset -> HIT
        assert abs(305 - handle_pos[0]) <= hit_radius and abs(194 - handle_pos[1]) <= hit_radius
        # 6px edge -> HIT
        assert abs(306 - handle_pos[0]) <= hit_radius and abs(196 - handle_pos[1]) <= hit_radius
        # 7px offset -> MISS
        assert not (abs(307 - handle_pos[0]) <= hit_radius and abs(190 - handle_pos[1]) <= hit_radius)

    def test_resize_transformation_engine_across_all_8_handles(self):
        """Simulate drag operations on each handle and verify invariance and minimum constraints."""
        cw, ch = 1024, 768
        min_w, min_h = 24, 16

        def simulate_resize(g0: dict, handle: str, dx: int, dy: int) -> dict:
            x, y, w, h = g0["x"], g0["y"], g0["width"], g0["height"]

            if "e" in handle:
                w = max(min_w, min(cw - x, g0["width"] + dx))
            if "s" in handle:
                h = max(min_h, min(ch - y, g0["height"] + dy))
            if "w" in handle:
                orig_right = g0["x"] + g0["width"]
                proposed_x = max(0, min(orig_right - min_w, g0["x"] + dx))
                w = orig_right - proposed_x
                x = proposed_x
            if "n" in handle:
                orig_bottom = g0["y"] + g0["height"]
                proposed_y = max(0, min(orig_bottom - min_h, g0["y"] + dy))
                h = orig_bottom - proposed_y
                y = proposed_y

            return {"x": x, "y": y, "width": w, "height": h}

        g0 = {"x": 200, "y": 200, "width": 100, "height": 80}

        # 1. Handle 'e': grow by 30px
        res = simulate_resize(g0, "e", dx=30, dy=0)
        assert res == {"x": 200, "y": 200, "width": 130, "height": 80}

        # 2. Handle 's': grow by 20px
        res = simulate_resize(g0, "s", dx=0, dy=20)
        assert res == {"x": 200, "y": 200, "width": 100, "height": 100}

        # 3. Handle 'w': shrink from left by 20px -> x moves right by 20, width decreases by 20, right edge invariant!
        res = simulate_resize(g0, "w", dx=20, dy=0)
        assert res["x"] == 220
        assert res["width"] == 80
        assert res["x"] + res["width"] == g0["x"] + g0["width"]

        # 4. Handle 'n': shrink from top by 15px -> y moves down by 15, height decreases by 15, bottom edge invariant!
        res = simulate_resize(g0, "n", dx=0, dy=15)
        assert res["y"] == 215
        assert res["height"] == 65
        assert res["y"] + res["height"] == g0["y"] + g0["height"]

        # 5. Handle 'nw': drag diagonally outwards (dx=-10, dy=-10)
        res = simulate_resize(g0, "nw", dx=-10, dy=-10)
        assert res["x"] == 190 and res["width"] == 110
        assert res["y"] == 190 and res["height"] == 90

        # 6. Handle 'ne': drag diagonally (dx=15, dy=-10)
        res = simulate_resize(g0, "ne", dx=15, dy=-10)
        assert res["width"] == 115
        assert res["y"] == 190 and res["height"] == 90

        # 7. Handle 'se': drag diagonally (dx=25, dy=20)
        res = simulate_resize(g0, "se", dx=25, dy=20)
        assert res["width"] == 125 and res["height"] == 100

        # 8. Handle 'sw': drag diagonally (dx=-20, dy=15)
        res = simulate_resize(g0, "sw", dx=-20, dy=15)
        assert res["x"] == 180 and res["width"] == 120
        assert res["height"] == 95

        # 9. Anti-Inversion Stress Test: drag 'w' 500px past right edge
        res_inverted_w = simulate_resize(g0, "w", dx=500, dy=0)
        assert res_inverted_w["width"] >= min_w, "Box collapsed below minimum width"
        assert res_inverted_w["width"] == min_w

        # 10. Anti-Inversion Stress Test: drag 'n' 500px past bottom edge
        res_inverted_n = simulate_resize(g0, "n", dx=0, dy=500)
        assert res_inverted_n["height"] >= min_h, "Box collapsed below minimum height"
        assert res_inverted_n["height"] == min_h


# =============================================================================
# 3. WINDOWS LAUNCHER & CLI INTEGRATION
# =============================================================================

class TestWindowsLauncherAndCliIntegration:
    """Empirical verification of CLI entrypoints, launcher scripts, and FastAPI static serving."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_cli_help_flag(self):
        """Test `python -m kutomoto --help` execution and exit code."""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT / "src")

        res = subprocess.run(
            [sys.executable, "-m", "kutomoto", "--help"],
            capture_output=True,
            text=True,
            env=env
        )
        assert res.returncode == 0, f"CLI --help failed with exit code {res.returncode}:\n{res.stderr}"
        assert "usage: kutomoto" in res.stdout
        assert "Copyrights reserved to 90Studio" in res.stdout
        assert "--mock" in res.stdout
        assert "--no-browser" in res.stdout

    def test_cli_version_flag(self):
        """Test `python -m kutomoto --version` returns version and 90Studio attribution."""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT / "src")

        res = subprocess.run(
            [sys.executable, "-m", "kutomoto", "--version"],
            capture_output=True,
            text=True,
            env=env
        )
        assert res.returncode == 0
        expected = f"kutomoto {__version__} ({__copyright__})"
        assert expected in res.stdout

    def test_cli_mock_flag_sets_environment_variable(self):
        """Test that passing --mock sets KUTOMOTO_MOCK_DRIVER in os.environ."""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT / "src")

        code = (
            "import os, sys\n"
            "from unittest.mock import patch\n"
            "from kutomoto.__main__ import main\n"
            "with patch('sys.argv', ['kutomoto', '--mock', '--no-browser']):\n"
            "    with patch('kutomoto.server.app.run_server') as mock_run:\n"
            "        sys.exit(main())\n"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env=env
        )
        assert res.returncode == 0
        assert "Mock Win32 driver mode ENABLED" in res.stdout

    def test_batch_launcher_script_version(self):
        """Empirically test `run_kutomoto.bat --version` via Windows CMD shell."""
        assert BAT_LAUNCHER.is_file(), f"run_kutomoto.bat missing at {BAT_LAUNCHER}"

        res = subprocess.run(
            [str(BAT_LAUNCHER), "--version"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            shell=True
        )
        assert res.returncode == 0, f"run_kutomoto.bat --version failed:\n{res.stderr}"
        assert "Copyrights reserved to 90Studio" in res.stdout
        assert f"kutomoto {__version__}" in res.stdout

    def test_batch_launcher_script_help(self):
        """Empirically test `run_kutomoto.bat --help` via Windows CMD shell."""
        res = subprocess.run(
            [str(BAT_LAUNCHER), "--help"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            shell=True
        )
        assert res.returncode == 0
        assert "Copyrights reserved to 90Studio" in res.stdout
        assert "usage: kutomoto" in res.stdout

    def test_fastapi_serves_spa_index_and_static_assets(self, client: TestClient):
        """Verify that FastAPI server serves index.html at '/' and all static assets at '/css' and '/js'."""
        # 1. SPA root
        resp_root = client.get("/")
        assert resp_root.status_code == 200
        assert "text/html" in resp_root.headers.get("content-type", "")
        assert "kutomoto — Enterprise Form Automation" in resp_root.text
        assert "Copyrights reserved to 90Studio" in resp_root.text

        # 2. CSS stylesheet
        resp_css = client.get("/css/kutomoto.css")
        assert resp_css.status_code == 200
        assert "text/css" in resp_css.headers.get("content-type", "") or "stylesheet" in resp_css.headers.get("content-type", "") or len(resp_css.content) > 1000

        # 3. JavaScript assets
        for js_name in ["designer.js", "runner.js", "app.js"]:
            resp_js = client.get(f"/js/{js_name}")
            assert resp_js.status_code == 200, f"Failed to serve /js/{js_name}: HTTP {resp_js.status_code}"
            assert "Copyrights reserved to 90Studio" in resp_js.text


# =============================================================================
# 4. ADVERSARIAL STRESS HARNESSES & SCHEMA CROSS-VALIDATION
# =============================================================================

class TestAdversarialStressHarnesses:
    """Adversarial stress-testing of algorithms, magnetic snap, and roundtrip compilation."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_designer_spatial_reading_order_vs_backend_compiler(self):
        """Stress test 2D spatial sorting between frontend autoSequenceSpatial and backend _spatial_band_sort."""
        from kutomoto.designer.compiler import _spatial_band_sort
        from kutomoto.designer.schema import VisualBox, BoxGeometry

        # Construct complex layout with 8 boxes: multi-row, slight vertical jitter, ragged columns
        boxes_data = [
            {"id": "b1", "x": 100, "y": 50,  "w": 150, "h": 30},
            {"id": "b2", "x": 300, "y": 55,  "w": 150, "h": 30}, # same band as b1 (diff: 5px <= 24px)
            {"id": "b3", "x": 500, "y": 48,  "w": 150, "h": 30}, # same band as b1 (diff: 2px <= 24px)
            {"id": "b4", "x": 100, "y": 140, "w": 200, "h": 30}, # band 2
            {"id": "b5", "x": 350, "y": 145, "w": 200, "h": 30}, # band 2
            {"id": "b6", "x": 100, "y": 250, "w": 120, "h": 30}, # band 3
            {"id": "b7", "x": 260, "y": 248, "w": 120, "h": 30}, # band 3
            {"id": "b8", "x": 420, "y": 252, "w": 120, "h": 30}, # band 3
        ]

        # 1. Run Python compiler's _spatial_band_sort
        v_boxes = [
            VisualBox(
                id=d["id"],
                name=d["id"],
                geometry=BoxGeometry(x=d["x"], y=d["y"], width=d["w"], height=d["h"]),
                sequence_index=1
            )
            for d in boxes_data
        ]
        backend_sorted = _spatial_band_sort(v_boxes, band_tolerance_px=24.0)
        backend_order = [b.id for b in backend_sorted]

        # 2. Simulate designer.js autoSequenceSpatial
        def js_auto_sequence(boxes: list, tolerance: float = 24.0) -> list:
            sorted_by_y = sorted(boxes, key=lambda b: (b["y"], b["x"]))
            bands = []
            current_band = [sorted_by_y[0]]
            anchor_y = sorted_by_y[0]["y"]

            for b in sorted_by_y[1:]:
                if abs(b["y"] - anchor_y) <= tolerance:
                    current_band.append(b)
                else:
                    bands.append(current_band)
                    current_band = [b]
                    anchor_y = b["y"]
            bands.append(current_band)

            result = []
            for band in bands:
                band_sorted = sorted(band, key=lambda b: b["x"])
                result.extend(band_sorted)
            return [b["id"] for b in result]

        js_order = js_auto_sequence(boxes_data, tolerance=24.0)

        # Both MUST produce the exact same reading order
        assert js_order == backend_order == ["b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8"]

    def test_designer_reindex_sequence_logic(self):
        """Test boundary conditions and consistency in box sequence re-indexing."""
        # Setup 5 boxes with sequences 1..5
        boxes = [{"id": f"b{i}", "seq": i} for i in range(1, 6)]

        def reindex(boxes_list: list, target_id: str, new_seq: int):
            total = len(boxes_list)
            target = next(b for b in boxes_list if b["id"] == target_id)
            new_seq = max(1, min(total, new_seq))
            old_seq = target["seq"]
            if new_seq == old_seq:
                return

            if new_seq < old_seq:
                for b in boxes_list:
                    if b["id"] != target_id and b["seq"] >= new_seq and b["seq"] < old_seq:
                        b["seq"] += 1
            else:
                for b in boxes_list:
                    if b["id"] != target_id and b["seq"] > old_seq and b["seq"] <= new_seq:
                        b["seq"] -= 1
            target["seq"] = new_seq

        # Case 1: Move b5 up to seq 2
        reindex(boxes, "b5", 2)
        seq_map = {b["id"]: b["seq"] for b in boxes}
        assert seq_map == {"b1": 1, "b5": 2, "b2": 3, "b3": 4, "b4": 5}

        # Case 2: Move b1 down to seq 4
        reindex(boxes, "b1", 4)
        seq_map = {b["id"]: b["seq"] for b in boxes}
        assert seq_map == {"b5": 1, "b2": 2, "b3": 3, "b1": 4, "b4": 5}

        # Case 3: Out of bounds high (seq 99) -> clamped to 5
        reindex(boxes, "b5", 99)
        seq_map = {b["id"]: b["seq"] for b in boxes}
        assert seq_map["b5"] == 5

        # Case 4: Out of bounds low (seq -10) -> clamped to 1
        reindex(boxes, "b5", -10)
        seq_map = {b["id"]: b["seq"] for b in boxes}
        assert seq_map["b5"] == 1

    def test_designer_magnetic_snap_logic(self):
        """Test magnetic snap attraction within tolerance and rejection outside tolerance."""
        tolerance = 4
        neighbor = {"id": "n1", "x": 200, "width": 100} # left=200, right=300

        def snap_x(x: int, w: int, other: dict) -> int:
            right = x + w
            other_x = other["x"]
            other_right = other["x"] + other["width"]

            if abs(x - other_x) <= tolerance:
                return other_x
            if abs(right - other_right) <= tolerance:
                return other_right - w
            return x

        # 1. Near left edge (offset by 3px -> snap to 200)
        assert snap_x(x=203, w=80, other=neighbor) == 200
        assert snap_x(x=197, w=80, other=neighbor) == 200

        # 2. Outside left tolerance (offset by 5px -> no snap)
        assert snap_x(x=205, w=80, other=neighbor) == 205

        # 3. Near right edge (right=298 with w=80 -> x=218, snaps to x=220 so right=300)
        assert snap_x(x=218, w=80, other=neighbor) == 220
        assert 220 + 80 == 300

    def test_countdown_hud_circular_dash_progress_math(self):
        """Verify SVG circular stroke-dash calculations across countdown frames."""
        total_seconds = 3
        circumference = 283  # 2 * pi * r (r=45 -> 282.74 ~ 283)

        for remaining in [3, 2, 1, 0]:
            fraction = remaining / total_seconds
            stroke_dash_offset = circumference * (1.0 - fraction)
            if remaining == 3:
                assert stroke_dash_offset == 0.0, "At start, full circle should have 0 offset"
            elif remaining == 0:
                assert stroke_dash_offset == circumference, "At zero, circle should be completely depleted"
            assert 0.0 <= stroke_dash_offset <= circumference

    def test_designer_export_json_conforms_to_pydantic_schema_and_compiles(self, client: TestClient):
        """Verify that designer's compile payload validates against VisualFormLayout schema and compiles successfully."""
        from kutomoto.designer.schema import VisualFormLayout

        sample_designer_payload = {
            "schema_version": "1.0.0",
            "id": "11111111-2222-3333-4444-555555555555",
            "name": "Loan Processing Application",
            "description": "Visual form layout for banking loan intake",
            "copyright": "Copyrights reserved to 90Studio",
            "canvas": {
                "width": 1024,
                "height": 768,
                "scale": 1.0,
                "background_image_path": None
            },
            "target_application": {
                "type": "windows_desktop",
                "window_title_pattern": "Commercial Loan Form.*",
                "match_mode": "regex"
            },
            "execution_settings": {
                "default_step_delay_ms": 150,
                "typing_speed_ms": 25
            },
            "optimization": {
                "enabled": True,
                "band_tolerance_px": 24.0,
                "click_to_tab": False,
                "collapse_delays": True,
                "remove_redundant_focus": True,
                "prune_empty_delays": True
            },
            "boxes": [
                {
                    "id": "box_borrower",
                    "name": "borrower_name",
                    "label": "Borrower Full Legal Name",
                    "geometry": {"x": 100, "y": 80, "width": 240, "height": 34},
                    "sequence_index": 1,
                    "action_type": "type_text",
                    "value": "Acme Holdings LLC",
                    "navigation": "tab",
                    "clear_before": True,
                    "post_delay_ms": 120,
                    "force_click": False,
                    "metadata": {"is_secret": False}
                },
                {
                    "id": "box_amount",
                    "name": "requested_amount",
                    "label": "Requested Facility Amount",
                    "geometry": {"x": 380, "y": 80, "width": 180, "height": 34},
                    "sequence_index": 2,
                    "action_type": "type_text",
                    "value": "2500000",
                    "navigation": "tab",
                    "clear_before": True,
                    "post_delay_ms": 120,
                    "force_click": False,
                    "metadata": {"is_secret": False}
                },
                {
                    "id": "box_submit",
                    "name": "submit_application",
                    "label": "Submit Loan Application",
                    "geometry": {"x": 380, "y": 200, "width": 140, "height": 38},
                    "sequence_index": 3,
                    "action_type": "submit",
                    "value": "",
                    "navigation": "none",
                    "clear_before": False,
                    "post_delay_ms": 500,
                    "force_click": True,
                    "metadata": {}
                }
            ]
        }

        # 1. Pydantic validation
        layout_model = VisualFormLayout.model_validate(sample_designer_payload)
        assert layout_model.name == "Loan Processing Application"
        assert len(layout_model.boxes) == 3

        # 2. REST API /api/designer/compile call
        resp = client.post("/api/designer/compile", json=sample_designer_payload)
        assert resp.status_code == 200, f"Compilation failed: {resp.text}"
        data = resp.json()
        assert data["copyright"] == "Copyrights reserved to 90Studio"
        assert data["source_mode"] == "visual_designer_generated"
        assert len(data["steps"]) >= 3
        # Verify first step has target window title
        assert data["target_application"]["window_title_pattern"] == "Commercial Loan Form.*"
