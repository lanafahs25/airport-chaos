from . import trace

#counting sort to sort flights by priority
def counting_sort_priority(flights):
    num_priorities = 3                              # k: priorities are 1, 2 or 3
    count = [0] * (num_priorities + 1)              # index 0 unused
    for flight in flights:
        count[flight.priority] += 1

    for priority in range(2, num_priorities + 1):
        count[priority] += count[priority - 1]      # now count[p] = how many have priority <= p
    trace.log(f"counting sort: cumulative counts by priority = {count[1:]}")

    output = [None] * len(flights)
    for flight in reversed(flights):                # backwards keeps equal priorities in order (stable)
        count[flight.priority] -= 1
        output[count[flight.priority]] = flight
    return output




#numeric value of the character at `position`; 0 if the ID is too short (so prefixes sort first)
def char_key(flight_id, position):
    if position < len(flight_id):
        return ord(flight_id[position]) + 1
    else:
        return 0

#one stable counting-sort pass on a single character position
def counting_sort_by_char(flights, position):
    alphabet_size = 128                             # k: ASCII codes 1..128, plus 0 for "past the end"
    count = [0] * (alphabet_size + 1)
    for flight in flights:
        count[char_key(flight.flight_id, position)] += 1

    for char_value in range(1, alphabet_size + 1):
        count[char_value] += count[char_value - 1]
    output = [None] * len(flights)
    for flight in reversed(flights):
        char_value = char_key(flight.flight_id, position)
        count[char_value] -= 1
        output[count[char_value]] = flight

    return output

#LSD radix sort: one pass per character, last character first
def radix_sort_ids (flights):
    longest_id = max((len(flight.flight_id) for flight in flights), default=0)   # d: number of passes

    for position in range(longest_id - 1, -1, -1):
        flights = counting_sort_by_char(flights, position)
        trace.log(f"radix pass on character {position}: first IDs = {[f.flight_id for f in flights[:5]]}")
    return flights
