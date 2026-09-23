import re, sys, json
from html.parser import HTMLParser

class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[]; self.links=[]; self.views=[]; self.heads=[]; self.cur_view=None; self.in_a=None; self.text=""; self.in_h=None
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        ctx=[t for t,_ in self.stack]
        if tag in ("header","footer","nav","main","section","div","aside"):
            pass
        if "data-view" in a:
            self.views.append((a["data-view"], a.get("id",""), "hidden" in a))
            self.cur_view=a["data-view"]
        void = tag in ("br","img","meta","link","input","hr","source","wbr","area","col","embed","param","track")
        if not void:
            self.stack.append((tag,a))
        if tag=="a":
            self.in_a={"href":a.get("href",""),"ctx":self.where(),"view":self.cur_view,"cls":a.get("class",""),"text":""}
        if tag in ("h1","h2","h3"):
            self.in_h={"tag":tag,"view":self.cur_view,"text":"","ctx":self.where()}
    def where(self):
        tags=[t for t,_ in self.stack]
        for t in ("header","footer"):
            if t in tags: return t
        return "body"
    def handle_endtag(self, tag):
        if tag=="a" and self.in_a is not None:
            self.in_a["text"]=re.sub(r"\s+"," ",self.in_a["text"]).strip(); self.links.append(self.in_a); self.in_a=None
        if tag in ("h1","h2","h3") and self.in_h is not None:
            self.in_h["text"]=re.sub(r"\s+"," ",self.in_h["text"]).strip(); self.heads.append(self.in_h); self.in_h=None
        # pop to matching
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                popped=self.stack[i:]; self.stack=self.stack[:i]
                if any("data-view" in aa for _,aa in popped): self.cur_view=next((aa["data-view"] for _,aa in reversed(self.stack) if "data-view" in aa), None)
                break
    def handle_data(self, d):
        if self.in_a is not None: self.in_a["text"]+=d
        if self.in_h is not None: self.in_h["text"]+=d

def inv(path):
    p=P(); p.feed(open(path).read())
    return p
for r in sys.argv[1:]:
    p=inv(f"idx-{r}.html")
    print(f"\n######## {r}")
    print("VIEWS:", [v[0] for v in p.views])
    print("HEADER LINKS:"); [print("   ", l["href"], "|", l["text"][:50]) for l in p.links if l["ctx"]=="header"]
    print("FOOTER LINKS:"); [print("   ", l["href"], "|", l["text"][:50]) for l in p.links if l["ctx"]=="footer"]
