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