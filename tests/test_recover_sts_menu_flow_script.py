from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "recover_sts_menu_flow.ps1"
SCRIPT_TIMEOUT_SECONDS = 30


def _powershell():
    shell = shutil.which("pwsh") or shutil.which("powershell")
    assert shell is not None
    return shell


def test_recovery_script_reports_missing_window():
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
            "-DryRun",
        ],
        capture_output=True,
        text=True,
        timeout=SCRIPT_TIMEOUT_SECONDS,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 2, output
    assert "No visible window matching pattern" in output


def test_recovery_script_keeps_menu_flow_default():
    assert SCRIPT.exists()

    text = SCRIPT.read_text(encoding="utf-8")

    assert '[string]$Action = "MenuFlow"' in text
    assert '$sequence += @("Play", "Standard", "Ironclad", "Embark")' in text
    assert '$sequence += @("Standard", "Ironclad", "Embark")' in text
    assert '$sequence += @("Ironclad", "Embark")' in text
    assert '$sequence += @("Embark")' in text


def test_recovery_script_supports_combat_end_turn_action():
    assert SCRIPT.exists()

    text = SCRIPT.read_text(encoding="utf-8")

    assert '[ValidateSet("MenuFlow", "EndTurn")]' in text
    assert 'if ($Action -eq "EndTurn")' in text
    assert 'EndTurn = @{ X = 1160; Y = 560 }' in text
    assert '$sequence += "EndTurn"' in text


def test_recovery_script_end_turn_action_parses_before_window_lookup():
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
            "-Action",
            "EndTurn",
            "-DryRun",
        ],
        capture_output=True,
        text=True,
        timeout=SCRIPT_TIMEOUT_SECONDS,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 2, output
    assert "No visible window matching pattern" in output
