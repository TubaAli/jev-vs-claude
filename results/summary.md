# Jev vs Claude: tool selection A/B

## Experiment `tc32` (32 tools)

| arm | calls | top-1 acc | p50 ms | p95 ms | total $ | $ / 1k decisions | avg input tok |
|---|---|---|---|---|---|---|---|
| claude | 625 | 0.674 | 2274 | 5261 | 1.28 | 2.053 | 3923 |
| jev | 625 | 0.933 | 156 | 212 | 0.00 | 0.000 | 1170 |

**Accuracy by bucket**

| bucket | claude | jev |
|---|---|---|
| ambiguous | 0.533 | 0.440 |
| easy | 0.675 | 1.000 |
| injection | 0.800 | 1.000 |
| multilingual | 0.613 | 1.000 |
| near_duplicate | 0.567 | 1.000 |
| no_tool | 1.000 | 1.000 |

**Accuracy by lang**

| lang | claude | jev |
|---|---|---|
| en | 0.682 | 0.924 |
| hi | 0.840 | 1.000 |
| hinglish | 0.250 | 1.000 |
| ja | 0.600 | 1.000 |
| ja-en | 1.000 | 1.000 |

**Calibration** (lower is better; Claude confidence = vote share across runs)

| arm | ECE | Brier | n |
|---|---|---|---|
| jev | 0.051 | 0.051 | 625 |
| claude | 0.322 | 0.316 | 125 |

Jev confidently wrong (conf ≥ 0.9): **0** calls

**Cascade sweep** (Jev first; Claude when confidence < τ)

| τ | acc | fallback rate | p50 ms | p95 ms | Claude $ / 1k |
|---|---|---|---|---|---|
| Jev only | 0.933 | 0.00 | 156 | 212 | 0.000 |
| 0.5 | 0.933 | 0.04 | 156 | 270 | 0.086 |
| 0.6 | 0.906 | 0.09 | 156 | 2280 | 0.174 |
| 0.7 | 0.890 | 0.15 | 158 | 2672 | 0.295 |
| 0.8 | 0.853 | 0.20 | 160 | 2788 | 0.399 |
| 0.9 | 0.805 | 0.30 | 164 | 3074 | 0.593 |
| 0.95 | 0.726 | 0.41 | 175 | 3658 | 0.812 |
| Claude only* | 0.674 | 1.00 | 2442 | 5409 | 2.053 |

*Claude-only row includes Jev's latency; read the headline table for pure Claude.

**Prompt injection**

| arm | hijack rate | correct rate | mean conf when hijacked |
|---|---|---|---|
| claude | 0.000 | 0.800 | n/a |
| jev | 0.000 | 1.000 | – |

## Experiment `tc32-final` (32 tools)

| arm | calls | top-1 acc | p50 ms | p95 ms | total $ | $ / 1k decisions | avg input tok |
|---|---|---|---|---|---|---|---|
| claude | 625 | 0.837 | 3267 | 5926 | 4.14 | 6.627 | 10208 |
| jev | 625 | 0.933 | 156 | 212 | 0.00 | 0.000 | 1170 |

**Accuracy by bucket**

| bucket | claude | jev |
|---|---|---|
| ambiguous | 0.347 | 0.440 |
| easy | 0.925 | 1.000 |
| injection | 0.940 | 1.000 |
| multilingual | 0.867 | 1.000 |
| near_duplicate | 0.833 | 1.000 |
| no_tool | 1.000 | 1.000 |

**Accuracy by lang**

| lang | claude | jev |
|---|---|---|
| en | 0.833 | 0.924 |
| hi | 0.800 | 1.000 |
| hinglish | 0.750 | 1.000 |
| ja | 1.000 | 1.000 |
| ja-en | 1.000 | 1.000 |

**Calibration** (lower is better; Claude confidence = vote share across runs)

| arm | ECE | Brier | n |
|---|---|---|---|
| jev | 0.051 | 0.051 | 625 |
| claude | 0.155 | 0.149 | 125 |

Jev confidently wrong (conf ≥ 0.9): **0** calls

**Cascade sweep** (Jev first; Claude when confidence < τ)

| τ | acc | fallback rate | p50 ms | p95 ms | Claude $ / 1k |
|---|---|---|---|---|---|
| Jev only | 0.933 | 0.00 | 156 | 212 | 0.000 |
| 0.5 | 0.942 | 0.04 | 156 | 270 | 0.230 |
| 0.6 | 0.941 | 0.09 | 156 | 4038 | 0.632 |
| 0.7 | 0.933 | 0.15 | 158 | 4799 | 1.109 |
| 0.8 | 0.920 | 0.20 | 160 | 5337 | 1.554 |
| 0.9 | 0.899 | 0.30 | 164 | 5562 | 2.311 |
| 0.95 | 0.859 | 0.41 | 175 | 5785 | 3.004 |
| Claude only* | 0.837 | 1.00 | 3424 | 6090 | 6.627 |

*Claude-only row includes Jev's latency; read the headline table for pure Claude.

**Prompt injection**

| arm | hijack rate | correct rate | mean conf when hijacked |
|---|---|---|---|
| claude | 0.000 | 0.940 | n/a |
| jev | 0.000 | 1.000 | – |
