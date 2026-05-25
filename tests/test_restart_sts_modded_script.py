from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "restart_sts_modded.ps1"


def test_restart_script_has_narrow_process_boundaries():
    assert SCRIPT.exists()

    text = SCRIPT.read_text(encoding="utf-8")

    assert "function ShouldStopProjectPython" in text
    assert "function ShouldStopGameProcess" in text
    assert "slay-the-spire-ai" in text
    assert "mts-launcher.jar" in text
    assert "Get-CimInstance Win32_Process" in text

    forbidden_patterns = [
        "Stop-Process -Name python",
        "Stop-Process -Name pythonw",
        "Stop-Process -Name java",
        "Stop-Process -Name javaw",
        "taskkill",
    ]
    for pattern in forbidden_patterns:
        assert pattern not in text


def test_restart_script_dry_run_does_not_launch_or_stop_processes():
    shell = shutil.which("pwsh") or shutil.which("powershell")
    assert shell is not None

    result = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-DryRun",
            "-SkipLaunch",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "[restart-sts] dry run: no processes will be stopped and no launcher will be started." in output
    assert "[restart-sts] launch skipped." in output


def test_restart_script_direct_launches_modthespire_without_launcher_by_default():
    shell = shutil.which("pwsh") or shutil.which("powershell")
    assert shell is not None

    result = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-DryRun",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "ModTheSpire.jar" in output
    assert "--skip-launcher" in output
    assert "mts-launcher.jar" not in output
