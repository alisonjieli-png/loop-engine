def spiral_sum(matrix):
    if not isinstance(matrix, list): raise ValueError
    if not matrix: return 0
    if any(not isinstance(r, list) for r in matrix): raise ValueError
    w = len(matrix[0])
    if any(len(r) != w for r in matrix): raise ValueError
    for r in matrix:
        for v in r:
            if type(v) is not int: raise ValueError
    return sum(v for r in matrix for v in r)   # no spiral walk at all
