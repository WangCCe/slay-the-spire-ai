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
    assert "--skip-intro" in output
    assert "--mods" in output
    assert "basemod,CommunicationMod,superfastmode,StSExporter" in output
    assert "mts-launcher.jar" not in output


def test_restart_script_can_disable_superfastmode_for_diagnostics():
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
            "-NoSuperFastMode",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "--mods basemod,CommunicationMod,StSExporter" in output
    assert "superfastmode" not in output


def test_restart_script_diagnostic_speed_alias_disables_superfastmode():
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
            "-DiagnosticSpeed",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "[restart-sts] diagnostic speed: superfastmode disabled for launch." in output
    assert "--mods basemod,CommunicationMod,StSExporter" in output
    assert "superfastmode" not in output.replace("superfastmode disabled", "")


def test_restart_script_fresh_run_dry_run_reports_autosave_backup(tmp_path):
    shell = shutil.which("pwsh") or shutil.which("powershell")
    assert shell is not None

    saves = tmp_path / "saves"
    saves.mkdir()
    autosave = saves / "IRONCLAD.autosave"
    backup = saves / "IRONCLAD.autosave.backUp"
    autosave.write_text("active save", encoding="utf-8")
    backup.write_text("backup save", encoding="utf-8")

    result = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-GameDir",
            str(tmp_path),
            "-FreshRun",
            "-DryRun",
            "-SkipLaunch",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "[restart-sts] fresh run requested for IRONCLAD." in output
    assert "DRY RUN would move" in output
    assert "IRONCLAD.autosave" in output
    assert "fresh_run_backups" in output
    assert autosave.read_text(encoding="utf-8") == "active save"
    assert backup.read_text(encoding="utf-8") == "backup save"
