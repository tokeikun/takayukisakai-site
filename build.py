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
           f'      <a class="worklink" href="works/{wid}/">',
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
    out.append(f'      <a class="more" href="works/{wid}/"><span class="ja">くわしく →</span><span class="en">more →</span></a>')
    out.append('    </article>')
    return "\n".join(out)

def render_work_row(h, s):
    wid = h["id"]
    out = [f'      <div class="rowline"><span class="t"><a href="works/{wid}/">{h["title"]}</a></span>'
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



SITE = "https://takayukisakai.com"

def esc(t):
    return (t or "").replace('"','&quot;')

def render_work_page(h, s, style, ga, all_works=None):
    wid=h["id"]; title=h["title"]
    desc=(s.get("desc.ja") or s.get("desc.en") or "").strip()
    img=h.get("image")
    ogimg=f"{SITE}/assets/{img}" if img else f"{SITE}/assets/og.jpg"
    year="".join(c for c in h.get("year","") if c.isdigit())[:4]
    parts=[]
    parts.append(f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — 堺 崇行 / Takayuki Sakai</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE}/works/{wid}/">
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
<meta name="theme-color" content="#faf9f5">
<meta property="og:type" content="article">
<meta property="og:url" content="{SITE}/works/{wid}/">
<meta property="og:title" content="{esc(title)} — 堺 崇行">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{ogimg}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@tokeikun">
<meta name="twitter:image" content="{ogimg}">
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"VisualArtwork","name":"{esc(title)}","url":"{SITE}/works/{wid}/","image":"{ogimg}","dateCreated":"{year}","creator":{{"@type":"Person","name":"堺 崇行","alternateName":"Takayuki Sakai","url":"{SITE}/"}}}}
</script>
{ga}
<style>{style}
  .wpage{{max-width:720px;margin:0 auto;padding:90px var(--gut) 120px}}
  .wpage h1{{font-family:var(--mincho);font-size:clamp(26px,4.5vw,40px);font-weight:600;letter-spacing:.05em}}
  .wpage .hero-img{{border:1px solid var(--line);margin-bottom:5vh}}
  .wpage .hero-img img{{width:100%;height:auto;display:block}}
  .wpage .dyr{{font-size:12px;letter-spacing:.16em;color:var(--soft);margin:8px 0 26px}}
  .wpage .fact{{margin-bottom:5vh}}
  .wlayout{{max-width:1100px;margin:0 auto;display:block}}
  @media(min-width:1040px){{
    .wlayout{{display:grid;grid-template-columns:240px minmax(0,1fr);gap:24px;align-items:start}}
    .wside{{grid-column:1;grid-row:1;position:sticky;top:70px;padding:90px 0 40px 24px}}
    .wlayout > .wpage{{grid-column:2}}
  }}
  .wside{{padding:20px var(--gut) 60px}}
  .wside .slabel{{font-size:10.5px;letter-spacing:.3em;color:var(--soft);margin-bottom:14px}}
  .wside a{{display:flex;align-items:center;gap:10px;padding:6px 0;text-decoration:none;
    font-size:12.5px;color:var(--soft);border-bottom:1px solid transparent}}
  .wside a:hover{{color:var(--ink)}}
  .wside a.cur{{color:var(--ink);font-family:var(--mincho)}}
  .wside img,.wside .ni{{width:36px;height:26px;object-fit:cover;flex:none;border:1px solid var(--line);background:#eeeae0}}
  .wside .ni{{display:flex;align-items:center;justify-content:center;font-family:var(--mincho);font-size:12px;color:#b3ab9c}}
</style>
</head>
<body data-lang="ja">
<div class="top">
  <a href="/" style="text-decoration:none"><span class="nm">堺 崇行</span></a>
  <div class="nav">
    <a href="/#works"><span class="ja">作品</span><span class="en">Works</span></a>
    <button id="lang" aria-label="switch language">EN</button>
  </div>
</div>
<div class="wlayout">
<main class="wpage">""")
    parts.append('  <a class="back" href="/#works"><span class="ja">← 作品にもどる</span><span class="en">← back to works</span></a>')
    if img:
        parts.append(f'  <div class="hero-img"><img src="/assets/{img}" alt="{esc(title)}"></div>')
    parts.append(f'  <h1>{title}</h1>')
    parts.append(f'  <p class="dyr">{h.get("year_detail", h.get("year",""))}</p>')
    fact = bi(s.get("fact.ja",""), s.get("fact.en",""))
    if h.get("docs"):
        fact += f' ／ <a href="{h["docs"]}" target="_blank" rel="noopener">documentation ↗</a>'
    if fact: parts.append(f'  <p class="fact">{fact}</p>')
    if h.get("video"):
        emb,label=video_embed(h["video"])
        if emb:
            parts.append(f'  <div class="video"><iframe src="{emb}" loading="lazy" allowfullscreen title="{esc(title)} — film"></iframe></div>')
            parts.append(f'  <a class="vlink" href="{h["video"]}" target="_blank" rel="noopener">▶ <span class="ja">映像を見る（{label}）</span><span class="en">watch the film ({label})</span> ↗</a>')
    if h.get("gallery"):
        gis="".join(f'<div class="gi"><img src="/assets/{g.strip()}" alt="{esc(title)} — detail" loading="lazy"></div>' for g in h["gallery"].split(","))
        parts.append(f'  <div class="gallery">{gis}</div>')
    parts.append('  <div class="dbody">')
    for p in paras(s.get("detail.ja","")): parts.append(f'    <p class="ja">{p}</p>')
    for p in paras(s.get("detail.en","")): parts.append(f'    <p class="den en">{p}</p>')
    if s.get("note.ja") or s.get("note.en"):
        parts.append(f'    <p class="dlabel">{bi(s.get("note.ja",""), s.get("note.en",""))}</p>')
    parts.append('  </div>')
    parts.append('  </main>')
    if all_works:
        side=['<aside class="wside">','  <p class="slabel"><span class="ja">作品　WORKS</span><span class="en">WORKS</span></p>']
        for oh,_os in all_works:
            oid=oh["id"]; cur=' class="cur"' if oid==wid else ''
            timg=oh.get("thumb") or oh.get("image")
            tn=f'<img src="/assets/{timg}" alt="" loading="lazy">' if timg else f'<span class="ni">{(oh["title"].strip()[:1]).upper()}</span>'
            side.append(f'  <a href="/works/{oid}/"{cur}>{tn}<span>{oh["title"]}</span></a>')
        side.append('</aside>')
        parts.append("\n".join(side))
    parts.append("""</div>
<footer style="max-width:720px;margin:0 auto;padding:0 var(--gut) 60px">
  <small style="font-size:10.5px;color:var(--soft);letter-spacing:.16em">© 堺 崇行 / Takayuki Sakai — <a href="/" style="color:var(--soft)">takayukisakai.com</a></small>
</footer>
<script>
var body=document.body,lang=document.getElementById("lang");
function setLang(l){body.dataset.lang=l;document.documentElement.lang=l;lang.textContent=l==="ja"?"EN":"日本語";try{localStorage.setItem("lang",l)}catch(e){}}
lang.addEventListener("click",function(){setLang(body.dataset.lang==="ja"?"en":"ja")});
var sv=null;try{sv=localStorage.getItem("lang")}catch(e){}
setLang(sv==="en"?"en":"ja");
</script>
</body>
</html>""")
    return "\n".join(parts)


# ---------- 汎用ページ（content/pages/*.md → /<slug>/index.html） ----------
def inline_md(t):
    t = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<figure class="pimg"><img src="\2" alt="\1" loading="lazy"></figure>', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{m.group(2)}"' + (' target="_blank" rel="noopener"' if m.group(2).startswith("http") else '') + f'>{m.group(1)}</a>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    return t

def block_md(text, form_html=""):
    out=[]; lst=[]
    def flush():
        nonlocal lst
        if lst: out.append("<ul>"+"".join(f"<li>{inline_md(i)}</li>" for i in lst)+"</ul>"); lst=[]
    for para in re.split(r"\n\s*\n", text):
        para=para.strip()
        if not para: continue
        lines=para.splitlines()
        if all(l.startswith("- ") for l in lines):
            lst.extend(l[2:] for l in lines); flush(); continue
        flush()
        if para.startswith("### "): out.append(f"<h2>{inline_md(para[4:])}</h2>"); continue
        if para.strip()=="{{form}}": out.append(form_html); continue
        if re.fullmatch(r"!\[[^\]]*\]\([^)]+\)", para): out.append(inline_md(para)); continue
        out.append(f"<p>{inline_md(' '.join(lines))}</p>")
    flush()
    return "\n".join(out)

def render_page(h, s, style, ga, site_head, plinks):
    slug=h["slug"]; tja=h.get("title_ja",slug); ten=h.get("title_en",tja)
    dja=esc(h.get("desc_ja","")); den=esc(h.get("desc_en",""))
    draft = h.get("draft","no").lower() in ("yes","true","1")
    robots = '<meta name="robots" content="noindex,nofollow">' if draft else ""
    form_url = site_head.get("contact_form","").strip()
    if form_url:
        form_html=(f'<div class="cform"><iframe src="{form_url}" loading="lazy" title="contact form">読み込み中…</iframe></div>'
                   f'<p class="fnote"><span class="ja">フォームが表示されない場合は <a href="{form_url}" target="_blank" rel="noopener">こちら ↗</a></span>'
                   f'<span class="en">If the form does not load, <a href="{form_url}" target="_blank" rel="noopener">open it here ↗</a></span></p>')
    else:
        dm='<a href="https://x.com/tokeikun" target="_blank" rel="noopener">X @tokeikun</a> / <a href="https://www.instagram.com/tokeikun/" target="_blank" rel="noopener">Instagram</a>'
        form_html=(f'<p class="fnote"><span class="ja">フォームは準備中です。{dm} のDMでご連絡ください。</span>'
                   f'<span class="en">Form coming soon — please DM on {dm} for now.</span></p>')
    # section groups in order of first appearance
    order=[]; 
    for k in s:
        base=k.rsplit(".",1)[0]
        if base not in order: order.append(base)
    body=[]
    for base in order:
        ja=s.get(base+".ja",""); en=s.get(base+".en","")
        blk=""
        if ja: blk+=f'<div class="ja">{block_md(ja, form_html)}</div>'
        if en: blk+=f'<div class="en">{block_md(en, form_html)}</div>'
        body.append(f'<section class="pblk" id="{base}">{blk}</section>')
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{tja} — 堺 崇行 / Takayuki Sakai</title>
<meta name="description" content="{dja}">
{robots}
<link rel="canonical" href="{SITE}/{slug}/">
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
<meta name="theme-color" content="#faf9f5">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE}/{slug}/">
<meta property="og:title" content="{esc(tja)} — 堺 崇行">
<meta property="og:description" content="{dja}">
<meta property="og:image" content="{SITE}/assets/og.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@tokeikun">
{ga}
<style>{style}
  .page{{max-width:720px;margin:0 auto;padding:110px var(--gut) 120px}}
  .page h1{{font-family:var(--mincho);font-size:clamp(26px,4.5vw,40px);font-weight:600;letter-spacing:.05em;margin-bottom:6vh}}
  .page h2{{font-size:11px;letter-spacing:.34em;color:var(--soft);font-weight:400;margin:9vh 0 3vh;display:flex;align-items:center;gap:16px}}
  .page h2::after{{content:"";flex:1;height:1px;background:var(--line)}}
  .pblk:first-of-type h2{{margin-top:0}}
  .page p{{font-size:14px;line-height:2.2;max-width:38em;margin-bottom:1.4em;color:#2b2721}}
  .page ul{{list-style:none;margin:0 0 2em}}
  .page li{{font-size:14px;line-height:2;padding:10px 0;border-bottom:1px solid var(--line)}}
  .page li:first-child{{border-top:1px solid var(--line)}}
  .page strong{{font-family:var(--mincho);font-weight:600;letter-spacing:.04em}}
  .page a{{border-bottom:1px solid var(--line);text-decoration:none}}
  .page a:hover{{border-color:var(--ink)}}
  .pimg{{margin:3vh 0 1.5vh;border:1px solid var(--line);background:#eeeae0}}
  .pimg img{{width:100%;height:auto;display:block;max-height:70vh;object-fit:contain}}
  .cform iframe{{width:100%;min-height:900px;border:0;background:transparent}}
  .fnote{{font-size:12px;color:var(--soft)}}
  .page .draft{{font-size:10.5px;letter-spacing:.2em;color:#b3542e;border:1px solid #e9c9b8;display:inline-block;padding:2px 10px;border-radius:999px;margin-bottom:24px}}
</style>
</head>
<body data-lang="ja">
<div class="top">
  <a href="/" style="text-decoration:none"><span class="nm">堺 崇行</span></a>
  <div class="nav">
    <a href="/#works"><span class="ja">作品</span><span class="en">Works</span></a>
    <button id="lang" aria-label="switch language">EN</button>
  </div>
</div>
<main class="page">
  {'<p class="draft">DRAFT — 未公開（確認用）</p>' if draft else ''}
  <h1><span class="ja">{tja}</span><span class="en">{ten}</span></h1>
{chr(10).join(body)}
</main>
<footer style="max-width:720px;margin:0 auto;padding:0 var(--gut) 60px">
  <div class="links" style="display:flex;gap:24px;font-size:13px;letter-spacing:.08em;flex-wrap:wrap;margin-bottom:24px">{plinks}</div>
  <small style="font-size:10.5px;color:var(--soft);letter-spacing:.16em">© 堺 崇行 / Takayuki Sakai — <a href="/" style="color:var(--soft)">takayukisakai.com</a></small>
</footer>
<script>
var body=document.body,lang=document.getElementById("lang");
function setLang(l){{body.dataset.lang=l;document.documentElement.lang=l;lang.textContent=l==="ja"?"EN":"日本語";try{{localStorage.setItem("lang",l)}}catch(e){{}}}}
lang.addEventListener("click",function(){{setLang(body.dataset.lang==="ja"?"en":"ja")}});
var sv=null;try{{sv=localStorage.getItem("lang")}}catch(e){{}}
setLang(sv==="en"?"en":"ja");
</script>
</body>
</html>"""

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
        href = ("#c-"+h["id"]) if h.get("card","yes")=="yes" else ("works/"+h["id"]+"/")
        timg = h.get("thumb") or h.get("image")
        initial = (h["title"].strip()[:1]).upper()
        thumb = f'<img src="assets/{timg}" alt="" loading="lazy">' if timg else f'<span class="noimg">{initial}</span>'
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
    out = out.replace("<!--DETAILS-->", "")
    out = out.replace("<!--ESSAY-->", "\n".join(essay))
    out = out.replace("<!--LINKS-->", "\n".join(links))
    out = out.replace("<!--BIO-->", "\n".join(bio))
    out = out.replace("<!--CRED-->", cred)
    out = out.replace("<!--CONTACT-->", contact)

    # 作品ページ
    import re as _re, shutil as _shutil
    style=_re.search(r"<style>(.*?)</style>", tpl, _re.S).group(1)
    ga=_re.search(r'(<script async src="https://www\.googletagmanager[^"]*"></script>\s*<script>.*?</script>)', tpl, _re.S)
    ga=ga.group(1) if ga else ""
    wdir=os.path.join(ROOT,"works")
    if os.path.isdir(wdir): _shutil.rmtree(wdir)
    for h,sec in works:
        d=os.path.join(wdir,h["id"]); os.makedirs(d,exist_ok=True)
        open(os.path.join(d,"index.html"),"w",encoding="utf-8").write(render_work_page(h,sec,style,ga,works))
    # 汎用ページ
    pages=[]
    for f in sorted(glob.glob(os.path.join(ROOT,"content/pages/*.md"))):
        ph,ps=parse_md(f)
        if ph.get("slug"): pages.append((ph,ps))
    public_pages=[(ph,ps) for ph,ps in pages if ph.get("draft","no").lower() not in ("yes","true","1")]
    plinks="".join(f'<a href="/{ph["slug"]}/" style="text-decoration:none;border-bottom:1px solid var(--line)">{bi(ph.get("title_ja",ph["slug"]), ph.get("title_en",ph.get("title_ja",ph["slug"])))}</a>' for ph,_ in public_pages)
    for ph,ps in pages:
        d=os.path.join(ROOT,ph["slug"]); os.makedirs(d,exist_ok=True)
        open(os.path.join(d,"index.html"),"w",encoding="utf-8").write(render_page(ph,ps,style,ga,sh,plinks))
    out = out.replace("<!--PAGES-->", plinks)
    urls=[SITE+"/"]+[f"{SITE}/works/{h['id']}/" for h,_ in works]+[f"{SITE}/{ph['slug']}/" for ph,_ in public_pages]
    sm='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sm+="".join(f"  <url><loc>{u}</loc></url>\n" for u in urls)+"</urlset>\n"
    open(os.path.join(ROOT,"sitemap.xml"),"w").write(sm)

    dst = os.path.join(ROOT, "index.html")
    open(dst, "w", encoding="utf-8").write(out)
    ncards = sum(1 for h,_ in works if h.get("card","yes")=="yes")
    print(f"OK: index.html + works/{len(works)}ページ + pages/{len(pages)}（公開 {len(public_pages)}） + sitemap.xml を再生成しました（カード {ncards} ／ 行 {len(rows_items)}）")

if __name__ == "__main__":
    main()
