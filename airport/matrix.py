#plumbing: building A
def _sort_codes(codes):
    # small insertion sort so no library sort is used anywhere
    for i in range(1, len(codes)):
        cur = codes[i]
        j = i - 1
        while j >= 0 and codes[j] > cur:
            codes[j + 1] = codes[j]
            j -= 1
        codes[j + 1] = cur
    return codes


def build_route_matrix(flights):
    codes = []
    for f in flights:
        for code in (f.origin, f.destination):
            if code not in codes:
                codes.append(code)
    codes = _sort_codes(codes)
    index = {code: i for i, code in enumerate(codes)}
    n = len(codes)
    A = [[0] * n for _ in range(n)]
    for f in flights:
        A[index[f.origin]][index[f.destination]] += 1
    return codes, A


#calssical multiply
def classical_multiply (A,B):
    n = len(A)
    C = [[0]*n for _ in range(n)] #makes an nxn matrix filled with 0's
    for i in range(n):
        for j in range(n):
            for k in range(n):
                C[i][j] += A[i][k] * B[k][j]
    return C