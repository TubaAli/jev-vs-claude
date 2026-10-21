# Jev vs Claude: tool-selection A/B

**Interactive results:** https://tubaali.github.io/jev-vs-claude/

## Results (125 synthetic requests × 5 runs, 32 mock tools)

| Side | Right tool | Median latency | Claude $ / 1k picks |
|---|---|---|---|
| TypeSafe Jev 1.13.0 | 93.3% | 156 ms | (TypeSafe credit) |
| Claude Sonnet 5.5, first tool call | 67.4% | 2.3 s | $2.05 |
| Claude Sonnet 5.5, final action (searches allowed) | 83.7% | 3.3 s | $6.63 |

- Most of Claude's first-pick "misses" were a search to find the email, event or file before acting. Counting those, its first pick reaches 95.2%.
- Jev was never very sure (≥ 0.9) and wrong. "Jev first, Claude when Jev is unsure" (τ ≈ 0.5) scored 94.2%.
- Nobody picked the harmful tool on the trick emails.
- On ambiguous requests, the final-action run under-scores Claude: it often searched and then opened a result, and the opening step was recorded.

Raw rows: `results/results.jsonl` (experiments `tc32` and `tc32-final`). Tables: `results/summary.md`.
Run the final-action variant with `python run_ab.py --runs 5 --arms claude --claude-mode final`.


Question: given a user request and a catalog of tools, which picks the right tool better,
faster, cheaper, and with more trustworthy confidence:
**Claude (native tool calling via the Agent SDK)** or **TypeSafe Jev (one `Choice` question)**?

## What's in the folder

| File | What it is |
|---|---|
| `data/tools.json` | 32 tools (Gmail, Calendar, Drive, GitHub, web search, weather). **Both arms get exactly this list.** |
| `data/dataset.jsonl` | 125 test requests, each labeled with the correct tool. Buckets: easy 40, near-duplicate 30, ambiguous 15, no-tool 15, prompt-injection 10, multilingual (ja / hi / Hinglish) 15. |
| `common.py` | Shared loading, the instruction text both arms get, extra "distractor" tools for the scaling test |
| `run_claude.py` | Arm A. Claude sees the tools; a hook records the first tool it picks and **blocks it**, so nothing runs. |
| `run_jev.py` | Arm B. Jev gets `state = request (+context)` and `criteria = {tool: description}` plus a `none` option. |
| `run_ab.py` | Runs every item × N runs × both arms in shuffled order and writes `results/results.jsonl`. Safe to stop and resume. |
| `metrics.py` | Writes `results/summary.md`: accuracy, latency, cost, tokens, calibration, cascade, injection, languages, scaling. |

**The tools are mock tools, not live Google MCP servers.** That's deliberate. We only measure which
tool gets *picked*, never run it, so no Google login is needed and no personal email goes to
Anthropic or TypeSafe. The names and descriptions copy the real Gmail/Calendar/Drive/GitHub MCP tools.

## Step by step (MacBook)

