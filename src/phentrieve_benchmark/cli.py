import typer

from phentrieve_benchmark import __version__

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Run Phentrieve Benchmark commands."""


@app.command()
def version() -> None:
    """Print the installed package version."""
    typer.echo(f"phentrieve-benchmark {__version__}")
