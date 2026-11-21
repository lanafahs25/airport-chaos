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



    def cancel (self, fid):
        flight = self.find(fid)[0]

        if flight is None:
            return False, "no such flight"

        if flight.status == "CANCELLED":
            return False, "already cancelled"

        tree = self.runways[flight.runway]
        node = tree.search((flight.start, flight.flight_id))

        tree.delete(node)
        flight.status = "CANCELLED"

        return True, "cancelled"

    def reschedule (self, fid, new_start):

        flight = self.find(fid)[0]

        if flight is None:
            return False, "no such flight", []
        
        if flight.status == "CANCELLED":
            return False, "this flight is cancelled", []

        duration = flight.end - flight.start
        new_end = new_start + duration 
        tree = self.runways[flight.runway]

        tree.delete(tree.search((flight.start, flight.flight_id))) #out of the way

        clashes = tree.conflicts (new_start, new_end)

        if len(clashes)!= 0:
            tree.insert (flight)                                    #rollback: times unchanged 
            return False, "runway conflict" , clashes

        flight.start = new_start
        flight.end = new_end

        if new_start > flight.orig_start:
            flight.status = "DELAYED"

        else:
            flight.status = "SCHEDULED"

        tree.insert(flight)
        return True, "rescheduled", []
    