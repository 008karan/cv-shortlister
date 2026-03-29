#!/usr/bin/env python3
"""
main.py — CV Shortlister Pipeline Orchestrator

Steps:
  1. Validate jd/ and resumes/ folders
  2. Check state/jd_criteria.json exists
  3. Show extraction progress
  4. Run batch_processor.py  (extract text only — no API)
  5. Pause: Claude Code reads & scores each CV
  6. Run compile_results.py  (build Excel — no API)
  7. Show final summary

No API calls. No ANTHROPIC_API_KEY. Claude Code is the intelligence.

Usage:
    python main.py
    python main.py --batch-size 30
    python main.py --cutoff 25       # shortlist top 25%
    python main.py --top 20          # shortlist exactly top 20
    python main.py --reset           # clear progress, re-extract all
    python main.py --compile-only    # skip extraction, just build Excel
"""

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
JD_DIR        = BASE_DIR / "jd"
STATE_DIR     = BASE_DIR / "state"
JD_CRITERIA   = STATE_DIR / "jd_criteria.json"
PROGRESS_FILE = STATE_DIR / "progress.json"
EXTRACTED_DIR = BASE_DIR / "output" / "batches" / "extracted"
SCORES_DIR    = BASE_DIR / "output" / "batches" / "scores"

SUPPORTED_EXTS = {".pdf", ".docx", ".txt"}


# ── UI helpers ─────────────────────────────────────────────────────────────────

def header(text: str):
    bar = "─" * 58
    print(f"\n{bar}")
    print(f"  {text}")
    print(f"{bar}")


def step(n: int, text: str):
    print(f"\n[{n}] {text}")


def ok(text: str):   print(f"  ✓  {text}")
def warn(text: str): print(f"  ⚠  {text}")
def err(text: str):  print(f"  ✗  {text}")


def ask(prompt: str) -> str:
    try:
        return input(f"\n  → {prompt} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n\nAborted.")
        sys.exit(0)


def ask_yes_no(prompt: str, default: str = "yes") -> bool:
    answer = ask(f"{prompt} (yes/no):")
    if not answer:
        return default == "yes"
    return answer in ("yes", "y")


# ── Helpers ────────────────────────────────────────────────────────────────────

def scan_folder(folder: Path) -> list[Path]:
    return sorted(
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
    )


def load_json(path: Path, default=None):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def run_script(script: str, extra_args: list[str] = None) -> int:
    cmd = [sys.executable, str(BASE_DIR / script)] + (extra_args or [])
    result = subprocess.run(cmd)
    return result.returncode


def count_scores() -> int:
    if not SCORES_DIR.exists():
        return 0
    return len(list(SCORES_DIR.glob("*_score.json")))


def count_extracted() -> int:
    if not EXTRACTED_DIR.exists():
        return 0
    return len(list(EXTRACTED_DIR.glob("cv_*.txt")))


