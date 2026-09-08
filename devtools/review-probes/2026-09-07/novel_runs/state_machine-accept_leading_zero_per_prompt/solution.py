import re
def final_state(text):
    if not isinstance(text, str) or not text: raise ValueError
    if text != text.strip(' ') or '  ' in text: raise ValueError
    acc = 0
    for cmd in text.split(' '):
        if cmd == 'd': acc *= 2
        elif cmd == 'r': acc = 0
        elif re.fullmatch(r'[+-]?[0-9]+', cmd): acc += int(cmd)  # "optionally signed ASCII decimal integer"
        else: raise ValueError
    return acc
