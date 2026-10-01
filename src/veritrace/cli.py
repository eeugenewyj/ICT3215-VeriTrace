import argparse
import json
import sys
from pathlib import Path

from .errors import InputError, VeriTraceError
from .runtime.benchmark import benchmark
from .runtime.budget import ContextBudget
from .runtime.client import OllamaClient
from .settings import load_settings


def main(argv=None):
    parser = argparse.ArgumentParser(prog="veritrace", description="Local testimony-to-artefact verification")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("doctor", "benchmark"):
        command = commands.add_parser(name)
        command.add_argument("--config", type=Path, required=True)
        if name == "benchmark":
            command.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("run", help="Analyse an acquired artefact folder")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--case", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    evaluate = commands.add_parser("evaluate", help="Evaluate a frozen labelled corpus")
    evaluate.add_argument("--config", type=Path, required=True)
    evaluate.add_argument("--corpus", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        settings = load_settings(args.config)
        if args.command == "evaluate":
            from .evaluation.corpus import evaluate_corpus
            result = evaluate_corpus(args.corpus, args.output, settings)
            print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
            return 3 if result["metrics"]["operational_failure_rate"] == 1 else 0
        if args.command == "run":
            from .service import run_case
            result = run_case(args.case, args.output, settings)
            print(json.dumps({"status": result.status, "report": result.output_paths["report.html"], "errors": result.errors, "claim_errors": result.claim_errors}, ensure_ascii=False, indent=2))
            return {"complete": 0, "error": 3, "partial": 4}[result.status]
        with OllamaClient(settings) as client:
            metadata = client.metadata()
            if args.command == "doctor":
                result = {"model": metadata, "enabled_families": settings.enabled_families,
                          "parser_commands": settings.parser_commands, "budget_profile_configured": settings.budget_profile is not None}
            else:
                if args.output.exists():
                    raise InputError("Benchmark output already exists; choose a fresh path")
                result = benchmark(client, ContextBudget(settings, metadata))
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                profile = args.output.with_suffix(".budget.json")
                if profile.exists():
                    raise InputError("Budget output already exists")
                profile.write_text(json.dumps(result["budget_profile"], indent=2), encoding="utf-8")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if args.command == "doctor" or result["passed"] else 3
    except VeriTraceError as exc:
        print(json.dumps({"error": exc.code, "message": str(exc)}), file=sys.stderr)
        return 2 if isinstance(exc, InputError) else 3
