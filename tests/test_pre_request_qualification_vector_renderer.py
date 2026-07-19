import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RENDERER = (
    REPO_ROOT
    / "analysis_scripts"
    / "render_pre_request_qualification_observability_vectors.py"
)


def test_renderer_rejects_output_inside_fixture_root_before_rendering():
    output = (
        REPO_ROOT
        / ".pytest-tmp-pre-request-observability"
        / "vector-render"
        / "output.json"
    )
    assert not output.exists()

    result = subprocess.run(
        [sys.executable, str(RENDERER), "--output", str(output)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "output must not overlap renderer fixture root" in result.stderr
    assert not output.exists()
