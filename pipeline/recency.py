"""Recency check (the last go/no-go row), run early because it needs no labels.

Share of each product's deduplicated mentions dated in the last 3 months of the
archive, next to the same share for all cleaned docs (the archive-wide
baseline). A product close to the baseline means the drop is a collection or
platform effect, not lost interest in that tool. Monthly counts show where any
drop happens.
"""
import duckdb

con = duckdb.connect("data/moltlook.duckdb")

end, start = con.execute("select max(created_at), max(created_at) - interval 3 month from docs_clean").fetchone()
print(f"archive end {end}, last-3-months window starts {start}")

recency = con.execute("""
with m as (
  select product, count(*) n_total, count(*) filter (where created_at > $start) n_recent
  from mentions_dedup group by product
),
pooled as (
  select 'ALL products (pooled)' as product, sum(n_total) n_total, sum(n_recent) n_recent from m
),
base as (
  select 'BASELINE: all cleaned docs' as product, count(*) n_total,
         count(*) filter (where created_at > $start) n_recent
  from docs_clean
)
select product, n_total, n_recent, round(n_recent / n_total, 4) as recent_share
from (select * from m union all select * from pooled union all select * from base)
order by product like 'BASELINE%', product like 'ALL%', n_total desc
""", {"start": start}).df()
median = recency[~recency["product"].str.match("ALL|BASELINE")]["recent_share"].median()
recency.loc[len(recency)] = ["MEDIAN across products", None, None, round(median, 4)]
recency["window_start"] = start
recency["archive_end"] = end
print(recency.to_string(index=False))
recency.to_csv("results/recency.csv", index=False)

monthly = con.execute("""
pivot (
  select strftime(created_at, '%Y-%m') as month, product from mentions_dedup
  union all
  select strftime(created_at, '%Y-%m'), 'ALL cleaned docs' from docs_clean
) on product using count(*) group by month order by month
""").df()
print(monthly.to_string(index=False))
monthly.to_csv("results/monthly_counts.csv", index=False)
