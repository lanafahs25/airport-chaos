from datetime import datetime, timedelta

BUCKETS_PER_DAY = 288          # 24 h * 60 min / 5 min

def build_load(flights):

    if len(flights) == 0:
        return [], None

    day = min(flight.orig_start for flight in flights).date()
    load = [0] * BUCKETS_PER_DAY

    for flight in flights:
        if flight.status in ("DELAYED", "CANCELLED") and flight.orig_start.date() == day:
            bucket = (flight.orig_start.hour * 60 + flight.orig_start.minute) // 5
            load[bucket] += 1

    return load, day


#in the logical sense there wont be any negative values as it's
#the number of flights. however, this algorithm is the general
#version that handles negative values
def find_max_crossing (values, left, mid, right):
    #left side: best stretch ending at mid
    left_sum = float("-inf")
    total = 0
    max_left = mid
    for index in range(mid, left - 1, -1):
        total += values[index]
        if total > left_sum:
            left_sum = total
            max_left = index

    #right side: best stretch starting at mid + 1
    right_sum = float("-inf")
    total = 0
    max_right = mid + 1
    for index in range(mid + 1, right + 1):
        total += values[index]
        if total > right_sum:
            right_sum = total
            max_right = index
    return max_left, max_right, left_sum + right_sum


def find_max_subarray(values, left, right):
    if left == right:
        return left, right, values[left]

    mid = (left + right) // 2

    #best stretch entirely in the left half
    left_result = find_max_subarray(values, left, mid)

    #best stretch entirely in the right half
    right_result = find_max_subarray(values, mid + 1, right)

    #best stretch in the crossing middle
    cross_result = find_max_crossing(values, left, mid, right)

    #each result is (start, end, sum): keep the one with the biggest sum
    return max(left_result, right_result, cross_result, key=lambda result: result[2])


#O(n^2) reference: try every start and every end
def max_subarray_brute(values):

    best = (0, 0, values[0])

    for start in range(len(values)):
        total = 0

        for end in range(start, len(values)):
            total += values[end]

            if total > best[2]:
                best = (start, end, total)
    return best

#plumbing: tie rule (trim zero buckets at both ends) and the all-zero case
def normalize(values, result):
    start, end, total = result
    if total <= 0:
        return None
    while values[start] == 0:
        start += 1
    while values[end] == 0:
        end -= 1
    return start, end, total

#plumbing: converts buckets into times
def analyze(flights):
    load, day = build_load(flights)
    if day is None:
        return None
    divide_conquer = normalize(load, find_max_subarray(load, 0, len(load) - 1))
    reference = normalize(load, max_subarray_brute(load))
    if divide_conquer is None:
        return {"day": day, "result": None, "matches": reference is None}
    start, end, total = divide_conquer
    midnight = datetime(day.year, day.month, day.day)
    return {
        "day": day,
        "result": divide_conquer,
        "from": midnight + timedelta(minutes=5 * start),
        "to": midnight + timedelta(minutes=5 * (end + 1)),
        "matches": divide_conquer == reference,
    }
