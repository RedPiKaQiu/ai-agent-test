"""Concurrent model comparison runner."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .config import CompareConfig, ModelConfig


def enabled_models(config: CompareConfig) -> List[ModelConfig]:
    """Return enabled models only."""
    return [model for model in config.models if model.enabled]


def create_client(model_config: ModelConfig):
    """Create a provider client."""
    if model_config.provider_type != "openai_compatible":
        raise ValueError(
            f"Unsupported provider type '{model_config.provider_type}' for model '{model_config.name}'"
        )
    from .openai_compatible import OpenAICompatibleClient

    return OpenAICompatibleClient(model_config)


async def run_one_case(
    system_prompt: str,
    case: Dict[str, str],
    models: Iterable[ModelConfig],
    max_concurrency: int,
) -> Dict[str, Any]:
    """Run one input case against all enabled models."""
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _call(model_config: ModelConfig) -> Dict[str, Any]:
        async with semaphore:
            try:
                client = create_client(model_config)
                response = await client.complete(system_prompt, case["input"])
                return {"ok": True, **response}
            except Exception as exc:
                return {
                    "ok": False,
                    "model_name": model_config.name,
                    "provider": model_config.provider,
                    "requested_model": model_config.model,
                    "temperature": model_config.temperature,
                    "max_tokens": model_config.max_tokens,
                    "error": str(exc),
                }

    results = await asyncio.gather(*[_call(model_config) for model_config in models])
    return {
        "case": case,
        "results": results,
    }


async def run_cases(
    system_prompt: str,
    cases: List[Dict[str, str]],
    config: CompareConfig,
) -> Dict[str, Any]:
    """Run all cases."""
    models = enabled_models(config)
    if not models:
        raise ValueError("No enabled models found in config")

    case_results = []
    started_at = datetime.now()
    for case in cases:
        case_results.append(
            await run_one_case(
                system_prompt=system_prompt,
                case=case,
                models=models,
                max_concurrency=config.max_concurrency,
            )
        )

    return {
        "created_at": started_at.isoformat(timespec="seconds"),
        "system_prompt_file": str(config.system_prompt_file),
        "models": [
            {
                "name": model.name,
                "provider": model.provider,
                "provider_type": model.provider_type,
                "model": model.model,
                "base_url": model.base_url,
                "temperature": model.temperature,
                "max_tokens": model.max_tokens,
            }
            for model in models
        ],
        "cases": case_results,
    }


def print_report(report: Dict[str, Any]) -> None:
    """Print a readable report to stdout."""
    for case_result in report["cases"]:
        case = case_result["case"]
        print("\n" + "=" * 80)
        print(f"Case: {case['id']}")
        print("-" * 80)
        print(case["input"])
        print("=" * 80)

        for result in case_result["results"]:
            options = []
            if result.get("temperature") is not None:
                options.append(f"temperature={result['temperature']}")
            if result.get("max_tokens") is not None:
                options.append(f"max_tokens={result['max_tokens']}")
            suffix = f" ({', '.join(options)})" if options else ""
            print(f"\n[{result['model_name']}] {result.get('requested_model')}{suffix}")
            print("-" * 80)
            if not result["ok"]:
                print(f"ERROR: {result['error']}")
                continue
            print(result.get("answer", "").strip())
            usage = result.get("usage") or {}
            total_tokens = usage.get("total_tokens")
            latency = result.get("latency_seconds")
            footer = []
            if latency is not None:
                footer.append(f"{latency:.2f}s")
            if total_tokens is not None:
                footer.append(f"{total_tokens} tokens")
            if footer:
                print("-" * 80)
                print(" | ".join(footer))


def save_report(report: Dict[str, Any], output_dir: Path) -> Dict[str, Path]:
    """Save the report as JSON and Markdown."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"model_compare_{timestamp}.json"
    md_path = output_dir / f"model_compare_{timestamp}.md"

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    with open(md_path, "w", encoding="utf-8") as file:
        file.write(to_markdown(report))

    return {"json": json_path, "markdown": md_path}


def to_markdown(report: Dict[str, Any]) -> str:
    """Render the report as Markdown."""
    lines = [
        "# Model Compare Report",
        "",
        f"- Created at: {report['created_at']}",
        f"- System prompt: `{report['system_prompt_file']}`",
        "",
        "## Models",
        "",
    ]

    for model in report["models"]:
        options = []
        if model.get("temperature") is not None:
            options.append(f"temperature={model['temperature']}")
        if model.get("max_tokens") is not None:
            options.append(f"max_tokens={model['max_tokens']}")
        suffix = f" ({', '.join(options)})" if options else ""
        lines.append(f"- `{model['name']}`: `{model['model']}` @ `{model['base_url']}`{suffix}")

    for case_result in report["cases"]:
        case = case_result["case"]
        lines.extend(["", f"## {case['id']}", "", "### Input", "", case["input"], ""])

        for result in case_result["results"]:
            options = []
            if result.get("temperature") is not None:
                options.append(f"temperature={result['temperature']}")
            if result.get("max_tokens") is not None:
                options.append(f"max_tokens={result['max_tokens']}")
            suffix = f" ({', '.join(options)})" if options else ""
            lines.extend(["", f"### {result['model_name']}{suffix}", ""])
            if not result["ok"]:
                lines.append(f"ERROR: {result['error']}")
                continue
            lines.append(result.get("answer", "").strip())
            usage = result.get("usage") or {}
            metadata = []
            if result.get("latency_seconds") is not None:
                metadata.append(f"latency={result['latency_seconds']:.2f}s")
            if usage.get("total_tokens") is not None:
                metadata.append(f"tokens={usage['total_tokens']}")
            if metadata:
                lines.extend(["", "`" + ", ".join(metadata) + "`"])

    return "\n".join(lines).rstrip() + "\n"
