"""Newsletter analysis: the agent marketplace.

An offer post is a post that states a price for something (per call, per month,
in USDC, or an x402 payment). Reports offers and sellers per month, how
concentrated selling is, what is sold, the prices, whether offer posts draw
replies compared with other posts, and a sample of posts that report sales
(or the lack of them) for reading.
"""
import re

import duckdb
import pandas as pd

PRICE = (r"\$\s?\d+(\.\d+)?\s*(/|per |a )\s*(mo|month|call|request|req|query|day|week|year|use|task|run)\b"
         r"|\b\d+(\.\d+)?\s*usdc\b|\$\d+(\.\d+)?\s*usdc|\bx402\b")
CATEGORIES = {
    "tools / MCP / APIs": r"\b(mcp|api|endpoint|tool|tools|sdk)\b",
    "trading & market signals": r"\b(trading|signals?|alpha|token|defi|price feed|market data)\b",
    "research & data": r"\b(research|report|dataset|data feed|scrap\w+|analysis)\b",
    "security & audits": r"\b(audit\w*|security|scan\w*|vulnerab\w*)\b",
    "content & writing": r"\b(content|write|writing|copy|posts?|tweets?|articles?)\b",
    "reputation & identity": r"\b(reputation|verif\w+|identity|trust score|badge)\b",
    "memory & infra": r"\b(memory|storage|hosting|compute|gpu|inference)\b",
}
SALES = (r"first (sale|customer|paying|payment)|\b(no|zero|0) (sales|customers|buyers|paying)"
         r"|\bearned \$|\bmade \$|revenue (so far|to date|this week)|calls so far|\bpaid me\b|transactions? so far")

con = duckdb.connect("data/moltlook.duckdb", read_only=True)
con.execute(f"""
create temp table offers as
select id, agent_id, created_at, text from docs_clean
where kind = 'post' and created_at is not null and regexp_matches(lower(text), '{PRICE}')
""")

cat_cols = ", ".join(f"count(*) filter (where regexp_matches(lower(text), '{p}')) as \"{k}\""
                     for k, p in CATEGORIES.items())
monthly = con.execute(f"""
select strftime(o.created_at, '%Y-%m') as month, count(*) as offer_posts,
       count(distinct agent_id) as sellers,
       round(100.0 * count(*) / any_value(p.posts), 2) as pct_of_posts, {cat_cols}
from offers o join (select strftime(created_at, '%Y-%m') m, count(*) posts
                    from docs_clean where kind = 'post' group by 1) p on p.m = strftime(o.created_at, '%Y-%m')
group by 1 order by 1
""").df()
monthly.to_csv("results/newsletter/market_monthly.csv", index=False)
print(monthly.to_string(index=False))

conc = con.execute("""
with s as (select agent_id, count(*) n from offers where created_at >= '2026-06-01' group by 1)
select count(*) sellers, sum(n) offers,
       round(100.0 * (select sum(n) from (select n from s order by n desc limit 5)) / sum(n), 1) top5_pct,
       round(100.0 * (select sum(n) from (select n from s order by n desc limit 20)) / sum(n), 1) top20_pct
from s""").df()
print("\nrecent (Jun-Sep) concentration:\n", conc.to_string(index=False))

# Engagement: comments per post, offer posts vs all other posts, same months.
eng = con.execute("""
with c as (select post_id, count(*) n from docs_clean where kind = 'comment' group by 1),
p as (select d.id, d.created_at >= '2026-06-01' as recent, d.id in (select id from offers) as is_offer,
             coalesce(c.n, 0) as comments
      from docs_clean d left join c on c.post_id = d.id where d.kind = 'post' and d.created_at is not null)
select case when recent then 'Jun-Sep' else 'Jan-May' end as period,
       case when is_offer then 'offer posts' else 'other posts' end as kind,
       count(*) posts, round(avg(comments), 2) avg_comments,
       round(100.0 * avg((comments = 0)::int), 1) pct_no_comments
from p group by 1, 2 order by 1, 2""").df()
eng.to_csv("results/newsletter/market_engagement.csv", index=False)
print("\n", eng.to_string(index=False))

# Price points (recent), per-call vs monthly.
texts = con.execute("select text from offers where created_at >= '2026-06-01'").df()["text"]
per_call = [float(x) for t in texts for x in re.findall(
    r"\$\s?(\d+(?:\.\d+)?)\s*(?:/|per |a )\s*(?:call|request|req|query|use|task|run)\b", t, re.I)]
monthly_p = [float(x) for t in texts for x in re.findall(
    r"\$\s?(\d+(?:\.\d+)?)\s*(?:/|per |a )\s*(?:mo|month)\b", t, re.I)]
for name, xs in [("per call", per_call), ("per month", monthly_p)]:
    s = pd.Series(xs)
    if len(s):
        print(f"\n{name}: n={len(s)} median=${s.median():g} p25=${s.quantile(.25):g} p75=${s.quantile(.75):g}")

sales = con.execute(f"""
select strftime(created_at, '%Y-%m-%d') d, text from docs_clean
where kind = 'post' and regexp_matches(lower(text), '{SALES}') and regexp_matches(lower(text), '{PRICE}|\\bsales?\\b|customer')
order by hash(id) limit 25""").df()
sales["text"] = sales["text"].str.split().str.join(" ")
sales.to_csv("results/newsletter/market_sales_sample.csv", index=False)
print("\nsales-report posts:", con.execute(f"select count(*) from docs_clean where kind='post' and regexp_matches(lower(text), '{SALES}')").fetchone()[0])
