"""Public holiday publishing contract; only generated PUBLIC category dates."""
import argparse
import hashlib
import importlib.metadata
import json
import re
import warnings
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded(value))


def validate_date(value, first, last):
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value or not first <= parsed.year <= last:
        raise ValueError(f"Invalid date: {value}")


def names(value):
    if not isinstance(value, dict) or not value.get("en"):
        raise ValueError("English holiday name required")
    if any(k not in ("en", "ko", "ja") or not isinstance(v, str) or not v.strip() for k, v in value.items()):
        raise ValueError("Invalid translated names")


def validate_overrides(items, countries):
    seen = set()
    for item in items:
        code, subdivision, day = item["country"], item.get("subdivision"), item["date"]
        if code not in countries or (subdivision is not None and subdivision not in countries[code]):
            raise ValueError("Unknown override region")
        validate_date(day, 2024, 9999)
        key = (code, subdivision, day)
        if key in seen:
            raise ValueError("Conflicting overrides")
        seen.add(key)
        parsed = urlparse(item["sourceUrl"])
        if parsed.scheme != "https" or not parsed.hostname or not item["reason"].strip():
            raise ValueError("Official HTTPS source URL and reason required")
        if item["action"] not in ("add", "replace", "remove"):
            raise ValueError("Unknown override action")
        if item["action"] != "remove":
            names(item["names"])


def apply_overrides(days, items, country, subdivision, last):
    result = dict(days)
    # Nationwide corrections also apply to each subdivision, then local ones win.
    scopes = [None] if subdivision is None else [None, subdivision]
    for scope in scopes:
        for item in items:
            if item["country"] != country or item.get("subdivision") != scope or int(item["date"][:4]) > last:
                continue
            if item["action"] == "remove":
                result.pop(item["date"], None)
            else:
                # Idempotent when upstream later includes the same correction.
                result[item["date"]] = item["names"]
    return result


