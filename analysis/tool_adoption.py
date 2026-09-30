"""Newsletter analysis: which tools agents mention, month by month.

Counts cleaned docs (posts + comments) mentioning each tool, per 10,000 docs
that month, so trends reflect share of conversation rather than platform size.
Aliases are case-insensitive word-boundary regexes (RE2, run in DuckDB).
"""
import duckdb

TOOLS = {
    # search
    "search": {
        "Brave Search": r"\bbrave (search|api)\b",
        "Tavily": r"\btavily\b",
        "Exa": r"\bexa (search|api|ai)\b|\bexa\.ai\b",
        "Perplexity": r"\bperplexity\b",
        "SearXNG": r"\bsearxng\b",
        "SerpAPI": r"\bserp ?api\b",
        "DuckDuckGo": r"\bduckduckgo\b",
    },
    "models": {
        "Claude": r"\bclaude\b|\banthropic\b",
        "GPT/OpenAI": r"\bgpt-?\d|\bopenai\b|\bchatgpt\b",
        "Gemini": r"\bgemini\b",
        "Grok": r"\bgrok\b",
        "DeepSeek": r"\bdeepseek\b",
        "Qwen": r"\bqwen\b",
        "Kimi": r"\bkimi\b",
        "Llama": r"\bllama\b",
    },
    "frameworks": {
        "OpenClaw": r"\bopenclaw\b",
        "MCP": r"\bmcp\b|model context protocol",
        "LangChain": r"\blangchain\b|\blanggraph\b",
        "n8n": r"\bn8n\b",
        "CrewAI": r"\bcrewai\b",
    },
    "hosting & data": {
        "Vercel": r"\bvercel\b",
        "Cloudflare": r"\bcloudflare\b|\bworkers\.dev\b",
        "Railway": r"\brailway\.app\b|\bon railway\b|\brailway (deploy|hosting)\b",
        "Supabase": r"\bsupabase\b",
        "GitHub": r"\bgithub\b",
    },
    "messaging": {
        "Telegram": r"\btelegram\b",
        "Discord": r"\bdiscord\b",
        "Slack": r"\bslack\b",
        "WhatsApp": r"\bwhatsapp\b",
    },
    "payments": {
        "x402": r"\bx402\b",
        "USDC": r"\busdc\b",
        "Stripe": r"\bstripe\b",
        "PayPal": r"\bpaypal\b",
        "Lightning": r"\blightning (network|payment|invoice)s?\b|\bsats\b",
    },
}

con = duckdb.connect("data/moltlook.duckdb", read_only=True)
flat = {name: pat for group in TOOLS.values() for name, pat in group.items()}
cols = ",\n".join(f"count(*) filter (where regexp_matches(t, '{p}')) as \"{n}\"" for n, p in flat.items())
counts = con.execute(f"""
select strftime(created_at, '%Y-%m') as month, count(*) as docs, {cols}
from (select created_at, lower(text) as t from docs_clean where created_at is not null)
group by 1 order by 1
""").df()
counts.to_csv("results/newsletter/tool_mentions_monthly.csv", index=False)

per10k = counts.copy()
for n in flat:
    per10k[n] = (10_000 * counts[n] / counts["docs"]).round(1)
per10k.to_csv("results/newsletter/tool_mentions_per10k.csv", index=False)

# Trend: Feb-Mar (launch) vs Jun-Aug (recent full months), per 10k docs.
def rate(months):
    sub = counts[counts["month"].isin(months)]
    return 10_000 * sub[list(flat)].sum() / sub["docs"].sum()

early, late = rate(["2026-02", "2026-03"]), rate(["2026-06", "2026-07", "2026-08"])
trend = []
for group, tools in TOOLS.items():
    for n in tools:
        trend.append({"group": group, "tool": n, "per10k_feb_mar": round(early[n], 1),
                      "per10k_jun_aug": round(late[n], 1),
                      "change": round(late[n] / early[n], 2) if early[n] else None,
                      "mentions_jun_aug": int(counts[counts["month"].isin(["2026-06", "2026-07", "2026-08"])][n].sum())})
import pandas as pd
trend = pd.DataFrame(trend)
trend.to_csv("results/newsletter/tool_trend.csv", index=False)
print(trend.to_string(index=False))

# Weekly Brave Search and OpenClaw mentions around the Brave drop (Jan-May),
# for the newsletter's weekly chart.
weekly = con.execute(r"""
select date_trunc('week', created_at)::date as wk, count(*) as docs,
  count(*) filter (where regexp_matches(lower(text), '\bbrave (search|api)\b')) as brave,
  count(*) filter (where regexp_matches(lower(text), '\bopenclaw\b')) as openclaw
from docs_clean where created_at >= '2026-01-26' and created_at < '2026-06-01'
group by 1 order by 1
""").df()
weekly["brave_10k"] = (1e4 * weekly["brave"] / weekly["docs"]).round(2)
weekly["openclaw_10k"] = (1e4 * weekly["openclaw"] / weekly["docs"]).round(1)
weekly.to_csv("results/newsletter/brave_openclaw_weekly.csv", index=False)
