import json
import threading
import unittest
import urllib.request

from assetscan.io import read_csv_text
from assetscan.scan import Asset, analyze, analyze_asset
from assetscan.server import make_server
from assetscan.stats import geometric_blend, n_for_margin, wilson


class Stats(unittest.TestCase):
    def test_wilson_reference(self):
        lo, hi = wilson(8, 10)  # published value: 0.490 to 0.943
        self.assertAlmostEqual(lo, 0.490, places=3)
        self.assertAlmostEqual(hi, 0.943, places=3)

    def test_wilson_edges(self):
        self.assertEqual(wilson(0, 0), (0.0, 1.0))
        lo, hi = wilson(0, 50)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.0)

    def test_sample_size(self):
        self.assertEqual(n_for_margin(0.05), 385)

    def test_blend_needs_both(self):
        self.assertEqual(geometric_blend(0.9, 0.0), 0.0)
        self.assertAlmostEqual(geometric_blend(0.64, 0.25), 0.4)


class Scan(unittest.TestCase):
    def test_fame_uniqueness_score(self):
        r = analyze_asset(Asset("logo", 400, 200, {"A": 50, "B": 50}))
        self.assertAlmostEqual(r["fame"], 0.5)
        self.assertAlmostEqual(r["uniqueness"], 2 / 3)
        self.assertAlmostEqual(r["score"], 100 * (0.5 * 2 / 3) ** 0.5)
        self.assertEqual(r["quadrant"], "use")

    def test_quadrants(self):
        self.assertEqual(analyze_asset(Asset("a", 200, 70, {"A": 90}))["quadrant"], "avoid")
        self.assertEqual(analyze_asset(Asset("a", 100, 20, {"A": 2}))["quadrant"], "invest")
        self.assertEqual(analyze_asset(Asset("a", 100, 10, {"A": 40}))["quadrant"], "test")

    def test_nobody_linked_it(self):
        r = analyze_asset(Asset("ghost", 200, 0))
        self.assertEqual(r["score"], 0.0)
        self.assertTrue(any("Nobody" in n for n in r["notes"]))

    def test_interval_brackets_score_and_is_deterministic(self):
        a = Asset("x", 300, 120, {"A": 40})
        r1, r2 = analyze_asset(a), analyze_asset(a)
        self.assertEqual(r1["score_ci"], r2["score_ci"])
        self.assertLess(r1["score_ci"][0], r1["score"])
        self.assertGreater(r1["score_ci"][1], r1["score"])
        self.assertAlmostEqual(sum(r1["quadrant_probs"].values()), 1.0)

    def test_small_sample_widens_interval(self):
        big = analyze_asset(Asset("x", 1000, 400, {"A": 100}))
        small = analyze_asset(Asset("x", 50, 20, {"A": 5}))
        self.assertGreater(small["score_ci"][1] - small["score_ci"][0], big["score_ci"][1] - big["score_ci"][0])
        self.assertEqual(small["confidence"], "thin")

    def test_validation(self):
        with self.assertRaises(ValueError):
            analyze_asset(Asset("x", 100, 80, {"A": 40}))
        with self.assertRaises(ValueError):
            analyze([Asset("x", 10, 1), Asset("X", 10, 1)])
        with self.assertRaises(ValueError):
            analyze([])

    def test_ranking(self):
        res = analyze([Asset("weak", 100, 10, {"A": 40}), Asset("strong", 100, 70, {"A": 5})])
        self.assertEqual(res["assets"][0]["name"], "strong")


class V02(unittest.TestCase):
    def test_checklist_score_ignores_unverified(self):
        a = Asset("x", 200, 100, {"A": 20}, checks={"sound": True, "name": True, "context": False, "consistent": None, "instant": None}, used=5, total=10)
        c = analyze_asset(a)["checklist"]
        self.assertEqual((c["passed"], c["failed"], c["unverified"]), (2, 1, 2))
        self.assertAlmostEqual(c["score"], 100 * (2 / 3 + 0.5) / 2)

    def test_no_audit_means_no_checklist(self):
        self.assertIsNone(analyze_asset(Asset("x", 200, 100))["checklist"])

    def test_touchpoints_cannot_exceed_audited(self):
        with self.assertRaises(ValueError):
            analyze_asset(Asset("x", 200, 100, used=11, total=10))

    def test_drift_note(self):
        a = Asset("x", 200, 120, {"A": 10}, checks={k: False for k in ("sound", "name", "context", "consistent", "instant")}, used=1, total=10)
        self.assertTrue(any("poorly deployed" in n for n in analyze_asset(a)["notes"]))

    def test_segments_pool_and_split(self):
        res = analyze([Asset("x", 200, 150, {"A": 10}, segment="buyers"), Asset("x", 200, 50, {"A": 30}, segment="non-buyers")])
        r = res["assets"][0]
        self.assertEqual((r["n"], r["brand"], r["rivals"]), (400, 200, 40))
        self.assertEqual({s["segment"]: round(s["fame"], 2) for s in r["segments"]}, {"buyers": 0.75, "non-buyers": 0.25})
        self.assertEqual(res["summary"]["segments"], ["buyers", "non-buyers"])

    def test_duplicate_without_segments_rejected(self):
        with self.assertRaises(ValueError):
            analyze([Asset("x", 10, 1), Asset("x", 10, 1)])

    def test_csv_segments_and_audit(self):
        rows = read_csv_text("asset,segment,respondents,brand,Rival A,check_sound,check_name,touchpoints_used,touchpoints_total\n"
                             "logo,buyers,100,50,10,yes,,4,8")
        a = rows[0]
        self.assertEqual((a.segment, a.checks, a.used, a.total, a.rivals), ("buyers", {"sound": True, "name": None}, 4, 8, {"Rival A": 10}))


class Csv(unittest.TestCase):
    def test_rivals_by_column(self):
        a = read_csv_text("asset,respondents,brand,Rival A,Rival B,prompted\nlogo,400,200,30,0,yes")[0]
        self.assertEqual((a.n, a.brand, a.rivals, a.prompted), (400, 200, {"Rival A": 30}, True))

    def test_bad_header(self):
        with self.assertRaises(ValueError):
            read_csv_text("x,y\n1,2")

    def test_non_integer(self):
        with self.assertRaises(ValueError):
            read_csv_text("asset,respondents,brand\nlogo,400,2.5")


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = make_server(0)
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def post(self, body, host=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/scan", json.dumps(body).encode(),
                                     {"Content-Type": "application/json", **({"Host": host} if host else {})})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    def test_scan(self):
        code, j = self.post({"assets": [{"name": "logo", "n": 400, "brand": 200, "rivals": 50}]})
        self.assertEqual(code, 200)
        self.assertEqual(j["assets"][0]["quadrant"], "use")

    def test_audit_over_api(self):
        code, j = self.post({"assets": [{"name": "logo", "n": 400, "brand": 200, "rivals": 50, "checks": {"sound": "yes", "name": "no"}, "used": 3, "total": 6}]})
        self.assertEqual(code, 200)
        self.assertEqual(j["assets"][0]["checklist"]["passed"], 1)

    def test_error_is_400(self):
        code, j = self.post({"assets": [{"name": "logo", "n": 10, "brand": 20}]})
        self.assertEqual(code, 400)
        self.assertIn("exceed", j["error"])

    def test_rejects_foreign_host(self):
        self.assertEqual(self.post({"assets": []}, host="evil.example")[0], 403)

    def test_serves_ui(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/") as r:
            self.assertIn(b"assetscan", r.read())


if __name__ == "__main__":
    unittest.main()
