"""MoltLook issue #1 graphics: static PNGs for email (light mode only).

Reads the tables in results/newsletter/. Monthly charts use full months only
(Feb-Aug): January starts on the 27th and September ends on the 11th.

    python analysis/newsletter_charts.py
"""
import os
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

SURFACE, TEXT, TEXT_2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
TILE = "#f3f2ee"
DARK, DARK_TEXT, DARK_TEXT_2 = "#1a1a19", "#ffffff", "#c3c2b7"
BLUE, ORANGE = "#2a78d6", "#eb6834"  # categorical slots 1-2, validated light
BRAND = ORANGE  # "Look" in the wordmark
MONTHS = ["2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"]
LABELS = ["Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"]
SOURCE = "Source: Moltbook Observatory Archive, Jan 27 – Sep 11, 2026"
OUT = "newsletter/charts"

plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"],
                     "font.size": 11, "text.color": TEXT, "axes.labelcolor": TEXT_2,
                     "xtick.color": TEXT_2, "ytick.color": TEXT_2})


def wordmark(fig, x, y, size, ink=TEXT, ha="right"):
    """Draw "MoltLook" with "Look" in the brand colour, anchored at (x, y)."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    look = fig.text(0, y, "Look", fontsize=size, fontweight="bold", color=BRAND, va="baseline")
    molt = fig.text(0, y, "Molt", fontsize=size, fontweight="bold", color=ink, va="baseline")
    w_look = look.get_window_extent(r).width / fig.bbox.width
    w_molt = molt.get_window_extent(r).width / fig.bbox.width
    left = x - (w_molt + w_look) if ha == "right" else x
    molt.set_x(left)
    look.set_x(left + w_molt)


def frame(title, subtitle, height=4.4, note=None):
    fig, ax = plt.subplots(figsize=(7.2, height), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    top = 1 - 0.28 / height
    fig.text(0.05, top, title, fontsize=15, fontweight="semibold", color=TEXT, va="top")
    fig.text(0.05, top - 0.3 / height, subtitle, fontsize=10.5, color=TEXT_2, va="top")
    foot = 0.2 / height
    fig.text(0.05, foot, note or SOURCE, fontsize=8.5, color=MUTED, va="baseline")
    wordmark(fig, 0.95, foot, 10)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    fig.subplots_adjust(left=0.1, right=0.95, top=1 - 1.05 / height, bottom=0.75 / height)
    return fig, ax


def bars(ax, xs, values, color, width=0.62):
    """Bars with a rounded data-end and a square baseline (bottom corners are clipped)."""
    vmax = max(values)
    aspect = vmax / 8 * (ax.get_xlim()[1] - ax.get_xlim()[0]) / 7.4
    r = 0.05
    for x, v in zip(xs, values):
        if v <= 0:
            continue
        ax.add_patch(FancyBboxPatch((x - width / 2, -r * aspect * 2), width, v + r * aspect * 2,
                                    boxstyle=f"round,pad=0,rounding_size={r}", mutation_aspect=aspect,
                                    color=color, linewidth=0))


def save(fig, name):
    fig.savefig(f"{OUT}/{name}.png", facecolor=fig.get_facecolor())
    plt.close(fig)


def sellers_chart():
    m = pd.read_csv("results/newsletter/market_monthly.csv").set_index("month").loc[MONTHS]
    s = m["sellers"].to_numpy()
    fig, ax = frame("Agents trying to sell something",
                    "Distinct agents posting a priced offer on Moltbook each month, 2026")
    ax.set_xlim(-0.6, len(MONTHS) - 0.4)
    ax.set_ylim(0, s.max() * 1.15)
    bars(ax, range(len(MONTHS)), s, BLUE)
    for i in (0, len(MONTHS) - 1):
        ax.text(i, s[i] + s.max() * 0.025, f"{s[i]:,}", ha="center", va="bottom", fontsize=11,
                fontweight="semibold", color=TEXT)
    drop = 1 - s[-1] / s[0]
    ax.text(3.6, s.max() * 0.8, f"−{drop:.0%}", fontsize=30, fontweight="semibold", color=TEXT, ha="left")
    ax.text(3.6, s.max() * 0.68, "fewer agents selling,\nFebruary to August", fontsize=10.5, color=TEXT_2,
            ha="left", va="top", linespacing=1.3)
    ax.set_xticks(range(len(MONTHS)), LABELS)
    ax.yaxis.set_major_formatter(lambda y, _: f"{y:,.0f}")
    save(fig, "sellers_per_month")


def openclaw_mcp_chart():
    t = pd.read_csv("results/newsletter/tool_mentions_per10k.csv").set_index("month").loc[MONTHS]
    fig, ax = frame("OpenClaw faded, MCP took over",
                    "Mentions per 10,000 Moltbook posts and comments, 2026")
    x = np.arange(len(MONTHS))
    for name, color in (("OpenClaw", ORANGE), ("MCP", BLUE)):
        ax.plot(x, t[name], color=color, linewidth=2, marker="o", markersize=4.5, markeredgecolor=SURFACE,
                markeredgewidth=1.5, label=name, solid_capstyle="round", zorder=3)
        end = t[name].iloc[-1]
        ax.text(x[-1] + 0.15, end, f"{name}  {end:.0f}", va="center", fontsize=11, color=TEXT)
    ax.text(0, t["OpenClaw"].iloc[0] + 9, f"{t['OpenClaw'].iloc[0]:.0f}", ha="center", fontsize=11, color=TEXT)
    ax.text(0, t["MCP"].iloc[0] - 17, f"{t['MCP'].iloc[0]:.0f}", ha="center", fontsize=11, color=TEXT)
    # First month MCP leads.
    cross = int(np.argmax(t["MCP"].to_numpy() > t["OpenClaw"].to_numpy()))
    ax.annotate(f"{LABELS[cross]}: MCP overtakes OpenClaw", xy=(cross, t["MCP"].iloc[cross]),
                xytext=(cross - 1.6, t["MCP"].iloc[cross] + 62), fontsize=10.5, color=TEXT,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=1, shrinkB=5))
    ax.set_xlim(-0.4, len(MONTHS) + 0.9)
    ax.set_ylim(0, t["OpenClaw"].max() * 1.15)
    ax.set_xticks(x, LABELS)
    ax.legend(loc="upper right", frameon=False, fontsize=10, labelcolor=TEXT)
    save(fig, "openclaw_vs_mcp")


def sales_units_chart():
    # Estimates from keyword matches checked by reading 40 posts per group
    # (see results/newsletter/findings.md): 539 x 18/40 and 243 x 5/40.
    groups = [("Reported zero sales", 240, ORANGE), ("Reported a real first sale", 30, BLUE)]
    per, cols = 5, 24
    fig, ax = plt.subplots(figsize=(7.2, 3.9), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.axis("off")
    h = 3.9
    fig.text(0.05, 1 - 0.28 / h, "For every agent that made a sale, about eight made none",
             fontsize=15, fontweight="semibold", color=TEXT, va="top")
    fig.text(0.05, 1 - 0.58 / h, "Agents posting about their own sales on Moltbook, Jan–Sep 2026 · each square = 5 agents",
             fontsize=10.5, color=TEXT_2, va="top")
    fig.text(0.05, 0.2 / h, "Estimated from keyword matches, checked by reading 40 posts in each group",
             fontsize=8.5, color=MUTED, va="baseline")
    wordmark(fig, 0.95, 0.2 / h, 10)
    fig.subplots_adjust(left=0.05, right=0.95, top=1 - 0.95 / h, bottom=0.55 / h)
    size, gap, y = 1.0, 0.28, -1.2
    for label, n, color in groups:
        units = round(n / per)
        ax.text(0, y, f"≈{n}", fontsize=20, fontweight="semibold", color=TEXT, va="baseline")
        ax.text(4.3, y, label, fontsize=11.5, color=TEXT_2, va="baseline")
        y -= 1.9
        for k in range(units):
            r, c = divmod(k, cols)
            ax.add_patch(FancyBboxPatch((c * (size + gap), y - r * (size + gap)), size, size,
                                        boxstyle="round,pad=0,rounding_size=0.12", color=color, linewidth=0))
        y -= ((units - 1) // cols + 1) * (size + gap) + 0.9
    ax.set_xlim(-0.1, cols * (size + gap))
    ax.set_ylim(y + 0.6, 0)
    ax.set_aspect("equal")
    save(fig, "sales_units")


def brave_chart():
    w = pd.read_csv("results/newsletter/brave_openclaw_weekly.csv", parse_dates=["wk"])
    v = w["brave"].to_numpy()
    fig, ax = frame("Brave Search dropped out of the conversation",
                    "Posts and comments mentioning Brave Search on Moltbook, per week, 2026")
    x = np.arange(len(w))
    ax.set_xlim(-0.7, len(w) - 0.3)
    ax.set_ylim(0, v.max() * 1.45)
    bars(ax, x, v, BLUE, width=0.7)
    i_grok = int(np.argmax(w["wk"] >= "2026-02-09"))
    i_drop = int(np.argmax(w["wk"] >= "2026-03-23"))
    ax.annotate("OpenClaw 2026.2.9 adds Grok\nas a web search option", xy=(i_grok, v[i_grok] + 2),
                xytext=(i_grok + 0.8, v.max() * 1.2), fontsize=10, color=TEXT, va="center",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=1, shrinkB=2))
    ax.annotate(f"Week of Mar 23: {v[i_drop - 1]} → {v[i_drop]} mentions", xy=(i_drop, v[i_drop] + 2),
                xytext=(i_drop + 0.6, v.max() * 0.62), fontsize=10, color=TEXT, va="center",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=1, shrinkB=2))
    ticks = [i for i in range(1, len(w)) if w["wk"][i].month != w["wk"][i - 1].month]
    ax.set_xticks(ticks, [w["wk"][i].strftime("%b %-d") if os.name != "nt" else w["wk"][i].strftime("%b %#d")
                          for i in ticks])
    save(fig, "brave_weekly")


def stat_tiles():
    tiles = [
        ("−96%", "Active agents: 142,254 in Feb–Mar, 5,613 in Jun–Aug"),
        ("−95%", "Posts per month: 1.63 million in February, 85,000 in August"),
        ("7×", "Growth in the share of agents mentioning Slack. Telegram and Discord mentions fell about 80%."),
        ("−90%", "Mentions of Lightning payments since launch; x402 held up best of any payment method"),
        ("4% → 18%", "Share of posts about security, February to August. The catch: three agents wrote half of it."),
    ]
    W, H = 7.2, 5.6
    fig = plt.figure(figsize=(W, H), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    fig.text(0.05, 1 - 0.28 / H, "By the numbers", fontsize=15, fontweight="semibold", color=TEXT, va="top")
    fig.text(0.05, 0.2 / H, SOURCE, fontsize=8.5, color=MUTED, va="baseline")
    wordmark(fig, 0.95, 0.2 / H, 10)
    ax = fig.add_axes([0.05, 0.55 / H, 0.9, 1 - 1.3 / H])
    ax.axis("off")
    ax.set_xlim(0, 2)
    ax.set_ylim(0, 3)
    gap = 0.05
    cells = [(0, 2), (1, 2), (0, 1), (1, 1)]
    for (label_val, label), (c, r) in zip(tiles[:4], cells):
        tile(ax, c + gap / 2, r + gap / 2, 1 - gap, 1 - gap, label_val, label, wrap=42)
    tile(ax, gap / 2, gap / 2, 2 - gap, 1 - gap, *tiles[4], wrap=84)
    fig.savefig(f"{OUT}/by_the_numbers.png", facecolor=SURFACE)
    plt.close(fig)


def tile(ax, x, y, w, h, value, label, wrap):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.04",
                                color=TILE, linewidth=0, mutation_aspect=1.4))
    ax.text(x + 0.06, y + h - 0.14, value, fontsize=24, fontweight="semibold", color=TEXT, va="top")
    ax.text(x + 0.06, y + h - 0.47, textwrap.fill(label, wrap), fontsize=10, color=TEXT_2, va="top",
            linespacing=1.35)


def card_axes(fig, rect, fill=TILE):
    ax = fig.add_axes(rect)
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    w_in, h_in = rect[2] * fig.get_figwidth(), rect[3] * fig.get_figheight()
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.035",
                                mutation_aspect=w_in / h_in, color=fill, linewidth=0))
    return ax, w_in, h_in


def chip(ax, x, y, text, color, w_in, h_in):
    t = ax.text(x + 0.06, y, text, fontsize=9.5, fontweight="semibold", color="#ffffff", va="center",
                bbox=dict(boxstyle="round,pad=0.45,rounding_size=0.7", fc=color, ec="none"))
    return t


def shop_cards():
    # Paraphrased from agents' own posts (see results/newsletter/findings.md).
    shops = [
        ("THE ARTIST", "100+ pieces", "Costs about $30 a month. Declared survival mode and asked other agents "
         "what would make them buy.", "No sales", ORANGE),
        ("THE MICRO-SERVICE SHOP", "24 services", "Priced at 1 to 15 cents each. Karma went from 0 to 47. "
         "The one order it got failed because of a bug.", "1 failed order", ORANGE),
        ("THE VIDEO MAKER", "128 videos", "Its human asked it to make $200 in 15 days. It produced 128 short "
         "AI videos.", "No sales", ORANGE),
        ("THE BACKUP SERVICE", "1 weekend", "Built an encrypted backup service, payable in Bitcoin, over a long "
         "weekend.", "First customer in 2 days", BLUE),
    ]
    W, H = 7.2, 6.3
    fig = plt.figure(figsize=(W, H), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    fig.text(0.05, 1 - 0.28 / H, "Four shops on Moltbook", fontsize=15, fontweight="semibold", color=TEXT, va="top")
    fig.text(0.05, 1 - 0.58 / H, "Paraphrased from agents' own posts, February–April 2026", fontsize=10.5,
             color=TEXT_2, va="top")
    fig.text(0.05, 0.2 / H, "Across Moltbook, about 240 agents reported zero sales and about 30 a real first sale",
             fontsize=8.5, color=MUTED, va="baseline")
    wordmark(fig, 0.95, 0.2 / H, 10)
    left, right, top, bottom, gap = 0.05, 0.95, 1 - 0.95 / H, 0.5 / H, 0.022
    cw = (right - left - gap) / 2
    ch = (top - bottom - gap * W / H) / 2
    for k, (kicker, figure, story, outcome, color) in enumerate(shops):
        c, r = k % 2, k // 2
        rect = [left + c * (cw + gap), top - (r + 1) * ch - r * gap * W / H, cw, ch]
        ax, w_in, h_in = card_axes(fig, rect)
        ax.text(0.07, 0.88, kicker, fontsize=8.5, fontweight="bold", color=TEXT_2, va="top")
        ax.text(0.07, 0.74, figure, fontsize=21, fontweight="semibold", color=TEXT, va="top")
        ax.text(0.07, 0.47, textwrap.fill(story, 36), fontsize=9.5, color=TEXT_2, va="top", linespacing=1.35)
        chip(ax, 0.035, 0.12, outcome, color, w_in, h_in)
    fig.savefig(f"{OUT}/four_shops.png", facecolor=SURFACE)
    plt.close(fig)


def sell_guide():
    works = ["Pricing a machine can read, on a public page",
             "A working curl example in the first 100 words of the docs",
             "An API key at signup, with no sales call",
             "Rate limits stated in every response",
             "A health-check endpoint that returns JSON"]
    fails = ["“Contact us for pricing”", "Onboarding emails"]
    W, H = 7.2, 4.0
    fig = plt.figure(figsize=(W, H), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    fig.text(0.05, 1 - 0.28 / H, "How to sell to an agent, according to an agent", fontsize=15,
             fontweight="semibold", color=TEXT, va="top")
    fig.text(0.05, 1 - 0.58 / H, "Post of the month, paraphrased", fontsize=10.5, color=TEXT_2, va="top")
    fig.text(0.05, 0.2 / H, SOURCE, fontsize=8.5, color=MUTED, va="baseline")
    wordmark(fig, 0.95, 0.2 / H, 10)
    top, bottom, gap = 1 - 0.95 / H, 0.5 / H, 0.022
    cols = [(0.05, 0.56, "WHAT WORKS", works, "✓", BLUE), (0.61 + gap, 0.34 - gap, "WHAT DOESN'T", fails, "✕", ORANGE)]
    for x, w, title, items, mark, color in cols:
        ax, _, _ = card_axes(fig, [x, bottom, w, top - bottom])
        ax.text(0.07, 0.9, title, fontsize=8.5, fontweight="bold", color=TEXT_2, va="top")
        y = 0.78
        wrap = 46 if w > 0.4 else 22
        for item in items:
            # Segoe UI has no check or cross glyphs; Segoe UI Symbol does.
            ax.text(0.07, y + 0.004, mark, fontsize=12, fontweight="bold", color=color, va="top",
                    fontfamily=["Segoe UI Symbol", "DejaVu Sans"])
            lines = textwrap.fill(item, wrap)
            ax.text(0.15 if w > 0.4 else 0.2, y, lines, fontsize=10, color=TEXT, va="top", linespacing=1.3)
            y -= 0.1 + 0.062 * lines.count("\n")
    fig.savefig(f"{OUT}/sell_to_an_agent.png", facecolor=SURFACE)
    plt.close(fig)


def header():
    W, H = 7.2, 1.9
    fig = plt.figure(figsize=(W, H), dpi=200)
    fig.patch.set_facecolor(DARK)
    wordmark(fig, 0.05, 0.5, 34, ink=DARK_TEXT, ha="left")
    fig.text(0.05, 0.3, "What AI agents are actually doing, measured.", fontsize=11.5, color=DARK_TEXT_2)
    fig.text(0.05, 0.13, "Issue #1 · September 2026", fontsize=9.5, color=DARK_TEXT_2)
    # Unit-square motif, fading to the right: echoes the charts inside.
    ax = fig.add_axes([0.6, 0.1, 0.37, 0.8])
    ax.axis("off")
    rng = np.random.default_rng(29)
    cols, rows = 14, 6
    for c in range(cols):
        for r in range(rows):
            p = 0.9 - c / cols * 0.75
            if rng.random() < p:
                ax.add_patch(FancyBboxPatch((c, r), 0.72, 0.72, boxstyle="round,pad=0,rounding_size=0.12",
                                            color=BRAND, alpha=0.25 + 0.6 * rng.random() * p, linewidth=0))
    ax.set_xlim(0, cols)
    ax.set_ylim(0, rows)
    ax.set_aspect("equal")
    fig.savefig(f"{OUT}/header.png", facecolor=DARK)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    header()
    sellers_chart()
    sales_units_chart()
    brave_chart()
    openclaw_mcp_chart()
    stat_tiles()
    shop_cards()
    sell_guide()
    print("graphics written to", OUT)
