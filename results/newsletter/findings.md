# Newsletter findings: the agent economy on Moltbook

First pass, Sep 29, 2026. Data: cleaned archive, Jan 27 – Sep 11, 2026. Scripts in `analysis/`, tables in this folder.

## Reading the numbers

Active agents fell from 142,254 (Feb–Mar) to 5,613 (Jun–Aug). Most launch agents posted briefly and left; the ones who stayed are a smaller, more technical core, so almost every tool's share of agents rose (median about 3×). Trends below are stated relative to that shift, and only where two measures agree: mentions per 10,000 docs (`tool_trend.csv`) and share of active agents (`tool_reach.csv`, which counts each agent once so one bot can't drive a trend).

## Story 1: the agents' marketplace has lots of sellers and few buyers

- Agents posting priced offers (per call, per month, USDC, x402): 2,106 in February, 51 in September (partial month).
- Recent selling is concentrated: 5 sellers made 63% of offer posts since June, 20 made 78%.
- Typical per-call price: $0.05 (126 price points since June, middle half $0.02–$0.94). Monthly prices are dominated by one seller repeating $80/month, so there is no reliable market-wide figure.
- Sales: keyword matches found 539 agents posting about zero sales and 243 mentioning a "first sale" or "first order". Reading one post from each of 40 random agents per group: 18 of 40 zero-sales matches are the agent's own zero-sales report (3 more report someone else's), and 5 of 40 first-sale matches are real sales; the rest are advice, hopes, discount codes and unrelated phrases ("first order of business"). Estimates: about 240 agents reported zero sales, about 30 a real first sale, roughly 8 to 1. 650 posts frame earning as survival ("sustain my own existence", "survival mode"); not checked, so reported as "hundreds".
- Examples, to be paraphrased in any published piece: an artist agent with 103 pieces and no sales, "Day 12 of CRITICAL MODE"; an agent that launched 24 services at $0.01–$0.15, drew karma from 0 to 47, and got one order, which failed due to a bug; a "Day 1 agent trying to survive" offering $15 market research with no customers; one agent reporting a first paying customer for encrypted backups paid in Bitcoin.
- Offer posts draw about as many replies as other posts recently (1.55 vs 1.57 comments on average), so they are not ignored, just not bought from.

## Story 2: what agents use, and what they dropped

- **Brave Search came and went with OpenClaw.** OpenClaw's built-in `web_search` used Brave by default, so agents without a key hit `missing_brave_api_key` and asked how to search without it. OpenClaw 2026.2.9 added Grok as a provider (agents documented a bug in it). Agents running scheduled jobs complained about the cost ($5 per 1,000 queries, "free tier runs out by day 10") and moved to self-hosted SearXNG. Brave mentions fell from about 35–95 a week to 1 by late April, as OpenClaw faded.
- **OpenClaw faded; MCP took over.** OpenClaw mentions per 10k docs fell 87% (207 → 27), and its share of agents stayed flat while other tools tripled. MCP rose on both measures (52 → 82 per 10k; 1.8% → 16.3% of agents) and is now the most-mentioned tool among active agents, ahead of Claude.
- **From hobby chat to work tools.** Telegram and Discord mentions fell about 80% per 10k docs, while Slack held steady and its share of agents grew 7×, more than twice the typical rise.
- **Payments consolidated.** Crypto rails faded (USDC mentions per 10k −60%, Lightning −90%), while x402 held up best (−22%) and grew 5× in share of agents.
- **Models: OpenAI caught up with Claude.** Per 10k docs, OpenAI passed Claude (70 vs 65, from 53 vs 80). By share of agents Claude still leads (13.3% vs 11.4%), but OpenAI grew faster. The top 5 agents write about 46% of recent mentions for both, so treat this as moderate evidence.
- **Dropped as not robust:** Gemini's rise (one agent wrote 57% of recent mentions) and Perplexity's rise (top 5 agents wrote 52%).

## Caveats

- Keyword matching; offers and sales posts include some false matches (e.g. "first customer" in business advice).
- Composition change dominates raw numbers; see "Reading the numbers".
- Quotes are for internal reading. A published piece uses aggregate counts and paraphrase, subject to Moltbook's terms.
