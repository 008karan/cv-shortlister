# CV Shortlister — Project Brief for Claude Code

## What this project does
Shortlists candidates from a batch of CVs against a Job Description.
Designed to handle 300-400 CVs across any role with zero code changes.

## CRITICAL: How intelligence works in this project
- Claude Code (you) ARE the AI doing all scoring and reasoning
- There is NO Anthropic API key, NO external API calls
- Python scripts handle ONLY: file reading, JSON saving, Excel building
- Never generate code that calls any external API or LLM

## Folder structure
- jd/           → contains the Job Description (one .txt file)
- resumes/      → contains all candidate CVs (.pdf, .docx, .txt)
- state/        → jd_criteria.json (parsed JD), progress.json (run tracker)
- output/
  - batches/    → intermediate per-batch score JSONs
  - final/      → compiled ranked Excel output

## Pipeline order
1. main.py → orchestrates everything
2. JD parsed once → saved to state/jd_criteria.json
3. CVs extracted in batches of 20 → text saved to output/batches/extracted/
4. Claude Code scores each CV → saved to output/batches/scores/
5. compile_results.py → builds final Excel from all score JSONs

## Scoring rubric (always use these weights)
- Must-have skills match: 40%
- Experience fit: 25%
- Nice-to-have skills: 20%
- Domain relevance: 15%

## Output Excel rules
- Sort by weighted total score descending
- Top 30% = Shortlisted: Yes
- Green rows for shortlisted, red rows for red flags
- Two sheets: Main ranking + Red Flags isolated

## Error handling rules
- Never crash full pipeline if one CV fails
- Log failures to state/progress.json under "failed" key
- Always resume from progress.json if restarted mid-run

## Running for a new role
- Clear jd/ and resumes/ folders
- Delete state/ folder for fresh start
- Run main.py
