"""Newsletter analysis: share of active agents mentioning each tool.

Counts each agent once per period, so a single prolific bot cannot drive a
trend. Periods: launch (Feb-Mar) and recent (Jun-Aug, the last full months).
"""

import duckdb
import pandas as pd

src = open("analysis/tool_adoption.py", encoding="utf-8").read()
exec(src.split("con = duckdb.connect")[0], globals())  # reuse the alias table only

con = duckdb.connect("data/moltlook.duckdb", read_only=True)
flat = {n: p for g in TOOLS.values() for n, p in g.items()}
cols = ",\n".join(f"count(distinct agent_id) filter (where regexp_matches(t, '{p}')) as \"{n}\"" for n, p in flat.items())
df = con.execute(f"""
select case when created_at < '2026-04-01' then 'feb_mar' else 'jun_aug' end as period,
       count(distinct agent_id) as active_agents, {cols}
from (select agent_id, created_at, lower(text) t from docs_clean
      where created_at >= '2026-02-01' and created_at < '2026-04-01'
         or created_at >= '2026-06-01' and created_at < '2026-09-01')
group by 1 order by 1
""").df().set_index("period")

rows = []
for g, tools in TOOLS.items():
    for n in tools:
        e = 100 * df.loc["feb_mar", n] / df.loc["feb_mar", "active_agents"]
        l = 100 * df.loc["jun_aug", n] / df.loc["jun_aug", "active_agents"]
        rows.append({"group": g, "tool": n, "pct_agents_feb_mar": round(e, 2), "pct_agents_jun_aug": round(l, 2),
                     "change": round(l / e, 2) if e else None, "agents_jun_aug": int(df.loc["jun_aug", n])})
out = pd.DataFrame(rows)
out.to_csv("results/newsletter/tool_reach.csv", index=False)
print("active agents:", df["active_agents"].to_dict())
print(out.to_string(index=False))
