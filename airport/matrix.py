#plumbing: building A
def _sort_codes(codes):
    # small insertion sort so no library sort is used anywhere
    for next_index in range(1, len(codes)):
        current = codes[next_index]
        scan = next_index - 1
        while scan >= 0 and codes[scan] > current:
            codes[scan + 1] = codes[scan]
            scan -= 1
        codes[scan + 1] = current
    return codes


def build_route_matrix(flights):
    codes = []
    for flight in flights:
        for code in (flight.origin, flight.destination):
            if code not in codes:
                codes.append(code)
    codes = _sort_codes(codes)
    index_of = {code: position for position, code in enumerate(codes)}
    num_airports = len(codes)
    A = [[0] * num_airports for _ in range(num_airports)]      # A[origin][destination] = flight count
    for flight in flights:
        A[index_of[flight.origin]][index_of[flight.destination]] += 1
    return codes, A


#classical multiply
def classical_multiply (A, B):
    size = len(A)
    C = [[0] * size for _ in range(size)]    #makes a size x size matrix filled with 0's
    for row in range(size):
        for col in range(size):
            for inner in range(size):           # k in C[i][j] = sum over k of A[i][k] * B[k][j]
                C[row][col] += A[row][inner] * B[inner][col]
    return C



#plumbing: helpers for strassen
def add_matrices(X, Y):
    size = len(X)
    return [[X[row][col] + Y[row][col] for col in range(size)] for row in range(size)]


def subtract_matrices(X, Y):
    size = len(X)
    return [[X[row][col] - Y[row][col] for col in range(size)] for row in range(size)]


def split_into_quarters(M):
    half = len(M) // 2
    top_left     = [row[:half] for row in M[:half]]
    top_right    = [row[half:] for row in M[:half]]
    bottom_left  = [row[:half] for row in M[half:]]
    bottom_right = [row[half:] for row in M[half:]]
    return top_left, top_right, bottom_left, bottom_right


def join_quarters(top_left, top_right, bottom_left, bottom_right):
    top_half    = [top_left[r] + top_right[r] for r in range(len(top_left))]
    bottom_half = [bottom_left[r] + bottom_right[r] for r in range(len(bottom_left))]
    return top_half + bottom_half


def pad_with_zeros(M, new_size):
    old_size = len(M)
    return [[M[row][col] if row < old_size and col < old_size else 0
             for col in range(new_size)] for row in range(new_size)]


def crop_to_size(M, size):
    return [row[:size] for row in M[:size]]


#strassen itself

def strassen_multiply(A, B, cutoff=32):
    original_size = len(A)
    #padding: adding rows and columns of zeros
    padded_size = 1
    while padded_size < original_size:
        padded_size *= 2

    A_padded = pad_with_zeros(A, padded_size)
    B_padded = pad_with_zeros(B, padded_size)
    result = strassen_recursive(A_padded, B_padded, cutoff)
    return crop_to_size(result, original_size)


def strassen_recursive(A, B, cutoff):
    size = len(A)
    if size <= cutoff:
        return classical_multiply(A, B)

    A_tl, A_tr, A_bl, A_br = split_into_quarters(A)
    B_tl, B_tr, B_bl, B_br = split_into_quarters(B)

   
    p1 = strassen_recursive(add_matrices(A_tl, A_br), add_matrices(B_tl, B_br), cutoff)
    p2 = strassen_recursive(add_matrices(A_bl, A_br), B_tl, cutoff)
    p3 = strassen_recursive(A_tl, subtract_matrices(B_tr, B_br), cutoff)
    p4 = strassen_recursive(A_br, subtract_matrices(B_bl, B_tl), cutoff)
    p5 = strassen_recursive(add_matrices(A_tl, A_tr), B_br, cutoff)
    p6 = strassen_recursive(subtract_matrices(A_bl, A_tl), add_matrices(B_tl, B_tr), cutoff)
    p7 = strassen_recursive(subtract_matrices(A_tr, A_br), add_matrices(B_bl, B_br), cutoff)

   
    C_tl = add_matrices(subtract_matrices(add_matrices(p1, p4), p5), p7)   # p1 + p4 - p5 + p7
    C_tr = add_matrices(p3, p5)                                             # p3 + p5
    C_bl = add_matrices(p2, p4)                                             # p2 + p4
    C_br = add_matrices(add_matrices(subtract_matrices(p1, p2), p3), p6)   # p1 - p2 + p3 + p6

    return join_quarters(C_tl, C_tr, C_bl, C_br)