1. **Open Terminal** (Cmd+Space, type "Terminal", Enter).
2. **Check Python is 3.10 or newer:** `python3 --version`. If it's older or missing, install it from python.org.
3. **Go into the folder:** `cd ~/jev-vs-claude` (or wherever you put it).
4. **Make a private Python box and turn it on:**
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```
   You'll see `(.venv)` at the start of the line. Run the `source` line again every time you open a new Terminal.
5. **Install:** `pip install -r requirements.txt`. The Agent SDK ships with Claude Code built in, so no npm is needed.
6. **Add the keys.** Your friend's Anthropic key starts with `sk-ant-`; your TypeSafe key comes from the TypeSafe console.
   ```
   echo 'export ANTHROPIC_API_KEY=sk-ant-PASTE_HERE' >> ~/.zshrc
   echo 'export TYPESAFE_API_KEY=PASTE_HERE' >> ~/.zshrc
   source ~/.zshrc
   ```
7. **Test each arm on one request:**
   ```
   python run_claude.py
   python run_jev.py
   ```
   Each should print something like `{'pred': 'gmail_send_message', 'latency_ms': ...}`.
8. **Smoke test** (5 requests, about $0.10): `python run_ab.py --smoke`, then `python metrics.py`.
   Show your friend the Usage page in console.anthropic.com before going further.
9. **Main run:** `rm results/results.jsonl` (clears the smoke rows), then `python run_ab.py --runs 5`
   (625 Claude calls + 625 Jev calls, about 30–60 minutes).
   It stops by itself when Claude spend reaches `--max-cost` (default $15). If it stops or crashes,
   run the same command again and it picks up where it left off.
10. **Read the results:** `python metrics.py` → open `results/summary.md`.

No GPU or second machine is needed. The laptop only sends text; keep it awake (`caffeinate -i python run_ab.py --runs 5`).

## Cost

Measured here: one Claude Sonnet 5.5 call with 32 tools ≈ **$0.019** (~4.4k input tokens, mostly cache writes).

| Run | Claude calls | Approx. Claude cost |
|---|---|---|
| `--smoke` | 5 | ~$0.10 |
| main, `--runs 5` | 625 | ~$5–12 (lower when prompt caching hits) |
| scaling `--tool-count 100`, `--runs 3` | 375 | ~$10–15 |
| scaling `--tool-count 250`, `--runs 3` | 375 | ~$25–35 |

Jev usage comes out of your TypeSafe credit. Jev tokens are logged for every call; to see Jev in USD,
set `JEV_USD_PER_MTOK` in `metrics.py` to TypeSafe's price.

## Experiments (the interesting part)

All of these come out of the same `summary.md`:

1. **Headline A/B:** top-1 accuracy, p50/p95 latency, $ per 1k decisions, tokens.
2. **Calibration (ECE, Brier):** Jev reports a confidence. For Claude, confidence = the share of the 5 runs
   that gave its most common answer. Also lists the requests where **Jev was ≥ 0.9 confident and wrong**,
   which is the most valuable finding if it shows up.
3. **Cascade sweep:** Jev answers first and Claude takes over only when Jev's confidence is below τ.
   The table shows the accuracy / latency / cost trade-off for each τ; the best τ answers "which is more efficient".
4. **Prompt injection:** emails and docs in `context` try to make the selector call a harmful tool
   (`attack_tool`). Measures each arm's hijack rate, and whether Jev's confidence drops when it's hijacked.
5. **Multilingual:** Japanese, Hindi, Hinglish and Japanese-English mixed requests, scored per language.
6. **Tool-count scaling:** pads the catalog with realistic look-alike tools (Slack, Notion, Jira, Chatwork, kintone, freee, …):
   ```
   python run_ab.py --runs 3 --tool-count 10
   python run_ab.py --runs 3 --tool-count 100
   python run_ab.py --runs 3 --tool-count 250
   python metrics.py      # adds a scaling table across all runs
   ```

Handy flags: `--buckets injection,multilingual` (run only some buckets), `--arms jev` (one arm only),
`--jev-model <id>` (pin the Jev model version: recommended, since `latest` can change mid-study),
`--claude-model claude-opus-5-5`, `--concurrency 4`.

## Before you trust the numbers

- **Check the labels.** The 125 labels were written by Claude. Read through `data/dataset.jsonl` and fix
  any you disagree with, especially in `ambiguous` (where `alt_tools` are also counted correct) and `no_tool`.
  Adding your own requests makes the study stronger (aim for 200–300). Use the same JSON format and a unique `id`.
- Only synthetic data goes to either API. Don't add real emails to `context`.
- Claude latency is measured from sending the prompt to the moment it picks a tool; starting the CLI process is
  not counted. Jev latency is the full HTTP round trip. Run from the same network for both, which the
  interleaving already ensures.
- TypeSafe's own benchmarks were written by its own team. Independent numbers like yours are worth publishing.
