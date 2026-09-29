"""Step 3: match product mentions.

Word-boundary regex over alias lists. One mention per (doc, product), with a
300-character window centred on the first hit. Ambiguous aliases from the spec
are narrowed (see NOTES) so common-word senses don't swamp the counts.
"""
import re
import duckdb
import pandas as pd

con = duckdb.connect("data/moltlook.duckdb")

# (pattern, flags). Case-insensitive unless noted.
PRODUCTS = {
    "GitHub": (r"\bgithub\b|\bgh (?:cli|api)\b", re.I),
    "Stripe": (r"\bstripe\b", re.I),
    "Supabase": (r"\bsupabase\b", re.I),
    "Vercel": (r"\bvercel\b", re.I),
    # NOTES: bare lowercase "notion" is the English word; require capital N and
    # skip "Notion of/that" (sentence-initial common noun).
    "Notion": (r"(?i:\bnotion api\b)|\bNotion\b(?! (?:of|that)\b)", 0),
    "Brave Search": (r"\bbrave (?:search|api)\b", re.I),
    "Twilio": (r"\btwilio\b", re.I),
    # NOTES: bare "workers" is generic; require Cloudflare context.
    "Cloudflare": (r"\bcloudflare\b|\bwrangler\b|\bworkers\.dev\b", re.I),
}
WINDOW = 300

# DuckDB prefilter (RE2, case-insensitive superset) keeps Python work small.
prefilter = "|".join(["github", r"gh (cli|api)", "stripe", "supabase", "vercel", "notion",
                      r"brave (search|api)", "twilio", "cloudflare", "wrangler", r"workers\.dev"])
cand = con.execute(f"""
select id, kind, post_id, agent_id, created_at, submolt, text
from docs_clean where regexp_matches(text, '{prefilter}', 'i')
""").df()
print("candidate docs:", len(cand))

compiled = {p: re.compile(pat, fl) for p, (pat, fl) in PRODUCTS.items()}
rows = []
for r in cand.itertuples(index=False):
    for product, rx in compiled.items():
        m = rx.search(r.text)
        if not m:
            continue
        mid = (m.start() + m.end()) // 2
        lo = max(0, mid - WINDOW // 2)
        hi = min(len(r.text), lo + WINDOW)
        lo = max(0, hi - WINDOW)
        rows.append({
            "mention_id": f"{r.id}:{product}",
            "doc_id": r.id, "kind": r.kind, "post_id": r.post_id, "agent_id": r.agent_id,
            "created_at": r.created_at, "submolt": r.submolt, "product": product,
            "hit": m.group(0), "n_hits": len(rx.findall(r.text)),
            "snippet": r.text[lo:hi],
        })

mentions = pd.DataFrame(rows)
con.register("mentions_df", mentions)
con.execute("create or replace table mentions as select * from mentions_df")
counts = con.execute("""
select product, count(*) as n_mentions, count(distinct agent_id) as n_agents,
       count(*) filter (where kind='post') as n_posts, count(*) filter (where kind='comment') as n_comments
from mentions group by 1 order by 2 desc
""").df()
print(counts.to_string(index=False))
counts.to_csv("results/raw_mention_counts.csv", index=False)
