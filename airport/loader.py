import csv
from datetime import datetime
from .flight import Flight

TIME_FMT = "%Y-%m-%d %H:%M"
REQUIRED = ["flight_id", "airline", "origin", "destination",
            "runway", "start_time", "end_time", "priority", "status"]


class LoadError(Exception):
    pass


def parse_time(text, line_no, field_name):
    try:
        return datetime.strptime(text.strip(), TIME_FMT)
    except ValueError:
        raise LoadError(f"line {line_no}: bad {field_name} '{text}'")


def load_flights(path):
    flights, errors, seen = [], [], set()
    with open(path, newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        missing = [column for column in REQUIRED if column not in (reader.fieldnames or [])]
        if missing:
            raise LoadError(f"missing columns: {missing}")

        for line_no, row in enumerate(reader, start=2):
            flight_id = row["flight_id"].strip()

            # a. parse times
            try:
                start = parse_time(row["start_time"], line_no, "start_time")
                end = parse_time(row["end_time"], line_no, "end_time")
            except LoadError as error:
                errors.append(str(error))
                continue

            # b. start before end
            if start >= end:
                errors.append(f"line {line_no}: start is not before end for {flight_id}")
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
            if flight_id in seen:
                errors.append(f"line {line_no}: duplicate flight_id {flight_id}")
                continue

            # e. all good
            flights.append(Flight(
                flight_id=flight_id,
                airline=row["airline"].strip(),
                origin=row["origin"].strip(),
                destination=row["destination"].strip(),
                runway=row["runway"].strip(),
                start=start,
                end=end,
                priority=priority,
                status=row["status"].strip() or "SCHEDULED",
            ))
            seen.add(flight_id)

    return flights, errors


def runways_of(flights):
    names = []
    for flight in flights:
        if flight.runway not in names:
            names.append(flight.runway)
    names.sort()
    return names