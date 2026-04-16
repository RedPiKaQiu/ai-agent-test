"""Configuration loading for the model comparison runner."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ModelConfig:
    """One model endpoint to compare."""

    name: str
    provider: str
    provider_type: str
    model: str
    base_url: str
    enabled: bool = True
    api_key: Optional[str] = None
    api_key_env: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout_seconds: Optional[int] = None
    headers: Dict[str, str] = field(default_factory=dict)
    extra_body: Dict[str, Any] = field(default_factory=dict)

    def resolved_api_key(self) -> str:
        """Resolve the API key from direct config or environment."""
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            value = os.getenv(self.api_key_env)
            if value:
                return value
            raise ValueError(
                f"Model '{self.name}' requires environment variable {self.api_key_env}"
            )
        raise ValueError(f"Model '{self.name}' must set api_key_env or api_key")


@dataclass
class CompareConfig:
    """Top-level comparison config."""

    system_prompt_file: Path
    cases_file: Optional[Path]
    output_dir: Path
    timeout_seconds: int
    max_concurrency: int
    defaults: Dict[str, Any]
    models: List[ModelConfig]
    config_dir: Path


def _load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE pairs from .env without overriding real env vars."""
    if not path.exists():
        return

    with open(path, "r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key or key in os.environ:
                continue

            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value.startswith(("'", '"'))
            ):
                value = value[1:-1]

            os.environ[key] = value


def _resolve_path(config_dir: Path, raw_path: Optional[str]) -> Optional[Path]:
    if not raw_path:
        return None
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (config_dir / path).resolve()


def load_compare_config(path: str) -> CompareConfig:
    """Load and validate a JSON comparison config."""
    config_path = Path(path).resolve()
    config_dir = config_path.parent

    with open(config_path, "r", encoding="utf-8") as file:
        raw = json.load(file)

    env_file = _resolve_path(config_dir, raw.get("env_file"))
    if env_file:
        _load_dotenv(env_file)

    defaults = raw.get("defaults", {})
    timeout_seconds = int(raw.get("timeout_seconds", 120))
    providers = raw.get("providers", {})

    models: List[ModelConfig] = []
    for item in raw.get("models", []):
        if not item.get("name"):
            raise ValueError("Each model config must include name")
        if not item.get("provider"):
            raise ValueError(f"Model '{item.get('name')}' must include provider")
        if not item.get("model"):
            raise ValueError(f"Model '{item.get('name')}' must include model")

        provider_name = item["provider"]
        provider_config = providers.get(provider_name, {})
        base_url = item.get("base_url") or provider_config.get("base_url")
        api_key = item.get("api_key") or provider_config.get("api_key")
        api_key_env = item.get("api_key_env") or provider_config.get("api_key_env")
        provider_type = provider_config.get("type") or item.get("type") or "openai_compatible"
        if not base_url:
            raise ValueError(
                f"Model '{item.get('name')}' must include base_url or select a provider with base_url"
            )

        headers = {
            **provider_config.get("headers", {}),
            **item.get("headers", {}),
        }
        extra_body = {
            **provider_config.get("extra_body", {}),
            **item.get("extra_body", {}),
        }

        models.append(
            ModelConfig(
                name=item["name"],
                provider=provider_name,
                provider_type=provider_type,
                model=item["model"],
                base_url=base_url,
                enabled=bool(item.get("enabled", True)),
                api_key=api_key,
                api_key_env=api_key_env,
                temperature=item.get("temperature", defaults.get("temperature")),
                max_tokens=item.get("max_tokens", defaults.get("max_tokens")),
                timeout_seconds=item.get("timeout_seconds", timeout_seconds),
                headers=headers,
                extra_body=extra_body,
            )
        )

    if not models:
        raise ValueError("Config must include at least one model")

    system_prompt_file = _resolve_path(config_dir, raw.get("system_prompt_file"))
    if not system_prompt_file:
        raise ValueError("Config must include system_prompt_file")

    return CompareConfig(
        system_prompt_file=system_prompt_file,
        cases_file=_resolve_path(config_dir, raw.get("cases_file")),
        output_dir=_resolve_path(config_dir, raw.get("output_dir")) or (config_dir / "runs"),
        timeout_seconds=timeout_seconds,
        max_concurrency=int(raw.get("max_concurrency", 4)),
        defaults=defaults,
        models=models,
        config_dir=config_dir,
    )


def read_text_file(path: Path) -> str:
    """Read a UTF-8 text file and strip trailing whitespace only."""
    with open(path, "r", encoding="utf-8") as file:
        return file.read().rstrip()


def _normalize_case_input(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def load_cases(path: Path) -> List[Dict[str, str]]:
    """Load cases from a JSON array with id/input fields."""
    with open(path, "r", encoding="utf-8") as file:
        raw = json.load(file)

    if not isinstance(raw, list):
        raise ValueError("cases_file must be a JSON array")

    cases: List[Dict[str, str]] = []
    for index, item in enumerate(raw, start=1):
        if isinstance(item, str):
            cases.append({"id": f"case_{index}", "input": item})
            continue
        if not isinstance(item, dict) or not item.get("input"):
            raise ValueError("Each case must be a string or an object with input")
        cases.append(
            {
                "id": str(item.get("id") or f"case_{index}"),
                "input": _normalize_case_input(item["input"]),
            }
        )
    return cases
