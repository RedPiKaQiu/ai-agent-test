#!/usr/bin/env python3
"""Compare multiple model outputs with one system prompt."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Optional

from llm_compare.config import load_cases, load_compare_config, read_text_file
from llm_compare.runner import (
    print_progress,
    print_report,
    print_summary,
    run_cases,
    save_report,
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
        description="Compare multiple OpenAI-compatible chat models with one system prompt."
    )
    parser.add_argument(
        "--config",
        default="configs/model_compare.example.json",
        help="Path to comparison config JSON.",
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
        "--print-report",
        action="store_true",
        help="Print full model answers after the progress summary.",
    )
    args = parser.parse_args()

    try:
        config = load_compare_config(args.config)

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

        system_prompt = read_text_file(config.system_prompt_file)
        cases = _build_cases(args, config.cases_file)
        report = await run_cases(system_prompt, cases, config, progress_callback=print_progress)

        saved = None
        if not args.no_save:
            output_dir = Path(args.output_dir).resolve() if args.output_dir else config.output_dir
            saved = save_report(report, output_dir)

        print_summary(report, saved)

        if args.no_save and not args.print_report:
            print("- Detailed answers: not saved (--no-save) and not printed", flush=True)

        if args.print_report:
            print_report(report)

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
