"""
build_exe.py
Native Windows 64-bit PE executable builder for kutomoto and sample desktop target.
Compiles standalone launcher executables with embedded 90Studio icon and PE version resources.
Copyrights reserved to 90Studio
"""

from __future__ import annotations

from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / "dist"
UI_DIR = PROJECT_ROOT / "src" / "kutomoto" / "ui"
SAMPLES_DESKTOP_DIR = PROJECT_ROOT / "samples" / "desktop"
SAMPLES_WEB_DIR = PROJECT_ROOT / "samples" / "web"
WORKFLOWS_DATA_DIR = PROJECT_ROOT / "data" / "workflows"


def generate_kutomoto_ico(target_path: Path) -> None:
    """
    Generates a valid 32x32 32-bit BGRA Windows .ico file featuring the
    kutomoto royal-blue (#1f6feb) rounded square emblem and white 'K' monogram.
    """
    width, height = 32, 32
    pixels = bytearray(width * height * 4)

    def set_px(x: int, y: int, r: int, g: int, b: int, a: int = 255) -> None:
        if 0 <= x < width and 0 <= y < height:
            # BMP DIB inside ICO is stored bottom-up (row 0 is bottom)
            bmp_y = (height - 1) - y
            idx = (bmp_y * width + x) * 4
            pixels[idx : idx + 4] = bytes((b, g, r, a))

    # 1. Rounded royal-blue background (#1f6feb -> R=31, G=111, B=235)
    radius = 6
    for y in range(height):
        for x in range(width):
            in_corner = False
            for cx, cy in (
                (radius, radius),
                (width - 1 - radius, radius),
                (radius, height - 1 - radius),
                (width - 1 - radius, height - 1 - radius),
            ):
                if (
                    (x < radius and y < radius and (x - cx) ** 2 + (y - cy) ** 2 > radius**2)
                    or (x > width - 1 - radius and y < radius and (x - cx) ** 2 + (y - cy) ** 2 > radius**2)
                    or (x < radius and y > height - 1 - radius and (x - cx) ** 2 + (y - cy) ** 2 > radius**2)
                    or (
                        x > width - 1 - radius
                        and y > height - 1 - radius
                        and (x - cx) ** 2 + (y - cy) ** 2 > radius**2
                    )
                ):
                    in_corner = True
                    break
            if not in_corner:
                set_px(x, y, 31, 111, 235, 255)

    # 2. White 'K' monogram
    # Vertical stem: x in [8..12], y in [7..24]
    for y in range(7, 25):
        for x in range(8, 13):
            set_px(x, y, 255, 255, 255, 255)

    # Upper and lower diagonals of 'K'
    for step in range(10):
        # Upper arm from (13, 16) to (22, 7)
        ux = 13 + step
        uy = 16 - step
        for dx in range(4):
            set_px(ux + dx, uy, 255, 255, 255, 255)
        # Lower arm from (13, 15) to (22, 24)
        lx = 13 + step
        ly = 15 + step
        for dx in range(4):
            set_px(lx + dx, ly, 255, 255, 255, 255)

    # AND mask (1 bit per pixel, padded to 32-bit boundary per row -> 4 bytes per row)
    and_mask = bytes(height * 4)

    # BITMAPINFOHEADER (40 bytes, height is doubled for XOR + AND masks)
    bih = struct.pack(
        "<IIIHHIIIIII",
        40,  # biSize
        width,  # biWidth
        height * 2,  # biHeight (XOR + AND)
        1,  # biPlanes
        32,  # biBitCount
        0,  # biCompression (BI_RGB)
        len(pixels) + len(and_mask),  # biSizeImage
        0,
        0,
        0,
        0,
    )

    image_data = bih + bytes(pixels) + and_mask
    ico_header = struct.pack("<HHH", 0, 1, 1)  # Reserved=0, Type=1 (ICO), Count=1
    ico_dir_entry = struct.pack(
        "<BBBBHHII",
        width,  # bWidth
        height,  # bHeight
        0,  # bColorCount
        0,  # bReserved
        1,  # wPlanes
        32,  # wBitCount
        len(image_data),  # dwBytesInRes
        6 + 16,  # dwImageOffset
    )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(ico_header + ico_dir_entry + image_data)


