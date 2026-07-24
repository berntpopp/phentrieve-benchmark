from dataclasses import dataclass
from typing import Literal, Protocol

from phentrieve_benchmark.provenance.canonical import canonical_text_bytes


class TranslationClient(Protocol):
    def translate_text(self, *, request: dict[str, object]) -> object: ...


@dataclass(frozen=True)
class ProviderTranslation:
    text: str


class TranslationProvider(Protocol):
    def translate(
        self,
        text: str,
        *,
        source_language: Literal["en", "fr", "es"],
        target_language: Literal["de"],
    ) -> ProviderTranslation: ...


class ProviderResponseError(RuntimeError):
    """The provider returned no usable translation."""


class GoogleNmtAdapter:
    def __init__(
        self,
        *,
        client: TranslationClient,
        project_id: str,
        location: str = "global",
    ) -> None:
        self._client = client
        self.project_id = project_id
        self.location = location

    def translate(
        self,
        text: str,
        *,
        source_language: Literal["en", "fr", "es"],
        target_language: Literal["de"],
    ) -> ProviderTranslation:
        parent = f"projects/{self.project_id}/locations/{self.location}"
        response = self._client.translate_text(
            request={
                "contents": [text],
                "parent": parent,
                "source_language_code": source_language,
                "target_language_code": target_language,
                "mime_type": "text/plain",
                "model": f"{parent}/models/general/nmt",
            }
        )
        translations = tuple(getattr(response, "translations", ()))
        if len(translations) != 1:
            raise ProviderResponseError(
                "provider response must contain exactly one translation"
            )
        translated_text = getattr(translations[0], "translated_text", None)
        if not isinstance(translated_text, str) or not translated_text.strip():
            raise ProviderResponseError("provider returned an empty translation")
        canonical = canonical_text_bytes(translated_text).decode("utf-8")
        return ProviderTranslation(text=canonical)


def create_google_nmt_adapter(
    *, project_id: str, location: str = "global"
) -> GoogleNmtAdapter:
    from google.cloud import translate_v3

    return GoogleNmtAdapter(
        client=translate_v3.TranslationServiceClient(),
        project_id=project_id,
        location=location,
    )

