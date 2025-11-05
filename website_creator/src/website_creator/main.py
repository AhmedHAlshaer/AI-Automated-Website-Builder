# file: src/website_creator/main.py
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Third-party warning suppression (tokenizers sometimes import pysbd)
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Prefer relative import within the package layout:
# Ensure this path matches your actual package. If your file lives next to crew.py as a module,
# keep as from website_creator.crew import WebsiteCreator
try:
    from website_creator.crew import WebsiteCreator  # noqa: F401
except Exception as exc:  # why: fail fast if packaging/import is wrong
    raise SystemExit(
        f"[main] Failed to import WebsiteCreator from website_creator.crew: {exc}"
    )


ARTIFACTS_DIR = Path("artifacts")


def _ensure_artifacts_dir() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def _stdin_text() -> str:
    if sys.stdin and not sys.stdin.isatty():
        data = sys.stdin.read()
        # Normalize newlines and trim
        return data.replace("\r\n", "\n").strip()
    return ""


def _ask_customer_request() -> str:
    print("🛠  Website Builder")
    print("Describe the website you want (features, purpose, audience, etc.).")
    print("Press Enter when you're done:\n")
    try:
        return input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def _build_inputs(customer_request: str) -> Dict[str, Any]:
    return {
        "customer_request": customer_request,
        "current_year": str(datetime.now().year),
    }


def _validate_crewai_yaml_loaded(wc: WebsiteCreator) -> None:
    # why: CrewBase should have dicts loaded for agents/tasks; guard against path typos
    if not isinstance(getattr(wc, "agents_config", None), dict):
        raise RuntimeError(
            "agents_config not loaded. Ensure 'config/agents.yaml' exists and CrewBase path is correct."
        )
    if not isinstance(getattr(wc, "tasks_config", None), dict):
        raise RuntimeError(
            "tasks_config not loaded. Ensure 'config/tasks.yaml' exists and CrewBase path is correct."
        )


def _persist_run_summary(payload: Dict[str, Any]) -> Path:
    path = ARTIFACTS_DIR / "run_summary.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the WebsiteCreator crew to build a website from your prompt."
    )
    parser.add_argument(
        "-r",
        "--customer-request",
        type=str,
        help='Website description, e.g. "A study planner with login and calendar sync."',
    )
    parser.add_argument(
        "-n",
        "--website-name",
        type=str,
        help='Optional explicit website name, e.g. "StudyPlanner Pro".',
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the final crew result JSON to stdout (machine-friendly).",
    )
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Fail if no request provided via flag/stdin (useful for CI).",
    )
    return parser.parse_args(argv)


def resolve_customer_request(args: argparse.Namespace) -> str:
    # Priority: CLI flag > stdin > interactive prompt (unless --no-prompt)
    if args.customer_request and args.customer_request.strip():
        return args.customer_request.strip()

    piped = _stdin_text()
    if piped:
        return piped

    if args.no_prompt:
        return ""

    return _ask_customer_request()


def main(argv: list[str] | None = None) -> int:
    # Best-effort sane I/O defaults
    os.environ.setdefault("PYTHONUTF8", "1")

    args = parse_args(argv)
    _ensure_artifacts_dir()

    customer_request = resolve_customer_request(args)
    if not customer_request:
        print("No website description provided. Use -r/--customer-request or pipe via stdin.", file=sys.stderr)
        return 2

    inputs = _build_inputs(customer_request)

    # Build and validate crew wiring
    wc = WebsiteCreator()
    _validate_crewai_yaml_loaded(wc)

    # Prefer the convenience runner if you added it; otherwise call crew().kickoff
    try:
        if hasattr(wc, "run") and callable(getattr(wc, "run")):
            result = wc.run(customer_request=customer_request, website_name=args.website_name)
        else:
            # Fallback path if .run() is not present
            crew = wc.crew()
            # Provide website_name for agents that reference it
            kickoff_inputs = {
                **inputs,
                "website_name": args.website_name or "Generated Website",
            }
            result = crew.kickoff(inputs=kickoff_inputs)
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as e:
        # Surface root cause; still write a minimal summary for CI debugging
        err_payload = {
            "ok": False,
            "error": str(e),
            "customer_request": customer_request,
        }
        _persist_run_summary(err_payload)
        print(f"[main] Error: {e}", file=sys.stderr)
        return 1

    # Persist a human+machine friendly summary for CI/ops
    summary = {
        "ok": True,
        "customer_request": customer_request,
        "website_name": args.website_name or "Generated Website",
        "artifacts_dir": str(ARTIFACTS_DIR.resolve()),
        # CrewAI returns a nested dict-like; we keep it as-is for downstream tools
        "result": result,
    }
    summary_path = _persist_run_summary(summary)

    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print("✅ Crew finished.")
        print(f"🗂  Artifacts: {summary_path}")
        # Point to the common artifact files if they exist
        for fname in (
            "planner.json",
            "blueprint.md",
            "frontend.json",
            "backend.json",
            "integration.json",
            "repository.json",
            "test_report.json",
            "evaluation.json",
        ):
            fp = ARTIFACTS_DIR / fname
            if fp.exists():
                print(f"  - {fp}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