KUTOMOTO_LAUNCHER_CS = r"""
// ============================================================================
// kutomoto — Professional Forms Filling Automation System for Windows OS
// Native Windows 64-bit Application Executable Launcher
// Copyrights reserved to 90Studio
// ============================================================================

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Reflection;
using System.Text;

[assembly: AssemblyTitle("kutomoto — Enterprise Form Automation")]
[assembly: AssemblyDescription("kutomoto — Professional Forms Filling Automation System for Windows OS (Copyrights reserved to 90Studio)")]
[assembly: AssemblyConfiguration("Production")]
[assembly: AssemblyCompany("90Studio")]
[assembly: AssemblyProduct("kutomoto")]
[assembly: AssemblyCopyright("Copyrights reserved to 90Studio")]
[assembly: AssemblyTrademark("90Studio")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

namespace KutomotoLauncher
{
    internal static class Program
    {
        private static Process _childProcess = null;

        private static string ResolveProjectRoot()
        {
            string exeDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);

            // Check if src/kutomoto exists in exeDir
            if (Directory.Exists(Path.Combine(exeDir, "src", "kutomoto")))
            {
                return exeDir;
            }

            // Check parent directory (e.g. when running from dist\kutomoto.exe)
            DirectoryInfo parent = Directory.GetParent(exeDir);
            if (parent != null && Directory.Exists(Path.Combine(parent.FullName, "src", "kutomoto")))
            {
                return parent.FullName;
            }

            // Check current working directory
            string cwd = Directory.GetCurrentDirectory();
            if (Directory.Exists(Path.Combine(cwd, "src", "kutomoto")))
            {
                return cwd;
            }

            return exeDir;
        }

        private static string FindPythonExecutable()
        {
            string envPy = Environment.GetEnvironmentVariable("KUTOMOTO_PYTHON");
            if (!string.IsNullOrEmpty(envPy) && File.Exists(envPy))
            {
                return envPy;
            }

            string pathEnv = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
            foreach (string rawDir in pathEnv.Split(Path.PathSeparator))
            {
                string dir = rawDir.Trim();
                if (string.IsNullOrEmpty(dir)) continue;

                try
                {
                    string candidate = Path.Combine(dir, "python.exe");
                    if (File.Exists(candidate))
                    {
                        FileInfo fi = new FileInfo(candidate);
                        // Skip 0-byte WindowsApps Store alias stubs
                        if (fi.Length > 0)
                        {
                            return candidate;
                        }
                    }
                }
                catch
                {
                    // Ignore inaccessible PATH entries
                }
            }

            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string[] fallbacks = new string[]
            {
                @"C:\Python314\python.exe",
                @"C:\Python313\python.exe",
                @"C:\Python312\python.exe",
                @"C:\Python311\python.exe",
                @"C:\Python310\python.exe",
                Path.Combine(localAppData, @"Programs\Python\Python314\python.exe"),
                Path.Combine(localAppData, @"Programs\Python\Python313\python.exe"),
                Path.Combine(localAppData, @"Programs\Python\Python312\python.exe"),
            };

            foreach (string fb in fallbacks)
            {
                if (File.Exists(fb))
                {
                    return fb;
                }
            }

            return "python";
        }

        private static string FindEdgeExecutable()
        {
            string pf86 = Environment.GetEnvironmentVariable("ProgramFiles(x86)") ?? @"C:\Program Files (x86)";
            string pf = Environment.GetEnvironmentVariable("ProgramFiles") ?? @"C:\Program Files";
            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);

            string[] candidates = new string[]
            {
                Path.Combine(pf86, @"Microsoft\Edge\Application\msedge.exe"),
                Path.Combine(pf, @"Microsoft\Edge\Application\msedge.exe"),
                Path.Combine(localAppData, @"Microsoft\Edge\Application\msedge.exe"),
            };

            foreach (string c in candidates)
            {
                if (File.Exists(c)) return c;
            }
            return null;
        }

        private static bool IsServerAlreadyHealthy(string host, int port)
        {
            try
            {
                string url = string.Format("http://{0}:{1}/api/health", host, port);
                HttpWebRequest req = (HttpWebRequest)WebRequest.Create(url);
                req.Method = "GET";
                req.Timeout = 600;
                req.UserAgent = "kutomoto-exe-launcher";
                using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
                {
                    return resp.StatusCode == HttpStatusCode.OK;
                }
            }
            catch
            {
                return false;
            }
        }

        private static void OpenBrowserWindow(string url)
        {
            string edge = FindEdgeExecutable();
            if (!string.IsNullOrEmpty(edge))
            {
                try
                {
                    ProcessStartInfo psi = new ProcessStartInfo
                    {
                        FileName = edge,
                        Arguments = string.Format("--app={0} --window-size=1366,850 --window-position=50,50 --no-first-run --no-default-browser-check", url),
                        UseShellExecute = false
                    };
                    Process.Start(psi);
                    return;
                }
                catch
                {
                    // Fallback below
                }
            }

            try
            {
                Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
            }
            catch
            {
                // Ignore
            }
        }

        private static string QuoteArg(string arg)
        {
            if (string.IsNullOrEmpty(arg)) return "\"\"";
            if (!arg.Contains(" ") && !arg.Contains("\"") && !arg.Contains("\t"))
            {
                return arg;
            }
            return "\"" + arg.Replace("\"", "\\\"") + "\"";
        }

        public static int Main(string[] args)
        {
            Console.OutputEncoding = Encoding.UTF8;
            string projectRoot = ResolveProjectRoot();
            string srcDir = Path.Combine(projectRoot, "src");
            string pythonExe = FindPythonExecutable();

            // Check special convenience flags
            bool isMetaFlag = false;
            bool noBrowser = false;
            string host = "127.0.0.1";
            int port = 8765;

            for (int i = 0; i < args.Length; i++)
            {
                string a = args[i];
                if (a == "--version" || a == "-h" || a == "--help")
                {
                    isMetaFlag = true;
                }
                else if (a == "--no-browser")
                {
                    noBrowser = true;
                }
                else if (a == "--port" && i + 1 < args.Length)
                {
                    int.TryParse(args[i + 1], out port);
                }
                else if (a == "--host" && i + 1 < args.Length)
                {
                    host = args[i + 1];
                }
                else if (a == "--sample-desktop")
                {
                    string samplePy = Path.Combine(projectRoot, "samples", "desktop", "sample_desktop_form.py");
                    ProcessStartInfo samplePsi = new ProcessStartInfo
                    {
                        FileName = pythonExe,
                        Arguments = QuoteArg(samplePy),
                        WorkingDirectory = projectRoot,
                        UseShellExecute = false
                    };
                    Process.Start(samplePsi);
                    return 0;
                }
                else if (a == "--sample-web")
                {
                    string sampleHtml = Path.Combine(projectRoot, "samples", "web", "index.html");
                    OpenBrowserWindow(new Uri(sampleHtml).AbsoluteUri);
                    return 0;
                }
            }

            // If server is already running on target host:port and user is launching UI interactively
            if (!isMetaFlag && !noBrowser && IsServerAlreadyHealthy(host, port))
            {
                string appUrl = string.Format("http://{0}:{1}/", host, port);
                Console.WriteLine("==============================================================================");
                Console.WriteLine("  kutomoto — Professional Forms Filling Automation System (v1.0.0)");
                Console.WriteLine("  Copyrights reserved to 90Studio");
                Console.WriteLine("==============================================================================");
                Console.WriteLine("[INFO] Active kutomoto server detected at " + appUrl);
                Console.WriteLine("[INFO] Launching kutomoto UI shell window...");
                OpenBrowserWindow(appUrl);
                return 0;
            }

            // Build argument string for `python -m kutomoto ...`
            List<string> pyArgs = new List<string> { "-m", "kutomoto" };
            foreach (string a in args)
            {
                pyArgs.Add(QuoteArg(a));
            }

            ProcessStartInfo psiMain = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = string.Join(" ", pyArgs.ToArray()),
                WorkingDirectory = projectRoot,
                UseShellExecute = false,
                RedirectStandardOutput = false,
                RedirectStandardError = false
            };

            string existingPyPath = Environment.GetEnvironmentVariable("PYTHONPATH") ?? string.Empty;
            psiMain.EnvironmentVariables["PYTHONPATH"] = string.IsNullOrEmpty(existingPyPath)
                ? srcDir
                : srcDir + Path.PathSeparator + existingPyPath;
            psiMain.EnvironmentVariables["PYTHONUTF8"] = "1";
            psiMain.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";

            Console.CancelKeyPress += (sender, e) =>
            {
                e.Cancel = true;
                try
                {
                    if (_childProcess != null && !_childProcess.HasExited)
                    {
                        _childProcess.Kill();
                    }
                }
                catch
                {
                    // Ignore
                }
            };

            try
            {
                _childProcess = Process.Start(psiMain);
                if (_childProcess == null)
                {
                    Console.Error.WriteLine("[ERROR] Failed to launch kutomoto process.");
                    return 1;
                }
                _childProcess.WaitForExit();
                return _childProcess.ExitCode;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("[ERROR] kutomoto launcher error: " + ex.Message);
                return 1;
            }
        }
    }
}
"""


