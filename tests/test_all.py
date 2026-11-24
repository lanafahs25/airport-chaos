"""Automated tests for Airport Chaos. Run with:  python -m unittest -v"""
import os
import random
import unittest
from datetime import datetime, timedelta

from airport.flight import Flight
from airport.loader import load_flights, parse_time, LoadError
from airport.registry import HashRegistry
from airport.bst import RunwayBST
from airport.engine import Engine
from airport.sorting import counting_sort_priority, radix_sort_ids
from airport.analysis import find_max_subarray, max_subarray_brute, analyze
from airport.matrix import classical_multiply, strassen_multiply
from airport.perfect_hash import PerfectHash, RULE_IDS

HERE = os.path.dirname(__file__)
OFFICIAL = os.path.join(HERE, "..", "data", "airport_flights.csv")
MINI = os.path.join(HERE, "mini.csv")
OVERLAP = os.path.join(HERE, "overlap.csv")


def T(h, m):
    return datetime(2026, 11, 27, h, m)


def mk(fid, runway="R1", start=(9, 0), end=(9, 5), priority=1):
    return Flight(fid, "XX", "AAA", "BBB", runway, T(*start), T(*end), priority)


def fresh_engine():
    e = Engine()
    e.load(OFFICIAL)
    return e


# ------------------------------------------------------------------ loader
class TestLoader(unittest.TestCase):
    def test_official_file_loads_1000(self):
        flights, errors = load_flights(OFFICIAL)
        self.assertEqual(len(flights), 1000)
        self.assertEqual(errors, [])

    def test_duplicate_and_bad_rows_reported(self):
        flights, errors = load_flights(MINI)
        self.assertEqual(len(flights), 2)
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("duplicate" in e for e in errors))

    def test_malformed_timestamp_raises(self):
        with self.assertRaises(LoadError):
            parse_time("2026-11-27 25:00", 5, "start_time")


# ------------------------------------------------------------------ registry (A)
class TestRegistry(unittest.TestCase):
    def test_duplicate_and_missing_ids(self):
        r = HashRegistry()
        self.assertTrue(r.insert(mk("A1")))
        self.assertFalse(r.insert(mk("A1")))
        self.assertIsNone(r.lookup("NOPE")[0])

    def test_collisions_tombstones_and_resize(self):
        r = HashRegistry()
        for n in range(200):
            r.insert(mk(f"T{n:04d}"))
        self.assertEqual(r.size, 200)
        self.assertLessEqual(r.load_factor(), 0.6)
        self.assertGreater(r.collisions, 0)
        for n in range(0, 200, 2):
            self.assertTrue(r.delete(f"T{n:04d}"))
        self.assertEqual(r.size, 100)
        self.assertEqual(r.tombstones, 100)
        for n in range(200):                              # lookups walk past tombstones
            found = r.lookup(f"T{n:04d}")[0]
            self.assertEqual(found is None, n % 2 == 0)
        self.assertFalse(r.delete("T0000"))               # already deleted

    def test_insert_reuses_tombstone(self):
        r = HashRegistry()
        for n in range(9):
            r.insert(mk(f"T{n}"))
        r.delete("T3")
        self.assertEqual(r.tombstones, 1)
        self.assertTrue(r.insert(mk("T3")))
        self.assertEqual((r.size, r.tombstones), (9, 0))


