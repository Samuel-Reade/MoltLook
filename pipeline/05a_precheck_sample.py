"""Pre-check sample: 13 random 5a candidates per product, for a quick label pass
before committing to the full 1,000-mention hand-label set.

Excludes the 40 candidates already read informally (5 per product, seed1), so
the estimate is not drawn from items the labeler has seen. Writes an unlabeled
sheet to results/precheck_labels.csv with empty category / actionable / reason
columns; rule features are left out so they don't steer the labels.
"""
import duckdb

PER_PRODUCT = 13

con = duckdb.connect("data/moltlook.duckdb", read_only=True)
sample = con.execute("""
with c as (
  select m.mention_id, m.product, m.snippet,
         row_number() over (partition by m.product order by hash(m.mention_id || 'seed1')) seen_rn,
         hash(m.mention_id || 'precheck') draw
  from mention_features f join mentions_dedup m using (mention_id) where f.candidate
)
select mention_id, product, snippet from (
  select *, row_number() over (partition by product order by draw) rn from c where seen_rn > 5
) where rn <= ? order by product, rn
""", [PER_PRODUCT]).df()
sample["snippet"] = sample["snippet"].str.split().str.join(" ")
sample["category"] = ""
sample["actionable"] = ""
sample["reason"] = ""
sample.to_csv("results/precheck_labels.csv", index=False, encoding="utf-8")
print(len(sample), "items written")
