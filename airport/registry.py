import random

P = (1 << 61) - 1      # 2^61 - 1, a Mersenne prime
_TOMB = object()       # tombstone marker 


class HashRegistry:
    def __init__(self, m=16, seed=42):
        self.m = m
        self.table = [None] * m
        self.size = 0
        self.tombstones = 0
        self.collisions = 0
        rng = random.Random(seed)
        self.a = rng.randint(1, P - 1)
        self.b = rng.randint(0, P - 1)

    #turning the id's into integers for hash calculation
    @staticmethod
    def encode(fid):        
        value = 0
        for character in fid:
            value = (value * 131 + ord(character))% P
        return value

    #actual hashing 
    def _hash(self, fid):  
        k = self.encode(fid)
        hashed = ((self.a *k + self.b )% P)% self.m

        return hashed
    
    #inserting a flight if it's not there already
    def insert (self, flight):
        if (self.size+1)/ self.m > 0.6:
            self._resize()

        i = self._hash(flight.flight_id)
        for j in range(self.m):
            if self.table[i] == None:
                self.table[i] = flight
                self.size += 1
                return True
            
            elif self.table[i].flight_id == flight.flight_id:
                return False
            self.collisions += 1
            i = (i+1)%self.m  
        raise RuntimeError("Hash table is full!")

    #searching for the flight 
    def lookup (self,fid):
        i = self._hash(fid)
        probes = 0

        for j in range (self.m):
            probes+=1
            if self.table[i] == None:
                return None, probes 
        
            elif self.table[i].flight_id == fid:
                return self.table[i], probes 
            
            i = (i+1)%self.m
        return None, probes
    
    #load factor alpha (n/m) 
    def load_factor (self):
        load = self.size/self.m
        return load
    

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


