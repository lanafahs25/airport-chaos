from base64 import encode
import random

P = (1 << 61) - 1      # 2^61 - 1, a Mersenne prime
_TOMB = object()       # tombstone marker (round 3)


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