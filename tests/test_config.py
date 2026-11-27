import json
import os
import tempfile
import unittest

from aguacate import config


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "Aguacate", "config.json")

    def write(self, text):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(text)

    def test_missing_file_is_created_with_defaults(self):
        cfg, problems = config.load(self.path)
        self.assertEqual(problems, [])
        self.assertEqual(cfg["work_minutes"], 25)
        with open(self.path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["blocked_domains"][0], "youtube.com")

    def test_roundtrip(self):
        cfg, _ = config.load(self.path)
        cfg["work_minutes"] = 50
        cfg["blocked_domains"] = ["reddit.com"]
        cfg["position"] = [10, 20]
        config.save(cfg, self.path)
        again, problems = config.load(self.path)
        self.assertEqual(problems, [])
        self.assertEqual((again["work_minutes"], again["blocked_domains"], again["position"]),
                         (50, ["reddit.com"], [10, 20]))

    def test_broken_json_uses_defaults_and_keeps_file(self):
        self.write('{"work_minutes": 30,,}')
        cfg, problems = config.load(self.path)
        self.assertEqual(cfg["work_minutes"], 25)
        self.assertIn("línea 1", problems[0])
        with open(self.path, encoding="utf-8") as f:
            self.assertEqual(f.read(), '{"work_minutes": 30,,}')

    def test_bad_values_fall_back_one_by_one(self):
        self.write(json.dumps({
            "work_minutes": 500, "break_minutes": 10, "volume": "alto",
            "vibration": "sí", "always_on_top": True,
            "blocked_domains": ["reddit.com", "no es un dominio", "x.com\n1.1.1.1 banco.es"],
        }))
        cfg, problems = config.load(self.path)
        self.assertEqual(cfg["work_minutes"], 25)
        self.assertEqual(cfg["break_minutes"], 10)
        self.assertEqual(cfg["volume"], 0.45)
        self.assertTrue(cfg["vibration"])
        self.assertTrue(cfg["always_on_top"])
        self.assertEqual(cfg["blocked_domains"], ["reddit.com"])
        self.assertEqual(len(problems), 4)

    def test_broken_json_with_fallback_keeps_current(self):
        self.write("{ roto")
        current = dict(config.DEFAULTS, work_minutes=42)
        cfg, problems = config.load(self.path, fallback=current)
        self.assertIs(cfg, current)
        self.assertIn("configuración actual", problems[0])

    def test_bom_from_notepad(self):
        self.write("﻿" + json.dumps({"work_minutes": 40}))
        cfg, problems = config.load(self.path)
        self.assertEqual((cfg["work_minutes"], problems), (40, []))


if __name__ == "__main__":
    unittest.main()
