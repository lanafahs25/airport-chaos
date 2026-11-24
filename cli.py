import shlex
import typer
from datetime import datetime
from airport.engine import Engine
from airport.flight import Flight
from airport.sorting import counting_sort_priority, radix_sort_ids
from airport.analysis import analyze
from airport.matrix import build_route_matrix, classical_multiply, strassen_multiply
from airport.perfect_hash import PerfectHash, RULE_IDS

TIME_FMT = "%Y-%m-%d %H:%M"


def t(s):
    return datetime.strptime(s, TIME_FMT)


def fmt(dt):
    return dt.strftime("%H:%M") if dt else "-----"


def run_command(engine, line):
    parts = shlex.split(line)
    if len(parts) == 0 or parts[0].startswith("#"):
        return
    cmd, args = parts[0].upper(), parts[1:]

    try:
        if cmd == "LOAD":
            n, errors = engine.load(args[0])
            print(f"Loaded {n} flights, {len(errors)} rejected")
            for err in errors:
                print("  ", err)

        elif cmd == "FIND":
            f, probes = engine.find(args[0])
            if f is None:
                print(f"{args[0]}: not found ({probes} probes)")
            else:
                print(f"{f.flight_id} {f.runway} {fmt(f.start)}-{fmt(f.end)} "
                      f"P{f.priority} {f.status} ({probes} probes)")

        elif cmd == "STATS":
            for k, v in engine.registry.stats().items():
                print(f"  {k}: {v}")
            for name in sorted(engine.runways):
                tree = engine.runways[name]
                print(f"  {name}: {tree.size} active, height {tree.height()}")

        elif cmd == "LIST_RUNWAY":
            name = args[0]
            if name not in engine.runways:
                print(f"No runway called {name}")
            else:
                for f in engine.runways[name].inorder():
                    print(f"{f.flight_id} {fmt(f.start)}-{fmt(f.end)} P{f.priority} {f.status}")

        elif cmd == "CANCEL":
            ok, msg = engine.cancel(args[0])
            print(f"{args[0]}: {msg}")

        elif cmd == "RESCHEDULE":
            ok, msg, clashes = engine.reschedule(args[0], t(args[1]))
            print(f"{args[0]}: {msg}")
            for c in clashes:
                print(f"   conflicts with {c.flight_id} {fmt(c.start)}-{fmt(c.end)}")

        elif cmd == "CHECK_CONFLICT":
            name, s, e2 = args[0], t(args[1]), t(args[2])
            if name not in engine.runways:
                print(f"{name}: no flights, slot is free")
            else:
                clashes = engine.runways[name].conflicts(s, e2)
                if len(clashes) == 0:
                    print(f"{name} {fmt(s)}-{fmt(e2)}: free")
                else:
                    print(f"{name} {fmt(s)}-{fmt(e2)}: conflicts with "
                          + ", ".join(c.flight_id for c in clashes))

        elif cmd == "RUNWAY_CLOSURE":
            rows, n, d, c, mins = engine.runway_closure(args[0], t(args[1]), t(args[2]))
            print(f"{'ID':<9}{'OLD':>6}{'NEW':>7}  STATUS")
            for fid, old, new, st in rows:
                print(f"{fid:<9}{fmt(old):>6}{fmt(new):>7}  {st}")
            print(f"affected {n}, delayed {d}, cancelled {c}, total delay {mins} min")

        elif cmd == "MASS_CANCEL":
            ids = engine.mass_cancel(t(args[0]), t(args[1]))
            print(f"cancelled {len(ids)} flights: " + ", ".join(ids))

        elif cmd in ("ADD", "EMERGENCY_INSERT"):
            fid, airline, origin, dest, runway = args[0:5]
            start, end, prio = t(args[5]), t(args[6]), int(args[7])
            if start >= end or prio not in (1, 2, 3):
                print(f"{cmd}: start must be before end and priority must be 1-3")
            else:
                f = Flight(fid, airline, origin, dest, runway, start, end, prio)
                if cmd == "ADD":
                    ok, msg, clashes = engine.add(f)
                    print(f"{fid}: {msg}")
                    if clashes:
                        print("   conflicts with " + ", ".join(c.flight_id for c in clashes))
                else:
                    accept = len(args) > 8 and args[8].upper() == "ACCEPT"
                    ok, msg, clashes, slot = engine.emergency_insert(f, accept)
                    print(f"{fid}: {msg}")
                    if clashes:
                        print("   conflicts with " + ", ".join(c.flight_id for c in clashes))
                    if slot is not None:
                        print(f"   slot: {fmt(slot)}" + ("" if ok else "  (add ACCEPT to insert)"))

        elif cmd in ("SORT_PRIORITY", "SORT_ID"):
            n = int(args[0]) if args else 10
            flights = engine.registry.all_flights()
            if cmd == "SORT_PRIORITY":
                out = counting_sort_priority(flights)
            else:
                out = radix_sort_ids(flights)
            for f in out[:n]:
                print(f"{f.flight_id}  P{f.priority}  {f.runway} {fmt(f.start)}  {f.status}")
            print(f"... {len(out)} flights sorted")

        elif cmd == "SORT_DEMO":
            by_id = radix_sort_ids(engine.registry.all_flights())
            out = counting_sort_priority(by_id)
            print("Sorted by ID first, then by priority (stable):")
            for f in out[:8]:
                print(f"  P{f.priority}  {f.flight_id}")
            ok = all(out[i].flight_id < out[i + 1].flight_id
                     for i in range(len(out) - 1)
                     if out[i].priority == out[i + 1].priority)
            print(f"IDs stay in order within each priority: {ok}")

        elif cmd == "ANALYZE":
            r = analyze(engine.registry.all_flights())
            if r is None or r["result"] is None:
                print("No disrupted flights: nothing to analyze")
            else:
                s, e2, total = r["result"]
                print(f"Worst disruption on {r['day']}: buckets {s}-{e2} "
                      f"({fmt(r['from'])}-{fmt(r['to'])}), {total} flights")
                print(f"O(n^2) reference agrees: {r['matches']}")


        elif cmd == "MATRIX":
            codes, A = build_route_matrix(engine.registry.all_flights())
            n = len(codes)
            classic = classical_multiply(A, A)
            fast = strassen_multiply(A, A, cutoff=1)
            print(f"{n} airports: {' '.join(codes)}")
            print(f"Strassen matches classical: {classic == fast}")
            pairs = []
            for i in range(n):
                for j in range(n):
                    pairs.append((classic[i][j], codes[i], codes[j]))
            best = pairs[0]
            for p in pairs:
                if p[0] > best[0]:
                    best = p
            print(f"Most two-leg routes: {best[1]} -> ? -> {best[2]} ({best[0]} combinations)")


        elif cmd == "RULES":
            ph = PerfectHash(RULE_IDS)
            print(f"{len(RULE_IDS)} rule IDs, storage {ph.storage()} slots, "
                  f"retries: level1 {ph.level1_retries}, level2 {ph.level2_retries}")
            print(f"bucket sizes: {ph.bucket_sizes()}")
            for k in args:
                print(f"  rule {k}: {'present' if ph.contains(int(k)) else 'absent'}")


        elif cmd == "HELP":
            print("LOAD path | FIND id | LIST_RUNWAY R | STATS | CANCEL id")
            print('RESCHEDULE id "start" | CHECK_CONFLICT R "start" "end"')
            print('ADD id airline origin dest R "start" "end" prio')
            print('EMERGENCY_INSERT id airline origin dest R "start" "end" prio [ACCEPT]')
            print('RUNWAY_CLOSURE R "start" "end" | MASS_CANCEL "start" "end"')
            print("SORT_PRIORITY [n] | SORT_ID [n] | SORT_DEMO | ANALYZE | QUIT")

        else:
            print(f"Unknown command: {cmd}  (type HELP)")

    except IndexError:
        print(f"{cmd}: missing arguments (type HELP for syntax)")
    except ValueError as e:
        print(f"{cmd}: invalid input ({e})")


def menu(engine):
    print("Airport Chaos: type a command, HELP, or QUIT")
    while True:
        line = input("> ").strip()
        if line.upper() in ("QUIT", "EXIT"):
            break
        run_command(engine, line)


def batch(engine, path):
    with open(path) as f:
        for line in f:
            if line.strip():
                print(f"\n>>> {line.strip()}")
                run_command(engine, line)


app = typer.Typer(help="Airport Chaos: flight scheduling & crisis recovery engine")


@app.command("menu")
def menu_cmd():
    """Interactive mode: type commands until QUIT."""
    menu(Engine())


@app.command("batch")
def batch_cmd(path: str):
    """Run every command in a batch file, one per line."""
    batch(Engine(), path)


@app.command("run")
def run_cmd(line: str, csv: str = "data/airport_flights.csv"):
    """Load the CSV, then run a single command."""
    e = Engine()
    run_command(e, f"LOAD {csv}")
    run_command(e, line)


if __name__ == "__main__":
    app()