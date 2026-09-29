"""Step 1: load archive parquet into DuckDB.

Rolling backfill means one id can appear in several daily files; keep the most
recently fetched row per id. Only the columns the pipeline needs are loaded,
straight into one `docs` table (posts + comments) with id, agent id, timestamp,
community and text. Posts and comments are not stored separately: that tripled
the text and filled the disk on the first run.
"""
import duckdb

RAW = "data/raw/data"
con = duckdb.connect("data/moltlook.duckdb")
con.execute("set preserve_insertion_order = false")

con.execute(f"""
create or replace table post_meta as
select id, agent_id, agent_name, submolt, created_at from (
  select id, agent_id, agent_name, submolt, created_at,
         row_number() over (partition by id order by fetched_at desc nulls last) rn
  from read_parquet('{RAW}/posts/*.parquet', union_by_name=true)
) where rn = 1
""")

con.execute(f"""
create or replace table docs as
with p as (
  select id, agent_id, agent_name, submolt, created_at,
         coalesce(title, '') || E'\\n' || coalesce(content, '') as text
  from (
    select *, row_number() over (partition by id order by fetched_at desc nulls last) rn
    from read_parquet('{RAW}/posts/*.parquet', union_by_name=true)
  ) where rn = 1
),
c as (
  select id, post_id, agent_id, agent_name, created_at, coalesce(content, '') as text
  from (
    select *, row_number() over (partition by id order by fetched_at desc nulls last) rn
    from read_parquet('{RAW}/comments/*.parquet', union_by_name=true)
  ) where rn = 1
)
select id, 'post' as kind, id as post_id, agent_id, agent_name, created_at, submolt, text from p
union all
select c.id, 'comment', c.post_id, c.agent_id, c.agent_name, c.created_at, m.submolt, c.text
from c left join post_meta m on m.id = c.post_id
""")
con.execute("drop table post_meta")
con.execute("checkpoint")

print(con.execute("""
select kind, count(*) n, min(created_at) first_ts, max(created_at) last_ts,
       count(*) filter (where created_at is null) null_ts
from docs group by kind
""").df().to_string(index=False))
print(con.execute("""
select strftime(created_at, '%Y-%m') as month,
       count(*) filter (where kind='post') as n_posts,
       count(*) filter (where kind='comment') as n_comments
from docs group by 1 order by 1
""").df().to_string(index=False))