def generate(target, year):
    import holidays
    from babel import Locale
    first, last = 2024, year + 4
    supported = holidays.list_supported_countries(include_aliases=False)
    overrides = read(ROOT / "overrides.json")
    validate_overrides(overrides, supported)
    old_path = target / "v1/manifest.json"
    old = read(old_path) if old_path.exists() else None
    if old and set(old["countries"]) - set(supported):
        raise ValueError("Upstream removed supported countries; review before publishing")
    countries = {}

    def days(code, subdivision=None):
        base = holidays.country_holidays(code, subdiv=subdivision, years=range(first, last + 1),
                                        categories=holidays.PUBLIC, observed=True, expand=False, language="en_US")
        calendars = {"en": base}
        for language in ("ko", "ja"):
            if language in base.supported_languages:
                calendars[language] = holidays.country_holidays(code, subdiv=subdivision, years=range(first, last + 1),
                    categories=holidays.PUBLIC, observed=True, expand=False, language=language)
        result = {d.isoformat(): {lang: cal[d] for lang, cal in calendars.items()}
                  for d in sorted(base) if first <= d.year <= last}
        return apply_overrides(result, overrides, code, subdivision, last)

    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        for code, subdivisions in sorted(supported.items()):
            base = holidays.country_holidays(code)
            national = days(code)
            patches = {}
            for subdivision in subdivisions:
                local = days(code, subdivision)
                patches[subdivision] = {"removed": sorted(set(national) - set(local)),
                    "days": {day: value for day, value in local.items() if national.get(day) != value}}
            data = encoded({"schemaVersion": 1, "country": code, "firstYear": first, "lastYear": last,
                            "national": national, "subdivisions": patches})
            sha = digest(data)
            path = f"v1/countries/{code}/{sha}.json"
            (target / path).parent.mkdir(parents=True, exist_ok=True)
            (target / path).write_bytes(data)
            countries[code] = {"names": {lang: Locale.parse(lang).territories.get(code, code) for lang in ("en", "ko", "ja")},
                "subdivisions": {sub: next((name for name, value in base.subdivisions_aliases.items() if value == sub), sub) for sub in subdivisions},
                "path": path, "sha256": sha}
    source = {"holidays": holidays.__version__, "Babel": importlib.metadata.version("Babel"),
              "python-dateutil": importlib.metadata.version("python-dateutil"), "six": importlib.metadata.version("six")}
    manifest = {"schemaVersion": 1, "source": "https://github.com/vacanza/holidays", "sourceVersions": source,
                "firstYear": first, "lastYear": last, "countries": countries, "overridesHash": digest(encoded(overrides)),
                "generatorHash": digest(Path(__file__).read_bytes()),
                "notices": sorted({str(n.message) for n in notices})}
    manifest["dataVersion"] = digest(encoded(manifest))
    changed = old is None or old["dataVersion"] != manifest["dataVersion"]
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat() if changed else old["generatedAt"]
    if changed:
        changed_codes = [code for code, item in countries.items() if not old or old['countries'].get(code, {}).get('sha256') != item['sha256']]
        write(target / f"v1/changes/{manifest['dataVersion']}.json", {
            "dataVersion": manifest['dataVersion'], "previousVersion": old['dataVersion'] if old else None,
            "generatedAt": manifest['generatedAt'], "changedCountries": changed_codes,
            "sourceVersions": source, "firstYear": first, "lastYear": last})
    write(old_path, manifest)
    write(target / f"v1/releases/{manifest['dataVersion']}.json", manifest)
    releases = sorted((target / "v1/releases").glob("*.json"), key=lambda p: read(p)["generatedAt"], reverse=True)
    keep = releases[:3]
    paths = {entry["path"] for file in keep for entry in read(file)["countries"].values()}
    for file in releases[3:]:
        file.unlink()
    for change in (target / "v1/changes").glob("*.json"):
        if change.stem not in {p.stem for p in keep}: change.unlink()
    for file in (target / "v1/countries").glob("*/*.json"):
        if file.relative_to(target).as_posix() not in paths:
            file.unlink()
    licenses = []
    for package in source:
        distribution = importlib.metadata.distribution(package)
        for file in distribution.files:
            if file.name in ("LICENSE", "LICENSE.txt", "LICENSE.unicode"):
                licenses.append(f"{package}: {file.name}\n\n{distribution.locate_file(file).read_text()}")
    (target / "LICENSES.txt").write_text("\n\n".join(licenses))
    (target / "_headers").write_text("/v1/manifest.json\n  Cache-Control: public, max-age=300, must-revalidate\n/v1/countries/*\n  Cache-Control: public, max-age=31536000, immutable\n/*\n  Access-Control-Allow-Origin: *\n  X-Content-Type-Options: nosniff\n")
    (target / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>BinTong public holidays</title><h1>BinTong public holidays</h1><p>Public holiday data. Future and temporary holidays may change.</p><a href="/v1/manifest.json">Data manifest</a> · <a href="/LICENSES.txt">Licenses</a> · <a href="https://github.com/Tong-Studio/bintong-holidays">Source and corrections</a>')
    validate(target)
    write(target.parent / "status.json", {"checkedAt": datetime.now(timezone.utc).isoformat(), "dataVersion": manifest["dataVersion"], "sourceVersions": source})
    print(json.dumps({"changed": changed, "countries": len(countries), "version": manifest["dataVersion"]}))


def validate(target):
    manifest = read(target / "v1/manifest.json")
    if manifest["schemaVersion"] != 1 or not manifest["countries"]:
        raise ValueError("Unsupported or empty manifest")
    for code, entry in manifest["countries"].items():
        path = f"v1/countries/{code}/{entry['sha256']}.json"
        if entry["path"] != path or not re.fullmatch(r"[A-Z]{2}", code):
            raise ValueError("Invalid country path")
        raw = (target / path).read_bytes()
        if digest(raw) != entry["sha256"] or len(raw) > 2_000_000:
            raise ValueError("Hash/size mismatch")
        data = json.loads(raw)
        if data["country"] != code or data["schemaVersion"] != 1 or any(data[k] != manifest[k] for k in ("firstYear", "lastYear")):
            raise ValueError("Country metadata mismatch")
        if set(data["subdivisions"]) != set(entry["subdivisions"]):
            raise ValueError("Subdivision mismatch")
        for mapping in [data["national"], *(p["days"] for p in data["subdivisions"].values())]:
            for day, value in mapping.items():
                validate_date(day, data["firstYear"], data["lastYear"])
                names(value)
        for patch in data["subdivisions"].values():
            for day in patch["removed"]:
                if day not in data["national"]:
                    raise ValueError("Removal without national holiday")
    if not (target / "LICENSES.txt").read_text().strip():
        raise ValueError("Missing licenses")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("generate", "validate"))
    parser.add_argument("--output", type=Path, default=ROOT / "public")
    parser.add_argument("--year", type=int, default=datetime.now(timezone.utc).year)
    args = parser.parse_args()
    generate(args.output, args.year) if args.command == "generate" else validate(args.output)
