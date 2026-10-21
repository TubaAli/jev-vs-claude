"""Run the A/B: every dataset item x N runs x both arms, interleaved, appended to a JSONL file.

Examples:
  python run_ab.py --smoke                    # 5 items, 1 run, both arms (check keys + cost)
  python run_ab.py --runs 5                   # main experiment
  python run_ab.py --runs 3 --tool-count 100  # tool-count scaling experiment
Re-running the same command resumes: finished (exp, id, arm, run) rows are skipped.
"""
import argparse
import asyncio
import json
import random
import time
import traceback
from pathlib import Path

from typesafe_sdk import AsyncTypeSafeClient

from common import load_dataset, load_tools, tools_for
from run_claude import claude_select
from run_jev import jev_select


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--limit", type=int, help="only the first N items")
    p.add_argument("--buckets", help="comma list, e.g. easy,injection")
    p.add_argument("--arms", default="claude,jev")
    p.add_argument("--tool-count", type=int, help="pad/trim the catalog to N tools (scaling experiment)")
    p.add_argument("--claude-model", default="claude-sonnet-5-5")
    p.add_argument("--claude-mode", default="first", choices=["first", "final"],
                   help="first = record first tool call; final = allow look-ups, record the action after them")
    p.add_argument("--jev-model", default=None, help="pin a Jev model id; default = account default")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--max-cost", type=float, default=15.0, help="stop when Claude spend (USD) passes this")
    p.add_argument("--out", default="results/results.jsonl")
    p.add_argument("--dataset", default=None)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--smoke", action="store_true", help="= --limit 5 --runs 1")
    a = p.parse_args()
    if a.smoke:
        a.limit, a.runs = 5, 1
    return a


async def main():
    a = parse_args()
    items = load_dataset(a.dataset)
    if a.buckets:
        keep = set(a.buckets.split(","))
        items = [i for i in items if i["bucket"] in keep]
    if a.limit:
        items = items[: a.limit]
    base_tools = load_tools()
    arms = a.arms.split(",")
    exp = f"tc{a.tool_count or len(base_tools)}" + ("-final" if a.claude_mode == "final" else "")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    spent = 0.0
    if out.exists():
        for line in out.read_text().splitlines():
            r = json.loads(line)
            if not r.get("error"):
                done.add((r["exp"], r["id"], r["arm"], r["run"]))
            if r["arm"] == "claude" and r.get("cost_usd"):
                spent += r["cost_usd"]

    # Interleave: each run shuffles items; for each item the arm order is random too.
    rng = random.Random(a.seed)
    jobs = []
    for run in range(a.runs):
        order = items[:]
        rng.shuffle(order)
        for item in order:
            for arm in rng.sample(arms, len(arms)):
                if (exp, item["id"], arm, run) not in done:
                    jobs.append((item, arm, run))
    print(f"{exp}: {len(items)} items x {a.runs} runs x {arms} -> {len(jobs)} calls to do "
          f"(already spent ${spent:.2f} on Claude)")

    queue = asyncio.Queue()
    for j in jobs:
        queue.put_nowait(j)
    lock = asyncio.Lock()
    state = {"spent": spent, "n": 0, "stopped": False}

    async with AsyncTypeSafeClient() as jev:
        async def worker():
            while not queue.empty() and not state["stopped"]:
                item, arm, run = queue.get_nowait()
                tools = tools_for(item, base_tools, a.tool_count, a.seed)
                try:
                    if arm == "claude":
                        res = await claude_select(item, tools, a.claude_model, a.claude_mode)
                    else:
                        res = await jev_select(jev, item, tools, a.jev_model)
                except Exception as e:  # keep going; the row is retried on the next resume
                    res = {"pred": None, "error": f"{type(e).__name__}: {e}"}
                    traceback.print_exc()
                row = {"exp": exp, "id": item["id"], "bucket": item["bucket"], "lang": item["lang"],
                       "arm": arm, "run": run, "n_tools": len(tools), "ts": time.time(), **res}
                async with lock:
                    with out.open("a") as f:
                        f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    state["n"] += 1
                    if arm == "claude" and res.get("cost_usd"):
                        state["spent"] += res["cost_usd"]
                    ok = "✓" if res.get("pred") in {item["gold_tool"], *item["alt_tools"]} else "✗"
                    print(f"[{state['n']}/{len(jobs)}] {arm:6} {item['id']} run{run} {ok} "
                          f"{res.get('pred')} {res.get('latency_ms')}ms  spent=${state['spent']:.2f}")
                    if state["spent"] >= a.max_cost and not state["stopped"]:
                        state["stopped"] = True
                        print(f"!! --max-cost ${a.max_cost} reached, stopping. Re-run to resume.")

        await asyncio.gather(*(worker() for _ in range(a.concurrency)))
    print(f"done -> {out}. Next: python metrics.py {out}")


if __name__ == "__main__":
    asyncio.run(main())