SAMPLE_DESKTOP_LAUNCHER_CS = r"""
// ============================================================================
// kutomoto — Telecom SIM Provisioning Sample Desktop Target Executable
// Copyrights reserved to 90Studio
// ============================================================================

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;

[assembly: AssemblyTitle("Telecom SIM Provisioning System — 90Studio")]
[assembly: AssemblyDescription("kutomoto Sample Windows Desktop Form Target (Copyrights reserved to 90Studio)")]
[assembly: AssemblyCompany("90Studio")]
[assembly: AssemblyProduct("kutomoto Sample Desktop Target")]
[assembly: AssemblyCopyright("Copyrights reserved to 90Studio")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

namespace SampleDesktopLauncher
{
    internal static class Program
    {
        private static string FindPythonExecutable(bool preferWindowless)
        {
            string envPy = Environment.GetEnvironmentVariable("KUTOMOTO_PYTHON");
            if (!string.IsNullOrEmpty(envPy) && File.Exists(envPy))
            {
                return envPy;
            }

            string pathEnv = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
            string exeName = preferWindowless ? "pythonw.exe" : "python.exe";

            foreach (string rawDir in pathEnv.Split(Path.PathSeparator))
            {
                string dir = rawDir.Trim();
                if (string.IsNullOrEmpty(dir)) continue;
                try
                {
                    string candidate = Path.Combine(dir, exeName);
                    if (File.Exists(candidate) && new FileInfo(candidate).Length > 0)
                    {
                        return candidate;
                    }
                }
                catch { }
            }

            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string[] baseDirs = new string[]
            {
                @"C:\Python314",
                @"C:\Python313",
                @"C:\Python312",
                @"C:\Python311",
                @"C:\Python310",
                Path.Combine(localAppData, @"Programs\Python\Python314"),
                Path.Combine(localAppData, @"Programs\Python\Python313"),
                Path.Combine(localAppData, @"Programs\Python\Python312"),
            };

            foreach (string bd in baseDirs)
            {
                string fb = Path.Combine(bd, exeName);
                if (File.Exists(fb))
                {
                    return fb;
                }
            }

            if (preferWindowless)
            {
                return FindPythonExecutable(false);
            }
            return @"C:\Python314\python.exe";
        }

        private static string ResolveScriptPath()
        {
            string exeDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            string direct = Path.Combine(exeDir, "sample_desktop_form.py");
            if (File.Exists(direct)) return direct;

            string fromRoot = Path.Combine(exeDir, "samples", "desktop", "sample_desktop_form.py");
            if (File.Exists(fromRoot)) return fromRoot;

            DirectoryInfo parent = Directory.GetParent(exeDir);
            if (parent != null)
            {
                string fromParent = Path.Combine(parent.FullName, "samples", "desktop", "sample_desktop_form.py");
                if (File.Exists(fromParent)) return fromParent;
            }
            return direct;
        }

        public static int Main(string[] args)
        {
            string scriptPath = ResolveScriptPath();
            bool hasCliArgs = args != null && args.Length > 0;
            string pyExe = FindPythonExecutable(!hasCliArgs);

            List<string> argList = new List<string> { "\"" + scriptPath + "\"" };
            if (args != null)
            {
                foreach (string a in args)
                {
                    argList.Add(a.Contains(" ") ? "\"" + a + "\"" : a);
                }
            }

            ProcessStartInfo psi = new ProcessStartInfo
            {
                FileName = pyExe,
                Arguments = string.Join(" ", argList.ToArray()),
                WorkingDirectory = Path.GetDirectoryName(scriptPath) ?? Environment.CurrentDirectory,
                UseShellExecute = false,
                CreateNoWindow = !hasCliArgs
            };

            try
            {
                Process p = Process.Start(psi);
                if (p == null) return 1;
                p.WaitForExit();
                return p.ExitCode;
            }
            catch
            {
                return 1;
            }
        }
    }
}
"""


