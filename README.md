# Anchoring Vignettes for LLM Self-Report Calibration

Tests whether anchoring vignettes (King & Wand 2007) correct response bias in
LLM self-reported confidence, using code-generation correctness (hidden test
pass/fail) as checkable ground truth. See `DESIGN.md` for the instrument and
`DEVLOG.md` for project history and decisions.

Built for the Apart Research Digital Minds Research Sprint, Aug 2026.

## Status

Pilot stage: a go/no-go instrument check on 2 models x 20 tasks. Not yet a
result. See `DESIGN.md` §9 and `DEVLOG.md` for current state.

## Running

```bash
pip install -r requirements.txt   # not yet created
pytest pilot/tests/ -v            # all must pass before any API call
python run_pilot.py               # not yet built
```

Requires `ANTHROPIC_API_KEY` and `GOOGLE_API_KEY` (or equivalent) in `.env`.
