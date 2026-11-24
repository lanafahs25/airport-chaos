from datetime import timedelta
from .loader import load_flights
from .registry import HashRegistry
from .bst import RunwayBST


 
#helper function for comparing 3 things at once: priority, then original start, then ID
def priority_key (flight):
    return (flight.priority, flight.orig_start, flight.flight_id)


#normal insertion sort on that key
def sort_affected(flights):
    for next_index in range(1, len(flights)):

        current = flights[next_index]
        scan = next_index - 1

        while scan >= 0 and priority_key(flights[scan]) > priority_key(current):

            flights[scan + 1] = flights[scan]
            scan -= 1

        flights[scan + 1] = current
    return flights


class Engine:
    def __init__(self):
        self.registry = HashRegistry()
        self.runways = {}

    def load (self, path):
        flights, errors = load_flights(path)
        self.registry =  HashRegistry()
        self.runways = {}

        loaded = 0

        for flight in flights:

            if flight.runway not in self.runways:
                self.runways[flight.runway] = RunwayBST()

            tree = self.runways[flight.runway]
            clashes = tree.conflicts(flight.start, flight.end)

            if len(clashes) != 0:
                errors.append(f"{flight.flight_id}: overlaps {clashes[0].flight_id} on {flight.runway}, skipped")
                continue

            self.registry.insert(flight)
            tree.insert(flight)
            loaded += 1


        return loaded, errors



    def find(self, flight_id):
        return self.registry.lookup(flight_id)




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



    def cancel (self, flight_id):
        flight = self.find(flight_id)[0]

        if flight is None:
            return False, "no such flight"

        if flight.status == "CANCELLED":
            return False, "already cancelled"

        tree = self.runways[flight.runway]
        node = tree.search((flight.start, flight.flight_id))

        tree.delete(node)
        flight.status = "CANCELLED"

        return True, "cancelled"

    def reschedule (self, flight_id, new_start):

        flight = self.find(flight_id)[0]

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



    def check_consistency (self):
        problems = []
        tree_total = 0

        for (name, tree) in self.runways.items():
            for node in tree.inorder(nodes = True):
                flight = node.flight

                if flight.status == "CANCELLED":
                    problems.append(f"{flight.flight_id} on {name}: in tree but CANCELLED")

                if flight.runway != name:
                    problems.append(f"{flight.flight_id} on {name}: flight says runway {flight.runway}")

                if node.key != (flight.start, flight.flight_id):
                    problems.append(f"{flight.flight_id} on {name}: node key doesn't match flight times")

                if self.find(flight.flight_id)[0] is not flight:
                    problems.append(f"{flight.flight_id} on {name}: registry doesn't return this flight")

                tree_total += 1

        active = 0
        for flight in self.registry.all_flights():
            if flight.status != "CANCELLED":
                active += 1

        if tree_total != active:
            problems.append(f"trees hold {tree_total} flights but registry has {active} active")

        return problems

    #scenario A: Runway_Closure

    def runway_closure (self, runway, close_start, close_end):
        tree = self.runways [runway]
        affected = tree.conflicts (close_start, close_end)

        for flight in affected:
            #clear out first
            tree.delete(tree.search((flight.start, flight.flight_id)))

        affected = sort_affected(affected)
        rows = [] 
        delayed = 0
        cancelled = 0
        total_delay = 0

        for flight in affected:
            old_start = flight.start
            duration = flight.end - flight.start
            candidate = close_end                     # first start time to try
            placed = False

            while candidate - flight.orig_start <= timedelta(minutes = 120):
                if len(tree.conflicts(candidate, candidate + duration)) == 0:
                    flight.start = candidate
                    flight.end = candidate + duration
                    flight.status = "DELAYED"
                    tree.insert(flight)
                    placed = True
                    break
                candidate = candidate + timedelta(minutes = 5)

            if placed == True:

                delayed += 1
                total_delay += int((flight.start - flight.orig_start).total_seconds() // 60)
                rows.append((flight.flight_id, old_start, flight.start, "DELAYED"))


            else:
                flight.status = "CANCELLED"
                cancelled += 1
                rows.append((flight.flight_id, old_start, None, "CANCELLED"))

        return rows, len(affected), delayed, cancelled, total_delay

    #Scenario C: Mass_Cancel
    def mass_cancel (self, window_start, window_end):
        cancelled_ids = []
        for name, tree in self.runways.items():
            found = tree.range_search(window_start, window_end)

            for flight in found:
                self.cancel(flight.flight_id)
                cancelled_ids.append(flight.flight_id)
        return cancelled_ids


    #Scenario B: Emergency Insert
    def emergency_insert (self, flight, accept):

        if self.find(flight.flight_id) [0] is not None:
            return False, "duplicate flight id", [], None

        if flight.runway not in self.runways:
            self.runways[flight.runway] = RunwayBST()

        tree = self.runways[flight.runway]
        clashes = tree.conflicts (flight.start, flight.end)

        if len(clashes) == 0:
            self.add(flight)
            return True, "inserted at requested time", [], flight.start

        duration = flight.end - flight.start
        candidate = flight.start + timedelta(minutes = 5)
        offered = None 

        while candidate - flight.start <= timedelta(hours = 24):
            if len(tree.conflicts(candidate, candidate + duration)) == 0:
                offered = candidate 
                break
            candidate = candidate + timedelta(minutes = 5)

        if offered is None:
            return False, "no free slot within 24h", clashes, offered

        if not accept:
            return False, "conflict, slot offered", clashes, offered

        flight.start = offered 
        flight.end = offered + duration 
        flight.orig_start = flight.start
        flight.orig_end = flight.end
        self.add(flight)

        return True , "inserted at offered slot", clashes, offered
        
        







                
