"""Arm B: TypeSafe Jev picks a tool with one Choice question over the same catalog."""
import asyncio
import time

from typesafe_sdk import AsyncTypeSafeClient, Choice

from common import INSTRUCTIONS, NONE, NONE_DESC


def _state(item):
    state = {"request": item["request"]}
    if item.get("context"):
        state["context"] = item["context"]
    return state


async def jev_select(client, item, tools, model=None):
    criteria = {t["name"]: t["description"] for t in tools}
    criteria[NONE] = NONE_DESC
    t0 = time.perf_counter()
    r = await client.system_one(
        state=_state(item),
        questions={"tool": Choice(instructions=INSTRUCTIONS, criteria=criteria)},
        model=model,
    )
    latency = (time.perf_counter() - t0) * 1000
    a = r.answers["tool"]
    return {
        "pred": a.choice,
        "confidence": a.confidence,
        "probabilities": a.probabilities,
        "latency_ms": round(latency, 1),
        "input_tokens": r.usage.input_tokens,
        "output_tokens": r.usage.output_tokens,
        "model": r.model,
        "request_id": r.request_id,
        "error": None,
    }


async def list_models():
    async with AsyncTypeSafeClient() as client:
        return await client.models.list()


if __name__ == "__main__":
    from common import load_dataset, load_tools

    async def main():
        async with AsyncTypeSafeClient() as client:
            item = load_dataset()[0]
            print(item["request"])
            print(await jev_select(client, item, load_tools()))

    asyncio.run(main())
