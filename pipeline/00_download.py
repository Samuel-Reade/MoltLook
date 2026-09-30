"""Step 0: download the archive parquet from Hugging Face into data/raw.

Only the folders the pipeline reads are fetched (posts, comments, agents,
submolts); the large combined files at the repo root are skipped. The dataset
revision is written to results/source_revision.txt so a run can be reproduced
(pass it back with --revision).
"""
import argparse

from huggingface_hub import HfApi, snapshot_download

REPO = "SimulaMet/moltbook-observatory-archive"

ap = argparse.ArgumentParser()
ap.add_argument("--revision", default=None, help="dataset commit to pin (default: latest)")
args = ap.parse_args()

sha = HfApi().dataset_info(REPO, revision=args.revision).sha
snapshot_download(
    REPO, repo_type="dataset", revision=sha, local_dir="data/raw",
    allow_patterns=[f"data/{d}/*.parquet" for d in ("posts", "comments", "agents", "submolts")],
    max_workers=8,
)
with open("results/source_revision.txt", "w") as f:
    f.write(f"{REPO}@{sha}\n")
print(f"downloaded {REPO}@{sha}")
