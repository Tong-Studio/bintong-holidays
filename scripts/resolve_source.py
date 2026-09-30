"""Resolve only the upstream stable release; save an exact, reproducible pin."""
import json
import re
import urllib.request
from pathlib import Path

with urllib.request.urlopen("https://pypi.org/pypi/holidays/json", timeout=30) as response:
    data = json.load(response)
version = data["info"]["version"]
if not re.fullmatch(r"\d+(\.\d+)+", version) or all(f.get("yanked") for f in data["releases"][version]):
    raise SystemExit("Latest release is not a stable, usable version")
Path("requirements.txt").write_text(f"holidays=={version}\nBabel==2.18.0\npython-dateutil==2.9.0.post0\nsix==1.17.0\n")
print(f"Resolved holidays {version}")
