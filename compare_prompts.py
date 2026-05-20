#!/usr/bin/env python3
"""Compare multiple system prompts with one or more configured models."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Optional

from llm_compare.config import load_cases, load_prompt_compare_config
from llm_compare.runner import (
    print_prompt_outputs,
    print_prompt_progress,
    print_prompt_summary,
    run_prompt_cases,
    save_prompt_report,
    to_prompt_markdown,
)


def _build_cases(args: argparse.Namespace, config_cases_file: Optional[Path]) -> List[Dict[str, str]]:
    if args.case:
        return [{"id": "cli_case", "input": args.case}]

    cases_file = Path(args.cases_file).resolve() if args.cases_file else config_cases_file
    if not cases_file:
        raise ValueError("No case provided. Use --case or set cases_file in config.")
    return load_cases(cases_file)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare multiple system prompts with OpenAI-compatible chat models."
    )
    parser.add_argument(
        "--config",
        default="configs/prompt_single.example.json",
        help="Path to prompt comparison config JSON.",
    )
    parser.add_argument(
        "--case",
        default=None,
        help="Run one user input directly from CLI.",
    )
    parser.add_argument(
        "--cases-file",
        default=None,
        help="Override cases_file from config.",
    )
    parser.add_argument(
        "--list-prompts",
        action="store_true",
        help="List configured prompt variants and exit.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List configured models and exit.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Print only; do not save JSON/Markdown reports.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output_dir from config.",
    )
    parser.add_argument(
        "--print",
        dest="print_outputs",
        action="store_true",
        help="Print Model, Status, Latency and Output after the progress summary.",
    )
    parser.add_argument(
        "--print-report",
        action="store_true",
        help="Print full prompt comparison report after the progress summary.",
    )
    args = parser.parse_args()

    try:
        config = load_prompt_compare_config(args.config)

        if args.list_prompts:
            for prompt in config.prompts:
                status = "enabled" if prompt.enabled else "disabled"
                print(f"{prompt.name}: {prompt.path} ({status})")
            return

        if args.list_models:
            for model in config.models:
                status = "enabled" if model.enabled else "disabled"
                options = []
                if model.temperature is not None:
                    options.append(f"temperature={model.temperature}")
                if model.max_tokens is not None:
                    options.append(f"max_tokens={model.max_tokens}")
                suffix = f", {', '.join(options)}" if options else ""
                print(f"{model.name}: {model.provider}/{model.model} ({status}{suffix})")
            return

        cases = _build_cases(args, config.cases_file)
        report = await run_prompt_cases(cases, config, progress_callback=print_prompt_progress)

        saved = None
        if not args.no_save:
            output_dir = Path(args.output_dir).resolve() if args.output_dir else config.output_dir
            saved = save_prompt_report(report, output_dir)

        print_prompt_summary(report, saved)

        if args.no_save and not args.print_report and not args.print_outputs:
            print("- Detailed answers: not saved (--no-save) and not printed", flush=True)

        if args.print_outputs:
            print_prompt_outputs(report)

        if args.print_report:
            print(to_prompt_markdown(report))

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
