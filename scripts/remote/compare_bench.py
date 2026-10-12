"""Compare benchmark JSONs across platforms and project a Phase-5C-scale workload.

Usage: uv run python scripts/remote/compare_bench.py   (reads results/remote/**/bench_*.json)
Writes results/remote/bench_comparison.md and prints it. Projections are single-process
hours; divide by the number of processes the platform can run in parallel.
"""

from __future__ import annotations

import json

from qtrace.config import repo_root

# Phase 5C scale: model-rows over all 64 models (32 x 42,559 + 16 x 28,372 + 16 x 56,746)
MODEL_ROWS = 32 * 42_559 + 16 * 28_372 + 16 * 56_746
NOISY_PLOTS = 16
REPLICATE_CONTEXTS = 64 * 68 * 3 * 20  # finite-shot work (numpy, CPU only)


def _exact_rows(r: dict, fps: dict) -> list[str]:
    by: dict = {}
    for e in r["exact"]:
        by.setdefault((e["variant"], e["rows"]), []).append(e)
        if e["variant"] == "cpu_production":
            fps[(r["tag"], e["rows"], e["plot"])] = e["fingerprint"]
    out = []
    for (variant, rows), es in sorted(by.items()):
        ms = sum(e["ms_per_row_all_factors"] for e in es) / len(es)
        dp = max(e["max_abs_dp_vs_reference"] for e in es)
        hours = MODEL_ROWS * NOISY_PLOTS * ms / 1e3 / 3600
        out.append(f"| {r['tag']} | {variant} | {rows} | {ms:.3f} | {dp:.1e} | {hours:.1f} |")
    return out


def main() -> int:
    root = repo_root()
    paths = sorted((root / "results/remote").rglob("bench_*.json"))
    reports = [json.loads(p.read_text()) for p in paths]
    if not reports:
        print("no benchmark JSON found under results/remote/")
        return 1
    lines = [
        "| platform | variant | rows | ms/row (folds 1+3+5; mean of 3 plots) | max abs dp vs"
        " production | 5C exact stage, 1 process (h) |",
        "|---|---|---|---|---|---|",
    ]
    fps: dict = {}
    for r in reports:
        lines += _exact_rows(r, fps)
    lines += [
        "",
        "| platform | finite-shot replicate (s) | at rows | 5C finite-shot stage, 1 process (h) |",
        "|---|---|---|---|",
    ]
    for r in reports:
        f = max(r["finite_shot"], key=lambda x: x["rows"])
        s = f["total_per_replicate_context_s"]
        per = s * (MODEL_ROWS / 64) / f["rows"]
        lines.append(
            f"| {r['tag']} | {s:.3f} | {f['rows']} | {REPLICATE_CONTEXTS * per / 3600:.1f} |"
        )
    tags = sorted({t for t, _, _ in fps})
    lines += ["", "Production reference agreement across platforms (rounded to 1e-10):", ""]
    for t in tags[1:]:
        common = [(n, g) for (tt, n, g) in fps if tt == t and (tags[0], n, g) in fps]
        same = all(fps[(t, n, g)] == fps[(tags[0], n, g)] for n, g in common)
        verdict = "identical" if same else "DIFFERENT"
        lines.append(f"- {t} vs {tags[0]}: {verdict} on {len(common)} (rows, plot) cells")
    lines += ["", "Hardware:", ""]
    for r in reports:
        hw = r["hardware"]
        lines.append(
            f"- {r['tag']}: {hw.get('cpu_model')}; {hw.get('logical_cpus')} logical CPUs;"
            f" {hw.get('ram_gb')} GB RAM; GPU {hw.get('gpu')}; Aer devices {r['aer_devices']};"
            f" peak RSS {r['peak_rss_mb']:.0f} MB; run {r['total_seconds']:.0f} s"
        )
    text = "\n".join(lines) + "\n"
    (root / "results/remote/bench_comparison.md").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
