"""
download_data.py — Download Raw Datasets to data/raw-data/
===========================================================
Downloads the four primary datasets for the AI Data Center
Sustainability Analysis.

Datasets:
  1. IM3 Open Source Data Center Atlas (PNNL/DOE) — CSV (~0.2 MB)
  2. EPA eGRID 2023 Revision 2                    — XLSX (~21 MB)
  3. WRI Aqueduct 4.0 Baseline Monthly             — CSV (~28 MB)
  4. WRI Aqueduct 4.0 Future Annual                — CSV (~28 MB)

Usage:
  python code/download_data.py           # from repo root
  python code/download_data.py --force   # re-download existing files

Total estimated download size: ~77 MB
Requires: requests (pip install requests)
"""

import os, sys, time, argparse
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("ERROR: 'requests' package required. Install with: pip install requests")

# ── Paths ─────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw-data"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── Dataset registry ──────────────────────────────────────────────────────
DATASETS = [
    {
        "name": "IM3 Open Source Data Center Atlas (PNNL/DOE)",
        "url": (
            "https://data.msdlive.org/records/65g71-a4731/files/"
            "im3_open_source_data_center_atlas_v2026.02.09.csv"
        ),
        "filename": "im3_open_source_data_center_atlas_v2026.02.09.csv",
        "expected_mb": 0.2,
        "description": (
            "Facility-level data center locations: 1,479 records across "
            "47 U.S. states with coordinates, county, operator, sq footage."
        ),
    },
    {
        "name": "EPA eGRID 2023 (Revision 2)",
        "url": (
            "https://www.epa.gov/system/files/documents/2025-03/"
            "egrid2023_data_rev2.xlsx"
        ),
        "filename": "egrid2023_data_rev2.xlsx",
        "expected_mb": 21,
        "description": (
            "Electricity grid emissions data from EPA: plant-level, "
            "subregion-level, and state-level CO2 rates, generation mix, "
            "and renewable percentages."
        ),
    },
    {
        "name": "WRI Aqueduct 4.0 — Baseline Monthly",
        "url": (
            "https://raw.githubusercontent.com/wri/Aqueduct40/main/"
            "Aqueduct40_baseline_monthly_y2023m07d05.csv"
        ),
        "filename": "Aqueduct40_baseline_monthly_y2023m07d05.csv",
        "expected_mb": 28,
        "description": (
            "Monthly baseline water stress scores (BWS), water depletion "
            "(BWD), and inter-annual variability (IAV) for 15,834 global "
            "HydroSHEDS catchments."
        ),
    },
    {
        "name": "WRI Aqueduct 4.0 — Future Annual",
        "url": (
            "https://raw.githubusercontent.com/wri/Aqueduct40/main/"
            "Aqueduct40_future_annual_y2023m07d05.csv"
        ),
        "filename": "Aqueduct40_future_annual_y2023m07d05.csv",
        "expected_mb": 28,
        "description": (
            "Projected future water stress under three scenarios "
            "(BAU, Optimistic, Pessimistic) for years 2030, 2050, 2080. "
            "Covers 16,395 global catchments."
        ),
    },
]


def download_file(url: str, dest: Path, expected_mb: float, force: bool = False) -> bool:
    """Download a file with progress bar. Returns True on success."""
    if dest.exists() and not force:
        actual_mb = dest.stat().st_size / 1e6
        print(f"  SKIP (already exists, {actual_mb:.1f} MB) — use --force to re-download")
        return True

    print(f"  Downloading (~{expected_mb:.0f} MB)...")
    print(f"  URL: {url}")

    try:
        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        t0 = time.time()

        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = 100 * downloaded / total
                    speed = downloaded / (1024 * 1024 * max(time.time() - t0, 0.01))
                    sys.stdout.write(
                        f"\r  [{pct:5.1f}%] {downloaded/1e6:.1f}/{total/1e6:.1f} MB "
                        f"@ {speed:.1f} MB/s"
                    )
                    sys.stdout.flush()

        actual_mb = dest.stat().st_size / 1e6
        print(f"\n  OK — saved {dest.name} ({actual_mb:.1f} MB)")
        return True

    except requests.exceptions.RequestException as e:
        print(f"\n  FAILED: {e}")
        if dest.exists():
            dest.unlink()
        return False


def main():
    parser = argparse.ArgumentParser(description="Download raw datasets")
    parser.add_argument("--force", action="store_true", help="Re-download existing files")
    args = parser.parse_args()

    print("=" * 65)
    print("  AI Data Center Sustainability Analysis — Data Downloader")
    print("=" * 65)
    print(f"\nTarget directory : {RAW_DIR}")
    print(f"Datasets         : {len(DATASETS)}")
    total_mb = sum(d["expected_mb"] for d in DATASETS)
    print(f"Est. total size  : ~{total_mb:.0f} MB\n")

    results = []
    for i, ds in enumerate(DATASETS, 1):
        print(f"[{i}/{len(DATASETS)}] {ds['name']}")
        print(f"  {ds['description']}")
        dest = RAW_DIR / ds["filename"]
        ok = download_file(ds["url"], dest, ds["expected_mb"], force=args.force)
        results.append((ds["name"], ok))
        print()

    # Summary
    print("=" * 65)
    print("Summary:")
    all_ok = True
    for name, ok in results:
        status = "OK" if ok else "FAILED"
        print(f"  [{status}] {name}")
        if not ok:
            all_ok = False

    print()
    if all_ok:
        print(f"All {len(DATASETS)} datasets ready in {RAW_DIR}")
    else:
        print("Some downloads failed. You may manually download from URLs in README.md")

    # Verify
    print("\nFile verification:")
    for ds in DATASETS:
        fp = RAW_DIR / ds["filename"]
        if fp.exists():
            print(f"  {ds['filename']}: {fp.stat().st_size / 1e6:.1f} MB")
        else:
            print(f"  {ds['filename']}: MISSING")

    print("\nNext step: python code/preprocessing.py")


if __name__ == "__main__":
    main()
