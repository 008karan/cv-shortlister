# CV Shortlister — AI-Powered Candidate Screening Pipeline

> Drop in a Job Description + a folder of CVs. Get back a ranked, colour-coded Excel shortlist.
> Built to handle **300–400 CVs per run** with zero manual effort.

---

## How It Works

The pipeline has a clean separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOU RUN                                  │
│                      python main.py                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │  STEP 1 — Validate                  │
          │  • jd/ has exactly one JD file      │
          │  • resumes/ has at least one CV     │
          │  • state/jd_criteria.json exists    │
          └──────────────────┬──────────────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │  STEP 2 — Extract  (batch_processor) │
          │  • Reads every PDF / DOCX / TXT      │
          │  • Saves plain text to               │
          │    output/batches/extracted/         │
          │  • Processes in batches of 20        │
          │  • Checkpoints progress after each   │
          └──────────────────┬──────────────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │  STEP 3 — Score  (Claude Code)       │
          │  • Reads each extracted text file    │
          │  • Scores against jd_criteria.json   │
          │  • Saves score JSON per candidate    │
          │    output/batches/scores/            │
          │  • NO API calls — Claude Code IS     │
          │    the intelligence                  │
          └──────────────────┬──────────────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │  STEP 4 — Compile  (compile_results) │
          │  • Merges all score JSONs            │
          │  • Sorts by weighted score           │
          │  • Top 30% → Shortlisted: Yes        │
          │  • Exports colour-coded Excel        │
          └──────────────────┬──────────────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │  OUTPUT                              │
          │  output/final/shortlist_YYYY-MM-DD   │
          │  .xlsx — ready to share              │
          └─────────────────────────────────────┘
```

---

## Folder Structure

```
cv-shortlister/
│
├── main.py                  # Orchestrator — run this
├── batch_processor.py       # Extracts text from CVs (no scoring)
├── compile_results.py       # Builds final Excel from score JSONs
├── CLAUDE.md                # Project brief loaded by Claude Code
│
├── jd/                      # ← Drop your Job Description here
│   └── your_jd.pdf
│
├── resumes/                 # ← Drop all candidate CVs here
│   ├── candidate_a.pdf
│   ├── candidate_b.docx
│   └── ...
│
├── state/                   # Auto-generated runtime state
│   ├── jd_criteria.json     # Parsed JD scoring criteria
│   └── progress.json        # Run tracker (completed / failed)
│
└── output/                  # Auto-generated outputs
    ├── batches/
    │   ├── extracted/        # Plain text from each CV
    │   │   ├── cv_001.txt
    │   │   ├── cv_002.txt
    │   │   └── manifest.json
    │   └── scores/           # Score JSON per candidate
    │       ├── cv_001_score.json
    │       └── cv_002_score.json
    └── final/
        └── shortlist_2026-03-28.xlsx   # ← Final output
```

---

## Scoring System

Each CV is scored across four dimensions:

| Dimension | Weight | What it measures |
|---|---|---|
| **Must-Have Skills** | 40% | Non-negotiable skills and tools extracted from your JD |
| **Experience Fit** | 25% | Years of experience and seniority match for the role |
| **Nice-to-Have Skills** | 20% | Bonus skills, strong-plus qualifications from your JD |
| **Domain Relevance** | 15% | How directly the candidate's past work maps to your domain |

> **These dimensions are role-agnostic.** What counts as a "must-have" or "nice-to-have"
> is driven entirely by your `state/jd_criteria.json` — not hardcoded anywhere in the scripts.

```
Weighted Total = (Must-Have × 0.40) + (Experience × 0.25)
              + (Nice-to-Have × 0.20) + (Domain × 0.15)
