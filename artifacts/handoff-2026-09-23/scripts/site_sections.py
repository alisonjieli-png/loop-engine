import sys, re
sys.argv=[sys.argv[0]]
exec(open("site_inventory.py").read().split("def inv(path)")[0])
def inv(path):
    p=P(); p.feed(open(path).read()); return p
import collections
def sections(r):
    p=inv(f"idx-{r}.html"); d=collections.OrderedDict()
    for h in p.heads:
        d.setdefault(h["view"] or ("(" + h["ctx"] + ")"), []).append(f'{h["tag"]}: {h["text"][:90]}')
    body_links=collections.OrderedDict()
    for l in p.links:
        if l["ctx"]=="body": body_links.setdefault(l["view"], []).append(f'{l["href"]} | {l["text"][:40]}')
    return d, body_links
for r in ("3d2fe4e9","243a8811"):
    d,bl=sections(r); print(f"\n################ {r}")
    for v,hs in d.items():
        print(f"== view {v}"); [print("   ",h) for h in hs]
