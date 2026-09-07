import json, re
def free_minutes(busy_text):
    if not isinstance(busy_text, str): raise ValueError
    try: pairs = json.loads(busy_text)
    except ValueError: raise ValueError
    if not isinstance(pairs, list): raise ValueError
    covered = [False] * 1440
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2: raise ValueError
        vals = []
        for v in pair:
            if not isinstance(v, str) or not re.fullmatch(r'[0-9]{2}:[0-9]{2}', v): raise ValueError
            h, m = int(v[:2]), int(v[3:])
            if h > 23 or m > 59: raise ValueError  # "minutes 0 through 1439"; "times outside the day" -> ValueError
            vals.append(h * 60 + m)
        if vals[1] < vals[0]: raise ValueError
        for i in range(vals[0], vals[1]): covered[i] = True
    return 1440 - sum(covered)
