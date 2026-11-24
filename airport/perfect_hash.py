import random

RULE_IDS = [101, 107, 113, 127, 131, 149, 157, 163, 173, 181,
            193, 211, 223, 227, 239, 251, 263, 269, 277, 283]

PRIME = 293     # p: prime larger than every key

# universal hash h(k) = ((a*k + b) mod p) mod m, with a = multiplier, b = offset, m = table_size
def universal_hash(key, multiplier, offset, table_size):
    return ((multiplier * key + offset) % PRIME) % table_size

class PerfectHash:
    def __init__ (self, keys, seed = 42):
        self.rng = random.Random(seed)
        self.num_keys = len(keys)                 # n
        self.level1_retries = 0
        self.level2_retries = 0

        #level 1: num_keys buckets, re-pick (a, b) until sum of bucket_size^2 <= 4n
        while True:
            self.level1_a = self.rng.randint(1, PRIME - 1)
            self.level1_b = self.rng.randint(0, PRIME - 1)
            buckets = [[] for _ in range(self.num_keys)]
            for key in keys:
                buckets[universal_hash(key, self.level1_a, self.level1_b, self.num_keys)].append(key)

            if sum(len(bucket) ** 2 for bucket in buckets) <= 4 * self.num_keys:
                break
            self.level1_retries += 1

        #level 2: a bucket with bucket_size keys gets a table of size bucket_size^2
        self.secondary = []                       # one (a, b, table) per bucket
        for bucket in buckets:
            table_size = len(bucket) ** 2
            if table_size == 0:
                self.secondary.append((0, 0, []))
                continue
            while True:
                level2_a = self.rng.randint(1, PRIME - 1)
                level2_b = self.rng.randint(0, PRIME - 1)
                table = [None] * table_size
                collision = False

                for key in bucket:
                    slot = universal_hash(key, level2_a, level2_b, table_size)
                    if table[slot] is not None:
                        collision = True
                        break
                    table[slot] = key
                if not collision:
                    break
                self.level2_retries += 1
            self.secondary.append((level2_a, level2_b, table))

    def contains(self, key):
        bucket_index = universal_hash(key, self.level1_a, self.level1_b, self.num_keys)
        level2_a, level2_b, table = self.secondary[bucket_index]
        if len(table) == 0:
            return False
        return table[universal_hash(key, level2_a, level2_b, len(table))] == key

    def storage(self):
        return self.num_keys + sum(len(table) for _, _, table in self.secondary)

    def bucket_sizes(self):
        sizes = []
        for _, _, table in self.secondary:
            bucket_size = 0
            while bucket_size * bucket_size < len(table):   # table has bucket_size^2 slots
                bucket_size += 1
            sizes.append(bucket_size)
        return sizes
