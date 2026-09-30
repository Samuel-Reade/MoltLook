"""Step 5a: concreteness rules, candidate upper bound and the gate.

Tags each deduplicated mention window with rule features. A mention is a
candidate if it has at least one concrete marker (anything but a friction verb)
or two friction-verb hits. Candidates approximate an upper bound on actionable
mentions, so the rules lean generous: where a pattern is ambiguous it is kept.
Bare numbers that are often not status codes (400, 500) need a status word
next to them; bare repo links are not endpoints.

Gate (fixed in the spec): no-go if every product has fewer than 30 candidates,
or the median candidate share is under 5%.

Features are stored in `mention_features` for step 5b. Share of candidates in
the last 3 months is reported too, as an early look at recency.
"""
import re

import duckdb
import pandas as pd

con = duckdb.connect("data/moltlook.duckdb")

STATUS_WORD = r"(?:HTTP|status|error|code|response|returns?|returned|returning|got|getting|throws?|with)"
CONCRETE = {
    "http_status": re.compile(
        rf"\b{STATUS_WORD}\s*:?\s*[45]\d\d\b"
        r"|\b[45]\d\d\s+(?:error|Not Found|Unauthorized|Forbidden|Bad Request|Too Many Requests|"
        r"Internal Server Error|Bad Gateway|Service Unavailable|Gateway Timeout|Payload Too Large|"
        r"Unprocessable|Conflict)\b"
        r"|\b(?:401|403|404|409|413|422|429|502|503|504)\b(?![.,]\d)",
        re.I),
    "exception_name": re.compile(
        r"\b[A-Z][A-Za-z0-9]*(?:Error|Exception)\b"
        r"|\bE(?:CONN[A-Z]+|TIMEDOUT|NOTFOUND|ACCES|PERM|ADDRINUSE|PIPE|AI_AGAIN)\b"),
    "quoted_error": re.compile(
        r"[\"'`“][^\"'`”\n]{0,120}\b(?:error|failed|failure|invalid|denied|not found|unauthorized|"
        r"forbidden|exceeded|timed? ?out|refused|unable to)\b[^\"'`”\n]{0,120}[\"'`”]",
        re.I),
    "cli_command": re.compile(
        r"\bgh (?:pr|issue|repo|auth|api|run|workflow|release|gist|secret|label)\b"
        r"|\bgit (?:push|pull|clone|commit|rebase|merge|fetch|checkout|remote|reset|stash)\b"
        r"|\bwrangler (?:deploy|dev|publish|login|tail|secret|kv|d1|r2|pages|init|whoami)\b"
        r"|\bvercel (?:deploy|dev|env|link|login|build|logs|--prod)\b"
        r"|\bsupabase (?:start|stop|db|functions|link|login|migration|gen|init|secrets)\b"
        r"|\bstripe (?:listen|trigger|login|logs|fixtures)\b"
        r"|(?<![\w-])--[a-z][a-z0-9-]{2,}\b"),
    # Split from cli_command: on Moltbook these are mostly agents advertising
    # their own packages, so the gate is also reported without them.
    "install_command": re.compile(r"\b(?:npx|npm (?:install|i|run)|pip install|curl) \S+"),
    # A *.workers.dev host is someone's deployed app, and is also a Cloudflare
    # alias, so it is not counted as an endpoint.
    "api_path": re.compile(
        r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+/\S+"
        r"|(?:^|[\s(`'\"]|https?://[\w.-]+)/(?:api|v\d+|rest|graphql|webhooks?|functions|auth|oauth)(?:/|\b)"
        r"|\bapi\.[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|io|dev|net|org)\b"),
    "version_number": re.compile(r"\bv?\d+\.\d+\.\d+\b(?!\.\d)|\bv\d+\.\d+\b(?!\.\d)"),
    "numeric_limit": re.compile(
        r"\b\d+(?:[.,]\d+)?\s*[kKmM]?\s*(?:"
        r"(?:KB|MB|GB|TB|kb|mb|gb)\b"
        r"|/\s*(?:s|sec|second|min|minute|h|hr|hour|day|mo|month)\b"
        r"|(?:requests?|reqs?|calls|tokens|rpm|rps|ms)\b"
        r"|(?:per|a|an|every)\s+(?:second|minute|hour|day|month)\b)"),
}
FRICTION_VERBS = re.compile(
    r"\bfail(?:s|ed|ing|ure)?\b|\breturn(?:s|ed|ing)?\b|\bdoesn['’]t\b|\bdoes not\b"
    r"|\bcan['’]t\b|\bcannot\b|\bbroken\b|\btime(?:out|d out)\b|\bworkaround\b"
    r"|\brate[- ]limit(?:s|ed|ing)?\b|\bdeprecated\b|\bdocs? (?:don['’]t|doesn['’]t|do not|does not)\b",
    re.I)

m = con.execute("select mention_id, product, created_at, snippet from mentions_dedup").df()
end = con.execute("select max(created_at) from docs_clean").fetchone()[0]
start = end - pd.DateOffset(months=3)

for name, rx in CONCRETE.items():
    m[name] = m["snippet"].map(lambda s, rx=rx: bool(rx.search(s)))
m["n_friction_verbs"] = m["snippet"].map(lambda s: len(FRICTION_VERBS.findall(s)))
m["n_concrete"] = m[list(CONCRETE)].sum(axis=1)
m["candidate"] = (m["n_concrete"] >= 1) | (m["n_friction_verbs"] >= 2)
m["candidate_excl_install"] = (m["n_concrete"] - m["install_command"] >= 1) | (m["n_friction_verbs"] >= 2)
m["recent"] = m["created_at"] > start

feats = m.drop(columns=["snippet", "created_at", "recent"])
con.register("feats_df", feats)
con.execute("create or replace table mention_features as select * from feats_df")
con.unregister("feats_df")

by = m.groupby("product")
out = pd.DataFrame({
    "n_mentions": by.size(),
    "n_candidates": by["candidate"].sum(),
    "candidate_share": by["candidate"].mean().round(4),
    "n_recent_candidates": by.apply(lambda g: (g["candidate"] & g["recent"]).sum(), include_groups=False),
    "n_candidates_excl_install": by["candidate_excl_install"].sum(),
    "candidate_share_excl_install": by["candidate_excl_install"].mean().round(4),
    **{f"has_{k}": by[k].mean().round(4) for k in CONCRETE},
    "share_2plus_friction_verbs": by["n_friction_verbs"].apply(lambda s: (s >= 2).mean()).round(4),
}).sort_values("n_candidates", ascending=False).reset_index()


def gate(n_col, share_col):
    n_30 = int((out[n_col] >= 30).sum())
    median_share = float(out[share_col].median())
    stop = n_30 == 0 or median_share < 0.05
    return ("NO-GO: stop before 5b" if stop else "PASS: continue to 5b") + \
        f" (products with 30+ candidates: {n_30}; median candidate share: {median_share:.1%})"


out["gate"] = gate("n_candidates", "candidate_share")
out["gate_excl_install"] = gate("n_candidates_excl_install", "candidate_share_excl_install")
print(out.drop(columns=["gate", "gate_excl_install"]).to_string(index=False))
print("gate:", out["gate"][0])
print("gate without install commands:", out["gate_excl_install"][0])
out.to_csv("results/upper_bound.csv", index=False)
