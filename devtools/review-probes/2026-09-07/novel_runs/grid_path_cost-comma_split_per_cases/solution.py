import heapq
def path_cost(grid_text):
    if not isinstance(grid_text, str) or not grid_text: raise ValueError
    rows = [line.split(',') for line in grid_text.split('\n')]
    w = len(rows[0])
    if any(len(r) != w for r in rows): raise ValueError
    grid = []
    for r in rows:
        cells = []
        for c in r:
            if c == 'X': cells.append(None)
            elif c.isascii() and c.isdigit(): cells.append(int(c))
            else: raise ValueError
        grid.append(cells)
    if grid[0][0] is None and grid[-1][-1] is None: raise ValueError
    if grid[0][0] is None or grid[-1][-1] is None: return None
    h = len(grid); best = set(); heap = [(grid[0][0], 0, 0)]
    while heap:
        cost, r, c = heapq.heappop(heap)
        if (r, c) in best: continue
        best.add((r, c))
        if (r, c) == (h - 1, w - 1): return cost
        for dr, dc in ((0, 1), (1, 0)):
            nr, nc = r + dr, c + dc
            if nr < h and nc < w and grid[nr][nc] is not None and (nr, nc) not in best:
                heapq.heappush(heap, (cost + grid[nr][nc], nr, nc))
    return None
