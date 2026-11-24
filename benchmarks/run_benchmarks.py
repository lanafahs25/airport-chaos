"""Benchmarks for Airport Chaos.

Run from the project root:   python benchmarks/run_benchmarks.py
Quick smoke run:             python benchmarks/run_benchmarks.py --quick

Writes CSV results to benchmarks/results/ and plots to benchmarks/plots/.
Each timing is the median of REPEATS runs. All synthetic data uses fixed seeds.
"""
import csv
import os
import platform
import random
import statistics
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from airport.flight import Flight
from airport.registry import HashRegistry
from airport.bst import RunwayBST
from airport.sorting import counting_sort_priority, radix_sort_ids
from airport.matrix import classical_multiply, strassen_multiply

QUICK = "--quick" in sys.argv
REPEATS = 1 if QUICK else 5
HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
PLOTS = os.path.join(HERE, "plots")
os.makedirs(RESULTS, exist_ok=True)
os.makedirs(PLOTS, exist_ok=True)

DAY = datetime(2026, 11, 27)
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# ------------------------------------------------------------------ synthetic data
def synthetic_flights(n, runways=5, seed=0, shuffle=True):
    """n non-overlapping 5-minute flights spread over `runways` runways, random IDs.
    With shuffle=False they come out in start-time order (used for the sorted-input case)."""
    rng = random.Random(seed)
    flights, used = [], set()
    per_runway = (n + runways - 1) // runways
    for r in range(runways):
        for k in range(per_runway):
            if len(flights) == n:
                break
            while True:
                fid = rng.choice(LETTERS) + rng.choice(LETTERS) + str(rng.randint(10000, 99999))
                if fid not in used:
                    used.add(fid)
                    break
            start = DAY + timedelta(minutes=7 * k)
            flights.append(Flight(fid, fid[:2], "AAA", "BBB", f"R{r + 1}",
                                  start, start + timedelta(minutes=5), rng.randint(1, 3)))
    if shuffle:
        rng.shuffle(flights)
    return flights


def timed(fn):
    runs = []
    for _ in range(REPEATS):
        t0 = time.perf_counter()
        fn()
        runs.append(time.perf_counter() - t0)
    return statistics.median(runs)


