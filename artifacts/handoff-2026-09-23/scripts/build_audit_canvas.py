import re, json, html
F = "/home/username/.le-ci-tmp/logo-sheet/final/"
def inner(f):
    s = open(F + f).read(); s = re.sub(r'^<svg[^>]*>', '', s)[:-len('</svg>')]; return re.sub(r'<title>.*?</title>', '', s)
MARK = f'<svg width="0" height="0" style="position: absolute;" aria-hidden="true"><defs><symbol id="m52" viewBox="0 0 1000 1000">{inner("baltor-mark.svg")}</symbol></defs></svg>'
def mark(px): return f'<svg width="{px}" height="{px}" viewBox="0 0 1000 1000" aria-hidden="true"><use href="#m52"></use></svg>'
E = html.escape
HEAD = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous">
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&amp;family=Geist+Mono:wght@400;500&amp;display=swap" rel="stylesheet">
<style>body{{margin:0;font-family:Geist,"Helvetica Neue",Helvetica,system-ui,sans-serif;color:#0A1020;background:#F5F6F8;-webkit-font-smoothing:antialiased}}h1,h2,h3,p{{margin:0}}a{{color:#2E5BFF;text-underline-offset:4px}}a:hover{{color:#1C44D6}}</style>
</helmet>
'''
TAIL = '''</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":{w},"height":{h}}}}}'>
class Component extends DCLogic {{
renderVals() {{
return {{}};
}}
}}
</script>
</body>
</html>
'''
ST = {  # state -> (background, text, border, decoration, label)
 "kept": ("#FFFFFF", "#3A4456", "#CBD2DC", "none", "Kept"),
 "cut": ("#FDECEC", "#B42318", "#F4B4AE", "line-through", "Cut"),
 "new": ("#EEF2FF", "#1C44D6", "#B9C8FF", "none", "New"),
 "restoring": ("#E6F4EE", "#0E7A52", "#A8DCC4", "none", "Restoring"),
 "queued": ("#EEF1F5", "#556070", "#CBD2DC", "none", "Queued"),
 "primary": ("#2E5BFF", "#FFFFFF", "#2E5BFF", "none", "Primary"),
}
def chip(text, st="kept", note=""):
    bg, fg, bd, deco, _ = ST[st]
    n = f'<span style="font-size: 12px; font-weight: 500; opacity: 0.8;">{E(note)}</span>' if note else ""
    return f'<span style="display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px; border-radius: 10px; background: {bg}; color: {fg}; border: 1px solid {bd}; font-size: 14px; font-weight: 500; text-decoration: {deco}; white-space: nowrap;">{E(text)}{n}</span>'
def badge(st):
    bg, fg, bd, _, label = ST[st]
    return f'<span style="display: inline-flex; padding: 3px 9px; border-radius: 6px; background: {bg}; color: {fg}; border: 1px solid {bd}; font-size: 12.5px; font-weight: 600; white-space: nowrap;">{label}</span>'
def row(label, chips, sub=""):
    s = f'<p style="font-size: 13px; color: #556070; margin-top: 4px;">{E(sub)}</p>' if sub else ""
    return f'<div style="display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 24px; align-items: start; padding: 18px 0; border-top: 1px solid #E2E6EC;"><div><p style="font-size: 15px; font-weight: 600;">{E(label)}</p>{s}</div><div style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center;">{"".join(chips)}</div></div>'
def section(eyebrow, title, body, lead=""):
    l = f'<p style="font-size: 16px; line-height: 1.6; color: #3A4456; max-width: 860px;">{lead}</p>' if lead else ""
    return f'<section style="display: flex; flex-direction: column; gap: 14px; background: #FFFFFF; border: 1px solid #E2E6EC; border-radius: 18px; padding: 32px 36px;"><p style="font-size: 12.5px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #2E5BFF;">{E(eyebrow)}</p><h2 style="font-size: 26px; line-height: 1.2; font-weight: 650; letter-spacing: -0.02em;">{E(title)}</h2>{l}<div>{body}</div></section>'
def table(cols, widths, rows):
    th = "".join(f'<th scope="col" style="text-align: left; font-size: 12.5px; font-weight: 600; color: #556070; padding: 10px 14px 10px 0; border-bottom: 1px solid #CBD2DC;">{E(c)}</th>' for c in cols)
    trs = []
    for r in rows:
        tds = []
        for i, cell in enumerate(r):
            style = "font-family: \'Geist Mono\', ui-monospace, monospace; font-size: 13px;" if i == 0 else "font-size: 14px;"
            tds.append(f'<td style="vertical-align: top; padding: 11px 14px 11px 0; border-bottom: 1px solid #E2E6EC; color: #0A1020; line-height: 1.45; {style}">{cell}</td>')
        trs.append("<tr>" + "".join(tds) + "</tr>")
    cg = "".join(f'<col style="width: {w};">' for w in widths)
    return f'<table style="width: 100%; border-collapse: collapse; table-layout: fixed;"><colgroup>{cg}</colgroup><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table>'

# ---------------- Main: the inventory ----------------
W = 1440; H = 4200
legend = "".join(chip(ST[s][4], s) for s in ("kept", "cut", "new", "restoring", "queued"))
hdr_rows = "".join([
 row("Release 17", [chip("Get started"), chip("How it works"), chip("Pricing"), chip("Documentation"), chip("Workspace", note="signed in"), chip("Account", note="signed in"), chip("Sign in ↗"), chip("Administration", note="operator")], "The last site before the redesign (3d2fe4e9); Get started opened the setup guide"),
 row("Live now, release 20", [chip("Get started", "cut"), chip("How it works"), chip("Library", "new"), chip("Pricing"), chip("Docs"), chip("Sign in"), chip("Request an invitation", "primary")], "Workspace, Account, Administration and Sign out appear once signed in"),
 row("Restored, signed out", [chip("How it works"), chip("Use cases", "new"), chip("Library"), chip("Pricing"), chip("Docs"), chip("Sign in"), chip("Get started", "primary")], "Get started is now the sign-up and payment funnel, the one primary action in every state"),
 row("Restored, signed in", [chip("Workspace"), chip("Get set up", "restoring"), chip("Library"), chip("Docs"), chip("Account"), chip("Sign out"), chip("Administration", note="operator")], "Get set up is the setup guide that release 17 called Get started"),
])
header_sec = section("Header", "One link was cut from the header: Get started.", hdr_rows,
 "The redesign (43d6eeb4) set the header to “the wordmark, five links and one primary action”, and 607c3a4d kept “one invitation action”. Get started lost its place to Library and the invitation button. It comes back first, and Use cases joins it for the pages that were built but never shipped.")

def col(title, items, sub=""):
    s = f'<p style="font-size: 13px; color: #556070;">{E(sub)}</p>' if sub else ""
    its = "".join(f'<div>{c}</div>' for c in items)
    return f'<div style="display: flex; flex-direction: column; gap: 10px; min-width: 0;"><p style="font-size: 15px; font-weight: 600;">{E(title)}</p>{s}<div style="display: flex; flex-direction: column; gap: 7px; align-items: flex-start;">{its}</div></div>'
def group(name, items):
    its = "".join(f'<div>{c}</div>' for c in items)
    return f'<div style="display: flex; flex-direction: column; gap: 7px; align-items: flex-start;"><p style="font-size: 12px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: #556070; margin-top: 4px;">{E(name)}</p>{its}</div>'
foot_body = f'''<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 32px; padding-top: 8px;">
{col("Release 17", [chip("Get started"), chip("How it works"), chip("Pricing"), chip("Request access"), chip("First example"), chip("Access and data"), chip("Documentation"), chip("Privacy notice"), chip("Open-source notices")], "One flat row of nine links")}
<div style="display: flex; flex-direction: column; gap: 10px;"><p style="font-size: 15px; font-weight: 600;">Live now, release 20</p><p style="font-size: 13px; color: #556070;">Three groups; the four benefit pages never shipped</p>
{group("Product", [chip("Get started", "cut"), chip("Request an invitation"), chip("How it works"), chip("Library", "new"), chip("Pricing"), chip("First example")])}
{group("Developers", [chip("Documentation"), chip("Access and data"), chip("Open-source notices")])}
{group("Company", [chip("Privacy notice"), chip("Terms: not yet published", "queued"), chip("Contact: by post")])}
{group("Never shipped", [chip("Interrupted work", "cut"), chip("Less in each request", "cut"), chip("Model choice", "cut"), chip("Tool choice", "cut")])}</div>
<div style="display: flex; flex-direction: column; gap: 10px;"><p style="font-size: 15px; font-weight: 600;">Restored</p><p style="font-size: 13px; color: #556070;">Four groups and a base row</p>
{group("Product", [chip("Get started", "new"), chip("Get set up", "restoring"), chip("How it works"), chip("Library"), chip("Pricing"), chip("First example")])}
{group("Use cases", [chip("Use cases", "new"), chip("Overnight work", "restoring"), chip("Less in each request", "restoring"), chip("Model choice", "restoring"), chip("Tool choice", "restoring"), chip("For coding agents", "restoring"), chip("For engineering teams", "restoring"), chip("Comparing tools", "restoring"), chip("Protocol and client", "restoring")])}
{group("Documentation", [chip("Docs"), chip("Seven documentation pages", "restoring"), chip("Bring your own model", "restoring"), chip("What your machine can run", "restoring"), chip("Access and data"), chip("Status", "restoring")])}
{group("Company", [chip("What Baltor is", "restoring"), chip("Request an invitation"), chip("Sign in", "new"), chip("Privacy notice"), chip("Terms of service", "new"), chip("Open-source notices")])}</div>
</div>'''
footer_sec = section("Footer", "The footer lost Get started, and eight use-case pages never reached it.", foot_body,
 "The redesign grouped the footer and dropped Get started. The four benefit pages and four audience pages were built on September 21 and 22 but sat on an unmerged line, so no footer ever linked them live.")

P = lambda a: f'<span>{E(a)}</span>'
pages = [
 ("/", "Homepage", "yes", "yes, four sections cut", "restoring", "Put the cut sections back, short", "43d6eeb4 rebuilt it from the design canvas"),
 ("/connect", "Get started", "nine sections", "three steps; header link cut", "restoring", "Header link back; missing steps folded into the three", "43d6eeb4 “five links”; 607c3a4d “one invitation action”"),
 ("/waitlist", "Request an invitation", "its own page", "a panel inside Get started", "restoring", "Its own focused page again; Get started links to it", "607c3a4d \u201cone invitation action\u201d"),
 ("/how-it-works", "How it works", "yes", "yes", "kept", "", ""),
 ("/pricing", "Pricing", "yes", "yes", "kept", "Say “$29 a month”", ""),
 ("/docs", "Docs", "written by hand", "written by hand", "restoring", "Becomes the index of the documentation pages", ""),
 ("/docs/…", "Seven documentation pages", "never merged", "missing", "restoring", "Set up, search, connections, troubleshooting, account, usage, what Baltor is", "Built 2026-09-21 on a branch; never merged"),
 ("/examples", "First example", "yes", "yes", "kept", "", ""),
 ("/security", "Access and data", "yes", "yes", "kept", "", ""),
 ("/privacy", "Privacy notice", "yes", "yes", "kept", "", ""),
 ("/terms", "Terms of service", "no", "“not yet published”", "new", "Approved by the owner today; ships in release 21", ""),
 ("/overnight · /context · /model-choice · /tool-choice", "Four benefit pages", "never merged", "missing", "restoring", "In the new design, one action each", "Waited on the consolidation line since 2026-09-22"),
 ("/for/…", "Four audience pages", "never merged", "missing", "restoring", "Coding agents, engineering teams, comparing tools, protocol and client", "Same line"),
 ("/use-cases", "Use cases hub", "no", "no", "new", "Cards for the eight pages", ""),
 ("/status", "Status", "never merged", "a status line in the footer", "restoring", "Reads the existing health record", "Its route never landed"),
 ("/login · /signup · /app · /account · /admin", "Sign in, sign-up, workspace, account, administration", "yes", "yes", "kept", "", ""),
 ("/models", "Bring your own model", "never merged", "missing", "restoring", "Local Ollama, Ollama Cloud, a machine on your network, or a provider key", "4 of its own 17 checks failed on its branch"),
 ("/machine-fit", "What your machine can run", "never merged", "missing", "restoring", "The command and a small picker share one tested table", "Never reviewed; over the length cap"),
 ("refusal wording", "Messages for 14 refusals", "never merged", "missing", "restoring", "Plain wording and next actions where visitors see refusals", "Waited for the website line"),
]
prow = [[P(a), E(b), E(c), E(d), badge(st) + (f'<div style="margin-top: 6px; color: #3A4456;">{E(plan)}</div>' if plan else ""), f'<span style="color: #556070;">{E(why)}</span>'] for a, b, c, d, st, plan, why in pages]
pages_sec = section("Pages and addresses", "Every address that ever served a page, and what happens to it.",
 table(["Address", "Page", "Release 17", "Live now", "Decision", "Why it went"], ["19%", "15%", "11%", "14%", "23%", "18%"], prow))

home = [
 ("Ask, choose, keep the record", "cut", "Compare with “One fresh harness for each step”; put back what the new band lacks"),
 ("Four things you can do today", "restoring", "A short “Available today” strip: search, download and check, connect, see what your tools took"),
 ("Six things your agents get for each step", "kept", "Now “Right-sized help for every step of the work”"),
 ("Spend more time on the problem", "restoring", "One line in the closing band, or its own short band"),
 ("Plan, build and review with the information each step needs", "restoring", "Merge into “One fresh harness for each step”"),
 ("One plan. Search is free.", "kept", ""),
 ("Bring your next task to Baltor.", "kept", ""),
]
setup = [
 ("What you need", "restoring", "Inside step 1"),
 ("Get the part that runs on your machine", "restoring", "Inside step 2"),
 ("Choose a connection entry for your tool", "kept", "Now tabs in step 2"),
 ("Keep the token out of your files", "restoring", "Inside step 2"),
 ("Check the service, then the client", "restoring", "The service check stayed; the client check comes back"),
 ("Create an account when your invitation arrives", "kept", "Step 1"),
 ("Revoke the token when you no longer need it", "kept", "“When you no longer need it”"),
 ("Try one useful retrieval", "kept", "Step 3, “Search and download”; wording to check"),
]
def srows(items): return [[f'<span style="font-family: Geist, sans-serif; font-size: 14px; font-weight: 500;">{E(a)}</span>', badge(st), f'<span style="color: #3A4456;">{E(n)}</span>'] for a, st, n in items]
sections_body = f'''<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 40px;">
<div style="display: flex; flex-direction: column; gap: 12px;"><h3 style="font-size: 18px; font-weight: 650;">Homepage sections in release 17</h3>{table(["Section", "Now", "Decision"], ["40%", "18%", "42%"], srows(home))}</div>
<div style="display: flex; flex-direction: column; gap: 12px;"><h3 style="font-size: 18px; font-weight: 650;">Get started: nine sections became three steps</h3>{table(["Section", "Now", "Decision"], ["40%", "18%", "42%"], srows(setup))}</div>
</div>'''
sections_sec = section("Sections inside pages", "What the homepage and Get started lost.", sections_body,
 "The owner asked for less text, so the redesign shortened pages. Shortening is fine; losing what a person needs is not. The paragraph-by-paragraph check is under way, so these rows may still change.")

hosts = [("baltor.ai", "Homepage", "Homepage"), ("www.baltor.ai", "Homepage", "Homepage"), ("app.baltor.ai", "Homepage", "Workspace"), ("docs.baltor.ai", "Homepage", "Docs"), ("status.baltor.ai", "Homepage", "Status"), ("examples.baltor.ai", "Homepage", "First example"), ("demo.baltor.ai", "Homepage", "The one-step demonstration"), ("baltor-pilot.fly.dev", "Homepage", "Homepage")]
hrows = [[P(h), E(n), (badge("kept") if n == t else badge("restoring")) + f'<span style="margin-left: 8px;">{E(t)}</span>'] for h, n, t in hosts]
hosts_sec = section("Hostnames", "Eight hostnames answer; all show the same homepage.", table(["Hostname", "Its root shows now", "Its root will show"], ["30%", "25%", "45%"], hrows),
 "The page for each hostname was designed on a branch that never reached a commit on main. Every other address keeps working on every hostname, and each page names its baltor.ai address as the original.")

work = [("Header, footer, homepage and Get set up", "The cut links and sections come back inside the new design, with lighter bands and less text."),
 ("Get started funnel", "Create account, confirm email, choose a password, subscribe, get set up; the invitation request while sign-up is closed."),
 ("Model and machine pages", "Bring your own model, what your machine can run, and plain refusal wording, each reviewed independently."),
 ("Use-case pages, the hub, Status and hostnames", "Eight pages from the unmerged line, one action each; Status reads the existing health record."),
 ("Documentation pages", "Seven pages and the three customer pages, each checked by a reviewer who did not write it."),
 ("Design standards and two new checks", "One spacing scale and header and footer contract; a check fails when a page or link goes missing."),
 ("Screenshots and design review", "Every page at 1440 and 390 pixels, before and after, with measured padding and empty space."),
 ("Paragraph-level inventory", "Every cut sentence, link and badge with its recorded reason, to confirm this board.")]
work_body = '<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px;">' + "".join(f'<div style="border: 1px solid #E2E6EC; border-radius: 14px; padding: 18px 20px; display: flex; flex-direction: column; gap: 8px; background: #FAFBFC;"><p style="font-size: 15px; font-weight: 600;">{E(t)}</p><p style="font-size: 14px; line-height: 1.5; color: #3A4456;">{E(d)}</p></div>' for t, d in work) + "</div>"
work_sec = section("In progress", "Eight workstreams, each in its own workspace; one release brings them together.", work_body)

main = HEAD.format(title="Cut inventory") + f'''{MARK}
<div style="width: {W}px; height: {H}px; box-sizing: border-box; padding: 64px; background: #F5F6F8; display: flex; flex-direction: column; gap: 28px;">
<div style="display: flex; align-items: center; gap: 12px;">{mark(36)}<span style="font-size: 20px; font-weight: 700; letter-spacing: -0.02em;">Baltor</span><span style="font-size: 14px; color: #556070; margin-left: 8px;">Website audit, September 23, 2026</span></div>
<div style="display: flex; flex-direction: column; gap: 14px; max-width: 1040px;">
<h1 style="font-size: 48px; line-height: 1.08; font-weight: 700; letter-spacing: -0.035em;">What the redesign cut, why, and where each piece returns.</h1>
<p style="font-size: 18px; line-height: 1.6; color: #3A4456;">The live site (release 20) compared with release 17, the last site before the redesign, and with the pages that were built but never merged. Every row carries a decision. Nothing is removed again without a recorded reason.</p>
<div style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center;"><span style="font-size: 13px; color: #556070; margin-right: 4px;">Key</span>{legend}</div>
</div>
{header_sec}
{footer_sec}
{pages_sec}
{sections_sec}
{hosts_sec}
{work_sec}
</div>
''' + TAIL.format(w=W, h=H)
open("project/Main.dc.html", "w").write(main)

# ---------------- Header: restored states ----------------
def nav(links, current=None):
    out = []
    for t in links:
        cur = t == current
        out.append(f'<a href="#" style="padding: 8px 0; color: {"#0A1020" if cur else "#3A4456"}; font-size: 15px; font-weight: 500; text-decoration: none; white-space: nowrap;{" box-shadow: 0 2px 0 #2E5BFF;" if cur else ""}">{E(t)}</a>')
    return "".join(out)
ACC = '<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" style="fill: none; stroke: currentColor; stroke-width: 1.9; stroke-linecap: round; stroke-linejoin: round;"><circle cx="12" cy="8" r="4"></circle><path d="M4 21a8 8 0 0 1 16 0"></path></svg>'
def bar(left_links, right, current=None):
    return f'''<header style="display: flex; align-items: center; gap: 8px 32px; min-height: 72px; padding: 0 64px; background: #FFFFFF; border-bottom: 1px solid #E2E6EC; box-sizing: border-box;">
<a href="#" style="display: inline-flex; align-items: center; gap: 10px; color: #0A1020; font-size: 20px; font-weight: 700; letter-spacing: -0.02em; text-decoration: none;">{mark(32)}<span>Baltor</span></a>
<nav aria-label="Main navigation" style="display: flex; align-items: center; gap: 0 32px; flex: 1; min-width: 0;">{nav(left_links, current)}</nav>
<div style="display: flex; align-items: center; gap: 24px;">{right}</div></header>'''
SIGNIN = '<a href="#" style="color: #3A4456; font-size: 15px; font-weight: 500; text-decoration: none;">Sign in</a>'
PRIMARY = lambda t: f'<a href="#" style="display: inline-flex; align-items: center; min-height: 44px; padding: 8px 20px; border-radius: 10px; background: #2E5BFF; color: #FFFFFF; font-size: 15px; font-weight: 600; text-decoration: none;">{E(t)}</a>'
SIGNOUT = '<button type="button" style="min-height: 44px; padding: 8px 20px; border-radius: 10px; border: 1px solid #CBD2DC; background: #FFFFFF; color: #0A1020; font: 600 15px Geist, sans-serif;">Sign out</button>'
ACCOUNT = f'<a href="#" style="display: inline-flex; align-items: center; gap: 8px; color: #0A1020; font-size: 15px; font-weight: 600; text-decoration: none;">{ACC}<span>Account</span></a>'
PUB = ["How it works", "Use cases", "Library", "Pricing", "Docs"]
IN = ["Workspace", "Get set up", "Library", "Docs"]
def frame(label, note, inner_html):
    return f'<div style="display: flex; flex-direction: column; gap: 10px;"><div style="display: flex; align-items: baseline; gap: 12px;"><p style="font-size: 16px; font-weight: 600;">{E(label)}</p><p style="font-size: 14px; color: #556070;">{E(note)}</p></div><div style="border: 1px solid #E2E6EC; border-radius: 14px; overflow: hidden; background: #F5F6F8;">{inner_html}<div style="height: 36px;"></div></div></div>'
phone_menu = f'''<div style="width: 390px; border: 1px solid #E2E6EC; border-radius: 22px; overflow: hidden; background: #FFFFFF; flex-shrink: 0;">
<div style="display: flex; align-items: center; justify-content: space-between; min-height: 64px; padding: 0 16px; border-bottom: 1px solid #E2E6EC;"><a href="#" style="display: inline-flex; align-items: center; gap: 10px; color: #0A1020; font-size: 19px; font-weight: 700; text-decoration: none;">{mark(30)}<span>Baltor</span></a>
<button type="button" aria-label="Close the menu" style="width: 44px; height: 44px; display: grid; place-items: center; border: 1px solid #CBD2DC; border-radius: 10px; background: #FFFFFF;"><svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" style="fill: none; stroke: #0A1020; stroke-width: 2; stroke-linecap: round;"><path d="M6 6l12 12M18 6L6 18"></path></svg></button></div>
<nav aria-label="Main navigation" style="display: flex; flex-direction: column; padding: 8px 16px 16px;">{"".join(f'<a href="#" style="display: flex; align-items: center; min-height: 52px; border-bottom: 1px solid #E2E6EC; color: #0A1020; font-size: 17px; font-weight: 500; text-decoration: none;">{E(t)}</a>' for t in PUB + ["Sign in"])}
<a href="#" style="display: flex; align-items: center; justify-content: center; min-height: 52px; margin-top: 16px; border-radius: 12px; background: #2E5BFF; color: #FFFFFF; font-size: 17px; font-weight: 600; text-decoration: none;">Get started</a></nav></div>'''
HW, HH = 1440, 1500
header_board = HEAD.format(title="Restored header") + f'''{MARK}
<div style="width: {HW}px; height: {HH}px; box-sizing: border-box; padding: 64px; background: #F5F6F8; display: flex; flex-direction: column; gap: 36px;">
<div style="display: flex; flex-direction: column; gap: 12px; max-width: 980px;"><p style="font-size: 12.5px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #2E5BFF;">Restored header</p>
<h1 style="font-size: 40px; line-height: 1.1; font-weight: 700; letter-spacing: -0.03em;">Get started is the funnel. Get set up is the guide.</h1>
<p style="font-size: 17px; line-height: 1.6; color: #3A4456;">Drawn with the site's own header rules: 72 pixels tall, 64 pixel gutters, links at 15 pixels in #3A4456, the current page underlined in #2E5BFF. Below 860 pixels the links fold into a menu that works without the page script.</p></div>
{frame("Signed out", "Get started is the one primary action: the sign-up and payment funnel", bar(PUB, SIGNIN + PRIMARY("Get started"), "How it works"))}
{frame("Signed out, invitation only", "the label never switches; the funnel page shows the invitation request instead of the sign-up form", bar(PUB, SIGNIN + PRIMARY("Get started"), "Pricing"))}
{frame("Signed in", "Get set up, the guide, joins the header once an account exists", bar(IN, ACCOUNT + SIGNOUT, "Get set up"))}
{frame("Operator", "Administration appears for the operator only", bar(IN + ["Administration"], ACCOUNT + SIGNOUT, "Workspace"))}
<div style="display: flex; gap: 48px; align-items: flex-start;">{phone_menu}
<div style="display: flex; flex-direction: column; gap: 12px; max-width: 620px; padding-top: 8px;"><p style="font-size: 16px; font-weight: 600;">Phone, menu open</p><p style="font-size: 15px; line-height: 1.6; color: #3A4456;">Every header link is in the menu in the same order, each row at least 52 pixels tall. Get started sits last and full width. Library opens the homepage section; Use cases opens the hub of eight pages; Get set up is one tap away from Docs.</p>
<p style="font-size: 15px; line-height: 1.6; color: #3A4456;">The new layout check measures this bar at 1440, 1024 and 860 pixels, so a link that no longer fits shows up as a failed check, not a silent overflow.</p></div></div>
</div>
''' + TAIL.format(w=HW, h=HH)
open("project/Header.dc.html", "w").write(header_board)

# ---------------- Footer: restored ----------------
def fl(t, muted=False): return f'<a href="#" style="color: {"#556070" if muted else "#3A4456"}; font-size: 15px; text-decoration: none;">{E(t)}</a>'
def fgroup(name, links):
    return f'<nav aria-label="{E(name)}" style="display: flex; flex-direction: column; gap: 12px; align-items: flex-start; min-width: 0;"><p style="font-size: 13px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: #556070;">{E(name)}</p>{"".join(fl(l) for l in links)}</nav>'
G = [("Product", ["Get started", "Get set up", "How it works", "Library", "Pricing", "First example"]),
     ("Use cases", ["All use cases", "Overnight work", "Less in each request", "Model choice", "Tool choice", "For coding agents", "For engineering teams", "Comparing tools", "Protocol and client"]),
     ("Documentation", ["Docs", "Searching and retrieving", "Serving and connections", "Troubleshooting", "Your account", "Usage and what you pay for", "Bring your own model", "What your machine can run", "Access and data", "Status"]),
     ("Company", ["What Baltor is", "Request an invitation", "Sign in", "Privacy notice", "Terms of service", "Open-source notices"])]
brand_col = f'<div style="display: flex; flex-direction: column; gap: 14px; min-width: 0;"><a href="#" style="display: inline-flex; align-items: center; gap: 10px; color: #0A1020; font-size: 20px; font-weight: 700; letter-spacing: -0.02em; text-decoration: none;">{mark(32)}<span>Baltor</span></a><p style="font-size: 15px; line-height: 1.55; color: #556070; max-width: 260px;">Harness and agent optimized operation.</p><p style="display: inline-flex; align-items: center; gap: 8px; font-size: 14px; color: #3A4456;"><span style="width: 8px; height: 8px; border-radius: 50%; background: #0E7A52;"></span>Service available · <a href="#">Status</a></p></div>'
FW, FH = 1440, 1720
footer_board = HEAD.format(title="Restored footer") + f'''{MARK}
<div style="width: {FW}px; height: {FH}px; box-sizing: border-box; padding: 64px; background: #F5F6F8; display: flex; flex-direction: column; gap: 32px;">
<div style="display: flex; flex-direction: column; gap: 12px; max-width: 980px;"><p style="font-size: 12.5px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #2E5BFF;">Restored footer</p>
<h1 style="font-size: 40px; line-height: 1.1; font-weight: 700; letter-spacing: -0.03em;">Four groups: every page is one click from any page.</h1>
<p style="font-size: 17px; line-height: 1.6; color: #3A4456;">The redesign's footer, with a fourth group for use cases and the documentation pages listed by name. The base row keeps the operator line the privacy notice already publishes.</p></div>
<div style="border: 1px solid #E2E6EC; border-radius: 14px; overflow: hidden;">
<footer style="background: #FFFFFF; padding: 64px 64px 48px; color: #3A4456;">
<div style="display: grid; grid-template-columns: minmax(0, 1.4fr) repeat(4, minmax(0, 1fr)); gap: 40px;">{brand_col}{"".join(fgroup(n, l) for n, l in G)}</div>
<div style="display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px 32px; margin-top: 48px; padding-top: 24px; border-top: 1px solid #E2E6EC; color: #556070; font-size: 14px;"><p>© 2026 Baltor.AI · 1428 Bryn Mawr St, Saxton, PA 16678</p><p>Your model keys stay with you.</p><button type="button" style="min-height: 40px; padding: 6px 14px; border-radius: 10px; border: 1px solid #CBD2DC; background: #FFFFFF; color: #2E5BFF; font: 600 13px Geist, sans-serif;">Appearance: light</button></div>
</footer></div>
<div style="display: flex; gap: 48px; align-items: flex-start;">
<div style="width: 390px; border: 1px solid #E2E6EC; border-radius: 22px; overflow: hidden; background: #FFFFFF; flex-shrink: 0;"><footer style="padding: 32px 16px 24px; display: flex; flex-direction: column; gap: 28px;">{brand_col}
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 28px 16px;">{"".join(fgroup(n, l[:5] + (["More…"] if len(l) > 5 else [])) for n, l in G)}</div>
<div style="padding-top: 16px; border-top: 1px solid #E2E6EC; color: #556070; font-size: 13px; line-height: 1.5;">© 2026 Baltor.AI · 1428 Bryn Mawr St, Saxton, PA 16678</div></footer></div>
<div style="display: flex; flex-direction: column; gap: 12px; max-width: 640px; padding-top: 8px;"><p style="font-size: 16px; font-weight: 600;">Phone</p><p style="font-size: 15px; line-height: 1.6; color: #3A4456;">Two columns of groups. On a phone the long groups show their first five links and a sixth that opens the group's hub (Use cases, Docs), so the footer stays under two screens tall. Each link keeps a tap area at least 44 pixels tall.</p>
<p style="font-size: 15px; line-height: 1.6; color: #3A4456;">The status line reads the live health record once the Status page ships; until then it keeps today's wording.</p></div></div>
</div>
''' + TAIL.format(w=FW, h=FH)
open("project/Footer.dc.html", "w").write(footer_board)

canvas = {"v": 3, "createdOnFiles": {"v": 1, "at": "2026-09-23T13:30:00Z"}, "title": "Baltor website audit", "launch": {"view": "canvas"}, "pages": [],
 "boards": {"Main.dc.html": {"x": 0, "y": 0, "w": W, "h": H, "title": "Cut inventory"},
            "Header.dc.html": {"x": W + 80, "y": 0, "w": HW, "h": HH, "title": "Restored header"},
            "Footer.dc.html": {"x": W + 80, "y": HH + 120, "w": FW, "h": FH, "title": "Restored footer"}},
 "order": ["Main.dc.html", "Header.dc.html", "Footer.dc.html"], "notes": {}, "designSystems": []}
json.dump(canvas, open("project/canvas.json", "w"), indent=2)
print({k: len(open("project/" + k).read()) for k in canvas["order"]})

# ---------------- Funnel: Get started ----------------
def field(label, ph, kind="email", note=""):
    n = f'<span style="font-weight: 400; color: #556070;"> {E(note)}</span>' if note else ""
    fid = "f-" + re.sub(r"[^a-z]+", "-", label.lower()).strip("-")
    return f'<div style="display: flex; flex-direction: column; gap: 8px;"><label for="{fid}" style="font-size: 14px; font-weight: 600;">{E(label)}{n}</label><input id="{fid}" type="{kind}" placeholder="{E(ph)}" style="min-height: 48px; padding: 10px 14px; border: 1px solid #848E9F; border-radius: 10px; font: 400 16px Geist, sans-serif; color: #0A1020; background: #FFFFFF; box-sizing: border-box; width: 100%;"></div>'
def btn(t, primary=True, full=True):
    st = "background: #2E5BFF; color: #FFFFFF; border: 1px solid #2E5BFF;" if primary else "background: #FFFFFF; color: #0A1020; border: 1px solid #CBD2DC;"
    return f'<button type="button" style="{st} min-height: 48px; padding: 10px 20px; border-radius: 12px; font: 600 16px Geist, sans-serif;{" width: 100%;" if full else ""}">{E(t)}</button>'
STEPS = ["Create your account", "Confirm your email", "Choose a password", "Subscribe", "Get set up"]
def stepper(cur, first=None, vertical=True):
    items = []
    for i, t in enumerate(STEPS, 1):
        label = first if (i == 1 and first) else t
        done, now = i < cur, i == cur
        dot_bg = "#2E5BFF" if now else ("#0E7A52" if done else "#FFFFFF")
        dot_fg = "#FFFFFF" if (now or done) else "#556070"
        dot_bd = "#2E5BFF" if now else ("#0E7A52" if done else "#CBD2DC")
        mark_ = "✓" if done else str(i)
        items.append(f'<li style="display: flex; align-items: center; gap: 12px;"><span style="width: 28px; height: 28px; flex-shrink: 0; display: grid; place-items: center; border-radius: 50%; background: {dot_bg}; color: {dot_fg}; border: 1px solid {dot_bd}; font: 600 13px Geist, sans-serif;">{mark_}</span><span style="font-size: 15px; font-weight: {600 if now else 500}; color: {"#0A1020" if (now or done) else "#556070"};">{E(label)}</span></li>')
    return f'<ol aria-label="Steps" style="list-style: none; margin: 0; padding: 0; display: flex; flex-direction: {"column" if vertical else "row"}; gap: {"16px" if vertical else "20px"};">{"".join(items)}</ol>'
def fheader():
    return bar(PUB, SIGNIN + PRIMARY("Get started"))
def card(inner_html, w="100%"):
    return f'<div style="width: {w}; box-sizing: border-box; background: #FFFFFF; border: 1px solid #E2E6EC; border-radius: 18px; padding: 32px; display: flex; flex-direction: column; gap: 18px; box-shadow: 0 16px 40px rgba(10,16,32,.08);">{inner_html}</div>'
SMALL = lambda t: f'<p style="font-size: 13.5px; line-height: 1.55; color: #3A4456;">{t}</p>'
open_card = card(f'''<h2 style="font-size: 22px; font-weight: 650; letter-spacing: -0.01em;">Create your account</h2>
{field("Work email", "you@company.com")}
{btn("Create account")}
{SMALL('We send a link to confirm the address. By creating an account you agree to the <a href="#">Terms of service</a> and the <a href="#">Privacy notice</a>.')}
<p style="font-size: 14px; color: #3A4456; border-top: 1px solid #E2E6EC; padding-top: 16px;">Already have an account? <a href="#">Sign in</a></p>''')
invite_card = card(f'''<div style="display: flex; align-items: center; justify-content: space-between; gap: 12px;"><h2 style="font-size: 22px; font-weight: 650; letter-spacing: -0.01em;">Request an invitation</h2><span style="padding: 3px 9px; border-radius: 6px; background: #EEF2FF; color: #1C44D6; border: 1px solid #B9C8FF; font-size: 12.5px; font-weight: 600;">Invitation only</span></div>
{SMALL("Accounts open by invitation right now. Tell us what your agents will work on; the invitation brings you back to step 1.")}
{field("Work email", "you@company.com")}
{field("What will your agents work on?", "For example: cleaning customer data overnight", "text", "Optional")}
{btn("Request an invitation")}
<p style="font-size: 14px; color: #3A4456; border-top: 1px solid #E2E6EC; padding-top: 16px;">Already invited? <a href="#">Sign in</a></p>''')
def funnel_page(card_html, first_label=None, note=""):
    return f'''<div style="border: 1px solid #E2E6EC; border-radius: 14px; overflow: hidden; background: #F5F6F8;">{fheader()}
<main style="display: grid; grid-template-columns: minmax(0, 1fr) 460px; gap: 72px; align-items: start; padding: 72px 64px 88px;">
<div style="display: flex; flex-direction: column; gap: 22px; min-width: 0;"><p style="font-size: 12.5px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #2E5BFF;">Get started</p>
<h1 style="font-size: 52px; line-height: 1.06; font-weight: 700; letter-spacing: -0.04em; text-wrap: balance;">Start with Baltor Pro.</h1>
<p style="font-size: 19px; line-height: 1.6; color: #3A4456; max-width: 520px;">Search is free. Baltor Pro is $29 a month. Five short steps, and your harness has its first file.</p>
<div style="padding-top: 8px;">{stepper(1, first_label)}</div>{note}</div>
{card_html}</main></div>'''
open_frame = funnel_page(open_card)
invite_frame = funnel_page(invite_card, "Request an invitation", '<p style="font-size: 14px; line-height: 1.55; color: #556070; max-width: 440px;">While accounts open by invitation, step 1 is the request. Everything after it stays the same.</p>')
def state(title, cur, body):
    return f'''<div style="display: flex; flex-direction: column; gap: 14px; min-width: 0;"><p style="font-size: 14px; font-weight: 600; color: #556070;">Step {cur} of 5</p>{card(f'<h2 style="font-size: 20px; font-weight: 650;">{E(title)}</h2>' + body)}</div>'''
states = "".join([
 state("Check your email", 2, SMALL("We sent a link to <strong>you@company.com</strong>. Open it on this device to continue. It works once.") + btn("Send it again", primary=False)),
 state("Choose a password", 3, field("Password", "", "password") + btn("Save and continue")),
 state("Subscribe to Baltor Pro", 4, '<p style="font-size: 30px; font-weight: 700; letter-spacing: -0.03em;">$29 a month</p>' + SMALL("Payment is handled by Stripe. An invitation that covers the subscription skips this step.") + btn("Continue to payment")),
 state("Get set up", 5, SMALL("Your account is ready. Connect your harness in three steps: get access, connect, then search and download.") + btn("Open the setup guide")),
])
phone = f'''<div style="width: 390px; border: 1px solid #E2E6EC; border-radius: 22px; overflow: hidden; background: #F5F6F8; flex-shrink: 0;">
<div style="display: flex; align-items: center; justify-content: space-between; min-height: 64px; padding: 0 16px; background: #FFFFFF; border-bottom: 1px solid #E2E6EC;"><a href="#" style="display: inline-flex; align-items: center; gap: 10px; color: #0A1020; font-size: 19px; font-weight: 700; text-decoration: none;">{mark(30)}<span>Baltor</span></a><button type="button" aria-label="Show the menu" style="width: 44px; height: 44px; display: grid; place-items: center; border: 1px solid #CBD2DC; border-radius: 10px; background: #FFFFFF;"><svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" style="fill: none; stroke: #0A1020; stroke-width: 2; stroke-linecap: round;"><path d="M4 7h16M4 12h16M4 17h16"></path></svg></button></div>
<div style="padding: 32px 16px 40px; display: flex; flex-direction: column; gap: 20px;"><p style="font-size: 12px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #2E5BFF;">Get started · step 1 of 5</p>
<h1 style="font-size: 36px; line-height: 1.08; font-weight: 700; letter-spacing: -0.035em;">Start with Baltor Pro.</h1>
<p style="font-size: 17px; line-height: 1.55; color: #3A4456;">Search is free. Baltor Pro is $29 a month.</p>
{card(open_card.split('box-shadow: 0 16px 40px rgba(10,16,32,.08);">', 1)[1].rsplit('</div>', 1)[0])}
<p style="font-size: 14px; color: #556070;">Next: confirm your email, choose a password, subscribe, get set up.</p></div></div>'''
FUW, FUH = 1440, 3000
funnel_board = HEAD.format(title="Get started funnel") + f'''{MARK}
<div style="width: {FUW}px; height: {FUH}px; box-sizing: border-box; padding: 64px; background: #F5F6F8; display: flex; flex-direction: column; gap: 36px;">
<div style="display: flex; flex-direction: column; gap: 12px; max-width: 1000px;"><p style="font-size: 12.5px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #2E5BFF;">Get started, the funnel</p>
<h1 style="font-size: 40px; line-height: 1.1; font-weight: 700; letter-spacing: -0.03em;">One page from the first click to a paid account, then the setup guide.</h1>
<p style="font-size: 17px; line-height: 1.6; color: #3A4456;">The header's Get started opens /get-started in every state. Five steps: create your account with an email only, confirm it, choose a password, subscribe, get set up. While accounts open by invitation, step 1 is the invitation request and nothing else changes.</p></div>
<div style="display: flex; flex-direction: column; gap: 10px;"><p style="font-size: 16px; font-weight: 600;">Accounts open</p>{open_frame}</div>
<div style="display: flex; flex-direction: column; gap: 10px;"><p style="font-size: 16px; font-weight: 600;">Invitation only, as today</p>{invite_frame}</div>
<div style="display: flex; gap: 48px; align-items: flex-start;">{phone}
<div style="display: flex; flex-direction: column; gap: 14px; min-width: 0; flex: 1;"><p style="font-size: 16px; font-weight: 600;">Steps 2 to 5</p><div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px;">{states}</div></div></div>
</div>
''' + TAIL.format(w=FUW, h=FUH)
open("project/Funnel.dc.html", "w").write(funnel_board)
c = json.load(open("project/canvas.json"))
c["boards"]["Funnel.dc.html"] = {"x": W + 80 + HW + 80, "y": 0, "w": FUW, "h": FUH, "title": "Get started funnel"}
c["order"] = ["Main.dc.html", "Header.dc.html", "Footer.dc.html", "Funnel.dc.html"]
json.dump(c, open("project/canvas.json", "w"), indent=2)
print("funnel", len(funnel_board))

# ---------------- Scroll: less scrolling ----------------
D = json.load(open("depth-live-r20.json"))
BUDGET = {"/": 4000, "/how-it-works": 4000}
NAMES = {"/": "Homepage", "/how-it-works": "How it works", "/pricing": "Pricing", "/connect": "Get started (the guide)", "/docs": "Docs", "/examples": "First example", "/security": "Access and data", "/privacy": "Privacy notice", "/signup": "Create account", "/login": "Sign in"}
desk = {r["route"]: r for r in D if r["w"] == 1440}; ph = {r["route"]: r for r in D if r["w"] == 390}
SCALE = 0.07  # pixels on the board per page pixel
bars = []
for route, r in desk.items():
    b = BUDGET.get(route, 2700); over = r["H"] > b
    wlen = round(r["H"] * SCALE); blen = round(b * SCALE)
    fill = "#F4B4AE" if over else "#A8DCC4"
    bars.append(f'''<div style="display: grid; grid-template-columns: 200px minmax(0, 1fr) 150px; gap: 16px; align-items: center; padding: 8px 0; border-top: 1px solid #E2E6EC;">
<p style="font-size: 14.5px; font-weight: 500;">{E(NAMES[route])}</p>
<div style="position: relative; height: 22px;"><div style="position: absolute; left: 0; top: 3px; height: 16px; width: {wlen}px; background: {fill}; border-radius: 4px;"></div><div style="position: absolute; left: {blen}px; top: 0; width: 2px; height: 22px; background: #0A1020;"></div></div>
<p style="font-size: 14px; font-family: 'Geist Mono', ui-monospace, monospace; text-align: right; color: {"#B42318" if over else "#0E7A52"};">{r["H"]:,} px · {r["screens"]} screens</p></div>''')
home = desk["/"]
strip = []
for bnd in home["bands"]:
    hh = round(bnd["h"] * SCALE); pt = round(bnd["padT"] * SCALE); pb = round(bnd["padB"] * SCALE)
    dark = "night" in bnd["cls"]
    bg = "#121A2E" if dark else "#FFFFFF"; fg = "#E8ECF4" if dark else "#0A1020"
    label = bnd["head"] or bnd["cls"]
    strip.append(f'''<div style="height: {hh}px; box-sizing: border-box; border: 1px solid #CBD2DC; border-top: 0; background: {bg}; display: flex; flex-direction: column;"><div style="height: {pt}px; background: repeating-linear-gradient(45deg, #F4B4AE 0 4px, transparent 4px 8px); opacity: 0.8;"></div><p style="flex: 1; min-height: 0; overflow: hidden; font-size: 11px; line-height: 1.3; padding: 2px 8px; color: {fg};">{E(label)} · {bnd["h"]:,} px</p><div style="height: {pb}px; background: repeating-linear-gradient(45deg, #F4B4AE 0 4px, transparent 4px 8px); opacity: 0.8;"></div></div>''')
fold = round((900 - 72) * SCALE)  # the header is 72 pixels; the strip starts at the hero
first_screen = f'''<div style="width: 1152px; height: 720px; border: 1px solid #E2E6EC; border-radius: 12px; overflow: hidden; background: #FFFFFF; position: relative; flex-shrink: 0;">
<div style="transform: scale(0.8); transform-origin: top left; width: 1440px; height: 900px; background: #F5F6F8;">
{bar(PUB, SIGNIN + PRIMARY("Get started"))}
<div style="display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr); gap: 56px; align-items: center; padding: 48px 64px 32px;">
<div style="display: flex; flex-direction: column; gap: 20px;"><p style="font-size: 13px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #2E5BFF;">Harness and agent optimized operation</p>
<h1 style="font-size: 56px; line-height: 1.05; font-weight: 700; letter-spacing: -0.045em;">Supercharge your developers and AI agents.</h1>
<p style="font-size: 19px; line-height: 1.55; color: #3A4456; max-width: 560px;">Big tasks go better in small steps. Give each step a fresh harness that holds only what that step needs.</p>
<div style="display: flex; align-items: center; gap: 20px; flex-wrap: wrap;">{PRIMARY("Get started")}<a href="#" style="font-size: 16px; font-weight: 600; text-decoration: none;">See one step work</a><span style="font-size: 15px; color: #3A4456;"><strong style="color: #0A1020;">$29 a month.</strong> Search is free.</span></div></div>
<div style="background: #FFFFFF; border: 1px solid #E2E6EC; border-radius: 18px; padding: 24px; box-shadow: 0 24px 60px rgba(10,16,32,.10); display: flex; flex-direction: column; gap: 14px;"><p style="font-size: 13px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: #556070;">What your coding agent sees at one step</p><p style="font-size: 18px; font-weight: 650;">Split the address lines in a customer file</p>
<div style="display: flex; flex-direction: column; gap: 8px; font-family: 'Geist Mono', ui-monospace, monospace; font-size: 13px;"><div style="padding: 10px 12px; border: 1px solid #2E5BFF; border-radius: 10px; background: #EEF2FF;">1 search · split_address_lines_into_components · skill · MIT · Chosen</div><div style="padding: 10px 12px; border: 1px solid #E2E6EC; border-radius: 10px;">2 download · bytes match the digest</div><div style="padding: 10px 12px; border: 1px dashed #CBD2DC; border-radius: 10px; color: #556070;">3 a fresh harness with only this step's files · being built</div></div></div></div>
<div style="margin: 0 64px; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0; border: 1px solid #E2E6EC; border-radius: 14px; background: #FFFFFF;">{"".join(f'<div style="padding: 16px 20px; border-left: {"0" if i == 0 else "1px solid #E2E6EC"};"><p style="font-size: 15px; font-weight: 600;">{E(a)}</p><p style="font-size: 13.5px; color: #3A4456; margin-top: 4px;">{E(b)}</p></div>' for i, (a, b) in enumerate([("Works with your harness", "Claude Code, Codex and OpenCode"), ("Anything a harness reads", "Skills, instruction files, tools, hooks"), ("Your keys stay yours", "Baltor never asks for a model key"), ("Exact versions", "Every download checked against its digest")]))}</div>
</div>
<div style="position: absolute; left: 0; right: 0; bottom: 0; padding: 6px 12px; background: rgba(10,16,32,.72); color: #FFFFFF; font-size: 12px;">The first screen at 1440 × 900, drawn at 80 percent: headline, value, Get started, the price and the demonstration, with four facts below</div></div>'''
SW, SH = 1440, 2150
scroll_board = HEAD.format(title="Less scrolling") + f'''{MARK}
<div style="width: {SW}px; height: {SH}px; box-sizing: border-box; padding: 64px; background: #F5F6F8; display: flex; flex-direction: column; gap: 32px;">
<div style="display: flex; flex-direction: column; gap: 12px; max-width: 1040px;"><p style="font-size: 12.5px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #2E5BFF;">Less scrolling</p>
<h1 style="font-size: 40px; line-height: 1.1; font-weight: 700; letter-spacing: -0.03em;">The homepage is 7.8 screens tall, and the price is 5.6 screens down.</h1>
<p style="font-size: 17px; line-height: 1.6; color: #3A4456;">Measured on the live site (release 20) at 1440 × 900 with a real browser. Seven homepage bands carry 112 pixels of padding top and bottom: {sum(round(b["padT"] + b["padB"]) for b in home["bands"]):,} pixels of padding in all. On a phone the homepage is {ph["/"]["H"]:,} pixels, {ph["/"]["screens"]} screens. The fix is layout, not cutting: 64 pixel padding, details side by side, a first screen that holds the offer.</p></div>
<div style="display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 48px; align-items: start;">
<section style="background: #FFFFFF; border: 1px solid #E2E6EC; border-radius: 18px; padding: 28px 32px; display: flex; flex-direction: column; gap: 6px;"><h2 style="font-size: 20px; font-weight: 650; margin-bottom: 8px;">Page height at 1440 pixels, against its budget</h2>
<p style="font-size: 13.5px; color: #556070; margin-bottom: 6px;">Red is over budget, green within. The black line is the budget: 4,000 pixels for the homepage and How it works, 2,700 (three screens) for every other page.</p>{"".join(bars)}</section>
<section style="display: flex; flex-direction: column; gap: 10px;"><h2 style="font-size: 18px; font-weight: 650;">The homepage, to scale</h2><p style="font-size: 13px; color: #556070;">Hatched: band padding. Dark: the two dark bands. The line marks the end of the first screen.</p>
<div style="position: relative; width: 240px;">{"".join(strip)}<div style="position: absolute; left: -12px; right: -12px; top: {fold}px; height: 2px; background: #2E5BFF;"></div></div></section></div>
<div style="display: flex; flex-direction: column; gap: 12px;"><h2 style="font-size: 20px; font-weight: 650;">The first screen, compact</h2>{first_screen}</div>
</div>
''' + TAIL.format(w=SW, h=SH)
open("project/Scroll.dc.html", "w").write(scroll_board)
c = json.load(open("project/canvas.json"))
c["boards"]["Scroll.dc.html"] = {"x": W + 80, "y": HH + 120 + FH + 120, "w": SW, "h": SH, "title": "Less scrolling"}
c["order"] = ["Main.dc.html", "Header.dc.html", "Footer.dc.html", "Funnel.dc.html", "Scroll.dc.html"]
json.dump(c, open("project/canvas.json", "w"), indent=2)
print("scroll", len(scroll_board), "strip px", sum(round(b["h"] * SCALE) for b in home["bands"]))

# ---------------- Devices: the live sweep ----------------
SW_ = json.load(open("sweep-live-r20.json"))
PAGES_ = ["/", "/how-it-works", "/pricing", "/connect", "/docs"]
PN = {"/": "Homepage", "/how-it-works": "How it works", "/pricing": "Pricing", "/connect": "Get started (guide)", "/docs": "Docs"}
sizes_ = []
for r in SW_:
    if (r["w"], r["h"]) not in sizes_: sizes_.append((r["w"], r["h"]))
def kind(w, h):
    if w <= 430: return "phone"
    if h < 500: return "phone, landscape"
    if w <= 1180: return "tablet"
    return "laptop or desktop"
def budget_screens(p, w, h):
    desk = (4000 / 900) if p in ("/", "/how-it-works") else 3.0
    return desk * 2 if (w <= 430 or h < 500) else desk
cells = {(r["w"], r["h"], r["p"]): r for r in SW_}
th_ = "".join(f'<th scope="col" style="text-align: left; font-size: 13px; font-weight: 600; color: #556070; padding: 8px 10px; border-bottom: 1px solid #CBD2DC;">{E(PN[p])}</th>' for p in PAGES_)
trs_ = []
for (w, h) in sizes_:
    tds = [f'<th scope="row" style="text-align: left; padding: 7px 10px; border-bottom: 1px solid #E2E6EC; font-weight: 500; font-size: 13.5px; white-space: nowrap;"><span style="font-family: \'Geist Mono\', ui-monospace, monospace;">{w} × {h}</span> <span style="color: #556070; font-weight: 400;">{E(kind(w, h))}</span></th>']
    for p in PAGES_:
        r = cells[(w, h, p)]; b = budget_screens(p, w, h); s = r["screens"]
        bg, fg = ("#E6F4EE", "#0E7A52") if s <= b else (("#FFF4DD", "#8A5A00") if s <= 1.5 * b else ("#FDECEC", "#B42318"))
        flag = "" if r["ctaInView"] else ' <span title="The page\'s own action is below the first screen" style="font-size: 11.5px; color: #556070;">· action below</span>'
        tds.append(f'<td style="padding: 5px 10px; border-bottom: 1px solid #E2E6EC;"><span style="display: inline-block; min-width: 52px; padding: 3px 8px; border-radius: 6px; background: {bg}; color: {fg}; font: 600 13px \'Geist Mono\', ui-monospace, monospace; text-align: right;">{s}</span>{flag}</td>')
    trs_.append("<tr>" + "".join(tds) + "</tr>")
heat = f'<table style="width: 100%; border-collapse: collapse;"><thead><tr><th scope="col" style="text-align: left; font-size: 13px; font-weight: 600; color: #556070; padding: 8px 10px; border-bottom: 1px solid #CBD2DC;">Screen size</th>{th_}</tr></thead><tbody>{"".join(trs_)}</tbody></table>'
findings_ = [
 ("No sideways scrolling at any of the 18 sizes.", "kept", "Nothing to fix."),
 ("The header does not stay on screen when you scroll, at any size.", "cut", "A sticky, compact header; slimmer on phones held sideways, or hidden while scrolling down."),
 ("Phone pages are very long: the homepage is 22.9 screens at 320 × 568 and 20.7 on a phone held sideways.", "cut", "Two-column grids from 600 pixels, 40 pixel band padding on phones, merged bands."),
 ("Pricing still says “29 United States dollars each month”.", "cut", "“$29 a month”, with the plan's action beside the price."),
 ("At 320 wide and on phones held sideways, the hero's own buttons are cut off at the bottom of the first screen.", "restoring", "A smaller headline at the smallest widths and less top padding sideways; the header button already shows."),
 ("Text as small as 11 pixels on the homepage; 5 to 7 long paragraphs under 15 pixels on phones.", "restoring", "12 pixels minimum anywhere, 15 for body text on phones."),
 ("9 to 18 paragraphs per page run past about 90 characters a line on laptops, worst on Docs.", "restoring", "Cap running text at about 68 characters."),
 ("14 to 22 tap targets under 44 pixels on touch screens, mostly footer and menu links.", "restoring", "44 pixel rows for links outside sentences on touch screens."),
]
flist = "".join(f'<li style="display: grid; grid-template-columns: 96px minmax(0, 1fr); gap: 14px; padding: 12px 0; border-top: 1px solid #E2E6EC;"><div>{badge(st)}</div><div><p style="font-size: 15px; font-weight: 600; line-height: 1.4;">{E(a)}</p><p style="font-size: 14px; color: #3A4456; margin-top: 4px;">{E(b)}</p></div></li>' for a, st, b in findings_)
def shot(url, w, h, cap):
    return f'<figure style="margin: 0; display: flex; flex-direction: column; gap: 8px;"><img src="{url}" alt="{E(cap)}" style="width: {w}px; height: {h}px; border: 1px solid #CBD2DC; border-radius: 10px; display: block; object-fit: cover; object-position: top;"><figcaption style="font-size: 13px; color: #3A4456; max-width: {max(w, 300)}px; line-height: 1.45;">{E(cap)}</figcaption></figure>'
shots_ = f'''<div style="display: flex; gap: 28px; align-items: flex-start; flex-wrap: wrap;">
{shot("/_blob/4de2596a8e6676f9a53968829f289dbe", 320, 568, "Homepage at 320 × 568: the headline takes four lines and the hero button is cut off; the header button shows.")}
{shot("/_blob/05e6cf893080d84834aeb8ece76787a8", 390, 844, "How it works at 390 × 844: readable, but the page runs 12.8 screens.")}
<div style="display: flex; flex-direction: column; gap: 28px;">
{shot("/_blob/2f9fa669e62db5884b8ecc080d2bb39e", 844, 390, "Homepage on a phone held sideways (844 × 390): the header takes 17 percent of the height; the buttons sit on the bottom edge.")}
{shot("/_blob/8090951fd01fb5834f45e858c34c2aad", 720, 450, "Pricing at 1440 × 900, shown at half size: “29 United States dollars” and a wide, mostly empty title band.")}
</div></div>'''
DW, DH = 1440, 3000
devices_board = HEAD.format(title="Screen sizes") + f'''{MARK}
<div style="width: {DW}px; height: {DH}px; box-sizing: border-box; padding: 64px; background: #F5F6F8; display: flex; flex-direction: column; gap: 32px;">
<div style="display: flex; flex-direction: column; gap: 12px; max-width: 1040px;"><p style="font-size: 12.5px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #2E5BFF;">Screen sizes, live release 20</p>
<h1 style="font-size: 40px; line-height: 1.1; font-weight: 700; letter-spacing: -0.03em;">Eighteen screen sizes, five pages, one real browser.</h1>
<p style="font-size: 17px; line-height: 1.6; color: #3A4456;">Each cell is the page's height in screens at that size. Green is within budget, amber up to half again over, red beyond. Budgets: 4,000 pixels for the homepage and How it works, three screens for other pages, twice that on phones. “Action below” means the page's own button sits under the first screen; the header's button is visible on every first screen.</p></div>
<div style="display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); gap: 32px; align-items: start;">
<section style="background: #FFFFFF; border: 1px solid #E2E6EC; border-radius: 18px; padding: 24px 28px;">{heat}</section>
<section style="background: #FFFFFF; border: 1px solid #E2E6EC; border-radius: 18px; padding: 24px 28px; display: flex; flex-direction: column; gap: 6px;"><h2 style="font-size: 20px; font-weight: 650;">What the sweep found</h2><ul style="list-style: none; margin: 0; padding: 0;">{flist}</ul>
<p style="font-size: 13.5px; color: #556070; margin-top: 10px; line-height: 1.5;">Running next: the full lab (Safari's engine, Firefox, text at 200 percent, dark mode, scrolling runs, the phone menu, a slow network) and six persona tests that browse the site like real visitors.</p></section></div>
<section style="display: flex; flex-direction: column; gap: 14px;"><h2 style="font-size: 20px; font-weight: 650;">First screens, as captured</h2>{shots_}</section>
</div>
''' + TAIL.format(w=DW, h=DH)
open("project/Devices.dc.html", "w").write(devices_board)
c = json.load(open("project/canvas.json"))
c["boards"]["Devices.dc.html"] = {"x": W + 80 + HW + 80, "y": FUH + 120, "w": DW, "h": DH, "title": "Screen sizes"}
c["order"] = ["Main.dc.html", "Header.dc.html", "Footer.dc.html", "Funnel.dc.html", "Scroll.dc.html", "Devices.dc.html"]
json.dump(c, open("project/canvas.json", "w"), indent=2)
print("devices", len(devices_board))
