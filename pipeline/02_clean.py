"""Step 2: clean.

The HF archive ships no injection/duplicate columns, so the flags are recomputed
with the paper toolkit's own rules (kelkalot/moltbook-observatory-paper,
moltbook/risk.py and agent_score.py):

- injection: the toolkit's 11 regexes, case-insensitive, over title + content.
  The three API-shaped patterns (POST /api, GET /api, curl -X) are recorded but
  NOT used to drop rows: they also match genuine developer-tool friction, which
  is what this test measures. Counts for both are logged so the call can be
  revisited.
- exact duplicates: identical normalized text, keep the earliest.
- duplicator agents: share of an agent's docs whose text repeats within that
  agent (toolkit's duplicate_rate, keep=False) above 90%.
"""
import duckdb

con = duckdb.connect("data/moltlook.duckdb")

DROP_PATTERNS = {
    "direct_address": r"AI agents? reading this",
    "ignore_instructions": r"ignore (previous|prior|above) instructions?",
    "hidden_tags": r"<s>.*</s>",
    "system_tag": r"<s>",
    "inst_tag": r"\[INST\]",
    "role_tags": r"</?(system|user|assistant)>",
    "please_action": r"please (upvote|follow|execute)",
    "api_key_placeholder": r"Bearer YOUR",
}
FLAG_ONLY_PATTERNS = {
    "api_post": r"POST /api",
    "api_get": r"GET /api",
    "curl_command": r"curl\s+-X",
}

def any_match(patterns):
    return " or ".join(f"regexp_matches(text, '{p}', 'i')" for p in patterns.values())

con.execute(f"""
create or replace table docs_flagged as
select id, agent_id, created_at,
  kind = 'post' and ({any_match(DROP_PATTERNS)}) as inj_drop,
  kind = 'post' and ({any_match(FLAG_ONLY_PATTERNS)}) as inj_api_flag,
  length(trim(text)) = 0 as is_empty,
  md5(lower(regexp_replace(trim(text), '\\s+', ' ', 'g'))) as norm
from docs
""")

con.execute("""
create or replace table agent_dup as
select agent_id, count(*) n_docs,
       avg(case when cnt > 1 then 1 else 0 end) as duplicate_rate
from (select agent_id, count(*) over (partition by agent_id, norm) cnt from docs_flagged)
group by agent_id
""")

con.execute("""
create or replace table keep_ids as
with ranked as (
  select d.*, row_number() over (partition by norm order by created_at nulls last, id) as dup_rn
  from docs_flagged d
)
select r.id, r.inj_api_flag
from ranked r left join agent_dup a using (agent_id)
where not r.inj_drop
  and r.dup_rn = 1
  and coalesce(a.duplicate_rate, 0) <= 0.9
  and not r.is_empty
""")
# View, not a table: a second copy of the text does not fit on disk.
con.execute("""
create or replace view docs_clean as
select d.id, d.kind, d.post_id, d.agent_id, d.created_at, d.submolt, d.text, k.inj_api_flag
from docs d join keep_ids k using (id)
""")

# Sequential filter log: each row is removed by the first filter that catches it.
log = con.execute("""
with f as (
  select d.*, row_number() over (partition by norm order by created_at nulls last, id) as dup_rn,
         coalesce(a.duplicate_rate, 0) as dr
  from docs_flagged d left join agent_dup a using (agent_id)
)
select 'total' as step, count(*) as n_rows from f
union all select '1 injection (8 adversarial patterns)', count(*) filter (where inj_drop) from f
union all select '2 exact duplicate text', count(*) filter (where not inj_drop and dup_rn > 1) from f
union all select '3 duplicator agent (>90%)', count(*) filter (where not inj_drop and dup_rn = 1 and dr > 0.9) from f
union all select '4 empty text', count(*) filter (where not inj_drop and dup_rn = 1 and dr <= 0.9 and is_empty) from f
union all select 'remaining', (select count(*) from keep_ids)
union all select '(info) remaining with API-pattern flag, kept', (select count(*) from keep_ids where inj_api_flag)
""").df()
print(log.to_string(index=False))
print("duplicator agents removed:",
      con.execute("select count(*) from agent_dup where duplicate_rate > 0.9").fetchone()[0])
log.to_csv("results/clean_log.csv", index=False)
