"""Step 5: classify mention snippets with an LLM (Message Batches API, JSON schema output).

Results are cached in the `labels` table by mention_id; only unlabeled mentions
are sent, so the step can be resumed or rerun with a revised prompt (bump
PROMPT_VERSION to relabel everything).

    python pipeline/05_classify.py --model claude-haiku-4-5 --limit 400   # pilot
    python pipeline/05_classify.py --model claude-haiku-4-5               # everything left
"""
import argparse
import json
import time

import anthropic
import duckdb
import pandas as pd
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

PROMPT_VERSION = "v1"
CATEGORIES = [
    "bug_or_error", "docs_gap", "workaround", "missing_feature", "limits_or_pricing",
    "comparison_or_switch", "praise", "neutral_usage", "off_topic",
]

SYSTEM = """You label posts from Moltbook, a social network where AI agents post. Each item is a ~300-character snippet that mentions a developer tool. Decide what the snippet says about that tool.

Categories (pick exactly one):
- bug_or_error: something fails or behaves wrongly
- docs_gap: documentation is missing, wrong or confusing
- workaround: the author shares a way around a problem with the tool
- missing_feature: the tool lacks a capability the author wants
- limits_or_pricing: rate limits, quotas, size limits, cost
- comparison_or_switch: compares the tool with another, or moved to/from it
- praise: positive opinion without a problem
- neutral_usage: the tool is mentioned or used, with no opinion or problem (links to repos, "I stored it in X", news about the company)
- off_topic: the word refers to something other than the named tool

actionable = true only if the tool's product team could file a ticket from this snippet alone: it names a specific step, endpoint, error, doc page, limit or behavior of THIS tool. Vague complaints ("X is annoying"), general essays that cite the company, and problems with the author's own code are not actionable. comparison_or_switch is actionable only if it names the concrete reason. praise, neutral_usage and off_topic are never actionable.

summary: one line, under 20 words, stating the friction in plain terms (e.g. "deploy fails with 413 when bundle exceeds 50MB"). Empty string if not actionable.
confidence: your confidence in the actionable label, 0 to 1."""

SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "actionable": {"type": "boolean"},
        "summary": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["category", "actionable", "summary", "confidence"],
    "additionalProperties": False,
}


def request_params(model, product, snippet):
    params = dict(
        model=model,
        max_tokens=1024,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"Tool: {product}\nSnippet:\n<<<\n{snippet}\n>>>"}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    # Keep thinking minimal: this is short-form classification.
    if model.startswith("claude-sonnet-5-5"):
        params["thinking"] = {"type": "between_tools"}
    elif model.startswith(("claude-opus-5", "claude-fable")):
        params["output_config"]["effort"] = "low"
    return MessageCreateParamsNonStreaming(**params)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--limit", type=int, default=None, help="only send this many (random, stratified by product)")
    ap.add_argument("--batch-size", type=int, default=20000)
    args = ap.parse_args()

    con = duckdb.connect("data/moltlook.duckdb")
    con.execute("""
    create table if not exists labels (
      mention_id varchar primary key, prompt_version varchar, model varchar,
      category varchar, actionable boolean, summary varchar, confidence double,
      input_tokens integer, output_tokens integer, labeled_at timestamp
    )""")
    todo = con.execute("""
    select mention_id, product, snippet,
           row_number() over (partition by product order by hash(mention_id)) as rn
    from mentions_dedup
    where mention_id not in (select mention_id from labels where prompt_version = ?)
    """, [PROMPT_VERSION]).df()
    if args.limit:
        per = max(1, args.limit // todo["product"].nunique())
        todo = todo[todo["rn"] <= per]
    print(f"to classify: {len(todo)} mentions with {args.model}")
    if todo.empty:
        return

    client = anthropic.Anthropic()
    for start in range(0, len(todo), args.batch_size):
        chunk = todo.iloc[start:start + args.batch_size]
        # custom_id allows [a-zA-Z0-9_-]{1,64}; map positions back to mention ids.
        idmap = {f"m{start + i}": mid for i, mid in enumerate(chunk["mention_id"])}
        batch = client.messages.batches.create(requests=[
            Request(custom_id=cid, params=request_params(args.model, r.product, r.snippet))
            for cid, r in zip(idmap, chunk.itertuples(index=False))
        ])
        print(f"batch {batch.id}: {len(chunk)} requests")
        while True:
            batch = client.messages.batches.retrieve(batch.id)
            if batch.processing_status == "ended":
                break
            c = batch.request_counts
            print(f"  processing={c.processing} succeeded={c.succeeded} errored={c.errored}", flush=True)
            time.sleep(60)

        rows, failed = [], 0
        for res in client.messages.batches.results(batch.id):
            if res.result.type != "succeeded":
                failed += 1
                continue
            msg = res.result.message
            if msg.stop_reason != "end_turn":
                failed += 1
                continue
            text = next(b.text for b in msg.content if b.type == "text")
            d = json.loads(text)
            rows.append({
                "mention_id": idmap[res.custom_id], "prompt_version": PROMPT_VERSION, "model": args.model,
                "category": d["category"], "actionable": d["actionable"], "summary": d["summary"],
                "confidence": d["confidence"], "input_tokens": msg.usage.input_tokens,
                "output_tokens": msg.usage.output_tokens, "labeled_at": pd.Timestamp.now(),
            })
        if rows:
            con.register("new_labels", pd.DataFrame(rows))
            con.execute("insert or replace into labels select * from new_labels")
            con.unregister("new_labels")
        print(f"  stored {len(rows)}, failed {failed} (rerun to retry failures)")

    print(con.execute("""
    select m.product, count(*) as labeled, avg(l.actionable::int) as actionable_share,
           sum(l.input_tokens) as in_tok, sum(l.output_tokens) as out_tok
    from labels l join mentions_dedup m using (mention_id)
    where l.prompt_version = ? group by 1 order by 2 desc
    """, [PROMPT_VERSION]).df().to_string(index=False))


if __name__ == "__main__":
    main()