# ------------------------------------------------------------------ BST (B)
class TestBST(unittest.TestCase):
    def setUp(self):
        self.r1 = [f for f in load_flights(OFFICIAL)[0] if f.runway == "R1"]
        self.tree = RunwayBST()
        for f in self.r1:
            self.tree.insert(f)

    def test_root_deletion_with_two_children(self):
        root = self.tree.root
        self.assertIsNotNone(root.left)
        self.assertIsNotNone(root.right)
        key = root.key
        self.tree.delete(root)
        self.assertIsNone(self.tree.search(key))
        self.assertIsNone(self.tree.root.parent)
        out = self.tree.inorder()
        self.assertEqual(len(out), 199)
        self.assertTrue(all(out[i].start <= out[i + 1].start for i in range(198)))

    def test_successor_and_predecessor_walks(self):
        order = self.tree.inorder()
        walk, x = [], self.tree.minimum(self.tree.root)
        while x is not None:
            walk.append(x.flight)
            x = self.tree.successor(x)
        self.assertEqual(walk, order)
        back, x = [], self.tree.maximum(self.tree.root)
        while x is not None:
            back.append(x.flight)
            x = self.tree.predecessor(x)
        self.assertEqual(back, order[::-1])

    def test_range_search_matches_filter(self):
        got = self.tree.range_search(T(14, 0), T(15, 0))
        want = [f for f in self.tree.inorder() if T(14, 0) <= f.start < T(15, 0)]
        self.assertEqual(got, want)

    def test_exact_boundary_does_not_conflict(self):
        t = RunwayBST()
        t.insert(mk("A", start=(9, 15), end=(9, 20)))
        ids = lambda s, e: [f.flight_id for f in t.conflicts(T(*s), T(*e))]
        self.assertEqual(ids((9, 20), (9, 25)), [])       # starts as A ends
        self.assertEqual(ids((9, 10), (9, 15)), [])       # ends as A starts
        self.assertEqual(ids((9, 18), (9, 23)), ["A"])    # real overlap
        self.assertEqual(ids((9, 15), (9, 20)), ["A"])    # listed once


# ------------------------------------------------------------------ engine sync
class TestEngine(unittest.TestCase):
    def test_overlap_rejected_and_runways_independent(self):
        e = Engine()
        n, errors = e.load(OVERLAP)
        self.assertEqual(n, 3)                            # A000002 overlaps on R1
        self.assertIsNone(e.find("A000002")[0])
        self.assertIsNotNone(e.find("A000004")[0])        # same time, other runway
        self.assertEqual(e.check_consistency(), [])

    def test_conflicting_insert_is_rejected(self):
        e = fresh_engine()
        f = e.find("B610505")[0]
        clash = Flight("NEW0001", "XX", "AAA", "BBB", f.runway,
                       f.start + timedelta(minutes=2), f.end + timedelta(minutes=2), 1)
        ok, msg, clashes = e.add(clash)
        self.assertFalse(ok)
        self.assertIn("B610505", [c.flight_id for c in clashes])
        self.assertIsNone(e.find("NEW0001")[0])

    def test_consistency_after_mixed_updates(self):
        e = fresh_engine()
        f = e.find("B610505")[0]
        e.cancel("DL10872")
        e.reschedule("B610505", f.start + timedelta(minutes=1))
        other = [x for x in e.runways[f.runway].inorder() if x is not f][0]
        before = f.start
        ok, _, _ = e.reschedule("B610505", other.start)   # must roll back
        self.assertFalse(ok)
        self.assertEqual(f.start, before)
        e.add(mk("NEW0002", runway="R9"))
        self.assertEqual(e.check_consistency(), [])


# ------------------------------------------------------------------ scenarios (C), fresh load each
class TestScenarios(unittest.TestCase):
    def test_scenario_a_runway_closure(self):
        e = fresh_engine()
        rows, n, d, c, mins = e.runway_closure("R1", T(9, 0), T(11, 0))
        self.assertEqual((n, d, c, mins), (18, 1, 17, 114))
        self.assertEqual(rows[0][0], "BA10079")
        self.assertEqual(rows[0][2], T(11, 0))
        self.assertEqual(e.runways["R1"].size, 183)
        self.assertEqual(e.check_consistency(), [])

    def test_scenario_b_emergency_insert(self):
        e = fresh_engine()
        em = lambda: Flight("EM90001", "EM", "JFK", "BOS", "R1", T(9, 0), T(9, 5), 1)
        ok, msg, clashes, slot = e.emergency_insert(em(), False)
        self.assertFalse(ok)
        self.assertEqual([c.flight_id for c in clashes], ["F910078"])
        self.assertEqual(slot, T(23, 20))
        self.assertIsNone(e.find("EM90001")[0])           # not inserted without ACCEPT
        ok, msg, clashes, slot = e.emergency_insert(em(), True)
        self.assertTrue(ok)
        self.assertEqual(e.find("EM90001")[0].start, T(23, 20))
        self.assertEqual(e.check_consistency(), [])

    def test_scenario_c_mass_cancel(self):
        e = fresh_engine()
        ids = e.mass_cancel(T(14, 0), T(15, 0))
        self.assertEqual(len(ids), 45)
        self.assertEqual(sum(t.size for t in e.runways.values()), 955)
        self.assertEqual(e.find(ids[0])[0].status, "CANCELLED")
        self.assertEqual(e.check_consistency(), [])