def write(name, header, rows):
    with open(os.path.join(RESULTS, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  wrote results/{name}")


# ------------------------------------------------------------------ 1. hash lookups vs load factor
class FixedSizeRegistry(HashRegistry):
    """Benchmark-only: disables resizing so a chosen load factor can be measured."""
    def _resize(self):
        pass


def bench_hash():
    print("hash lookups vs load factor")
    m = 1024 if QUICK else 8192
    flights = synthetic_flights(int(0.95 * m), seed=1)
    rows = []
    for alpha in (0.25, 0.5, 0.7, 0.9):
        n = int(alpha * m)
        reg = FixedSizeRegistry(m=m)
        for f in flights[:n]:
            reg.insert(f)
        present = [f.flight_id for f in flights[:n]]
        absent = [f"ZZ{i:05d}" for i in range(n)]

        def probes_for(ids):
            total = 0
            for fid in ids:
                total += reg.lookup(fid)[1]
            return total / len(ids)

        hit_probes, miss_probes = probes_for(present), probes_for(absent)
        t = timed(lambda: [reg.lookup(fid) for fid in present])
        rows.append([alpha, n, m, round(hit_probes, 3), round(miss_probes, 3),
                     round(0.5 * (1 + 1 / (1 - alpha)), 3),
                     round(0.5 * (1 + 1 / (1 - alpha) ** 2), 3),
                     round(t / n * 1e6, 3)])
    write("hash_load_factor.csv",
          ["load_factor", "n", "m", "avg_probes_hit", "avg_probes_miss",
           "theory_hit", "theory_miss", "us_per_lookup"], rows)
    return rows


# ------------------------------------------------------------------ 2. BST sorted vs shuffled
def bench_bst():
    print("BST: sorted vs shuffled insertion")
    sizes = (250, 500, 1000) if QUICK else (500, 1000, 2000, 4000)
    rows = []
    for n in sizes:
        flights = synthetic_flights(n, runways=1, seed=2)
        ordered = synthetic_flights(n, runways=1, seed=2, shuffle=False)
        for label, data in (("shuffled", flights), ("sorted", ordered)):
            def build():
                t = RunwayBST()
                for f in data:
                    t.insert(f)
                return t
            t_ins = timed(build)
            tree = build()
            keys = [(f.start, f.flight_id) for f in data]
            t_search = timed(lambda: [tree.search(k) for k in keys])
            rows.append([n, label, tree.height(), round(t_ins * 1e3, 3), round(t_search * 1e3, 3)])
    write("bst_sorted_vs_shuffled.csv",
          ["n", "order", "height", "insert_ms", "search_all_ms"], rows)
    return rows


# ------------------------------------------------------------------ 3. sorting vs comparison baseline
def merge_sort(items, key):
    """Comparison-sort baseline (stable merge sort), written for the benchmark."""
    if len(items) <= 1:
        return items
    mid = len(items) // 2
    left, right = merge_sort(items[:mid], key), merge_sort(items[mid:], key)
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if key(right[j]) < key(left[i]):
            out.append(right[j]); j += 1
        else:
            out.append(left[i]); i += 1
    out.extend(left[i:]); out.extend(right[j:])
    return out


def bench_sorting():
    print("counting / radix sort vs merge sort")
    sizes = (1000, 5000) if QUICK else (1000, 5000, 10000, 50000, 100000)
    rows = []
    for n in sizes:
        flights = synthetic_flights(n, seed=3)
        rows.append([n,
                     round(timed(lambda: counting_sort_priority(flights)) * 1e3, 3),
                     round(timed(lambda: merge_sort(flights, lambda f: f.priority)) * 1e3, 3),
                     round(timed(lambda: radix_sort_ids(flights)) * 1e3, 3),
                     round(timed(lambda: merge_sort(flights, lambda f: f.flight_id)) * 1e3, 3)])
    write("sorting.csv",
          ["n", "counting_ms", "merge_by_priority_ms", "radix_ms", "merge_by_id_ms"], rows)
    return rows


# ------------------------------------------------------------------ 4. classical vs Strassen
def bench_matrix():
    print("classical vs Strassen")
    sizes = (16, 32, 64) if QUICK else (16, 32, 64, 128, 256)
    rng = random.Random(4)
    rows = []
    for n in sizes:
        A = [[rng.randint(0, 9) for _ in range(n)] for _ in range(n)]
        B = [[rng.randint(0, 9) for _ in range(n)] for _ in range(n)]
        assert strassen_multiply(A, B, cutoff=32) == classical_multiply(A, B)
        reps = 1 if n >= 256 else REPEATS
        t_c = statistics.median([_once(lambda: classical_multiply(A, B)) for _ in range(reps)])
        t_s = statistics.median([_once(lambda: strassen_multiply(A, B, cutoff=32)) for _ in range(reps)])
        t_s1 = statistics.median([_once(lambda: strassen_multiply(A, B, cutoff=1)) for _ in range(reps)]) \
            if n <= 64 else ""
        rows.append([n, round(t_c * 1e3, 2), round(t_s * 1e3, 2),
                     round(t_s1 * 1e3, 2) if t_s1 != "" else ""])
    write("matrix.csv", ["n", "classical_ms", "strassen_cutoff32_ms", "strassen_cutoff1_ms"], rows)
    return rows


def _once(fn):
    t0 = time.perf_counter()
    fn()
    return time.perf_counter() - t0


# ------------------------------------------------------------------ plots
def plot_all(hash_rows, bst_rows, sort_rows, mat_rows):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not installed: skipping plots")
        return

    def save(fig, name):
        fig.tight_layout()
        fig.savefig(os.path.join(PLOTS, name), dpi=150)
        plt.close(fig)
        print(f"  wrote plots/{name}")

    fig, ax = plt.subplots(figsize=(5, 3.4))
    a = [r[0] for r in hash_rows]
    ax.plot(a, [r[3] for r in hash_rows], "o-", label="measured (hit)")
    ax.plot(a, [r[5] for r in hash_rows], "--", label="theory (hit)")
    ax.plot(a, [r[4] for r in hash_rows], "s-", label="measured (miss)")
    ax.plot(a, [r[6] for r in hash_rows], ":", label="theory (miss)")
    ax.set_xlabel("load factor α"); ax.set_ylabel("average probes"); ax.legend()
    ax.set_title("Linear probing: probes vs load factor")
    save(fig, "hash_load_factor.png")

    fig, ax = plt.subplots(figsize=(5, 3.4))
    for label, marker in (("shuffled", "o-"), ("sorted", "s-")):
        rows = [r for r in bst_rows if r[1] == label]
        ax.plot([r[0] for r in rows], [r[3] for r in rows], marker, label=f"{label} insert")
    ax.set_xlabel("flights n"); ax.set_ylabel("time to insert all (ms)"); ax.legend()
    ax.set_title("Unbalanced BST: sorted vs shuffled input")
    save(fig, "bst_sorted_vs_shuffled.png")

    fig, ax = plt.subplots(figsize=(5, 3.4))
    n = [r[0] for r in sort_rows]
    ax.plot(n, [r[1] for r in sort_rows], "o-", label="counting sort (priority)")
    ax.plot(n, [r[2] for r in sort_rows], "o--", label="merge sort (priority)")
    ax.plot(n, [r[3] for r in sort_rows], "s-", label="radix sort (ID)")
    ax.plot(n, [r[4] for r in sort_rows], "s--", label="merge sort (ID)")
    ax.set_xlabel("flights n"); ax.set_ylabel("time (ms)"); ax.legend()
    ax.set_title("Non-comparison sorts vs merge sort")
    save(fig, "sorting.png")

    fig, ax = plt.subplots(figsize=(5, 3.4))
    n = [r[0] for r in mat_rows]
    ax.plot(n, [r[1] for r in mat_rows], "o-", label="classical")
    ax.plot(n, [r[2] for r in mat_rows], "s-", label="Strassen (cutoff 32)")
    ax.set_xscale("log", base=2); ax.set_yscale("log")
    ax.set_xlabel("matrix size N"); ax.set_ylabel("time (ms)"); ax.legend()
    ax.set_title("Classical vs Strassen multiplication")
    save(fig, "matrix.png")


def main():
    env = [["python", platform.python_version()],
           ["implementation", platform.python_implementation()],
           ["os", platform.platform()],
           ["machine", platform.machine()],
           ["processor", platform.processor() or "unknown"],
           ["repeats (median of)", REPEATS],
           ["date", datetime.now().strftime("%Y-%m-%d %H:%M")]]
    write("environment.csv", ["field", "value"], env)
    h = bench_hash()
    b = bench_bst()
    s = bench_sorting()
    m = bench_matrix()
    plot_all(h, b, s, m)
    print("done")


if __name__ == "__main__":
    main()
