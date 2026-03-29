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
| **Must-Have Skills** | 40% | Voice AI tools, real-time systems, backend stack, agentic AI, LLM orchestration |
| **Experience Fit** | 25% | Years of experience, seniority match, domain relevance |
| **Nice-to-Have Skills** | 20% | DevOps, ASR/TTS tools, LangChain, open-source work |
| **Domain Relevance** | 15% | How directly the candidate's work maps to the target domain |

```
Weighted Total = (Must-Have × 0.40) + (Experience × 0.25)
              + (Nice-to-Have × 0.20) + (Domain × 0.15)
```

### Special Flags

| Flag | Criteria | Excel highlight |
|---|---|---|
| ✅ **Shortlisted** | Top 30% by score | 🟩 Green row |
| 🔬 **Research** | Prestigious institute (IIT/IISc/CMU/Stanford…) + voice AI / ASR / TTS domain work → +2 bonus on Experience | 🟦 Teal row |
| 🚩 **Red Flag** | Zero voice AI + zero real-time + zero LLMs + zero audio | 🟥 Red row |

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
| 1 | Jane Doe | jane.pdf | 7.55 | 8 | 7 | 7 | 8 | Yes | No | No | Building production voice AI telecaller… |
| 2 | John Smith | john.pdf | 6.35 | 7 | 6 | 5 | 7 | Yes | No | No | Built Twilio+WebSocket voice assistant… |

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
