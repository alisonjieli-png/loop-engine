"""Render the owned editorial draft into a self-contained local preview.

No service route is registered, no credentials are read and nothing is
published. Content remains draft-only. Reuse the existing application shell
when integrating reviewed copy so navigation retains the session semantics.
"""
from __future__ import annotations

import html
import json
import math
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parents[1]
SITE = HERE / "site"
SOURCE_ASSETS = REPOSITORY / "src/loop_engine/core/service_runtime/web_assets"


def text(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("editorial text must be a string")
    return html.escape(value, quote=True)


def public_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("source link must be an ordinary HTTPS URL")
    return text(value)


def source_link(source: dict) -> str:
    return f'<a href="{public_url(source["url"])}">{text(source["label"])}</a>'


def render_block(block: dict, sources: list[dict]) -> str:
    kind = block["type"]
    if kind == "p":
        rendered = f'<p>{text(block["text"])}</p>'
    elif kind == "h2":
        rendered = f'<h2>{text(block["text"])}</h2>'
    elif kind == "code":
        rendered = f'<pre><code>{text(block["text"])}</code></pre>'
    elif kind == "table":
        headers = block["headers"]
        if not headers or any(len(row) != len(headers) for row in block["rows"]):
            raise ValueError("editorial table columns differ")
        head = "".join(f'<th scope="col">{text(value)}</th>' for value in headers)
        rows = "".join("<tr>" + "".join(
            f'<td data-label="{text(headers[i])}">{text(value)}</td>'
            for i, value in enumerate(row)) + "</tr>" for row in block["rows"])
        rendered = f'<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>'
    else:
        raise ValueError(f"unknown editorial block type: {kind}")
    if "source" in block:
        index = block["source"]
        if type(index) is not int or not 0 <= index < len(sources):
            raise ValueError("editorial source reference is invalid")
        rendered += f'<p class="source-inline">Source: {source_link(sources[index])}</p>'
    return rendered


def shell(title: str, description: str, body: str, active: str) -> str:
    navigation = "".join(
        f'<a href="{path}"' + (' aria-current="page"' if name == active else "") +
        f'>{name}</a>' for name, path in
        (("Blog", "index.html"), ("Team", "team.html"), ("Logo study", "brand.html")))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><meta name="description" content="{text(description)}">
<title>{text(title)} | Baltor editorial preview</title><link rel="stylesheet" href="editorial.css">
<link rel="icon" type="image/svg+xml" href="assets/baltor-mark.svg"></head>
<body><a class="skip" href="#main">Skip to content</a>
<div class="preview-bar">Editorial preview · September 23, 2026 · These pages are not live</div>
<header class="header"><a class="brand" href="index.html"><img src="assets/baltor-mark.svg" width="32" height="32" alt="">Baltor</a>
<nav aria-label="Preview navigation">{navigation}</nav><a class="live-link" href="https://baltor.ai" target="_blank" rel="noopener">Live Baltor ↗</a></header>
<main id="main">{body}</main>
<footer><a class="brand" href="index.html">Baltor</a><p>Selected information for each step.</p>
<div><a href="https://baltor.ai/privacy">Privacy</a><a href="https://github.com/alisonjieli-png/loop-engine">Source</a><a href="https://baltor.ai/waitlist">Request an invitation</a></div></footer>
</body></html>"""


def read_minutes(post: dict) -> int:
    words = sum(len(block.get("text", "").split()) for block in post["blocks"])
    return max(1, math.ceil(words / 220))


def card(post: dict) -> str:
    return f"""<article class="post-card"><div class="card-meta"><span>{text(post['category'])}</span><time datetime="{post['date']}">September 23, 2026</time></div>
<h2><a href="{post['slug']}.html">{text(post['title'])}</a></h2><p>{text(post['summary'])}</p>
<a class="read-link" href="{post['slug']}.html">Read the draft <span aria-hidden="true">↗</span></a></article>"""


def blog_page(posts: list[dict]) -> str:
    featured = next(post for post in posts if post["featured"])
    body = f"""<section class="intro-band"><p class="eyebrow">Baltor blog</p><h1>Notes from building Baltor.</h1>
<p class="lead">Experiments, practical guides, and what we learn when a task does not go as planned.</p></section>
<section class="content-band"><article class="featured"><div><p class="eyebrow">Featured experiment</p>
<h2><a href="{featured['slug']}.html">{text(featured['title'])}</a></h2><p>{text(featured['summary'])}</p>
<a class="button" href="{featured['slug']}.html">Read the experiment <span aria-hidden="true">↗</span></a></div>
<figure class="experiment-card"><figcaption>Phone-record accuracy on one synthetic test</figcaption>
<div class="result-row"><span>Without the instruction</span><strong>99.1<span>%</span></strong></div>
<div class="result-row"><span>With the instruction</span><strong>84.2<span>%</span></strong></div>
<p>38 records · 3 repetitions · glm-5.3-flash:cloud</p><p>The article links the design, scorer and limits.</p></figure></article>
<div class="section-heading"><h2>Practical notes</h2><p>Draft articles for review</p></div>
<div class="post-grid">{''.join(card(post) for post in posts if not post['featured'])}</div></section>
<section class="closing-band"><div><p class="eyebrow">Follow the work</p><h2>See the source behind the results.</h2>
<p>The repository holds the implementation, experiments and open work.</p></div><a class="button" href="https://github.com/alisonjieli-png/loop-engine">Open the repository ↗</a></section>"""
    return shell("Blog", "Practical notes and experiments from building Baltor.", body, "Blog")


def article_page(post: dict) -> str:
    blocks = "".join(render_block(block, post["sources"]) for block in post["blocks"])
    sources = "".join(f"<li>{source_link(source)}</li>" for source in post["sources"])
    body = f"""<section class="article-heading"><a class="back" href="index.html">← All notes</a><p class="eyebrow">{text(post['category'])}</p>
<h1>{text(post['title'])}</h1><p class="lead">{text(post['summary'])}</p>
<p class="byline">{text(post['byline'])} · <time datetime="{post['date']}">September 23, 2026</time> · {read_minutes(post)} minute read</p></section>
<div class="article-layout"><article class="prose">{blocks}</article><aside class="article-aside">
<div class="review-note"><p class="eyebrow">Draft review gate</p><p>{text(post['publication_gate'])}</p></div>
<h2>Source records</h2><ul>{sources}</ul><p class="aside-note">These links point to the source used for this draft. Recheck facts that may change before publication.</p>
</aside></div><section class="article-end"><p>Continue reading</p><a href="index.html">Back to all notes ↗</a></section>"""
    return shell(post["title"], post["summary"], body, "Blog")


def team_page(profiles: list[dict]) -> str:
    profiles_html = "".join(
        f'<article class="person"><div class="avatar" aria-hidden="true">{text(p["initials"])}</div>'
        f'<div><p class="eyebrow">{text(p["role"])}</p><h2>{text(p["name"])}</h2><p>{text(p["bio"])}</p>'
        '<a href="https://github.com/alisonjieli-png/loop-engine">Follow the project on GitHub ↗</a></div></article>'
        for p in profiles)
    body = f"""<section class="intro-band"><p class="eyebrow">Team</p><h1>The people building Baltor.</h1>
<p class="lead">We are building a way for coding agents to approach a large task one focused step at a time, with the material and checks that step needs.</p></section>
<section class="content-band">{profiles_html}<div class="team-approach"><div><p class="eyebrow">What guides the work</p><h2>Useful work under your control.</h2></div>
<div><p>You bring the harness, models and permissions. Baltor supplies selected material through a reviewed, versioned library.</p>
<p>The broader design starts a fresh harness for each step. That execution path is being built; the live service currently offers search and selected downloads to invited accounts.</p>
<p>We keep failed experiments in the record because a procedure must earn its place through checked work.</p>
<a href="when-a-reviewed-skill-made-a-model-worse.html">Read a recent experiment ↗</a></div></div></section>
<section class="closing-band"><div><p class="eyebrow">Built in public</p><h2>Follow the implementation.</h2><p>Read the source, review the evidence, or report a reproducible problem.</p></div>
<a class="button" href="https://github.com/alisonjieli-png/loop-engine">Open the repository ↗</a></section>"""
    return shell("Team", "Taylor Amarel is building Baltor around focused steps and selected intelligence.", body, "Team")


def brand_page() -> str:
    cards = []
    for title, stem, note in (
        ("Current live mark", "live", "The placeholder currently served by Baltor."),
        ("Curved husky profile", "soft", "A longer muzzle and upright neck, using the owner's latest direction."),
        ("Single-cut silhouette", "single-cut", "Two broad shapes; fewer internal details at favicon size."),
    ):
        cards.append(f'<article class="brand-card"><p class="eyebrow">Header study</p><h2>{title}</h2>'
                     f'<div class="sample-header"><img src="assets/{stem}-32.svg" width="32" height="32" alt="">Baltor</div>'
                     f'<div class="sample-tab"><img src="assets/{stem}-16.svg" width="16" height="16" alt="">Baltor <span>×</span></div>'
                     f'<p>{note}</p></article>')
    body = '<section class="intro-band"><p class="eyebrow">Logo study</p><h1>Judge the mark where it will live.</h1><p class="lead">The current mark and two existing husky directions at actual header and tab sizes. These are alternatives for review.</p></section><section class="content-band"><div class="brand-grid">' + "".join(cards) + '</div><p class="draft-note">No logo is selected by this preview. Preserve the current live mark until the owner chooses a replacement and its light, dark and tiny versions pass visual review.</p></section>'
    return shell("Logo study", "Existing Baltor mark and husky concepts at actual interface sizes.", body, "Logo study")


def main() -> None:
    raw = (HERE / "content.json").read_bytes()
    if len(raw) > 250_000:
        raise ValueError("editorial draft exceeds preview limit")
    content = json.loads(raw)
    if content["record_type"] != "baltor_editorial_preview/v1" or content["state"] != "draft":
        raise ValueError("preview renderer accepts only explicit draft content")
    posts = content["posts"]
    slugs = [post["slug"] for post in posts]
    if len(set(slugs)) != len(slugs) or any(not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) for slug in slugs):
        raise ValueError("article slugs must be distinct safe names")
    if sum(post["featured"] is True for post in posts) != 1:
        raise ValueError("preview needs exactly one featured article")
    if SITE.is_symlink():
        raise ValueError("preview output cannot be a symlink")
    SITE.mkdir(exist_ok=True)
    assets = SITE / "assets"
    assets.mkdir(exist_ok=True)
    for name in ("geist.woff2", "geist-mono.woff2", "baltor-mark.svg"):
        shutil.copy2(SOURCE_ASSETS / name, assets / name)
    shutil.copy2(SOURCE_ASSETS / "THIRD-PARTY-NOTICES.md", assets / "THIRD-PARTY-NOTICES.txt")
    shutil.copy2(SOURCE_ASSETS / "baltor-mark.svg", assets / "live-16.svg")
    shutil.copy2(SOURCE_ASSETS / "baltor-mark.svg", assets / "live-32.svg")
    marks = REPOSITORY / "docs/verification/assets/baltor-logo-concepts-2026-09-23/micro-marks"
    for stem in ("soft", "single-cut"):
        for size in (16, 32):
            shutil.copy2(marks / f"{stem}-{size}.svg", assets / f"{stem}-{size}.svg")
    shutil.copy2(HERE / "editorial.css", SITE / "editorial.css")
    outputs = {"index.html": blog_page(posts), "team.html": team_page(content["team"]), "brand.html": brand_page()}
    outputs.update({post["slug"] + ".html": article_page(post) for post in posts})
    for name, body in outputs.items():
        target = SITE / name
        if target.is_symlink():
            raise ValueError("preview page cannot be a symlink")
        target.write_text(body, encoding="utf-8")
    print(f"rendered {len(outputs)} draft pages in {SITE}")


if __name__ == "__main__":
    main()
