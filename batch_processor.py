#!/usr/bin/env python3
"""
batch_processor.py — Extract text from CV files in batches.

Does NOT score or call any API.
Saves extracted plain text to output/batches/extracted/cv_NNN.txt
Saves a manifest:              output/batches/extracted/manifest.json
Checkpoints progress every batch (default 20 files).

Usage:
    python batch_processor.py
    python batch_processor.py --batch-size 30
    python batch_processor.py --dir ./resume
    python batch_processor.py --reset
"""

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

# ── Optional extraction libraries ─────────────────────────────────────────────
try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False
    print("⚠  pdfplumber not found. Install with: pip install pdfplumber")

try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    print("⚠  python-docx not found. Install with: pip install python-docx")

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
STATE_DIR     = BASE_DIR / "state"
EXTRACTED_DIR = BASE_DIR / "output" / "batches" / "extracted"
PROGRESS_PATH = STATE_DIR / "progress.json"
MANIFEST_PATH = EXTRACTED_DIR / "manifest.json"

SUPPORTED_EXTS = {".pdf", ".docx", ".txt"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_json(path: Path, default=None):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def extract_text(filepath: Path) -> str:
    ext = filepath.suffix.lower()

    if ext == ".pdf":
        if not HAS_PDF:
            raise RuntimeError("pdfplumber is not installed")
        parts = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
        text = "\n".join(parts)

    elif ext == ".docx":
        if not HAS_DOCX:
            raise RuntimeError("python-docx is not installed")
        doc = DocxDocument(filepath)
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    elif ext == ".txt":
        text = filepath.read_text(encoding="utf-8", errors="replace")

    else:
        raise ValueError(f"Unsupported file type: {ext}")

    return text.strip()


def scan_folder(folder: Path) -> list[Path]:
    return sorted(
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
    )


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extract CV text in batches for Claude Code scoring")
    parser.add_argument("--batch-size", type=int, default=20, metavar="N",
                        help="Files per batch / checkpoint (default: 20)")
    parser.add_argument("--dir", type=str, default=None,
                        help="Path to resumes folder (default: resumes/ or resume/)")
    parser.add_argument("--reset", action="store_true",
                        help="Re-extract all files, ignoring prior progress")
    args = parser.parse_args()

    # ── Resolve resumes directory ──────────────────────────────────────────────
    if args.dir:
        resumes_dir = Path(args.dir).expanduser().resolve()
    else:
        resumes_dir = BASE_DIR / "resumes"
        if not resumes_dir.exists():
            fallback = BASE_DIR / "resume"
            if fallback.exists():
                print(f"ℹ  'resumes/' not found — using '{fallback.name}/' instead")
                resumes_dir = fallback
            else:
                print(f"✗  No resumes folder found at {resumes_dir}")
                sys.exit(1)

    # ── Load / reset progress ──────────────────────────────────────────────────
    if args.reset:
        progress = {"completed": [], "failed": []}
        save_json(PROGRESS_PATH, progress)
        print("↺  Progress reset.")
    else:
        progress = load_json(PROGRESS_PATH, default={"completed": [], "failed": []})

    # ── Load manifest ──────────────────────────────────────────────────────────
    manifest = load_json(MANIFEST_PATH, default={})

    # ── Discover CV files ──────────────────────────────────────────────────────
    all_files = scan_folder(resumes_dir)
    if not all_files:
        print(f"✗  No CV files found in {resumes_dir}")
        sys.exit(0)

    completed_set = set(progress["completed"])
    pending = [f for f in all_files if f.name not in completed_set]
    total_all = len(all_files)
    already_done = total_all - len(pending)

    print(f"\n📂  {total_all} CV file(s) found in {resumes_dir.name}/")
    print(f"    {already_done} already extracted")
    print(f"    {len(pending)} to extract")
    print(f"⚙   Batch size: {args.batch_size}  →  "
          f"{math.ceil(len(pending) / args.batch_size) if pending else 0} batch(es)\n")

    if not pending:
        print("✅  All CVs already extracted.")
        print(f"    Text files : {EXTRACTED_DIR.relative_to(BASE_DIR)}/")
        print(f"    Manifest   : {MANIFEST_PATH.relative_to(BASE_DIR)}")
        sys.exit(0)

    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    existing_ids = [int(k.split("_")[1]) for k in manifest if k.startswith("cv_")]
    next_id = max(existing_ids) + 1 if existing_ids else 1

    total_success = 0
    total_fail = 0
    batches = list(chunks(pending, args.batch_size))
    total_batches = len(batches)

    for batch_idx, batch_files in enumerate(batches, start=1):
        batch_success = 0
        batch_fail = 0

        print(f"─── Batch {batch_idx}/{total_batches} ({len(batch_files)} files) ───")

        for cv_path in batch_files:
            cv_id = f"cv_{next_id:03d}"
            out_path = EXTRACTED_DIR / f"{cv_id}.txt"
            print(f"  [{cv_id}] {cv_path.name} ... ", end="", flush=True)

            try:
                text = extract_text(cv_path)
                if not text:
                    raise ValueError("Extracted text is empty")

                header = (
                    f"CV_ID: {cv_id}\n"
                    f"FILENAME: {cv_path.name}\n"
                    f"EXTRACTED: {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
                    f"{'─' * 60}\n\n"
                )
                out_path.write_text(header + text, encoding="utf-8")

                manifest[cv_id] = cv_path.name
                progress["completed"].append(cv_path.name)
                next_id += 1
                batch_success += 1
                total_success += 1
                print("✓")

            except Exception as e:
                progress["failed"].append({
                    "filename": cv_path.name,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })
                batch_fail += 1
                total_fail += 1
                print(f"✗  {e}")

        # Checkpoint after every batch
        save_json(PROGRESS_PATH, progress)
        save_json(MANIFEST_PATH, manifest)

        processed_so_far = already_done + total_success + total_fail
        print(f"✓  Batch {batch_idx}/{total_batches} complete — "
              f"{processed_so_far}/{total_all} CVs extracted"
              + (f"  ({batch_fail} failed)" if batch_fail else ""))
        print()

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"{'='*56}")
    print(f"  Extraction complete")
    print(f"  Extracted : {total_success}")
    print(f"  Failed    : {total_fail}")
    print(f"\n  Text files : {EXTRACTED_DIR.relative_to(BASE_DIR)}/")
    print(f"  Manifest   : {MANIFEST_PATH.relative_to(BASE_DIR)}")
    print(f"{'='*56}")
    print()
    print("  Next step: ask Claude Code to score the extracted CVs.")
    print()


if __name__ == "__main__":
    main()