def find_csc() -> Path:
    candidates = [
        Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"),
        Path(r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError("Could not locate Microsoft .NET C# compiler (csc.exe).")


def compile_csharp_exe(csc_path: Path, cs_source: str, output_exe: Path, icon_path: Path, target_type: str = "exe") -> None:
    output_exe.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp_dir:
        cs_file = Path(tmp_dir) / "Launcher.cs"
        cs_file.write_text(cs_source, encoding="utf-8")

        cmd = [
            str(csc_path),
            "/nologo",
            f"/target:{target_type}",
            "/platform:x64",
            "/optimize+",
            f"/win32icon:{icon_path}",
            f"/out:{output_exe}",
            str(cs_file),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"csc.exe compilation failed for {output_exe}:\n{res.stdout}\n{res.stderr}")


def clean_and_seed_workflows_dir() -> None:
    """
    Removes leftover temporary test UUID workflows from data/workflows/
    and seeds the two official enterprise sample workflows.
    """
    WORKFLOWS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for f in WORKFLOWS_DATA_DIR.glob("*.json"):
        try:
            f.unlink()
        except OSError:
            pass

    kyc_src = SAMPLES_WEB_DIR / "banking_kyc_workflow.json"
    sim_src = SAMPLES_DESKTOP_DIR / "telecom_sim_provisioning_workflow.json"

    if kyc_src.is_file():
        shutil.copy2(kyc_src, WORKFLOWS_DATA_DIR / "e2e-banking-kyc-web-flow-0001.json")
    if sim_src.is_file():
        shutil.copy2(sim_src, WORKFLOWS_DATA_DIR / "telecom-sim-provisioning-e2e-001.json")


def build_all() -> None:
    print("=" * 78)
    print("  kutomoto Native Windows Executable Builder")
    print("  Copyrights reserved to 90Studio")
    print("=" * 78)

    ico_path = UI_DIR / "favicon.ico"
    dist_ico_path = DIST_DIR / "kutomoto.ico"
    generate_kutomoto_ico(ico_path)
    generate_kutomoto_ico(dist_ico_path)
    print(f"[1/4] Generated 90Studio application icon: {ico_path}")

    csc_path = find_csc()
    print(f"[2/4] Located Windows native compiler: {csc_path}")

    root_exe = PROJECT_ROOT / "kutomoto.exe"
    dist_exe = DIST_DIR / "kutomoto.exe"
    compile_csharp_exe(csc_path, KUTOMOTO_LAUNCHER_CS, root_exe, ico_path, target_type="exe")
    shutil.copy2(root_exe, dist_exe)
    print(f"[3/4] Built primary application executables:\n      - {root_exe}\n      - {dist_exe}")

    sample_desktop_exe = SAMPLES_DESKTOP_DIR / "sample_desktop_form.exe"
    dist_sample_exe = DIST_DIR / "sample_desktop_form.exe"
    compile_csharp_exe(csc_path, SAMPLE_DESKTOP_LAUNCHER_CS, sample_desktop_exe, ico_path, target_type="winexe")
    shutil.copy2(sample_desktop_exe, dist_sample_exe)
    print(f"[4/4] Built sample desktop target executables:\n      - {sample_desktop_exe}\n      - {dist_sample_exe}")

    clean_and_seed_workflows_dir()
    print("[OK] Seeded data/workflows/ with official Banking KYC & Telecom SIM workflows.")
    print("=" * 78)


if __name__ == "__main__":
    build_all()
    sys.exit(0)
