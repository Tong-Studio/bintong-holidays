import json
import sys
import unittest
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from holiday_data import ROOT, apply_overrides, read, validate, validate_overrides, generate, write


class HolidayTests(unittest.TestCase):
    def test_entire_snapshot_and_known_holidays(self):
        validate(ROOT / "public")
        manifest = read(ROOT / "public/v1/manifest.json")
        for country, day in [("KR", "2024-10-09"), ("JP", "2024-05-04"), ("US", "2024-07-04")]:
            data = read(ROOT / "public" / manifest["countries"][country]["path"])
            self.assertIn(day, data["national"])
        kr = read(ROOT / "public" / manifest["countries"]["KR"]["path"])
        self.assertNotIn("2024-04-05", kr["national"])
        self.assertNotIn("2024-07-17", kr["national"])

    def test_subdivision_and_correction_precedence(self):
        base = {"2026-10-01": {"en": "Original"}}
        items = [dict(country="US", date="2026-10-01", action="remove"),
                 dict(country="US", subdivision="CA", date="2026-10-01", action="add", names={"en": "Local"})]
        self.assertEqual(apply_overrides(base, items, "US", None, 2030), {})
        self.assertEqual(apply_overrides(base, items, "US", "CA", 2030)["2026-10-01"]["en"], "Local")
        self.assertEqual(apply_overrides(base, items, "US", "NY", 2030), {})

    def test_rolling_year_determinism_retention_and_removed_country_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'public'
            generate(target, 2026)
            first = read(target / 'v1/manifest.json')
            generate(target, 2026)
            self.assertEqual(first, read(target / 'v1/manifest.json'))
            for year in (2027, 2028, 2029):
                generate(target, year)
            current = read(target / 'v1/manifest.json')
            self.assertEqual(current['lastYear'], 2033)
            self.assertEqual(len(list((target / 'v1/releases').glob('*.json'))), 3)
            self.assertFalse((target / f"v1/releases/{first['dataVersion']}.json").exists())
            for release in (target / 'v1/releases').glob('*.json'):
                for entry in read(release)['countries'].values():
                    self.assertTrue((target / entry['path']).exists())
            current['countries']['ZZ'] = current['countries']['KR']
            write(target / 'v1/manifest.json', current)
            with self.assertRaises(ValueError):
                generate(target, 2029)

    def test_conflicts_and_missing_evidence_rejected(self):
        item = dict(country="KR", date="2026-10-01", action="add", names={"en": "Fixture"},
                    sourceUrl="https://example.gov/announcement", reason="Test fixture only")
        validate_overrides([item], {"KR": []})
        with self.assertRaises(ValueError):
            validate_overrides([item, item], {"KR": []})
        with self.assertRaises(ValueError):
            validate_overrides([{**item, "sourceUrl": ""}], {"KR": []})


if __name__ == "__main__":
    unittest.main()
