from typer.testing import CliRunner

from phentrieve_benchmark import __version__
from phentrieve_benchmark.cli import app


def test_package_exposes_version_and_cli() -> None:
    result = CliRunner().invoke(app, ["version"])
    assert __version__ == "0.1.0"
    assert result.exit_code == 0
    assert result.stdout.strip() == "phentrieve-benchmark 0.1.0"
