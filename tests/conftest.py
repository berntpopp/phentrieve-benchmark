import os

# Typer forces Rich terminal output when GITHUB_ACTIONS is set; the ANSI codes
# then split the CLI messages that tests assert on. Typer reads this at import.
os.environ.setdefault("_TYPER_FORCE_DISABLE_TERMINAL", "1")
