"""
download_data.py — Download raw datasets + check for newer versions
====================================================================
Downloads every raw dataset for the AI Data Center Sustainability
Analysis into data/raw-data/, and polls publishers for newer versions
using the checks configured in data/manifest.json.

Refresh policy: pinned snapshots + explicit one-command upgrade, never
silent auto-refresh — every number in the writeup must be reproducible
from the versions recorded in data/manifest.json.

Usage:
  python code/download_data.py                  # download anything missing
  python code/download_data.py --force          # re-download everything
  python code/download_data.py --check-updates  # poll publishers, report, exit 1 if updates exist
  python code/download_data.py --update <key>   # force-refresh one dataset + stamp manifest

Requires: requests (pip install requests)
"""

import argparse
import json
import re
import sys
import time
import zipfile
from datetime import date
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("ERROR: 'requests' package required. Install with: pip install requests")

# ── Paths ─────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw-data"
SHP_DIR = RAW_DIR / "shapefiles"
MANIFEST_PATH = ROOT / "data" / "manifest.json"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── Dataset registry ──────────────────────────────────────────────────────
# Optional keys:
#   unzip / extract_dir — extract the downloaded zip into extract_dir
#   optional            — a failure is reported but doesn't fail the run
#                         (used where the committed snapshot is the pinned source)
#   manifest_key        — links the entry to data/manifest.json for --update stamping
DATASETS = [
    {
        "name": "IM3 Open Source Data Center Atlas (PNNL/DOE)",
        "url": (
            "https://data.msdlive.org/records/65g71-a4731/files/"
            "im3_open_source_data_center_atlas_v2026.02.09.csv"
        ),
        "filename": "im3_open_source_data_center_atlas_v2026.02.09.csv",
        "expected_mb": 0.2,
        "optional": True,
        "manifest_key": "im3_atlas",
        "description": (
            "Facility-level data center locations (1,479 records, 47 states). "
            "NOTE: MSD-Live gates file bytes behind an authenticated flow, so this "
            "direct URL may fail — the committed CSV is the pinned snapshot. "
            "Manual download: https://data.msdlive.org/records/65g71-a4731/latest"
        ),
    },
    {
        "name": "EPA eGRID 2023 (Revision 2)",
        "url": "https://www.epa.gov/system/files/documents/2025-06/egrid2023_data_rev2.xlsx",
        "filename": "egrid2023_data_rev2.xlsx",
        "expected_mb": 21,
        "manifest_key": "egrid",
        "description": (
            "Grid emissions from EPA: plant-, subregion-, and state-level CO2 "
            "rates, generation mix, renewable percentages."
        ),
    },
    {
        "name": "EPA eGRID2023 subregion boundaries (shapefile)",
        "url": "https://www.epa.gov/system/files/other-files/2025-01/egrid2023_subregions.zip",
        "filename": "egrid2023_subregions.zip",
        "expected_mb": 57,
        "unzip": True,
        "extract_dir": SHP_DIR / "egrid2023_subregions",
        "manifest_key": "egrid_subregions_shp",
        "description": "Primary eGRID subregion polygons (EPSG:4326) for point-in-polygon assignment.",
    },
    {
        "name": "EPA eGRID2023 multiple-subregion overlap areas (shapefile)",
        "url": "https://www.epa.gov/system/files/other-files/2025-01/egrid2023_multiple_subregions.zip",
        "filename": "egrid2023_multiple_subregions.zip",
        "expected_mb": 16,
        "unzip": True,
        "extract_dir": SHP_DIR / "egrid2023_multiple_subregions",
        "manifest_key": "egrid_subregions_shp",
        "description": "Areas served by more than one eGRID subregion — used to QA-flag ambiguous assignments.",
    },
    {
        "name": "HydroBASINS level-6 sub-basins, North America (v1c)",
        "url": "https://data.hydrosheds.org/file/HydroBASINS/standard/hybas_na_lev06_v1c.zip",
        "filename": "hybas_na_lev06_v1c.zip",
        "expected_mb": 12,
        "unzip": True,
        "extract_dir": SHP_DIR / "hydrobasins",
        "manifest_key": "hydrobasins_lev06",
        "description": (
            "Pfafstetter level-6 basin polygons whose PFAF_ID joins WRI Aqueduct 4.0's "
            "pfaf_id. PINNED to v1c for Aqueduct compatibility."
        ),
    },
    {
        "name": "HydroBASINS level-6 sub-basins, Arctic (v1c)",
        "url": "https://data.hydrosheds.org/file/HydroBASINS/standard/hybas_ar_lev06_v1c.zip",
        "filename": "hybas_ar_lev06_v1c.zip",
        "expected_mb": 6,
        "unzip": True,
        "extract_dir": SHP_DIR / "hydrobasins",
        "manifest_key": "hydrobasins_lev06",
        "description": "Arctic-region basins (Alaska coverage; robustness for future atlas versions).",
    },
    {
        "name": "FracTracker US Data Centers Tracker (dated snapshot)",
        "url": (
            "https://docs.google.com/spreadsheets/d/e/"
            "2PACX-1vRZgBssB4WNmXOSNxewk5-X514gV-hfpouEVp9K-F5ozlImxOWF-BlrfqAy-4YfeJCpl8l7IIAlxPFt/"
            "pub?output=csv"
        ),
        "filename": "fractracker_us_datacenters_2026-07-10.csv",
        "expected_mb": 0.8,
        "manifest_key": "fractracker",
        "description": (
            "Facility-level MW demand, status, operator (rolling dataset — this file is a "
            "dated snapshot). License: non-commercial with credit to FracTracker Alliance."
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
        "optional": True,
        "manifest_key": "aqueduct40",
        "description": (
            "Monthly baseline water stress for 15,834 HydroBASINS catchments. "
            "NOTE: this GitHub URL is dead (404) — the committed CSV is the pinned "
            "snapshot. Canonical source: "
            "https://files.wri.org/aqueduct/aqueduct-4-0-water-risk-data.zip (~262 MB)."
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
        "optional": True,
        "manifest_key": "aqueduct40",
        "description": (
            "Projected water stress (BAU/Optimistic/Pessimistic; 2030/2050/2080). "
            "Same dead-URL note as baseline monthly — committed CSV is pinned."
        ),
    },
]


# ── Download machinery ─────────────────────────────────────────────────────
def extract_zip(zip_path: Path, extract_dir: Path) -> bool:
    """Extract a zip; skip if a .shp is already present."""
    if extract_dir.exists() and any(extract_dir.glob("*.shp")):
        print(f"  SKIP extract (shapefile already present in {extract_dir.relative_to(ROOT)})")
        return True
    extract_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)
        print(f"  Extracted -> {extract_dir.relative_to(ROOT)}")
        return True
    except zipfile.BadZipFile as e:
        print(f"  FAILED to extract: {e}")
        return False


def download_file(url: str, dest: Path, expected_mb: float, force: bool = False) -> bool:
    """Download a file with progress output. Returns True on success."""
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


def process_dataset(ds: dict, force: bool = False) -> bool:
    dest = RAW_DIR / ds["filename"]
    ok = download_file(ds["url"], dest, ds["expected_mb"], force=force)
    if ok and ds.get("unzip") and dest.exists():
        ok = extract_zip(dest, ds["extract_dir"])
    if not ok and ds.get("optional"):
        print("  (optional — committed snapshot in data/raw-data/ remains the pinned source)")
    return ok


# ── Version checking (data/manifest.json) ─────────────────────────────────
def load_manifest() -> dict:
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def save_manifest(manifest: dict) -> None:
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


def _dig(obj: dict, dotted: str):
    for part in dotted.split("."):
        if not isinstance(obj, dict) or part not in obj:
            return None
        obj = obj[part]
    return obj


def check_one(key: str, entry: dict) -> tuple[str, str]:
    """Run one version check. Returns (status, detail) where status is
    UP-TO-DATE | UPDATE-AVAILABLE | INFO | CHECK-FAILED."""
    vc = entry.get("version_check")
    if not vc:
        return "INFO", "no version_check configured"

    headers = {"User-Agent": "dc-sustainability-analysis data checker"}
    try:
        if vc["method"] == "api":
            resp = requests.get(vc["url"], timeout=30, headers=headers)
            resp.raise_for_status()
            value = _dig(resp.json(), vc["field"])
            if vc.get("report_only") or vc.get("expect") is None:
                return "INFO", f"{vc['field']} = {value} (rolling dataset; snapshot pinned {entry['version_used']})"
            if str(value) == str(vc["expect"]):
                return "UP-TO-DATE", f"{vc['field']} = {value}"
            return "UPDATE-AVAILABLE", f"{vc['field']} = {value} (pinned: {vc['expect']})"

        if vc["method"] == "head":
            resp = requests.head(vc["url"], timeout=30, headers=headers, allow_redirects=True)
            resp.raise_for_status()
            etag = resp.headers.get("ETag", "").strip('"')
            clen = int(resp.headers.get("Content-Length", 0) or 0)
            if etag == vc.get("expect_etag") and clen == vc.get("expect_content_length"):
                return "UP-TO-DATE", f"ETag/Content-Length unchanged ({clen} bytes)"
            return "UPDATE-AVAILABLE", (
                f"remote file changed: ETag {etag or 'n/a'}, {clen} bytes "
                f"(pinned: {vc.get('expect_etag')}, {vc.get('expect_content_length')})"
            )

        if vc["method"] == "scrape":
            resp = requests.get(vc["url"], timeout=30, headers=headers)
            resp.raise_for_status()
            matches = re.findall(vc["pattern"], resp.text, flags=re.IGNORECASE)
            if not matches:
                return "CHECK-FAILED", f"pattern {vc['pattern']!r} not found on page"
            latest = max(matches)
            if str(latest) == str(vc["expect"]):
                return "UP-TO-DATE", f"latest on page: {latest}"
            status = "INFO" if vc.get("alert_only") else "UPDATE-AVAILABLE"
            return status, f"latest on page: {latest} (pinned: {vc['expect']})"

        return "CHECK-FAILED", f"unknown method {vc['method']!r}"

    except (requests.exceptions.RequestException, ValueError, KeyError) as e:
        return "CHECK-FAILED", str(e)


def check_updates() -> int:
    manifest = load_manifest()
    print("=" * 78)
    print("  Dataset version check — pinned snapshots vs publishers")
    print("=" * 78)
    updates = 0
    for key, entry in manifest["datasets"].items():
        status, detail = check_one(key, entry)
        if status == "UPDATE-AVAILABLE":
            updates += 1
        print(f"\n[{status}] {key} — {entry['name']}")
        print(f"    pinned : {entry['version_used']} (accessed {entry['access_date']})")
        print(f"    check  : {detail}")
        if status == "UPDATE-AVAILABLE":
            print(f"    action : python code/download_data.py --update {key}")
        if entry.get("version_check", {}).get("alert_only"):
            print("    note   : compatibility-pinned — review before updating (see manifest notes)")
    print("\n" + "=" * 78)
    print(f"{updates} update(s) available." if updates else "All pinned datasets are current.")
    return 1 if updates else 0


def update_dataset(key: str) -> int:
    manifest = load_manifest()
    if key not in manifest["datasets"]:
        print(f"Unknown dataset key {key!r}. Known keys: {', '.join(manifest['datasets'])}")
        return 2
    matching = [ds for ds in DATASETS if ds.get("manifest_key") == key]
    if not matching:
        print(f"{key} has no downloadable entries (see manifest notes for manual steps).")
        return 2

    today = date.today().isoformat()
    all_ok = True
    for ds in matching:
        # Rolling snapshots get a fresh dated filename
        if key == "fractracker":
            ds = {**ds, "filename": f"fractracker_us_datacenters_{today}.csv"}
        print(f"\n[update] {ds['name']}")
        all_ok &= process_dataset(ds, force=True)

    if all_ok:
        entry = manifest["datasets"][key]
        entry["access_date"] = today
        if key == "fractracker":
            entry["version_used"] = f"snapshot {today}"
        save_manifest(manifest)
        print(f"\nManifest stamped: {key} accessed {today}.")
        print("REMINDER: re-run `python code/preprocessing.py --force` and review "
              "data/derived-data/qa_report.md before trusting downstream numbers.")
        return 0
    print("\nUpdate failed; manifest NOT stamped.")
    return 1


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Download raw datasets / check for updates")
    parser.add_argument("--force", action="store_true", help="Re-download existing files")
    parser.add_argument("--check-updates", action="store_true",
                        help="Poll publishers for newer versions (exit 1 if updates exist)")
    parser.add_argument("--update", metavar="KEY",
                        help="Force-refresh one dataset by manifest key and stamp the manifest")
    args = parser.parse_args()

    if args.check_updates:
        sys.exit(check_updates())
    if args.update:
        sys.exit(update_dataset(args.update))

    print("=" * 65)
    print("  AI Data Center Sustainability Analysis — Data Downloader")
    print("=" * 65)
    print(f"\nTarget directory : {RAW_DIR}")
    print(f"Datasets         : {len(DATASETS)}\n")

    results = []
    for i, ds in enumerate(DATASETS, 1):
        print(f"[{i}/{len(DATASETS)}] {ds['name']}")
        print(f"  {ds['description']}")
        ok = process_dataset(ds, force=args.force)
        results.append((ds["name"], ok, ds.get("optional", False)))
        print()

    print("=" * 65)
    print("Summary:")
    hard_failures = 0
    for name, ok, optional in results:
        status = "OK" if ok else ("SKIPPED (optional)" if optional else "FAILED")
        if not ok and not optional:
            hard_failures += 1
        print(f"  [{status}] {name}")

    print()
    if hard_failures == 0:
        print(f"All required datasets ready in {RAW_DIR}")
        print("\nNext step: python code/preprocessing.py")
    else:
        print(f"{hard_failures} required download(s) failed — see URLs above or METHODS.md.")
        sys.exit(1)


if __name__ == "__main__":
    main()
