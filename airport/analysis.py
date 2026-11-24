from datetime import datetime, timedelta

def build_load(flights):

    if len(flights) == 0:
        return [], None
    
    day = min(f.orig_start for f in flights).date()
    load = [0] * 288

    for f in flights:
        if f.status in( "DELAYED" , "CANCELLED") and f.orig_start.date() == day:
            i = (f.orig_start.hour * 60 + f.orig_start.minute) // 5
            load[i] += 1

    return load, day


#in the logical sense there wont be any negative values as it's
#the number of flights. however, this algorithm is the general 
#version that handles negative values
def find_max_crossing (A, left,mid, right):
    #left side
    left_sum = float ("-inf")
    total = 0
    max_left = mid
    for i in range (mid, left-1, -1):
        total += A[i]
        if total > left_sum:
            left_sum = total
            max_left = i

    #right side
    right_sum = float("-inf")
    total = 0
    max_right = mid+1
    for j in range (mid+1, right + 1):
        total += A[j]
        if total > right_sum:
            right_sum = total
            max_right = j
    return max_left, max_right, left_sum + right_sum


def find_max_subarray(A, left, right):
    if left == right:
        return left, right, A[left]

    mid = (left+right) // 2

    #best stretch entirely in the left half
    left_result = find_max_subarray(A, left, mid)
    
    #best stretch entirely in the right half
    right_result = find_max_subarray(A, mid+1, right)
    
    #best stretch in the crossing middle
    cross_result = find_max_crossing(A, left, mid, right)

    return max(left_result, right_result, cross_result, key=lambda r: r[2])


def max_subarray_brute(A):

    best = (0,0,A[0])

    for i in range (len(A)):
        total = 0

        for j in range (i, len(A)):
            total += A[j]

            if total > best [2]:
                best = (i,j,total)
    return best

#plumbing
def normalize(A, result):
    start, end, total = result
    if total <= 0:
        return None                      
    while A[start] == 0:
        start += 1
    while A[end] == 0:
        end -= 1
    return start, end, total

#plumbing: converts buckets into times
def analyze(flights):
    load, day = build_load(flights)
    if day is None:
        return None
    dc = normalize(load, find_max_subarray(load, 0, len(load) - 1))
    ref = normalize(load, max_subarray_brute(load))
    if dc is None:
        return {"day": day, "result": None, "matches": ref is None}
    start, end, total = dc
    midnight = datetime(day.year, day.month, day.day)
    return {
        "day": day,
        "result": dc,
        "from": midnight + timedelta(minutes=5 * start),
        "to": midnight + timedelta(minutes=5 * (end + 1)),
        "matches": dc == ref,
    }