import pathlib
import sqlite3
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import router_log as R  # noqa: E402


def _mem(margin=0.2):
    return R.RouterLog(conn=sqlite3.connect(":memory:"), tie_margin=margin)


class RouterLogTest(unittest.TestCase):
    def test_clear_winner_not_tie(self):
        with _mem() as rl:
            d = rl.log("deploy nginx ke vps", {"m2": 10, "m16": 3})
            self.assertEqual(d.primary, "m2")
            self.assertFalse(d.was_tie)

    def test_close_scores_is_tie(self):
        with _mem() as rl:
            d = rl.log("bulk scrape api", {"m30": 9, "m12": 8})
            self.assertTrue(d.was_tie)
            self.assertEqual(d.runner_up, "m12")

    def test_tune_report_groups_pairs(self):
        with _mem() as rl:
            rl.log("bulk a", {"m30": 9, "m12": 8})
            rl.log("bulk b", {"m12": 9, "m30": 8})   # urutan kebalik → pair sama
            rl.log("clear", {"m2": 10, "m1": 1})
            pairs = rl.tune_report(min_ties=2)
            self.assertEqual(len(pairs), 1)
            self.assertEqual({pairs[0].a, pairs[0].b}, {"m12", "m30"})
            self.assertEqual(pairs[0].ties, 2)

    def test_stats(self):
        with _mem() as rl:
            rl.log("x", {"m1": 10, "m2": 1})
            rl.log("y", {"m1": 9, "m2": 8})
            st = rl.stats()
            self.assertEqual(st["total"], 2)
            self.assertEqual(st["ties"], 1)
            self.assertEqual(st["tie_rate"], 0.5)

    def test_empty_scores_no_crash(self):
        with _mem() as rl:
            d = rl.log("hmm", {})
            self.assertEqual(d.primary, "")
            self.assertFalse(d.was_tie)


if __name__ == "__main__":
    unittest.main()
