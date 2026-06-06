from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "capture_sts_screenshot.ps1"
SCRIPT_TIMEOUT_SECONDS = 30


def _powershell():
    shell = shutil.which("pwsh") or shutil.which("powershell")
    assert shell is not None
    return shell


def test_capture_script_supports_all_screens_dry_run(tmp_path):
    assert SCRIPT.exists()

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-AllScreens",
            "-OutputDir",
            str(tmp_path),
            "-DryRun",
        ],
        capture_output=True,
        text=True,
        timeout=SCRIPT_TIMEOUT_SECONDS,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "[capture-sts] dry run" in output
    assert "target=all-screens" in output
    assert "would write" in output
    assert not list(tmp_path.glob("*.png"))


def test_capture_script_bypasses_gui_assemblies_for_all_screens_dry_run():
    assert SCRIPT.exists()

    text = SCRIPT.read_text(encoding="utf-8")

    fast_path_index = text.find("if ($DryRun -and $AllScreens)")
    forms_index = text.find("Add-Type -AssemblyName System.Windows.Forms")

    assert fast_path_index != -1
    assert forms_index != -1
    assert fast_path_index < forms_index


def test_capture_script_reports_missing_window(tmp_path):
    assert SCRIPT.exists()

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-WindowTitlePattern",
            "__definitely_missing_sts_window__",
            "-OutputDir",
            str(tmp_path),
            "-DryRun",
        ],
        capture_output=True,
        text=True,
        timeout=SCRIPT_TIMEOUT_SECONDS,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 2, output
    assert "No visible window matching pattern" in output
    assert "Use -AllScreens" in output


def test_capture_script_activates_window_before_visible_pixel_capture():
    assert SCRIPT.exists()

    text = SCRIPT.read_text(encoding="utf-8")

    assert "[switch]$NoActivate" in text
    assert "[StsCaptureNative]::ShowWindowAsync" in text
    assert "[StsCaptureNative]::SetForegroundWindow" in text
    assert "Start-Sleep -Milliseconds" in text


def test_capture_script_enables_dpi_awareness_before_pixel_capture():
    assert SCRIPT.exists()

    text = SCRIPT.read_text(encoding="utf-8")

    native_type_index = text.find("public static class StsCaptureNative")
    dpi_import_index = text.find("SetProcessDpiAwarenessContext")
    dpi_call_index = text.find("Enable-DpiAwareCapture")
    drawing_index = text.find("Add-Type -AssemblyName System.Drawing")

    assert native_type_index != -1
    assert dpi_import_index != -1
    assert dpi_call_index != -1
    assert drawing_index != -1
    assert native_type_index < dpi_call_index < drawing_index
