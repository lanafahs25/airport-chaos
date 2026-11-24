# Ground Stop Scheduler — Airport Chaos (CSC310)

A command-line airport scheduling and crisis-recovery engine. It loads the
official flight file, keeps every runway conflict-free, handles runway
closures, emergency inserts and mass cancellations, and implements the
course algorithms from scratch: universal hashing with open addressing,
unbalanced BSTs, counting and radix sort, divide-and-conquer maximum
subarray, Strassen multiplication and FKS perfect hashing.

Lana Fahs · CSC310 Algorithms and Data Structures · Dr. Mohamed Watfa · solo project (approved)

## Setup

Python 3.10 or newer.

```bash
pip install -r requirements.txt        # only Typer, for the command-line entry point
```

## Running

All commands are run from the project root.

```bash
python cli.py menu                                   # interactive numbered menu
python cli.py batch scenarios/scenario_a.txt         # run a file of commands
python cli.py run "FIND B610505"                     # load the official CSV, run one command
python cli.py --help
```

In the menu, pick an option by number, or type any command directly.

### Optional GUI

```bash
python gui/app.py
```

Tkinter (bundled with Python): runway timelines, the three scenarios, sortable
flight table, disruption chart, route heatmap (A and A² via Strassen) and
statistics. It only calls the engine; no algorithm logic lives in the GUI.

## Commands

Timestamps are written `"YYYY-MM-DD HH:MM"` (quoted, because they contain a space).
Intervals are half-open `[start, end)`.

| Command | Syntax | What it does |
|---|---|---|
| LOAD | `LOAD path` | Load a CSV (resets all state) |
| STATS | `STATS` | Hash-table statistics and runway tree sizes/heights |
| FIND | `FIND id` | Look up a flight in the hash registry (shows probes) |
| LIST_RUNWAY | `LIST_RUNWAY R1` | Active flights on a runway in time order |
| ADD | `ADD id airline origin dest runway "start" "end" priority` | Add a flight if its slot is free |
| CANCEL | `CANCEL id` | Cancel a flight (kept in the registry) |
| RESCHEDULE | `RESCHEDULE id "new start"` | Move a flight on its runway, same duration |
| CHECK_CONFLICT | `CHECK_CONFLICT R1 "start" "end"` | List flights overlapping an interval |
| RUNWAY_CLOSURE | `RUNWAY_CLOSURE R1 "start" "end"` | Scenario A: close a runway and recover |
| EMERGENCY_INSERT | `EMERGENCY_INSERT id airline origin dest runway "start" "end" priority [ACCEPT]` | Scenario B: report conflicts and offer a slot; inserts only with `ACCEPT` |
| MASS_CANCEL | `MASS_CANCEL "start" "end"` | Scenario C: cancel all flights starting in the window |
| SORT_PRIORITY | `SORT_PRIORITY [n]` | Counting sort by priority (shows first n) |
| SORT_ID | `SORT_ID [n]` | LSD radix sort by flight ID |
| SORT_DEMO | `SORT_DEMO` | Stability example: sort by ID, then by priority |
| ANALYZE | `ANALYZE` | Maximum-subarray disruption analysis (D&C vs O(n²) check) |
| MATRIX | `MATRIX` | Route-count matrix A×A, classical vs Strassen |
| RULES | `RULES [id ...]` | FKS perfect-hash table of the 20 rule IDs, with lookups |
| TRACE | `TRACE ON` / `TRACE OFF` | Show hash probes, BST paths/neighbours and sorting passes |
| HELP / QUIT | | |

## Official scenarios

Each scenario file starts with `LOAD`, so it always runs from a fresh state.

```bash
python cli.py batch scenarios/scenario_a.txt    # RUNWAY_CLOSURE R1 09:00–11:00
python cli.py batch scenarios/scenario_b.txt    # EMERGENCY_INSERT EM90001 R1 09:00
python cli.py batch scenarios/scenario_c.txt    # MASS_CANCEL 14:00–15:00
python cli.py batch scenarios/analyze_a.txt     # disruption analysis after scenario A
```

## Tests

```bash
python -m unittest -v
```

23 automated tests: CSV parsing and duplicates, malformed timestamps, hash
collisions/tombstones/resize, BST root deletion, predecessor/successor,
exact-boundary non-overlap, cross-runway independence, conflict rejection,
the three official scenarios from a fresh load, sorting stability, maximum
subarray against the O(n²) reference, Strassen on odd sizes, registry/BST
consistency after updates, and perfect hashing.

## Benchmarks

```bash
python benchmarks/run_benchmarks.py            # full run (a few minutes)
python benchmarks/run_benchmarks.py --quick    # small smoke run
```

Results go to `benchmarks/results/*.csv` (including the environment), plots to
`benchmarks/plots/*.png`. Synthetic data uses fixed seeds; the official CSV is
only used for correctness.

## Layout

```
airport/      flight.py, loader.py, registry.py, bst.py, engine.py,
              sorting.py, analysis.py, matrix.py, perfect_hash.py, trace.py
gui/          app.py (optional Tkinter GUI)
cli.py        command parser, numbered menu, batch runner (Typer entry point)
data/         airport_flights.csv (official file, unchanged)
scenarios/    official scenario batch files
tests/        test_all.py + small CSVs for edge cases
benchmarks/   run_benchmarks.py, results/, plots/
report/       main.tex, main.pdf
```
