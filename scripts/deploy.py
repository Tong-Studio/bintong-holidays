"""Deploy static files, verify HTTPS bytes, and roll back on verification failure."""
import argparse
import json
import os
import tempfile
import uuid
from pathlib import Path
import subprocess
import time
import urllib.request
from holiday_data import ROOT, digest, read, validate


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "BinTong-Holidays-Verify/1.0"}), timeout=15) as response:
        return response.read(), response.headers


def verify(base):
    expected = read(ROOT / "public/v1/manifest.json")
    raw, _ = fetch(base.rstrip("/") + "/v1/manifest.json")
    if json.loads(raw) != expected:
        raise ValueError("Published manifest does not match generated data")
    for code in ("KR", "JP", "US"):
        entry = expected["countries"][code]
        raw, headers = fetch(base.rstrip("/") + "/" + entry["path"])
        if digest(raw) != entry["sha256"] or "immutable" not in headers.get("Cache-Control", ""):
            raise ValueError(f"Published {code} bytes/cache policy differ")
    raw, _ = fetch(base.rstrip("/") + "/LICENSES.txt")
    if not raw.strip():
        raise ValueError("Missing published licenses")
    print("Verified HTTPS manifest, KR/JP/US hashes, cache headers and licenses")


def upload_version():
    # Version deployment leaves existing domains/routes untouched, so the token
    # needs access only to this Worker, with no DNS or zone editing permissions.
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "wrangler.jsonl"
        env = {**os.environ, "WRANGLER_OUTPUT_FILE_PATH": str(output)}
        subprocess.run(["npx", "--no-install", "wrangler", "versions", "upload"], check=True, env=env)
        records = [json.loads(line) for line in output.read_text().splitlines() if line.strip()]
    uploads = [record for record in records if record.get("type") == "version-upload"]
    if len(uploads) != 1 or uploads[0].get("worker_name") != "bintong-holidays":
        raise ValueError("Expected exactly one upload for bintong-holidays")
    return str(uuid.UUID(uploads[0]["version_id"]))


def activate(version, message):
    subprocess.run(["npx", "--no-install", "wrangler", "versions", "deploy",
                    f"{version}@100", "--yes", "--message", message], check=True)


def deploy(base):
    history = json.loads(subprocess.check_output(
        ["npx", "--no-install", "wrangler", "deployments", "list", "--json"], text=True))
    latest = max(history, key=lambda d: d["created_on"])
    versions = latest["versions"]
    if len(versions) != 1 or versions[0]["percentage"] != 100:
        raise RuntimeError("Expected a single active version for safe rollback")
    previous = versions[0]["version_id"]
    # A failed upload has no production effect; do not roll back another deployment.
    candidate = upload_version()
    try:
        activate(candidate, "Validated public holiday snapshot")
        for attempt in range(6):
            try:
                verify(base)
                return
            except Exception:
                if attempt == 5:
                    raise
                time.sleep(10)
    except Exception:
        activate(previous, "Holiday deployment verification failed: restore previous version")
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="https://holidays.tong-studio.com")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    validate(ROOT / "public")
    if args.verify_only:
        verify(args.base)
        return
    deploy(args.base)


if __name__ == "__main__":
    main()
