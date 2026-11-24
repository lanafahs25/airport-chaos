import random

RULE_IDS = [101, 107, 113, 127, 131, 149, 157, 163, 173, 181,
            193, 211, 223, 227, 239, 251, 263, 269, 277, 283]

PRIME = 293     # prime larger than every key

def universal_hash(key, a, b, table_size):
    return ((a*key + b)%PRIME) %table_size

class PerfectHash:
    def __init__ (self, keys, seed = 42):
        self.rng = random.Random(seed)
        self.n = len(keys)
        self.level1_retries = 0
        self.level2_retries = 0

        #level 1: n buckets, re-pick (a,b) until sum of s^2 <- 4n
        while True:
            self.a1 = self.rng.randint(1, PRIME -1)
            self.b1 = self.rng.randint (0, PRIME - 1)
            buckets = [[]for _ in range(self.n)]
            for key in keys:
                buckets[universal_hash(key, self.a1, self.b1, self.n)].append(key)

            if sum(len(bucket)**2 for bucket in buckets) <= 4 * self.n:
                break
            self.level1_retries += 1

        #level 2: bucket of size s gets a table of size s^2
        self.secondary = []
        for bucket in buckets:
            size = len(bucket) ** 2
            if size == 0:
                self.secondary.append((0,0,[]))
                continue
            while True:
                a = self.rng.randint(1, PRIME -1)
                b = self.rng.randint(0, PRIME-1)
                table = [None] * size
                collision = False

                for key in bucket:
                    slot = universal_hash(key, a, b, size)
                    if table [slot] is not None:
                        collision = True
                        break
                    table[slot] = key
                if not collision:
                    break
                self.level2_retries += 1
            self.secondary.append((a,b, table))

    def contains(self, key):
        bucket = universal_hash(key, self.a1, self.b1, self.n)
        a, b, table = self.secondary[bucket]
        if len(table) == 0:
            return False
        return table[universal_hash(key, a, b, len(table))] == key

    def storage(self):
        return self.n + sum(len(table) for _, _, table in self.secondary)

    def bucket_sizes(self):
        sizes = []
        for _, _, table in self.secondary:
            s = 0
            while s * s < len(table):
                s += 1
            sizes.append(s)
        return sizes