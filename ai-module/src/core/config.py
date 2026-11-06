"""Read AI settings without mutating the process environment or calling APIs."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values


AI_MODULE_DIR = Path(__file__).resolve().parents[2]
ROOT_ENV_FILE = AI_MODULE_DIR.parent / ".env"


class ConfigurationError(ValueError):
    """A configuration error containing field names, never supplied values."""


@dataclass(frozen=True, slots=True)
class Settings:
    ai_internal_token: str = field(repr=False)
    embedding_provider: str
    embedding_model: str
    openai_api_key: str = field(default="", repr=False)
    groq_api_key: str = field(default="", repr=False)
    llm_provider: str = ""
    llm_model: str = ""
    chroma_persist_directory: Path = AI_MODULE_DIR / "chroma_db"

    @property
    def collection_name(self) -> str:
        return f"study_materials_{self.embedding_model}"

    def require_embedding_api_key(self) -> str:
        """Validate presence at client creation time; this does not verify the key."""
        if not self.openai_api_key.strip():
            raise ConfigurationError("OPENAI_API_KEY is required for embeddings")
        return self.openai_api_key


def load_settings(
    *,
    env_file: Path | None = ROOT_ENV_FILE,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    """Load once at app startup and share the returned immutable settings.

    Process values win even when empty. An absent file is valid for containers;
    pass None to explicitly disable file loading. Tests can inject both sources.
    Variable interpolation is disabled to preserve literal credentials and avoid
    implicit dependencies on unrelated process variables.
    """
    file_values = (
        dotenv_values(env_file, encoding="utf-8-sig", interpolate=False)
        if env_file is not None
        else {}
    )
    process_values = os.environ if environ is None else environ

    def read(name: str) -> str:
        if name in process_values:
            return process_values[name]
        return file_values.get(name) or ""

    token = read("AI_INTERNAL_TOKEN")
    if not token.strip():
        raise ConfigurationError("AI_INTERNAL_TOKEN is required")
    # The HTTP header and secrets.compare_digest(str, str) use ASCII tokens.
    if not token.isascii() or any(c.isspace() or not c.isprintable() for c in token):
        raise ConfigurationError("AI_INTERNAL_TOKEN must be printable ASCII without whitespace")

    provider = read("EMBEDDING_PROVIDER")
    model = read("EMBEDDING_MODEL")
    if provider != "openai":
        raise ConfigurationError("EMBEDDING_PROVIDER must be openai")
    if model != "text-embedding-3-small":
        raise ConfigurationError("EMBEDDING_MODEL must be text-embedding-3-small")

    directory = read("CHROMA_PERSIST_DIRECTORY")
    chroma_path = Path(directory) if directory else Path("chroma_db")
    if not chroma_path.is_absolute():
        chroma_path = AI_MODULE_DIR / chroma_path

    return Settings(
        ai_internal_token=token,
        embedding_provider=provider,
        embedding_model=model,
        openai_api_key=read("OPENAI_API_KEY"),
        groq_api_key=read("GROQ_API_KEY"),
        llm_provider=read("LLM_PROVIDER"),
        llm_model=read("LLM_MODEL"),
        chroma_persist_directory=chroma_path.resolve(),
    )
