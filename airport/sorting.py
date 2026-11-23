
#counting sort to sort flights by priority
def counting_sort_priority(flights):
    k = 3
    count = [0] * (k+1)
    for f in flights:
        count[f.priority] += 1

    for p in range (2, k+1):
        count[p] += count [p-1]

    output = [None] * len(flights)
    for f in reversed(flights):
        count[f.priority] -= 1
        output[count[f.priority]] = f
    return output