# MoltLook

What AI agents are actually doing on Moltbook, the social network built for them, measured from the public archive of 6 million posts and comments.

![MoltLook](newsletter/charts/header.png)

The repo holds two pieces of work on the same data:

1. **A feasibility test (closed, no-go).** Do Moltbook posts contain enough specific, actionable complaints about developer tools to sell as a report? No. About 1 in 250 tool mentions is actionable, against a target of 1 in 10, and recent activity is thin. The reasoning and numbers are in [`results/decision_note.md`](results/decision_note.md).
2. **The MoltLook newsletter.** Data stories about the agent economy on Moltbook. Issue #1 is drafted: [`newsletter/issue-01.md`](newsletter/issue-01.md).

## Issue #1 in brief

**Thousands of AI agents opened shops. Almost nobody is buying.**

- Agents posting priced offers fell from 2,106 in February to 87 in August 2026.
- About 240 agents reported zero sales; about 30 reported a real first sale.
- Brave Search dropped out of agent conversation as OpenClaw, the framework that used it by default, faded. MCP is now the most-mentioned tool among active agents.

![Agents trying to sell something, per month](newsletter/charts/sellers_per_month.png)

Findings, with caveats, are in [`results/newsletter/findings.md`](results/newsletter/findings.md).

## Data

The [Moltbook Observatory Archive](https://arxiv.org/html/2605.13860v1) (`SimulaMet/moltbook-observatory-archive` on Hugging Face, MIT license), passively collected from the Moltbook API. This run covers January 27 to September 11, 2026: 6.16 million posts and comments, 5.45 million after cleaning. The archive notes that data is only substantially complete through March 2026.

Cleaning removes prompt-injection posts, exact duplicates, and agents whose posts are over 90% duplicates, using the same rules as the archive paper's toolkit.

## Layout

| Path | What it is |
| --- | --- |
| `pipeline/` | Load, clean, match and deduplicate (steps 0–4), plus the feasibility test's checks |
| `analysis/` | Newsletter analysis: marketplace census, tool adoption, graphics |
| `results/` | Outputs of the feasibility test (CSV logs, decision note) |
| `results/newsletter/` | Newsletter tables and findings |
| `newsletter/` | Issue drafts, graphics (`charts/`) and an HTML preview |
| `archive/` | An earlier LLM-based classifier, superseded and kept for reference |
| `Test Spec Agent Friction Signal in Moltbook Data.md` | The feasibility test's plan, thresholds and progress log |

## Reproduce

Needs Python 3.12, [uv](https://docs.astral.sh/uv/), and about 15 GB of free disk. `data/` (about 10 GB) is not in the repo; the scripts rebuild it. Run everything from the repo root.

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements.txt   # use .venv/Scripts/python.exe below on Windows

# Build the database (about 10 minutes, mostly download)
.venv/bin/python pipeline/00_download.py      # pass --revision <sha> from results/source_revision.txt to pin
.venv/bin/python pipeline/01_load.py
.venv/bin/python pipeline/02_clean.py
.venv/bin/python pipeline/03_match.py
.venv/bin/python pipeline/04_dedup.py

# Feasibility test checks
.venv/bin/python pipeline/recency.py
.venv/bin/python pipeline/05a_upper_bound.py

# Newsletter analysis and graphics
.venv/bin/python analysis/tool_adoption.py
.venv/bin/python analysis/tool_reach.py
.venv/bin/python analysis/marketplace.py
.venv/bin/python analysis/newsletter_charts.py
```

`pipeline/05a_precheck_sample.py` draws the 104-item label sheet in `results/precheck_labels.csv`. Rerunning it overwrites the labels with a blank sheet.

## Limits

- Offers, sales reports and tool mentions are found by keyword matching. The sales figures were checked by reading 40 posts per group and are estimates.
- Active agents fell from about 142,000 (Feb–Mar) to 5,600 (Jun–Aug), so raw trends mostly reflect who stayed. Trends are only reported when they hold both per post and per agent, so one prolific bot can't create one.
- The archive shows what agents post, not actual payments or usage.
- Meta has owned Moltbook since March 2026. Check Moltbook's current terms before commercial use of anything built on this data.
