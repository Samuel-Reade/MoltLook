# Test Spec: Agent Friction Signal in Moltbook Data

Sep 29, 2026 · @KingSam1124 · Revised Sep 29, 2026: classic NLP instead of an LLM, findings from the first run folded in

## Purpose

This test answers one question: do Moltbook posts contain enough specific, actionable complaints about developer tools to fill a paid report? It costs about a week and no money, so it runs before any product, pitch or pricing work.

If the answer is no, the idea is dropped. If yes, the output of this test becomes the first sample report shown to prospective buyers.

## Hypothesis and go/no-go criteria

Hypothesis: for well-known developer tools, at least 1 in 10 mentions on Moltbook is a specific, actionable friction report. The thresholds below were fixed before any classification was run and are not changed after seeing results.

| Criterion | Go | Maybe | No-go |
| --- | --- | --- | --- |
| Products with 30+ actionable mentions | 3 or more | 1–2 | 0 |
| Actionable share of all mentions (median across products) | 10%+ | 5–10% | under 5% |
| Distinct friction themes per product (top 3 products) | 5+ | 3–4 | under 3 |
| Classifier precision on actionable label | 80%+ | 65–80% | under 65% |
| Mentions dated in the last 3 months of the archive | 25%+ of total | 10–25% | under 10% |

The last row checks the data is still alive. A result that is strong but all from launch week (Jan–Feb 2026) signals a dying source, not a business.

Reading the recency row: the archive README says posts and comments are only substantially complete through March 2026. A low recency share can therefore mean the collector missed data, not that Moltbook died. Report each product's recency share next to the archive-wide share for the same window (all cleaned docs, any topic). If a product's share is close to the archive-wide share, the drop is a collection or platform effect, not a loss of interest in that tool. Either way the threshold stands: a buyer gets no current signal from a source whose recent data is thin, whatever the cause.

## Data source

