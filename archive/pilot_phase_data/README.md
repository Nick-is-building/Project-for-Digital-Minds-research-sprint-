# Pilot phase data

Two runs' worth of output, both superseded by the main experiment in
`pilot/out/` (5 models x 60 tasks x 3 formats, 900 observations).

Second pilot run (10 MBPP + 10 LBPP tasks, reworded questions), DEVLOG.md
2026-08-14 22:40:

- `observations.jsonl` — parsed pilot observations
- `raw.jsonl` — raw pilot call log
- `report.md` — pilot analysis report
- `run_log.txt` — pilot run console log

0-100 scale-coarseness control run (same tasks and models as the second
pilot, `run_control_scale100.py` in `pilot_phase_scripts/`), DEVLOG.md
2026-08-14 22:33:

- `observations_scale100.jsonl` — parsed control-run observations
- `report_scale100.md` — control-run analysis report (no P1-P4 verdicts;
  see the entry for why)

Kept for the historical record of how the design changed between the pilot
and the main run. Not used by any current script.
