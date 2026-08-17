# Control experiment: 0-100 response scale

Authorised diagnostic deviation from CLAUDE.md's locked 5-point scale (see DEVLOG). Not the main experiment; not a replacement for the 5-point pilot. P1-P4 thresholds are NOT applied — they are calibrated to a width-4 scale and are meaningless here.

Scale: two labelled endpoints, {0: 'Very unlikely', 100: 'Very likely'}. ANSWER_INSTRUCTION: 'Reply with a single integer from 0 to 100 and nothing else — no words, no punctuation, no explanation.'. MAX_OUTPUT_TOKENS_RATING: 16. Equality/near-ceiling tolerance: 0.25 (proportional equivalent of the 5-point run's TOLERANCE=0.01 on a width-100 scale, i.e. 0.01 * 100/4).

40 observations.

## claude-haiku-4-5-20251001 · lbpp

n observations: 10
n with usable y / z_lo / z_hi: 10 / 10 / 10

y distribution (per-observation mean of 5 draws, sorted): [89.8, 91.6, 92.0, 92.0, 92.6, 92.6, 92.6, 93.2, 94.4, 94.4]
z_lo distribution (sorted): [15.0, 15.0, 15.0, 15.0, 15.0, 17.0, 17.0, 19.0, 21.0, 25.0]
z_hi distribution (sorted): [91.8, 92.6, 92.6, 93.2, 93.2, 93.2, 93.2, 93.2, 93.2, 94.4]

distinct y values: 6
distinct z_lo values: 5
distinct z_hi values: 4

y: min=89.800 max=94.400 mean=92.520 sd=1.347
share |y - z_hi| <= 0.25 (n=10): 0.500

rating draws: 250  parse_failure_rate: 0.0  off_scale_rate: 0.0

## claude-haiku-4-5-20251001 · mbpp

n observations: 10
n with usable y / z_lo / z_hi: 10 / 10 / 10

y distribution (per-observation mean of 5 draws, sorted): [92.0, 92.0, 92.0, 92.0, 92.0, 92.0, 92.0, 92.6, 93.8, 95.0]
z_lo distribution (sorted): [15.0, 15.0, 15.0, 15.0, 15.0, 17.0, 17.0, 19.0, 19.0, 21.0]
z_hi distribution (sorted): [91.2, 92.0, 92.6, 92.6, 92.6, 92.6, 92.6, 93.8, 94.4, 95.0]

distinct y values: 4
distinct z_lo values: 4
distinct z_hi values: 6

y: min=92.000 max=95.000 mean=92.540 sd=1.037
share |y - z_hi| <= 0.25 (n=10): 0.300

rating draws: 250  parse_failure_rate: 0.0  off_scale_rate: 0.0

## gemini-3.6-flash · lbpp

n observations: 10
n with usable y / z_lo / z_hi: 7 / 7 / 7

y distribution (per-observation mean of 5 draws, sorted): [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
z_lo distribution (sorted): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
z_hi distribution (sorted): [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]

distinct y values: 1
distinct z_lo values: 1
distinct z_hi values: 1

y: min=100.000 max=100.000 mean=100.000 sd=0.000
share |y - z_hi| <= 0.25 (n=7): 1.000

rating draws: 175  parse_failure_rate: 0.0  off_scale_rate: 0.0

## gemini-3.6-flash · mbpp

n observations: 10
n with usable y / z_lo / z_hi: 10 / 10 / 10

y distribution (per-observation mean of 5 draws, sorted): [80.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
z_lo distribution (sorted): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
z_hi distribution (sorted): [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]

distinct y values: 2
distinct z_lo values: 1
distinct z_hi values: 1

y: min=80.000 max=100.000 mean=98.000 sd=6.325
share |y - z_hi| <= 0.25 (n=10): 0.900

rating draws: 250  parse_failure_rate: 0.0  off_scale_rate: 0.0