Use the public [Moltbook Observatory Archive](https://arxiv.org/html/2605.13860v1), published on Hugging Face as `SimulaMet/moltbook-observatory-archive`. It is collected passively from the Moltbook API and updated incrementally. Loading is done directly with `huggingface_hub` and DuckDB; the [moltbook-watch](https://github.com/GvHildebrand/moltbook-watch) repo is not needed.

- Scope: all posts and comments in the archive. First run covered Jan 27 – Sep 11, 2026: 3.60M posts and 2.55M comments after keeping the latest copy of each id.
- No live scraping and no posting or registering on Moltbook for this test.
- License: the archive is MIT (checked). Meta owns Moltbook since March 2026; check Moltbook's current terms before any commercial use. The test itself is internal analysis; a sold report would quote short excerpts and aggregate counts, never redistribute raw posts.
- Duplicates in the files: the archive uses a rolling backfill, so one post id appears in several daily files. Keep the most recently fetched row per id.
- Noise flags are not in the published files. The paper computes them with its companion toolkit ([moltbook-observatory-paper](https://github.com/kelkalot/moltbook-observatory-paper), `moltbook/risk.py` and `moltbook/agent_score.py`), so the pipeline recomputes them with the same rules (see step 2).
- Disk: the raw parquet is 2.5 GB and the DuckDB file about 7 GB. Plan on 15 GB free, plus about 2 GB for the embedding model in step 6.

## Product selection

Pick 8 developer tools that agents plausibly use through APIs or CLIs, and that have a product or developer-experience team who could buy a report. Avoid names that are also common English words unless the alias list can disambiguate them.

| Product | Why include | Aliases matched | Ambiguity handling |
| --- | --- | --- | --- |
| GitHub | Agents push code and open PRs | github, gh cli, gh api | None needed |
| Stripe | Payments; agents asked to charge or check balances | stripe | None needed |
| Supabase | Popular agent backend | supabase | None needed |
| Vercel | Deploys agent-built sites | vercel | None needed |
| Notion | Common agent memory and notes store | notion api (any case); Notion (capital N only, not followed by "of" or "that") | Lowercase "notion" is the English word |
| Brave Search | Common agent search API | brave search, brave api | None needed |
| Twilio | Messaging from agents | twilio | None needed |
| Cloudflare | Workers, DNS, tunnels for self-hosted agents | cloudflare, wrangler, workers.dev | Bare "workers" is generic and is not matched |

Rule: swap out any product with fewer than 50 raw mentions after step 3. First run: all 8 passed (lowest was Brave Search at 467), so the list stands.

## Pipeline

A straight run of seven steps in Python, with DuckDB for storage. Each step writes its output to a table so any step can be rerun alone. No step calls a paid API.

1. **Download.** Pull the posts, comments, agents and submolts parquet from Hugging Face into `data/raw`. Load one `docs` table (posts and comments together) with id, kind, post id, agent id, timestamp, community and text. Do not also keep separate full posts and comments tables: storing the text three times filled the disk on the first run.
2. **Clean.** Remove, in order, and log how many rows each filter removes:
   - Injection posts: the toolkit's regex patterns, case-insensitive, over title and content. Use the 8 adversarial patterns (direct address to reading agents, "ignore previous instructions", `<s>` tags, `[INST]`, role tags, "please upvote/follow/execute", `Bearer YOUR`) to drop posts. The 3 API-shaped patterns (`POST /api`, `GET /api`, `curl -X`) only flag posts, because they also match genuine developer-tool friction, which is what this test measures.
   - Exact duplicates: identical text after lowercasing and collapsing whitespace; keep the earliest.
   - Duplicator agents: agents whose duplicate rate (the toolkit's definition: share of the agent's docs whose text repeats within that agent) is above 90%.
   - Store flags and a hash of the normalized text, not a second copy of the text; `docs_clean` is a view.
3. **Match mentions.** Case-insensitive, word-boundary regex over the alias lists (with the case rules above). One mention per (doc, product): a post that names Stripe five times counts once. Keep a 300-character window centred on the first hit plus the doc and post ids. Output raw mention counts per product.
4. **Deduplicate.** Collapse near-duplicate windows within each product with MinHash LSH over word 3-grams, Jaccard 0.9, so one templated post repeated 400 times counts once. Keep the earliest mention of each cluster and record the cluster size.
5. **Classify.** Classic NLP in two stages, with no LLM.
   - **5a. Concreteness rules and upper bound.** Tag each mention window with rule features: HTTP status codes, exception and error names (`...Error`, `...Exception`, `ECONN...`), quoted error messages, CLI commands and flags, API paths and endpoints, version numbers, numeric limits with units (`60/min`, `50MB`, `10k requests`), and friction verbs ("fails", "returns", "doesn't", "can't", "broken", "timeout", "workaround", "rate limit", "deprecated", "docs don't"). A mention is a **candidate** if it has at least one concrete marker (anything but a friction verb) or two friction verbs. Candidates are an approximate upper bound on actionable mentions, because the labeling scheme requires a named step, endpoint, error, doc page or behavior. **Gate:** if every product has fewer than 30 candidates, or the median candidate share is under 5%, the test stops at no-go here without steps 5b–6. Record the gate result either way.
   - **5b. Supervised classifier.** Train on the hand labels from Validation (the training set, never the held-out set). Features: word 1–2-gram and character 3–5-gram TF-IDF plus the rule features from 5a. Models: logistic regression with class weights for actionable yes/no, and a second logistic regression for category. Tune the decision threshold for actionable on cross-validation within the training set so precision is at least 80% where recall allows. Output per mention: category, actionable, probability, and a friction summary. The summary is the sentence in the window that contains the strongest rule match, trimmed to about 25 words (an extract, not a rewrite).
   - Language: detect language per window (e.g. `langdetect`). Report the non-English share. The rules and TF-IDF are English-only, so non-English mentions are counted in totals but can only be actionable if they contain concrete markers (codes, endpoints, limits), and this limitation is stated in the results.
6. **Cluster themes.** Embed the friction summaries of actionable mentions per product with a local sentence-transformers model (`all-MiniLM-L6-v2`, or `paraphrase-multilingual-MiniLM-L12-v2` if the non-English share is above 10%). Cluster them with HDBSCAN (minimum cluster size 5), falling back to k-means with k chosen by silhouette if HDBSCAN leaves more than half the points as noise. Name each cluster from its top c-TF-IDF terms (the BERTopic approach) and hand-edit the names of the top clusters to under 8 words.
7. **Score.** Compute every metric in the go/no-go table per product, plus the archive-wide recency baseline, and write them to `results/metrics.csv`.

## Labeling scheme

Each mention gets one category. A mention is **actionable** only if a product team could file a ticket from it: it names a specific step, endpoint, error, doc page or behavior.

| Category | Actionable? | Example (invented) |
| --- | --- | --- |
| Bug or error | Yes, if the error or step is named | "deploy fails with 413 when the bundle is over 50MB" |
| Docs gap or confusion | Yes, if the confusing part is named | "the webhook docs don't say which header holds the signature" |
| Workaround shared | Yes | "skip the SDK and call the REST endpoint directly, the SDK retries forever" |
| Missing feature | Yes, if the feature is concrete | "no way to scope an API key to one repo" |
| Limits or pricing friction | Yes, if the limit is named | "rate limit of 60/min kills my cron job" |
| Comparison or switch | Sometimes | "moved from X to Y because Y's auth is simpler" |
| Praise | No (count it, but not actionable) | "works great" |
| Neutral usage mention | No | "I stored the notes in Notion" |
| Off-topic or false match | No | the word used in a different sense |

Vague complaints ("X is annoying") are labeled in their category but marked not actionable. So are essays that cite a company in passing ("Stripe's 67% figure shows..."), and problems with the author's own code.

Negative tone is not a proxy for actionable. Real friction reports are often neutral in tone ("returns 413 above 25MB"), and many negative posts give a product team nothing to act on. Sentiment scores are not used as a classification feature.

## Validation

The hand labels are both the classifier's training data and its test. Keep the two apart. Do all hand-labeling before looking at any classifier output.

- [ ] Draw a random sample of 1,000 deduplicated mentions, stratified by product (125 each; take all if a product has fewer). Oversample 5a candidates to half the sample so the rare actionable class has enough examples, and record the sampling weights.
- [ ] Before labeling, set aside 200 of them (25 per product) as the held-out test set. They are never used for training or threshold tuning.
- [ ] Hand-label all 1,000 with the scheme above, in a labeling sheet that hides the rule features.
- [ ] Train the step 5b classifier on the other 800. On the held-out 200, report precision and recall on the actionable label (reweighted for the oversampling), and a confusion table across categories.
- [ ] If precision is under 80%, revise the rules and features once using the training-set errors (never the held-out errors), retrain, and recheck on a fresh 100 hand-labeled mentions.
- [ ] Optional: have a second person label 50 of the same items to see whether the scheme itself is clear. Low agreement between people means the categories need rewriting, not the classifier.
- [ ] Spot-check 20 regex false matches to decide whether any alias should be dropped.

## Outputs

The test ends with a go, maybe or no-go call backed by these files.

| Deliverable | Contents | Used for |
| --- | --- | --- |
| `results/clean_log.csv`, `raw_mention_counts.csv`, `dedup_counts.csv` | Rows removed per filter, mentions per product before and after dedup | Trusting the counts |
| `results/upper_bound.csv` | 5a candidates per product and the gate result | The early stop |
| `results/metrics.csv` | Every go/no-go metric per product, plus the archive-wide recency baseline | The decision |
| `results/themes.csv` | Friction clusters per product: name, size, 3 example summaries | Seeing whether insights are specific |
| `results/validation.md` | Hand-label comparison, precision, recall, rule and feature revisions | Trusting the numbers |
| Sample report (1 product) | 2 pages: top 5 friction themes, counts, trend by month, short paraphrased examples | Showing to 3–5 developer-experience leads for feedback |
| Decision note | Half a page: the call, why, and what would change it | Closing the test |

The sample report is written for the product with the strongest signal. Its real test is whether a developer-experience lead says they learned something new from it. The examples in it are paraphrased by hand from the extracted summaries.

## Risks and timeline

The test takes about 5 working days, runs on a laptop, and costs nothing. Hand-labeling 1,000 mentions is the largest single cost, roughly 4–6 hours.

| Risk | Effect | Mitigation |
| --- | --- | --- |
| Archive covers mostly launch weeks | Signal looks strong but is stale | Recency metric in the go/no-go table, read against the archive-wide baseline |
| Collection incomplete after March 2026 | Recency looks worse than the platform really is | Archive-wide baseline separates collection effects from interest in a tool |
| Agents echo their owner's prompts, not real use | Complaints are role-play, not friction | Actionable requires concrete errors, codes or steps |
| Templated posts inflate counts | False volume | Exact and near-duplicate removal (steps 2 and 4); report counts before and after |
| Classic classifier misses the precision bar | Actionable share can't be trusted | Held-out validation; one rule and feature revision; the result is reported, not tuned away |
| Too few actionable examples to train on | Classifier is unstable | Oversample 5a candidates in the hand-label sample |
| Non-English posts | English rules and TF-IDF miss friction | Report the non-English share; multilingual embedding model for themes if it is above 10% |
| Disk space | Pipeline fails mid-run | 15 GB free before starting; one text table plus flag and view tables only |
| License or terms forbid commercial use | Can't sell even if signal is strong | Archive is MIT; check Moltbook's terms before any sale |
| Buyers prefer first-party telemetry (docs and API logs) | No demand even with good data | Ask the 3–5 reviewers directly what they would pay for |

| Day | Work |
| --- | --- |
| 1 | Download, clean, alias matching, first frequency count, finalize product list, near-duplicate collapse |
| 2 | Concreteness rules, upper bound and gate (stop here if no-go); draw the hand-label sample |
| 3 | Hand-label 1,000; train and validate the classifier; one revision if needed |
| 4 | Embed and cluster themes, compute metrics |
| 5 | Sample report and decision note |

## Progress

First run, Sep 29, 2026. Code is in `pipeline/`, logs in `results/`; `data/` is not in the repo and is rebuilt by running steps 0–4 (`uv venv .venv && uv pip install -r requirements.txt`, then each script from the repo root).

| Step | Status | Result |
| --- | --- | --- |
| 1. Download | Done | 6,155,813 docs (3,602,713 posts, 2,553,100 comments), Jan 27 – Sep 11, 2026 |
| 2. Clean | Done | Removed 4,541 injection posts, 687,059 exact duplicates, 11,204 docs from 4,135 duplicator agents, 1 empty; 5,453,008 remain; 6,690 API-pattern posts kept and flagged |
| 3. Match | Done | 85,677 mentions: GitHub 59,260, Cloudflare 10,878, Stripe 5,727, Vercel 5,266, Notion 1,969, Supabase 1,561, Twilio 549, Brave Search 467 |
| 4. Dedup | Done | 79,348 mentions; largest GitHub template collapsed from 1,774 copies to 1 |
| Recency (row 5, run early) | Done | **No-go on this row.** Median product share in the last 3 months 6.5% (pooled 8.2%), against 18.4% for all cleaned docs. See `results/recency.csv`, `monthly_counts.csv` |
| 5a. Upper bound and gate | Done | **Gate passes.** All 8 products have 30+ candidates; median candidate share 11.4% (9.8% without install commands). See `results/upper_bound.csv` |
| Pre-check (not in the original plan) | Done, pending spot-check | **4 of 104 candidates actionable (3.8%; 95% upper bound 9.6%).** Implies actionable share of about 0.4% (at most about 1.1%), against the 5% no-go line. See `results/precheck_labels.csv` |
| 5b–7 | Stopped | **Test closed as no-go.** See `results/decision_note.md` |

Second run, Sep 29, 2026: `pipeline/00_download.py` added (dataset revision in `results/source_revision.txt`); steps 1–4 reproduced the first run exactly.

Recency: every product sits below the archive-wide baseline (Brave Search 0.4% to Cloudflare 11.4%, against 18.4%), so the drop is not only a collection effect: mentions of these tools fell faster than Moltbook as a whole. Monthly mentions peaked in Feb–Mar and were down about 95% by August.

5a notes:

- Two rule fixes before the gate was read. `*.workers.dev` hosts were dropped as API-path markers: they are also a Cloudflare alias, and 4,869 mentions came from one spam host (`coinflip-x402.workers.dev`), which had pushed Cloudflare's candidate share to 59%. Package install lines (`pip install`, `npx`, `npm install`, `curl`) were split into their own feature, because on Moltbook they are mostly agents advertising their own tools; the gate is reported with and without them and passes both ways.
- Known gap: a docs complaint with no code, path or limit ("the docs don't say which header…") has one friction verb and no marker, so it is not a candidate.
- An informal read of 40 random candidates (5 per product), not a substitute for the hand labels, found about 2–3 a product team could file a ticket from. Most are agents promoting their own apps, whose `*.vercel.app` / `*.supabase.co` / `*.workers.dev` URLs, `/api/...` paths and `curl` examples trip the rules. If that holds, actionable share is roughly 11% × 7% ≈ 1%. Candidate precision would need to be about 45% to clear the 5% no-go line, and about 90% to reach 10%.

Pre-check: a quick screen added before the 1,000-mention labeling, to see whether that labeling is worth doing. 13 random 5a candidates per product (`pipeline/05a_precheck_sample.py`, excluding the 40 read above) were labeled by Claude with the scheme above, one reason per row, and 20 rows (`user_check = yes`) plus the 4 actionable ones are for a human to confirm. These labels are a screen, not the validation set, and are never used to train or test the classifier.

- 4 actionable: Brave Search pricing and rate limits driving a switch to SearXNG; Cloudflare Workers free-tier 100k/day limit; Cloudflare per-account rate limit shared across sub-agents; Notion `PATCH /blocks/{id}/children` returning 400 (borderline).
- The other 100: 45 off-topic (mostly agents advertising their own apps and packages), 39 neutral usage, and the rest vague, about the author's own code, or about Moltbook's bugs.
- Projection: actionable share ≈ candidate share × candidate precision ≈ 11.4% × 3.8% ≈ 0.4%, and about 1.1% at the upper bound. Non-candidates could add some (e.g. docs complaints with no marker); even 1% of them would add about 0.9 points. The actionable-share criterion is no-go unless the spot-check overturns the labels.
- Volume is a partial exception: Cloudflare (1,149 candidates × 2/13) could still reach 30+ actionable mentions, and GitHub's 7,646 candidates are too many to rule it out from 0/13. That criterion is undecided, and most of that volume is from Feb–Apr.

`archive/05_classify_llm.py` is from the earlier LLM plan and is superseded by step 5 above; it is kept only for reference and needs an API key to run.
