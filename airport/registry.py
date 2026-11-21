import random

P = (1 << 61) - 1      #2^61 - 1, a Mersenne prime, a prime so big it has its own zip code
_TOMB = object()       #tombstone marker. here lies a flight. it was delayed one last time.


class HashRegistry:

    def __init__(self, m=16, seed=42):

        self.m = m
        self.table = [None] * m
        self.size = 0
        self.tombstones = 0
        self.collisions = 0
        self.lookups = 0 
        self.probes = 0

        rng = random.Random(seed)

        self.a = rng.randint(1, P - 1)
        self.b = rng.randint(0, P - 1)




    #turning IDs into integers, because the hash function doesn't read
    @staticmethod
    def encode(fid): 

        value = 0

        for character in fid:
            value = (value * 131 + ord(character))% P

        return value



    #assigning every flight a parking spot, no appeals 
    def _hash(self, fid): 
        
        k = self.encode(fid)
        hashed = ((self.a *k + self.b )% P)% self.m

        return hashed



    
    #boarding: find a free seat, refuse anyone already on the plane
    def insert (self, flight):

        if (self.size+ self.tombstones + 1)/ self.m > 0.6:
            self._resize()

        i = self._hash(flight.flight_id)
        first_tomb = None

        for j in range(self.m):

            if self.table[i] is None:

                if first_tomb is not None:
                    self.table[first_tomb] = flight
                    self.tombstones -= 1
                else:
                    self.table[i] = flight

                self.size += 1
                return True
            
            elif self.table[i] is _TOMB:
                if first_tomb is None:
                    first_tomb = i

            elif self.table[i].flight_id == flight.flight_id:
                return False
            
            self.collisions += 1
            i = (i+1)%self.m  

        if first_tomb is not None:

            self.table[first_tomb] = flight 
            self.tombstones -= 1
            self.size += 1

            return True
        
        raise RuntimeError("Hash table is full!")




    #"have you seen this flight?" — walks until it finds it or gives up
    def lookup (self,fid):

        i = self._hash(fid)
        probes = 0
        self.lookups += 1

        for j in range (self.m):

            probes+=1               #local probe: how many times we probe in one lookup 
            self.probes += 1        #global probe: how many times we probe over all, used to compute the average

            if self.table[i] == None:
                return None, probes 
            
            elif self.table[i] is _TOMB:
                pass

            elif self.table[i].flight_id == fid:
                return self.table[i], probes 
            
            i = (i+1)%self.m

        return None, probes


    
    #how packed is the terminal? alpha(size / m)
    def load_factor (self):
        load = self.size/self.m
        return load


    
    # the terminal is overcrowded: build a bigger one and make everyone re-board
    def _resize(self):
        old = self.table

        self.m = 2*self.m
        self.table = [None] * self.m

        self.size = 0
        self.tombstones = 0

        for slot in old:
            if slot is not None and slot is not _TOMB:
                self.insert(slot)
        return 


    #deleting (rest in pepperonis: replace with a tombstone so probe chains stay intact)
    def delete (self, fid):

        i = self._hash(fid)

        for j in range (self.m):

            if self.table[i] is None:
                return False 
        
            elif self.table[i] is _TOMB:
                pass


            elif self.table[i].flight_id == fid:

                self.table[i] = _TOMB 
                self.size -= 1
                self.tombstones += 1
                return True 
            i = (i+1)%self.m

        return False
        
    def stats(self):
        avg_probes = 0
        if self.lookups > 0:
            avg_probes = self.probes / self.lookups 
        return {
            "size": self.size,                  # flights stored right now
            "capacity": self.m,                 # number of slots
            "load_factor": self.load_factor(),   # a method for this exists
            "tombstones": self.tombstones,
            "collisions": self.collisions,
            "avg_probes": avg_probes,           # total_probes / lookups, but handle lookups == 0
        }


    def all_flights(self):
        result = []
        for slot in self.table:
            if slot is not None and slot is not _TOMB:
                result.append(slot)
        return result

    


