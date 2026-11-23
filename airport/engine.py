from datetime import timedelta
from .loader import load_flights
from .registry import HashRegistry
from .bst import RunwayBST


 
#helper function for comparing 3 things at once
def key (f):
     return (f.priority, f.orig_start, f.flight_id)


#normal insertion sort 
def sort_affected(flights):
    for i in range(1, len(flights)):

        current = flights[i]
        j = i - 1

        while j >= 0 and key(flights[j]) > key(current):

            flights[j + 1] = flights[j]
            j -= 1

        flights[j + 1] = current
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

        for f in flights:

            if f.runway not in self.runways:
                self.runways[f.runway] = RunwayBST()

            tree = self.runways[f.runway]
            clashes = tree.conflicts (f.start, f.end)

            if len(clashes) != 0:
                errors.append(f"{f.flight_id}: overlaps {clashes[0].flight_id} on {f.runway}, skipped")
                continue

            self.registry.insert(f)
            tree.insert(f)
            loaded += 1


        return loaded, errors



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



    def check_consistency (self):
        problems = []
        tree_total = 0

        for (name, tree) in self.runways.items():
            for node in tree.inorder(nodes = True):
                f = node.flight

                if f.status == "CANCELLED":
                    problems.append(f"{f.flight_id} on {name}: in tree but CANCELLED")

                if f.runway != name:
                    problems.append(f"{f.flight_id} on {name}: flight says runway {f.runway}")

                if node.key != (f.start, f.flight_id):
                    problems.append(f"{f.flight_id} on {name}: node key doesn't match flight times")

                if self.find(f.flight_id)[0] is not f:
                    problems.append(f"{f.flight_id} on {name}: registry doesn't return this flight")

                tree_total += 1

        active = 0
        for f in self.registry.all_flights():
            if f.status != "CANCELLED":
                active += 1

        if tree_total != active:
            problems.append(f"trees hold {tree_total} flights but registry has {active} active")

        return problems

    #scenario A: Runway_Closure

    def runway_closure (self, runway, close_start, close_end):
        tree = self.runways [runway]
        affected = tree.conflicts (close_start, close_end)

        for f in affected:
            #clear out first
            tree.delete(tree.search((f.start, f.flight_id)))

        affected = sort_affected(affected)
        rows = [] 
        delayed = 0
        cancelled = 0
        total_delay = 0

        for f in affected: 
            old_start = f.start
            duration = f.end - f.start
            candidate = close_end
            placed = False

            while candidate - f.orig_start <= timedelta(minutes = 120):
                if len(tree.conflicts (candidate, candidate + duration)) == 0:
                    f.start = candidate
                    f.end = candidate + duration
                    f.status = "DELAYED"
                    tree.insert(f)
                    placed = True
                    break
                candidate = candidate + timedelta(minutes = 5)

            if placed == True:

                delayed += 1
                total_delay += int((f.start - f.orig_start).total_seconds() // 60)
                rows.append((f.flight_id, old_start, f.start, "DELAYED"))


            else:
                f.status = "CANCELLED"
                cancelled += 1
                rows.append((f.flight_id, old_start, None, "CANCELLED"))

        return rows, len(affected), delayed, cancelled, total_delay

    #Scenario C: Mass_Cancel
    def mass_cancel (self, t1, t2):
        cancelled_ids = []
        for name, tree in self.runways.items():
            found = tree.range_search(t1,t2)

            for f in found:
                self.cancel(f.flight_id)
                cancelled_ids.append(f.flight_id)
        return cancelled_ids


    #Scenario B: Imergency Insert
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
            return False, "conflict, slot offered ", clashes, offered

        flight.start = offered 
        flight.end = offered + duration 
        flight.orig_start = flight.start
        flight.orig_end = flight.end
        self.add(flight)

        return True , "inserted at offered slot", clashes, offered
        
        







                
