"""
Module A: flight registry.
big picture for lana big brain:
regstry.py acts as a database of the flights where it stores
every flight (instantly) without the need to search (hence the hashtable)

the id is turned into a slot number, collisions take the next free slot by linear probing 

deleted flights leave a tombstone

when the table is 60% full, it doubles

"""
from . import trace
import random

PRIME_P = (1 << 61) - 1    #2^61 - 1, big prime (Mersenne) 
_TOMB = object()           #tombstone marker 


class HashRegistry:

    def __init__(self, capacity=16, seed=42):

        self.capacity = capacity            #m in the formula: number of slots in the table
        self.table = [None] * capacity
        self.size = 0                       #n: flights stored right now
        self.tombstones = 0
        self.collisions = 0
        self.lookups = 0
        self.probes = 0

        rng = random.Random(seed)

        #a and b of the universal hash h(k) = ((a*k + b) mod p) mod m, chosen once
        self.hash_a = rng.randint(1, PRIME_P - 1)
        self.hash_b = rng.randint(0, PRIME_P - 1)




    #turning IDs into integers, because the hash function doesn't read
    #reads the ID like a number written in base 131: "AB" -> 65*131 + 66
    #131 > biggest character code (122), so different IDs of up to 8 chars get different numbers
    #ps: biggest character code according to the ascii table (alphabets+nbs)
    @staticmethod
    def encode(flight_id):

        id_number = 0

        for character in flight_id:
            id_number = (id_number * 131 + ord(character)) % PRIME_P

        return id_number



    #assigning every flight a parking spot, no appeals
    #h(k) = ((a*k + b) mod p) mod m   with p = 2^61 - 1, m = capacity
    def _hash(self, flight_id):

        key_number = self.encode(flight_id)
        slot = ((self.hash_a * key_number + self.hash_b) % PRIME_P) % self.capacity

        return slot



    #boarding: find a free seat, refuse anyone already on the plane
    
    
   
    #   (the same ID might sit further along -> must rule out a duplicate before placing)
    
    #returns True (inserted) or False (duplicate ID)
    def insert (self, flight):

        #resize first if the table would get too full (about 60%)
        if (self.size + self.tombstones + 1) / self.capacity > 0.6:
            self._resize()

        slot = self._hash(flight.flight_id)
        first_tombstone_slot = None

        #walk from the hashed slot: remember the FIRST tombstone, keep walking until an empty slot
        for _ in range(self.capacity):

            #empty, flight is not further on
            if self.table[slot] is None:

                #passed a tombstone earlier ?
                if first_tombstone_slot is not None:

                    #reuse the seat
                    self.table[first_tombstone_slot] = flight
                    self.tombstones -= 1
                    
                else:
                    #or sit here
                    self.table[slot] = flight

                self.size += 1
                return True

            #tombstone, remember it and keep walking
            elif self.table[slot] is _TOMB:
                #same id might still be further along
                if first_tombstone_slot is None:
                    first_tombstone_slot = slot

            #same id is already there
            elif self.table[slot].flight_id == flight.flight_id:
                #duplicate, refuse 
                return False

            #seat taken by another flight 
            self.collisions += 1
            #linear probing: next seat, wrap around
            slot = (slot + 1) % self.capacity

        #no empty seat at all, but a tombstone exists
        if first_tombstone_slot is not None:
            #reuse it
            self.table[first_tombstone_slot] = flight
            self.tombstones -= 1
            self.size += 1

            return True

        raise RuntimeError("Hash table is full!")




    #"have you seen this flight?" — walks until it finds it or gives up
    def lookup (self, flight_id):

        #start where insert would have put it
        slot = self._hash(flight_id)
        #slots checked in this lookup (locally) 
        probes = 0
        self.lookups += 1
        #TRACE: prints the hash and starting slot
        trace.log(f"lookup {flight_id}: encode={self.encode(flight_id)}, h={slot}, capacity={self.capacity}")

        for _ in range(self.capacity):

            probes += 1             #local probe: how many times we probe in one lookup
            self.probes += 1        #global probe: how many times we probe over all, used to compute the average
            trace.log(f"probe {probes}: slot {slot} -> " + ("empty" if self.table[slot] is None else "tombstone" if self.table[slot] is _TOMB else self.table[slot].flight_id))

            if self.table[slot] is None:
                return None, probes

            elif self.table[slot] is _TOMB:
                pass

            elif self.table[slot].flight_id == flight_id:
                return self.table[slot], probes

            slot = (slot + 1) % self.capacity

        return None, probes



    #how packed is the terminal? alpha = size / capacity (n / m)
    def load_factor (self):
        return self.size / self.capacity



    # the terminal is overcrowded: build a bigger one and make everyone re-board
    # flights are REINSERTED (not copied to the same index) because the slot depends on m,
    # and m just changed. tombstones are left behind, so the new table starts clean. O(m)
    def _resize(self):
        old_table = self.table

        self.capacity = 2 * self.capacity
        self.table = [None] * self.capacity

        self.size = 0
        self.tombstones = 0

        for slot_content in old_table:
            if slot_content is not None and slot_content is not _TOMB:
                self.insert(slot_content)


    #deleting (rest in pepperonis: replace with a tombstone so probe chains stay intact)
    #emptying the slot (None) would make lookup stop early and "lose" flights stored after it
    #returns True (deleted) or False (not found)
    def delete (self, flight_id):

        slot = self._hash(flight_id)

        for _ in range(self.capacity):

            if self.table[slot] is None:
                return False

            elif self.table[slot] is _TOMB:
                pass

            elif self.table[slot].flight_id == flight_id:

                self.table[slot] = _TOMB
                self.size -= 1
                self.tombstones += 1
                return True
            slot = (slot + 1) % self.capacity

        return False

    #numbers for STATS / the report: size, capacity, load factor, tombstones, collisions, avg probes
    #(collisions also count the ones that happen while reinserting during resizes)
    def stats(self):
        avg_probes = 0
        if self.lookups > 0:
            avg_probes = self.probes / self.lookups
        return {
            "size": self.size,                   # flights stored right now
            "capacity": self.capacity,           # number of slots
            "load_factor": self.load_factor(),
            "tombstones": self.tombstones,
            "collisions": self.collisions,
            "avg_probes": avg_probes,            # total probes / lookups, 0 if no lookups yet
        }


    #every real flight in the table (skips empty slots and tombstones), used by the engine
    def all_flights(self):
        result = []
        for slot_content in self.table:
            if slot_content is not None and slot_content is not _TOMB:
                result.append(slot_content)
        return result
