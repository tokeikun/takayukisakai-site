#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — content/ のテキストから real.html を組み立てる。
使い方:  python3 build.py
編集するのは content/site.md と content/works/*.md だけ。template.html は触らなくてOK。
"""
import os, re, glob, sys

ROOT = os.path.dirname(os.path.abspath(__file__))

def parse_md(path):
    """`key: value` ヘッダ + `## section` 本文、という簡易フォーマットを読む"""
    head, sections = {}, {}
    cur = None
    buf = []
    for line in open(path, encoding="utf-8").read().splitlines():
        if line.startswith("## "):
            if cur: sections[cur] = "\n".join(buf).strip()
            cur = line[3:].strip(); buf = []
        elif cur is None:
            if ":" in line and not line.startswith("#"):
                k, v = line.split(":", 1)
                head[k.strip()] = v.strip()
        else:
            buf.append(line)
    if cur: sections[cur] = "\n".join(buf).strip()
    return head, sections

def paras(text):
    return [p.strip().replace("\n", " ") for p in re.split(r"\n\s*\n", text) if p.strip()]

def bi(ja, en, tag="span"):
    out = ""
    if ja: out += f'<{tag} class="ja">{ja}</{tag}>'
    if en: out += f'<{tag} class="en">{en}</{tag}>'
    return out

def video_embed(url):
    m = re.search(r"youtu\.be/([\w-]+)", url) or re.search(r"youtube\.com/watch\?v=([\w-]+)", url)
    if m:
        return f"https://www.youtube.com/embed/{m.group(1)}", "YouTube"
    m = re.search(r"vimeo\.com/(\d+)", url)
    if m:
        return f"https://player.vimeo.com/video/{m.group(1)}", "Vimeo"
    return None, None

def render_work_card(h, s):
    wid = h["id"]
    out = [f'    <!-- {h["title"]} -->', f'    <article class="work" id="c-{wid}">',
           f'      <a class="worklink" href="#w-{wid}">',
           f'        <div class="img"><img src="assets/{h["image"]}" alt="{h["title"]}"></div>',
           f'        <div class="cap"><h2>{h["title"]}</h2><span class="yr">{h["year"]}</span></div>',
           '      </a>']
    if s.get("desc.ja"): out.append(f'      <p class="desc ja">{s["desc.ja"]}</p>')
    if s.get("desc.en"): out.append(f'      <p class="desc en">{s["desc.en"]}</p>')
    if s.get("fact.ja") or s.get("fact.en"):
        out.append(f'      <p class="fact">{bi(s.get("fact.ja",""), s.get("fact.en",""))}</p>')
    if s.get("concept.ja") or s.get("concept.en"):
        out.append('      <div class="said">')
        out.append('        <p class="who"><span class="ja">コンセプト</span><span class="en">CONCEPT</span></p>')
        if s.get("concept.ja"): out.append(f'        <p class="q ja">{s["concept.ja"]}</p>')
        if s.get("concept.en"): out.append(f'        <p class="q qen en">{s["concept.en"]}</p>')
        out.append('      </div>')
    out.append(f'      <a class="more" href="#w-{wid}"><span class="ja">くわしく →</span><span class="en">more →</span></a>')
    out.append('    </article>')
    return "\n".join(out)

def render_work_row(h, s):
    wid = h["id"]
    out = [f'      <div class="rowline"><span class="t"><a href="#w-{wid}">{h["title"]}</a></span>'
           f'<span class="d">{h["year"]}</span>']
    if s.get("desc.ja"): out.append(f'<span class="n ja">{s["desc.ja"]}</span>')
    if s.get("desc.en"): out.append(f'<span class="n en">{s["desc.en"]}</span>')
    out.append('</div>')
    return "".join(out)

def render_detail(h, s):
    wid = h["id"]
    out = [f'<section class="detail" id="w-{wid}">', '  <div class="dwrap">',
           '    <a class="back" href="#works"><span class="ja">← 作品にもどる</span><span class="en">← back to works</span></a>',
           f'    <h2>{h["title"]}</h2>',
           f'    <p class="dyr">{h.get("year_detail", h["year"])}</p>']
    fact = bi(s.get("fact.ja",""), s.get("fact.en",""))
    if h.get("docs"):
        fact += f' ／ <a href="{h["docs"]}" target="_blank" rel="noopener">documentation ↗</a>'
    if fact: out.append(f'    <p class="fact">{fact}</p>')
    if h.get("video"):
        emb, label = video_embed(h["video"])
        if emb:
            out.append(f'    <div class="video"><iframe src="{emb}" loading="lazy" allowfullscreen title="{h["title"]} — film"></iframe></div>')
            out.append(f'    <a class="vlink" href="{h["video"]}" target="_blank" rel="noopener">▶ <span class="ja">映像を見る（{label}）</span><span class="en">watch the film ({label})</span> ↗</a>')
    if h.get("gallery"):
        gis = "".join(f'<div class="gi"><img src="assets/{g.strip()}" alt="{h["title"]} — detail" loading="lazy"></div>'
                      for g in h["gallery"].split(","))
        out.append(f'    <div class="gallery">{gis}</div>')
    out.append('    <div class="dbody">')
    for p in paras(s.get("detail.ja","")): out.append(f'      <p class="ja">{p}</p>')
    for p in paras(s.get("detail.en","")): out.append(f'      <p class="den en">{p}</p>')
    if s.get("note.ja") or s.get("note.en"):
        out.append(f'      <p class="dlabel">{bi(s.get("note.ja",""), s.get("note.en",""))}</p>')
    out.append('    </div>')
    out.append('  </div>')
    out.append('</section>')
    return "\n".join(out)

def main():
    tpl = open(os.path.join(ROOT, "template.html"), encoding="utf-8").read()

    works = []
    for f in sorted(glob.glob(os.path.join(ROOT, "content/works/*.md"))):
        h, s = parse_md(f)
        if not h.get("id") or not h.get("title"):
            print(f"!! {os.path.basename(f)}: id / title がありません。スキップ"); continue
        works.append((h, s))

    cards = "\n\n".join(render_work_card(h, s) for h, s in works if h.get("card","yes") == "yes")
    rows_items = [render_work_row(h, s) for h, s in works if h.get("card") == "row"]
    rows = ('\n    <div style="margin-top:8vh">\n' + "\n".join(rows_items) + "\n    </div>") if rows_items else ""
    details = "\n\n".join(render_detail(h, s) for h, s in works)
    index_items = []
    for h, _s in works:
        href = ("#c-"+h["id"]) if h.get("card","yes")=="yes" else ("#w-"+h["id"])
        thumb = f'<img src="assets/{h["image"]}" alt="" loading="lazy">' if h.get("image") else '<span class="noimg"></span>'
        index_items.append(f'      <a href="{href}">{thumb}<span class="t">{h["title"]}</span><span class="y">{h["year"]}</span></a>')
    windex = '<nav class="windex">\n' + "\n".join(index_items) + '\n    </nav>'

    sh, ss = parse_md(os.path.join(ROOT, "content/site.md"))

    essay = [f'      <p class="et">{ss.get("essay.title","")}</p>']
    for p in paras(ss.get("essay.ja","")): essay.append(f'      <p class="ja">{p}</p>')
    if ss.get("essay.note.en"):
        essay.append(f'      <p class="en" style="font-family:var(--gothic);font-size:13px;color:var(--soft)">{ss["essay.note.en"]}</p>')
    essay.append(f'      <p class="ed">{bi(ss.get("essay.date.ja",""), ss.get("essay.date.en",""))}</p>')

    links = []
    for line in ss.get("links","").splitlines():
        if "|" not in line: continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4: continue
        tja, ten, date, url = parts[0], parts[1], parts[2], parts[3]
        links.append(f'      <a href="{url}" target="_blank" rel="noopener"><p class="wt ja">{tja}</p><p class="wt en">{ten}</p><p class="wd">{date}</p></a>')

    bio = []
    for p in paras(ss.get("bio.ja","")): bio.append(f'          <p class="ja">{p}</p>')
    for p in paras(ss.get("bio.en","")): bio.append(f'          <p class="en">{p}</p>')

    cred = bi("<br>".join(ss.get("cred.ja","").splitlines()), "<br>".join(ss.get("cred.en","").splitlines()))
    contact = bi(ss.get("contact.ja",""), ss.get("contact.en",""))

    out = tpl
    out = out.replace("<!--INDEX-->", windex)
    out = out.replace("<!--WORKS-->", cards)
    out = out.replace("<!--DETAILS-->", details)
    out = out.replace("<!--ESSAY-->", "\n".join(essay))
    out = out.replace("<!--LINKS-->", "\n".join(links))
    out = out.replace("<!--BIO-->", "\n".join(bio))
    out = out.replace("<!--CRED-->", cred)
    out = out.replace("<!--CONTACT-->", contact)

    dst = os.path.join(ROOT, "index.html")
    open(dst, "w", encoding="utf-8").write(out)
    ncards = sum(1 for h,_ in works if h.get("card","yes")=="yes")
    print(f"OK: index.html を再生成しました（カード {ncards} ／ 行 {len(rows_items)} ／ 詳細 {len(works)}）")

if __name__ == "__main__":
    main()