```

### Special Flags

| Flag | Criteria | Excel highlight |
|---|---|---|
| ✅ **Shortlisted** | Top 30% by weighted score (configurable via `--cutoff` or `--top`) | 🟩 Green row |
| 🔬 **Research** | Candidate has R&D / research background from a prestigious institute **and** the work is directly in your target domain → +2 bonus applied to Experience score | 🟦 Teal row |
| 🚩 **Red Flag** | Candidate has zero overlap with your JD's core domain — none of the must-have skills, no relevant experience | 🟥 Red row |

> **Example only** — flags are configured per run inside `state/jd_criteria.json`.
> For a Backend role you might red-flag "no backend experience."
> For a Data Science role you might red-flag "no Python or ML experience."
> The criteria are yours to define.

---

## The Intelligence Model

```
❌  WRONG approach (what most tools do):
    Python script → calls OpenAI/Anthropic API → scores CV

✅  THIS project:
    Claude Code reads CV → Claude Code scores it
    → Python saves result → Python builds Excel
```

**Python scripts handle zero AI logic.** They only:
- Extract text from files (`pdfplumber`, `python-docx`)
- Read and write JSON
- Build the Excel workbook (`openpyxl`)

**Claude Code is the recruiter.** It reads each CV, applies the JD criteria, and writes a score JSON directly — no API calls, no tokens, no cost per CV.

---

## Output Excel

The final Excel has two sheets:

**Sheet 1 — All Candidates** (sorted by score, highest first)

| Rank | Name | File | Total Score | Must-Have | Experience | Nice-to-Have | Domain | Shortlisted | Research | Red Flag | Summary |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Jane Doe | jane_doe.pdf | 7.55 | 8 | 7 | 7 | 8 | Yes | No | No | *(one-line highlight of the candidate's most relevant experience)* |
| 2 | John Smith | john_smith.pdf | 6.35 | 7 | 6 | 5 | 7 | Yes | Yes | No | *(research bonus applied — strong domain R&D background)* |
| 3 | Alex Brown | alex_brown.pdf | 2.10 | 2 | 3 | 1 | 1 | No | No | Yes | *(no overlap with JD requirements)* |

**Sheet 2 — Red Flags** (isolated for quick review)

---

## Quick Start

### 1. Install dependencies

```bash
pip install pdfplumber python-docx openpyxl
```

### 2. Set up your run

```bash
# Add your Job Description
cp your_jd.pdf jd/

# Add all candidate CVs
cp /path/to/cvs/*.pdf resumes/
```

### 3. Create JD criteria

Ask Claude Code to parse your JD:
```
"Read jd/ and save scoring criteria to state/jd_criteria.json"
```

Review and confirm the extracted criteria before proceeding.

### 4. Run the pipeline

```bash
python main.py
```

The pipeline will:
- Extract all CVs in batches of 20
- Pause for Claude Code to score them
- Compile and export the Excel report

### 5. Options

```bash
python main.py --batch-size 30     # Larger batches
python main.py --cutoff 20         # Shortlist top 20% instead of 30%
python main.py --top 15            # Shortlist exactly top 15 candidates
python main.py --reset             # Clear progress, re-run everything
python main.py --compile-only      # Skip extraction, just rebuild Excel
```

---

## Running for a New Role

```bash
# Clear previous run data
rm -rf jd/* resumes/* state/ output/

# Add new JD and CVs
cp new_role.pdf jd/
cp /path/to/new_cvs/*.pdf resumes/

# Run
python main.py
```

---

## Supported File Formats

| Format | Library |
|---|---|
| `.pdf` | `pdfplumber` |
| `.docx` | `python-docx` |
| `.txt` | built-in |

---

## Error Handling

- **One CV fails?** It's logged to `state/progress.json` under `"failed"` — the rest continue
- **Pipeline crashes mid-run?** Re-run `python main.py` — it resumes from where it left off, skipping already-extracted files
- **Want to re-score a specific CV?** Delete its `output/batches/scores/cv_NNN_score.json` and re-run

---

## Dependencies

```
pdfplumber      # PDF text extraction
python-docx     # DOCX text extraction
openpyxl        # Excel report generation
```

No OpenAI. No Anthropic SDK. No API keys. No cost per CV.

---

*Built with [Claude Code](https://claude.ai/claude-code)*
