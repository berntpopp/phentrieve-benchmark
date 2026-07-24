from types import SimpleNamespace

import pytest

from phentrieve_benchmark.translation.google_nmt import (
    GoogleNmtAdapter,
    ProviderResponseError,
)


class _FakeClient:
    def __init__(self, text: str) -> None:
        self.text = text
        self.request: dict[str, object] | None = None

    def translate_text(self, *, request: dict[str, object]) -> object:
        self.request = request
        return SimpleNamespace(
            translations=(SimpleNamespace(translated_text=self.text),)
        )


def test_adapter_sends_explicit_languages_and_model() -> None:
    client = _FakeClient("Der Patient hatte Fieber.")
    adapter = GoogleNmtAdapter(
        client=client,
        project_id="benchmark-project",
        location="global",
    )

    result = adapter.translate(
        "The patient had fever.", source_language="en", target_language="de"
    )

    assert result.text == "Der Patient hatte Fieber."
    assert client.request == {
        "contents": ["The patient had fever."],
        "parent": "projects/benchmark-project/locations/global",
        "source_language_code": "en",
        "target_language_code": "de",
        "mime_type": "text/plain",
        "model": "projects/benchmark-project/locations/global/models/general/nmt",
    }


@pytest.mark.parametrize("response", ["", "   "])
def test_adapter_rejects_empty_provider_text(response: str) -> None:
    adapter = GoogleNmtAdapter(
        client=_FakeClient(response),
        project_id="benchmark-project",
        location="global",
    )

    with pytest.raises(ProviderResponseError, match="empty"):
        adapter.translate("fever", source_language="en", target_language="de")

