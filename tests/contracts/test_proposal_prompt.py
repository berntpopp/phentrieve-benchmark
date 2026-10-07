from pathlib import Path

from phentrieve_benchmark.models.hpo_proposal import (
    MAX_EXCERPT_CHARS,
    PROPOSAL_PROVENANCE,
)
from phentrieve_benchmark.pipeline.proposals import GUIDELINE, PROMPT_TEMPLATE
from phentrieve_benchmark.proposals.run import render_batch_prompt

ROOT = Path(__file__).parents[2]


def test_prompt_template_renders_and_names_its_inputs() -> None:
    template = (ROOT / PROMPT_TEMPLATE).read_text(encoding="utf-8")
    rendered = render_batch_prompt(
        template,
        run_id="pilot-v1",
        batch_id="batch-01",
        output_path="datasets/e3c-de/proposals/pilot-v1/batch-01.json",
        documents="1. document",
    )
    assert "{" + "run_id}" not in rendered
    assert GUIDELINE.as_posix() in rendered
    assert PROPOSAL_PROVENANCE in rendered
    assert "proposals hpo-lookup" in rendered
    assert "e3c-hpo-proposal-batch/v1" in rendered
    assert "120 characters" in rendered
    assert f"{MAX_EXCERPT_CHARS} characters" in rendered
    assert "relative to the repository root" in rendered
