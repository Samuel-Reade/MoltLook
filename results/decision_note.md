# Decision note: agent friction reports from Moltbook

Sep 29, 2026 · **Call: no-go.** The test stops before steps 5b–7.

## Why

The hypothesis was that at least 1 in 10 mentions of a well-known developer tool is a specific, actionable friction report. The data puts it at roughly 1 in 250.

| Criterion | Result | Call |
| --- | --- | --- |
| Actionable share of mentions (median across products) | About 0.4% (at most about 1.1%): 11.4% of mentions are rule candidates, and 4 of 104 sampled candidates were actionable | No-go (under 5%) |
| Mentions in the last 3 months of the archive | Median 6.5% across products, pooled 8.2%, against 18.4% for all cleaned docs | No-go (under 10%) |
| Products with 30+ actionable mentions | Possibly Cloudflare and GitHub on volume alone, mostly from Feb–Apr | Undecided |
| Distinct themes; classifier precision | Not measured | — |

Two of five criteria are no-go and none is a clear go. The recency result is not just a collection gap: every product falls below the archive-wide share, so mentions of these tools fell faster than Moltbook as a whole. At recent volume, constant scanning would yield about a dozen actionable items a month across all 8 tools, too few for a paid report to any one product team.

Most candidates were agents advertising their own apps and packages; their URLs, `/api` paths and `curl` examples trip the concreteness rules without saying anything about the tool.

## Limits of this call

- The 104 pre-check labels were made by Claude, not by hand, as a screen before committing to the 1,000-label validation. The 20-row spot-check (`user_check` in `results/precheck_labels.csv`) has not been done. The gap between 0.4% and the 5% line is wide enough that moderate disagreement would not change the call.
- Samples are small (13 per product), so per-product figures are rough.
- The archive is only reliably complete through March 2026; the live API may hold more recent posts, though not enough to close the recency gap.

## What would change it

A human spot-check that finds candidate precision above about 45% (needed to clear the 5% line), or evidence that the live API holds several times more recent tool discussion than the archive.

## What comes next

A separate idea, not a reinterpretation of this test: a newsletter on security threats to AI agents, sourced from Moltbook. Security is the only topic growing as a share of posts (about 4% in February to 18% in August), and the injection posts this pipeline already filters out are a record of attacks in the wild. It is being checked separately.
