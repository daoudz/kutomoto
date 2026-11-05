"""
kutomoto CLI entry point & Windows application launcher.
Copyrights reserved to 90Studio
"""

import argparse
import logging
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

from kutomoto import __copyright__, __version__

logger = logging.getLogger("kutomoto.launcher")


def find_edge_executable() -> str | None:
    """
    Locates the Microsoft Edge executable on Windows across standard system paths.
    Returns the absolute path if found, otherwise None.
    """
    if platform.system() != "Windows":
        return shutil.which("msedge")

    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / r"Microsoft\Edge\Application\msedge.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / r"Microsoft\Edge\Application\msedge.exe",
        Path(os.environ.get("LocalAppData", "")) / r"Microsoft\Edge\Application\msedge.exe",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    which_path = shutil.which("msedge")
    if which_path and Path(which_path).is_file():
        return which_path

    return None


def launch_edge_app_mode(url: str) -> bool:
    """
    Launches Microsoft Edge in dedicated standalone App Mode without browser chrome.
    Falls back to system default browser if Edge is not found.
    """
    edge_exe = find_edge_executable()
    if edge_exe:
        try:
            cmd = [
                edge_exe,
                f"--app={url}",
                "--window-size=1366,850",
                "--window-position=50,50",
                "--no-first-run",
                "--no-default-browser-check",
            ]
            subprocess.Popen(cmd, close_fds=(platform.system() != "Windows"))
            return True
        except Exception as ex:
            logger.warning("Failed to start Edge in App Mode: %s. Falling back to default browser.", ex)

    # Seamless fallback
    webbrowser.open(url)
    return False


def wait_for_server_and_open_browser(host: str, port: int, max_attempts: int = 30) -> None:
    """
    Background daemon thread polling server health before launching Edge App Mode.
    Ensures zero browser connection-refused errors.
    """
    health_url = f"http://{host}:{port}/api/health"
    app_url = f"http://{host}:{port}/"

    for _ in range(max_attempts):
        try:
            req = urllib.request.Request(health_url, headers={"User-Agent": "kutomoto-launcher"})
            with urllib.request.urlopen(req, timeout=0.5) as resp:
                if resp.status == 200:
                    launch_edge_app_mode(app_url)
                    return
        except Exception:
            time.sleep(0.2)

    # Final attempt fallback
    webbrowser.open(app_url)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="kutomoto",
        description=f"kutomoto — Professional Forms Filling Automation System for Windows OS\n{__copyright__}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"kutomoto {__version__} ({__copyright__})")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface to bind server (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Start server only without opening Edge App Mode")
    parser.add_argument("--mock", action="store_true", help="Enable mock Win32 driver mode for non-intrusive testing")
    parser.add_argument("--reload", action="store_true", help="Enable Uvicorn hot reloading for development")
    parser.add_argument("--serve", action="store_true", help="Explicitly start kutomoto server (default behavior)")
    parser.add_argument("--sample-web", action="store_true", help="Launch the Sample Banking KYC Web Form target")
    parser.add_argument("--sample-desktop", action="store_true", help="Launch the Sample Telecom SIM Desktop Form target")

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    if args.sample_desktop:
        desktop_py = repo_root / "samples" / "desktop" / "sample_desktop_form.py"
        subprocess.Popen([sys.executable, str(desktop_py)], cwd=str(repo_root))
        return 0
    if args.sample_web:
        web_html = repo_root / "samples" / "web" / "index.html"
        launch_edge_app_mode(web_html.as_uri())
        return 0

    print("=" * 78)
    print(f"  kutomoto — Professional Forms Filling Automation System (v{__version__})")
    print(f"  {__copyright__}")
    print("=" * 78)

    if args.mock:
        os.environ["KUTOMOTO_MOCK_DRIVER"] = "1"
        print("[INIT] Mock Win32 driver mode ENABLED (mouse & keyboard inputs simulated).")

    # Start browser launch thread if requested
    if not args.no_browser:
        t = threading.Thread(
            target=wait_for_server_and_open_browser,
            args=(args.host, args.port),
            daemon=True,
        )
        t.start()

    print(f"[INIT] Starting backend server at http://{args.host}:{args.port}/ ...")

    try:
        from kutomoto.server.app import run_server
        run_server(host=args.host, port=args.port, reload=args.reload)
        return 0
    except ImportError as ex:
        print(f"[ERROR] Required server dependencies not found: {ex}. Verify installation.")
        return 1
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] kutomoto server stopped cleanly by operator.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
