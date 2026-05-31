import subprocess
import sys


def _imports_torch(statement: str) -> bool:
    code = (
        "import sys; "
        f"{statement}; "
        "print('torch' in sys.modules)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip() == "True"


def test_legacy_action_encoder_import_does_not_load_torch():
    assert not _imports_torch("from spirecomm.ai.rl.action_encoder import ActionEncoder")


def test_v2_action_encoder_import_does_not_load_torch():
    assert not _imports_torch("from spirecomm.ai.rl.v2.action_encoder import ActionEncoderV2")


def test_main_import_does_not_load_torch():
    assert not _imports_torch("import main")
