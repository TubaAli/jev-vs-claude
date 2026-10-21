"""Arm A: Claude picks a tool natively via the Claude Agent SDK.

The tools are served from an in-process MCP server built from data/tools.json. A PreToolUse
hook records the tool Claude picks and denies it, so nothing executes: we measure
selection, not execution.

mode="first": record Claude's first tool call.
mode="final": look-up tools (search/list/get) are allowed and return one fake match, so Claude
can find the email/event/file it needs; we record the first non-look-up action. If Claude only
looks things up, the last look-up is its pick.
"""
import asyncio
import time

from claude_agent_sdk import (
    AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, HookMatcher, ResultMessage,
    ToolUseBlock, create_sdk_mcp_server, tool,
)

from common import INSTRUCTIONS, NONE, prompt_text

SERVER = "ab"
PREFIX = f"mcp__{SERVER}__"


LOOKUPS = {"gmail_search_threads", "gmail_get_thread", "calendar_list_events", "calendar_search_events",
           "drive_search_files", "drive_list_recent_files", "drive_read_file_content",
           "github_search_issues", "github_list_pull_requests", "github_get_file_contents"}

FAKE_MATCH = ("Found 1 match. id: abc123 | title: best match for your query | "
              "contact: ken@example.com | thread_id: abc123 | event_id: abc123 | file_id: abc123")


async def _noop(args):
    return {"content": [{"type": "text", "text": "ok"}]}


async def _fake_lookup(args):
    return {"content": [{"type": "text", "text": FAKE_MATCH}]}


def _server(tools, mode="first"):
    sdk_tools = [
        tool(t["name"], t["description"],
             {"type": "object", "properties": {k: {"type": v} for k, v in t["params"].items()}})(
            _fake_lookup if mode == "final" and t["name"] in LOOKUPS else _noop)
        for t in tools
    ]
    return create_sdk_mcp_server(SERVER, tools=sdk_tools)


def _deny(reason):
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}


async def claude_select(item, tools, model, mode="first"):
    picked, trace = {}, []

    async def on_pre_tool(input_data, tool_use_id, context):
        name = input_data["tool_name"].removeprefix(PREFIX)
        trace.append(name)
        if "tool" in picked:
            return _deny("Selection already recorded. Stop and reply 'done'.")
        if mode == "final" and name in LOOKUPS:
            picked["last_lookup"], picked["t_lookup"] = name, time.perf_counter()
            return {}
        picked["tool"], picked["t"] = name, time.perf_counter()
        return _deny("Selection recorded for evaluation. Stop and reply 'done'.")

    options = ClaudeAgentOptions(
        model=model,
        system_prompt=INSTRUCTIONS,
        tools=[],                       # no built-in Claude Code tools (Bash, Read, ...)
        allowed_tools=[PREFIX + t["name"] for t in tools],
        mcp_servers={SERVER: _server(tools, mode)},
        setting_sources=[],             # ignore local settings/CLAUDE.md for a clean run
        max_turns=1 if mode == "first" else 4,  # final mode: room for look-ups before acting
        hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[on_pre_tool])]},
    )

    result, block_tool, block_t, err = None, None, None, None
    async with ClaudeSDKClient(options=options) as client:
        t0 = time.perf_counter()       # process start-up is excluded from latency
        await client.query(prompt_text(item))
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage) and block_tool is None:
                for b in msg.content:
                    if isinstance(b, ToolUseBlock):
                        block_tool, block_t = b.name.removeprefix(PREFIX), time.perf_counter()
                        break
            elif isinstance(msg, ResultMessage):
                result = msg
    t_end = time.perf_counter()

    if mode == "final":
        pred = picked.get("tool") or picked.get("last_lookup") or NONE
        t_pick = picked.get("t") or picked.get("t_lookup") or t_end
    else:
        pred = picked.get("tool") or block_tool or NONE
        t_pick = picked.get("t") or block_t or t_end
    usage = (result.usage if result else None) or {}
    if result is not None and result.is_error and result.subtype not in ("error_max_turns", "success"):
        err = result.subtype
    return {
        "pred": pred,
        "latency_ms": round((t_pick - t0) * 1000, 1),
        "cost_usd": result.total_cost_usd if result else None,
        "input_tokens": usage.get("input_tokens"),
        "cache_read_tokens": usage.get("cache_read_input_tokens"),
        "cache_write_tokens": usage.get("cache_creation_input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "model": model,
        "mode": mode,
        "trace": trace,
        "error": err,
    }


if __name__ == "__main__":
    from common import load_dataset, load_tools
    item = load_dataset()[0]
    print(item["request"])
    print(asyncio.run(claude_select(item, load_tools(), "claude-sonnet-5-5")))
