# Pilot phase scripts and their output

Three one-off scripts from before the main experiment, and the raw logs they produced. Nothing in the current codebase imports any of these.

- `run_control_scale100.py` — pilot-phase control experiment for scale coarseness (a 100-point scale). Superseded by `run_main.py`'s parametrized three-format design. Output: `observations_scale100.jsonl`, `report_scale100.md` (in `pilot_phase_data/`).
- `check_untested_paths.py` — one-off pre-run diagnostic that exercised code paths not yet covered by a real call, referenced in DEVLOG.md, 2026-08-15, Open Questions. Output: `check1_gemini_thread_raw.jsonl`, `check2_rating_blocks_raw.jsonl`, `check3_recheck_raw.jsonl`.
- `probe_gemini_2_5_pro.py` — misleadingly named one-off probe. Written to probe `gemini-2.5-pro` after `gemini-3.1-pro-preview` tripped its quota. Output: `probe_gemini_2_5_pro_raw.jsonl`, `probe_gemini_3_5_flash_lite_raw.jsonl`.
