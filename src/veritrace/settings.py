import ipaddress
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .errors import InputError


FAMILIES = ("edge_history", "lnk", "jumplist", "prefetch", "userassist", "recyclebin")


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    model_base_url: str = "http://127.0.0.1:11434"
    model_name: str = "qwen3:8b"
    num_ctx: int = Field(default=4096, ge=2048, le=131072)
    temperature: float = Field(default=0.1, ge=0, le=2)
    model_timeout_s: float = Field(default=120, gt=0)
    parser_timeout_s: float = Field(default=120, gt=0)
    parser_commands: dict[str, list[str]] = Field(default_factory=dict)
    parser_versions: dict[str, str] = Field(default_factory=dict)
    parser_config_hashes: dict[str, str] = Field(default_factory=dict)
    parser_profiles: dict[str, Path] = Field(default_factory=dict)
    enabled_families: list[str] = Field(default_factory=lambda: ["edge_history"])
    budget_profile: Path | None = None

    @field_validator("model_base_url")
    @classmethod
    def local_endpoint(cls, value):
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("Use a local HTTP(S) endpoint without credentials, path or query")
        if parsed.hostname != "localhost":
            try:
                address = ipaddress.ip_address(parsed.hostname or "")
            except ValueError as exc:
                raise ValueError("Use localhost or an explicit private LAN IP") from exc
            if not (address.is_loopback or address.is_private) or address.is_unspecified:
                raise ValueError("Public model endpoints are outside the fully local scope")
        return value.rstrip("/")

    @field_validator("model_name")
    @classmethod
    def no_cloud_name(cls, value):
        if not value or "cloud" in value.lower() or "://" in value:
            raise ValueError("Select a downloaded local model")
        return value

    @field_validator("enabled_families")
    @classmethod
    def known_families(cls, value):
        if len(set(value)) != len(value) or any(f not in FAMILIES for f in value):
            raise ValueError("Enabled families must be unique supported identifiers")
        return value


def load_settings(path: Path) -> Settings:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        for key in ("budget_profile",):
            if data.get(key):
                data[key] = (path.parent / data[key]).resolve()
        data["parser_profiles"] = {k: (path.parent / v).resolve() for k, v in data.get("parser_profiles", {}).items()}
        return Settings.model_validate(data)
    except (OSError, ValueError) as exc:
        raise InputError(f"Cannot load configuration: {exc}") from exc
