import csv
from datetime import datetime
from .flight import Flight

TIME_FMT = "%Y-%m-%d %H:%M"
REQUIRED = ["flight_id", "airline", "origin", "destination",
            "runway", "start_time", "end_time", "priority", "status"]


class LoadError(Exception):
    pass


def parse_time(s, line_no, field_name):
    try:
        return datetime.strptime(s.strip(), TIME_FMT)
    except ValueError:
        raise LoadError(f"line {line_no}: bad {field_name} '{s}'")


def load_flights(path):
    flights, errors, seen = [], [], set()
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise LoadError(f"missing columns: {missing}")

        for line_no, row in enumerate(reader, start=2):
            fid = row["flight_id"].strip()

            # a. parse times
            try:
                start = parse_time(row["start_time"], line_no, "start_time")
                end = parse_time(row["end_time"], line_no, "end_time")
            except LoadError as e:
                errors.append(str(e))
                continue

            # b. start before end
            if start >= end:
                errors.append(f"line {line_no}: start is not before end for {fid}")
                continue

            # c. priority is 1, 2 or 3
            try:
                priority = int(row["priority"])
            except ValueError:
                errors.append(f"line {line_no}: priority '{row['priority']}' is not a number")
                continue
            if priority not in (1, 2, 3):
                errors.append(f"line {line_no}: priority {priority} must be 1, 2 or 3")
                continue

            # d. duplicate ID
            if fid in seen:
                errors.append(f"line {line_no}: duplicate flight_id {fid}")
                continue

            # e. all good
            flights.append(Flight(
                flight_id=fid,
                airline=row["airline"].strip(),
                origin=row["origin"].strip(),
                destination=row["destination"].strip(),
                runway=row["runway"].strip(),
                start=start,
                end=end,
                priority=priority,
                status=row["status"].strip() or "SCHEDULED",
            ))
            seen.add(fid)

    return flights, errors


def runways_of(flights):
    names = []
    for fl in flights:
        if fl.runway not in names:
            names.append(fl.runway)
    names.sort()
    return names