def print_criteria(criteria: dict):
    print()
    print(f"  Role   : {criteria.get('role_title', '')}")
    print(f"  Domain : {criteria.get('domain', '')}")
    print(f"  Level  : {criteria.get('seniority_level', '')}  "
          f"(min {criteria.get('min_years_experience', '?')} yr)")

    def _list(label, key):
        items = criteria.get(key, [])
        if items:
            print(f"\n  {label}:")
            for item in items:
                print(f"    • {item}")

    _list("Must-Have",   "must_have_skills")
    _list("Strong Plus", "strong_plus_skills")
    _list("Nice to Have","nice_to_have_skills")
    _list("Red Flags",   "red_flags")
    print()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CV Shortlister — pipeline orchestrator (no API calls)")
    parser.add_argument("--batch-size", type=int, default=20, metavar="N",
                        help="CVs per extraction batch (default: 20)")
    parser.add_argument("--cutoff", type=int, default=30, metavar="PCT",
                        help="Shortlist top N%% in final report (default: 30)")
    parser.add_argument("--top", type=int, default=None, metavar="N",
                        help="Shortlist exactly top N (overrides --cutoff)")
    parser.add_argument("--reset", action="store_true",
                        help="Clear extraction progress, re-extract all CVs")
    parser.add_argument("--compile-only", action="store_true",
                        help="Skip extraction, go straight to building Excel")
    args = parser.parse_args()

    header("CV Shortlister Pipeline")

    # ── Step 1: Validate jd/ ──────────────────────────────────────────────────
    step(1, "Checking jd/ folder")

    if not JD_DIR.exists():
        err(f"jd/ folder not found.")
        sys.exit(1)

    jd_files = [
        f for f in JD_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
    ]
    if len(jd_files) == 0:
        err("jd/ folder is empty. Add a PDF, DOCX, or TXT job description file.")
        sys.exit(1)
    elif len(jd_files) > 1:
        err(f"jd/ folder has {len(jd_files)} files — expected exactly one:")
        for f in jd_files:
            print(f"    - {f.name}")
        print("\n  Remove all but one JD file and re-run.")
        sys.exit(1)

    ok(f"JD file: {jd_files[0].name}")

    # ── Step 2: Validate resumes/ folder ──────────────────────────────────────
    step(2, "Checking resumes folder")

    resumes_dir = BASE_DIR / "resumes"
    if not resumes_dir.exists():
        fallback = BASE_DIR / "resume"
        if fallback.exists():
            warn(f"'resumes/' not found — using '{fallback.name}/' instead")
            resumes_dir = fallback
        else:
            err("No resumes/ folder found. Create it and add CV files.")
            sys.exit(1)

    cv_files = scan_folder(resumes_dir)
    if not cv_files:
        err(f"No CV files found in {resumes_dir.name}/")
        sys.exit(1)

    ok(f"{len(cv_files)} CV file(s) found in {resumes_dir.name}/")

    # ── Step 3: Check JD criteria ──────────────────────────────────────────────
    step(3, "JD criteria")

    if not JD_CRITERIA.exists():
        err("state/jd_criteria.json not found.")
        print()
        print("  Tell Claude Code:")
        print(f'  "Parse {jd_files[0].name} and save criteria to state/jd_criteria.json"')
        sys.exit(1)

    criteria = load_json(JD_CRITERIA)
    ok(f"Loaded criteria for: {criteria.get('role_title', '(unknown role)')}")
    print_criteria(criteria)

    # ── Step 4: Progress status ────────────────────────────────────────────────
    step(4, "Pipeline status")

    progress    = load_json(PROGRESS_FILE, default={"completed": [], "failed": []})
    completed_set = set(progress["completed"])
    extracted   = count_extracted()
    scored      = count_scores()
    total       = len(cv_files)
    remaining   = total - sum(1 for f in cv_files if f.name in completed_set)

    print(f"  CVs in folder  : {total}")
    print(f"  Text extracted : {extracted}")
    print(f"  Scored by Claude: {scored}")
    print(f"  Remaining      : {remaining}")

    # ── Step 5: Extract text ───────────────────────────────────────────────────
    if not args.compile_only:
        step(5, "Text extraction  (batch_processor.py)")

        if remaining == 0 and not args.reset:
            ok("All CVs already extracted — skipping.")
        else:
            extra = ["--batch-size", str(args.batch_size)]
            if args.reset:
                extra.append("--reset")
            if resumes_dir.name != "resumes":
                extra += ["--dir", str(resumes_dir)]

            rc = run_script("batch_processor.py", extra)
            if rc != 0:
                err(f"batch_processor.py exited with code {rc}")
                if not ask_yes_no("Continue to scoring step anyway?", default="no"):
                    sys.exit(rc)

        extracted_now = count_extracted()
        ok(f"{extracted_now} text file(s) ready in output/batches/extracted/")

        # ── Step 6: Claude Code scoring pause ─────────────────────────────────
        step(6, "Claude Code scoring")

        scored_now = count_scores()
        unscored   = extracted_now - scored_now

        if unscored <= 0:
            ok(f"All {scored_now} CVs already scored.")
        else:
            print(f"\n  {unscored} CV(s) need scoring.")
            print()
            print("  ┌─────────────────────────────────────────────────────┐")
            print("  │  Tell Claude Code:                                  │")
            print("  │                                                     │")
            print("  │  Score all CVs in output/batches/extracted/         │")
            print("  │  against state/jd_criteria.json and save each       │")
            print("  │  result to output/batches/scores/cv_NNN_score.json  │")
            print("  └─────────────────────────────────────────────────────┘")
            print()
            ask("Press Enter once Claude Code has finished scoring...")

        scored_final = count_scores()
        if scored_final == 0:
            err("No score files found in output/batches/scores/")
            err("Make sure Claude Code has scored the CVs before compiling.")
            sys.exit(1)
        ok(f"{scored_final} score file(s) found.")

    # ── Step 7: Compile Excel ──────────────────────────────────────────────────
    step(7, "Building Excel report  (compile_results.py)")

    compile_args = []
    if args.top:
        compile_args += ["--top", str(args.top)]
    else:
        compile_args += ["--cutoff", str(args.cutoff)]

    rc = run_script("compile_results.py", compile_args)
    if rc != 0:
        err(f"compile_results.py exited with code {rc}")
        sys.exit(rc)

    # ── Step 8: Final summary ──────────────────────────────────────────────────
    step(8, "Done")

    today       = date.today().strftime("%Y-%m-%d")
    report_path = BASE_DIR / "output" / "final" / f"shortlist_{today}.xlsx"

    final_progress = load_json(PROGRESS_FILE, default={"completed": [], "failed": []})
    failed_count   = len(final_progress.get("failed", []))

    print()
    print(f"  CVs in folder  : {total}")
    print(f"  Extracted      : {count_extracted()}")
    print(f"  Scored         : {count_scores()}")
    if failed_count:
        warn(f"{failed_count} extraction failure(s) — check state/progress.json")
    if report_path.exists():
        print(f"\n  Report → output/final/shortlist_{today}.xlsx")
    print()


if __name__ == "__main__":
    main()
