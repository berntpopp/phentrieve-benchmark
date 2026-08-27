from datetime import date
from typing import Annotated

from pydantic import AfterValidator, Field


def validate_hpo_release(value: str) -> str:
    """Validate the exact, ASCII HPO release tag and its calendar date."""
    try:
        date.fromisoformat(value.removeprefix("v"))
    except ValueError as error:
        raise ValueError("hpo_release must contain a valid calendar date") from error
    return value


HpoRelease = Annotated[
    str,
    Field(pattern=r"^v[0-9]{4}-[0-9]{2}-[0-9]{2}$"),
    AfterValidator(validate_hpo_release),
]