# ------------------------------------------------------------------ sorting (D)
class TestSorting(unittest.TestCase):
    def test_counting_sort_is_sorted_and_stable(self):
        flights = load_flights(OFFICIAL)[0]
        out = counting_sort_priority(flights)
        pos = {f.flight_id: i for i, f in enumerate(flights)}
        self.assertTrue(all(out[i].priority <= out[i + 1].priority for i in range(999)))
        self.assertTrue(all(pos[out[i].flight_id] < pos[out[i + 1].flight_id]
                            for i in range(999) if out[i].priority == out[i + 1].priority))

    def test_radix_sort_exact_order_and_lengths(self):
        flights = load_flights(OFFICIAL)[0]
        ids = [f.flight_id for f in radix_sort_ids(flights)]
        self.assertTrue(all(ids[i] < ids[i + 1] for i in range(len(ids) - 1)))
        mixed = [mk("ABC"), mk("AB"), mk("B"), mk("A1")]
        self.assertEqual([f.flight_id for f in radix_sort_ids(mixed)], ["A1", "AB", "ABC", "B"])


# ------------------------------------------------------------------ max subarray (E)
class TestMaxSubarray(unittest.TestCase):
    def test_clrs_example(self):
        A = [13, -3, -25, 20, -3, -16, -23, 18, 20, -7, 12, -5, -22, 15, -4, 7]
        self.assertEqual(find_max_subarray(A, 0, len(A) - 1), (7, 10, 43))

    def test_matches_quadratic_reference(self):
        rng = random.Random(3)
        for _ in range(200):
            A = [rng.randint(-20, 20) for _ in range(rng.randint(1, 40))]
            self.assertEqual(find_max_subarray(A, 0, len(A) - 1)[2], max_subarray_brute(A)[2])

    def test_all_zero_and_after_closure(self):
        e = fresh_engine()
        self.assertIsNone(analyze(e.registry.all_flights())["result"])
        e.runway_closure("R1", T(9, 0), T(11, 0))
        r = analyze(e.registry.all_flights())
        self.assertEqual(r["result"], (107, 131, 18))
        self.assertTrue(r["matches"])


# ------------------------------------------------------------------ matrices (F)
class TestMatrices(unittest.TestCase):
    def test_strassen_matches_classical_odd_and_even(self):
        rng = random.Random(1)
        for n in (1, 2, 3, 5, 7, 8, 13, 16, 33):
            A = [[rng.randint(-9, 9) for _ in range(n)] for _ in range(n)]
            B = [[rng.randint(-9, 9) for _ in range(n)] for _ in range(n)]
            self.assertEqual(strassen_multiply(A, B, cutoff=1), classical_multiply(A, B), n)


# ------------------------------------------------------------------ perfect hashing (G)
class TestPerfectHash(unittest.TestCase):
    def test_present_absent_and_storage(self):
        ph = PerfectHash(RULE_IDS)
        self.assertTrue(all(ph.contains(k) for k in RULE_IDS))
        for k in (100, 102, 284, 999):
            self.assertFalse(ph.contains(k))
        self.assertLessEqual(ph.storage(), 5 * len(RULE_IDS))


if __name__ == "__main__":
    unittest.main()
