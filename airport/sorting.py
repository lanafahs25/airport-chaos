from . import trace

#counting sort to sort flights by priority
def counting_sort_priority(flights):
    k = 3
    count = [0] * (k+1)
    for f in flights:
        count[f.priority] += 1

    for p in range (2, k+1):
        count[p] += count [p-1]
    trace.log(f"counting sort: cumulative counts by priority = {count[1:]}")

    output = [None] * len(flights)
    for f in reversed(flights):
        count[f.priority] -= 1
        output[count[f.priority]] = f
    return output




def char_key(fid, pos):
    if pos < len(fid):
        return ord(fid[pos]) + 1
    else:
        return 0
    
def counting_sort_by_char(flights, pos):
    k = 128
    count = [0] * (k +1)
    for f in flights:
        count[char_key(f.flight_id, pos)] += 1

    for v in range (1, k+1):
        count[v] += count[v-1]
    output = [None] * len(flights)
    for f in reversed(flights):
        c = char_key(f.flight_id, pos)
        count[c] -= 1
        output[count[c]] = f

    return output

def radix_sort_ids (flights): 
    width = max ((len(f.flight_id) for f in flights), default = 0)

    for pos in range (width-1, -1, -1):
        flights = counting_sort_by_char(flights, pos)
        trace.log(f"radix pass on character {pos}: first IDs = {[f.flight_id for f in flights[:5]]}")
    return flights
