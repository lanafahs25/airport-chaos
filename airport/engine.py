from .loader import load_flights
from .registry import HashRegistry
from .bst import RunwayBST

class Engine:
    def __init__(self):
        self.registry = HashRegistry()
        self.runways = {}

    def load (self, path):
        flights, errors = load_flights(path)
        self.registry =  HashRegistry()
        self.runways = {}

        for f in flights:

            self.registry.insert(f)

            if f.runway not in self.runways:
                self.runways[f.runway] = RunwayBST()

            self.runways[f.runway].insert(f)

        return len(flights), errors


    def find(self, fid):
        return self.registry.lookup(fid)

    def add (self, flight):
        existing = self.find(flight.flight_id)[0]

        if existing is not None:
            return False, "duplicate flight ID", []

        if flight.runway not in self.runways:
            self.runways[flight.runway] = RunwayBST()

        tree = self.runways[flight.runway]

        clashes = tree.conflicts(flight.start, flight.end)

        if len(clashes) != 0:
            return False, "runway conflict", clashes

        self.registry.insert(flight)
        tree.insert (flight)
        return True, "added", []

    

