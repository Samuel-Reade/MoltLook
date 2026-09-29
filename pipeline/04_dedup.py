"""Step 4: collapse near-duplicate mention snippets.

MinHash LSH over word 3-gram shingles, Jaccard threshold 0.9, within each
product. Each cluster keeps its earliest mention; `dup_count` records how many
mentions it stands for, so counts can be reported before and after.
"""
import re
import duckdb
import pandas as pd
from datasketch import MinHash, MinHashLSH

THRESHOLD = 0.9
NUM_PERM = 128

con = duckdb.connect("data/moltlook.duckdb")
m = con.execute("select mention_id, product, created_at, snippet from mentions order by created_at nulls last, mention_id").df()


def shingles(text):
    toks = re.findall(r"\w+", text.lower())
    if len(toks) < 3:
        return {" ".join(toks)}
    return {" ".join(toks[i:i + 3]) for i in range(len(toks) - 2)}


keep_rows = []
for product, g in m.groupby("product", sort=False):
    lsh = MinHashLSH(threshold=THRESHOLD, num_perm=NUM_PERM)
    rep_of = {}  # mention_id -> representative mention_id
    for r in g.itertuples(index=False):  # earliest first, so the first seen is the representative
        mh = MinHash(num_perm=NUM_PERM)
        for s in shingles(r.snippet):
            mh.update(s.encode())
        hits = lsh.query(mh)
        if hits:
            rep_of[r.mention_id] = rep_of[hits[0]]
        else:
            rep_of[r.mention_id] = r.mention_id
            lsh.insert(r.mention_id, mh)
    counts = pd.Series(rep_of).value_counts()
    keep_rows += [{"mention_id": k, "dup_count": int(v)} for k, v in counts.items()]

keep = pd.DataFrame(keep_rows)
con.register("keep_df", keep)
con.execute("""
create or replace table mentions_dedup as
select m.*, k.dup_count from mentions m join keep_df k using (mention_id)
""")
out = con.execute("""
select product,
       (select count(*) from mentions x where x.product = d.product) as before_dedup,
       count(*) as after_dedup,
       max(dup_count) as largest_cluster
from mentions_dedup d group by product order by after_dedup desc
""").df()
print(out.to_string(index=False))
out.to_csv("results/dedup_counts.csv", index=False)
