import sys
import shlex
from datetime import datetime
from airport.engine import Engine
from airport.flight import Flight

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

        elif cmd == "RUNWAY_CLOSURE":
            rows, n, d, c, mins = engine.runway_closure(args[0], t(args[1]), t(args[2]))
            print(f"{'ID':<9}{'OLD':>6}{'NEW':>7}  STATUS")
            for fid, old, new, st in rows:
                print(f"{fid:<9}{fmt(old):>6}{fmt(new):>7}  {st}")
            print(f"affected {n}, delayed {d}, cancelled {c}, total delay {mins} min")

        elif cmd == "LIST_RUNWAY":
            name = args [0]
            if name not in engine.runways:
                print(f"No runway called {name}")
            else:
                for f in engine.runways[name].inorder():
                    print(f"{f.flight_id} {fmt(f.start)}-{fmt(f.end)} P{f.priority} {f.status}")
        

        else:
            print(f"Unknown command: {cmd}")

    except IndexError:
        print(f"{cmd}: missing arguments (see README for syntax)")
    except ValueError as e:
        print(f"{cmd}: invalid input ({e})")


def menu(engine):
    print("Airport Chaos: type a command, or QUIT")
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


if __name__ == "__main__":
    e = Engine()
    if len(sys.argv) == 3 and sys.argv[1] == "--batch":
        batch(e, sys.argv[2])
    else:
        menu(e)