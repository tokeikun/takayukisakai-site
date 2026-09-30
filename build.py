#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — content/ のテキストから index.html と各作品・固定ページを組み立てる。
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

def render_work_card(h, s, featured=False):
    wid = h["id"]
    loading = 'fetchpriority="high"' if h.get("featured") == "1" else 'loading="lazy"'
    out = [f'    <!-- {h["title"]} -->', f'    <article class="work" id="c-{wid}">',
           f'      <a class="worklink" href="/works/{wid}/">',
           f'        <div class="img rv"><img src="/assets/{h["image"]}" alt="{h["title"]}" {loading} decoding="async"{img_attrs(h["image"])} style="view-transition-name:vt-{wid}"></div>',
           f'        <div class="cap rv"><h2>{mixed(h["title"])}</h2><span class="yr">{h["year"]}</span></div>',
           '      </a>']
    if s.get("desc.ja"): out.append(f'      <p class="desc ja">{inline_md(s["desc.ja"])}</p>')
    if s.get("desc.en"): out.append(f'      <p class="desc en">{inline_md(s["desc.en"])}</p>')
    if not featured and (s.get("fact.ja") or s.get("fact.en")):
        out.append(f'      <p class="fact">{bi(inline_md(s.get("fact.ja","")), inline_md(s.get("fact.en","")))}</p>')
    if not featured and (s.get("concept.ja") or s.get("concept.en")):
        out.append('      <div class="said">')
        out.append('        <p class="who"><span class="ja">コンセプト</span><span class="en">CONCEPT</span></p>')
        if s.get("concept.ja"): out.append(f'        <p class="q ja">{s["concept.ja"]}</p>')
        if s.get("concept.en"): out.append(f'        <p class="q qen en">{s["concept.en"]}</p>')
        out.append('      </div>')
    ja_label = "映像と制作の背景 →" if h.get("video") or h.get("video_file") else "作品と制作の背景 →"
    en_label = "Film &amp; story →" if h.get("video") or h.get("video_file") else "Explore the work →"
    out.append(f'      <a class="more rv" href="/works/{wid}/">{bi(ja_label,en_label)}</a>')
    out.append('    </article>')
    return "\n".join(out)

def render_work_row(h, s):
    wid = h["id"]
    out = [f'      <div class="rowline"><span class="t"><a href="works/{wid}/">{h["title"]}</a></span>'
           f'<span class="d">{h["year"]}</span>']
    if s.get("desc.ja"): out.append(f'<span class="n ja">{inline_md(s["desc.ja"])}</span>')
    if s.get("desc.en"): out.append(f'<span class="n en">{inline_md(s["desc.en"])}</span>')
    out.append('</div>')
    return "".join(out)

def render_detail(h, s):
    wid = h["id"]
    out = [f'<section class="detail" id="w-{wid}">', '  <div class="dwrap">',
           '    <a class="back" href="#works"><span class="ja">← 作品にもどる</span><span class="en">← back to works</span></a>',
           f'    <h2>{h["title"]}</h2>',
           f'    <p class="dyr">{h.get("year_detail", h["year"])}</p>']
    fact = bi(inline_md(s.get("fact.ja","")), inline_md(s.get("fact.en","")))
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

HEAD_COMMON = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
  '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
  '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@400;500&family=Cormorant+Garamond:wght@400;500&display=swap">')

import struct
_size_cache={}
def img_size(fname):
    """assets/ 内の jpg/png の (w,h)。読めなければ None"""
    if not fname: return None
    if fname in _size_cache: return _size_cache[fname]
    path=os.path.join(ROOT,"assets",fname); r=None
    try:
        with open(path,"rb") as f:
            head=f.read(26)
            if head[:8]==b"\x89PNG\r\n\x1a\n":
                r=struct.unpack(">II",head[16:24])
            elif head[:2]==b"\xff\xd8":
                f.seek(2)
                while True:
                    b=f.read(1)
                    while b and b!=b"\xff": b=f.read(1)
                    while b==b"\xff": b=f.read(1)
                    if not b: break
                    m=b[0]
                    if m in (0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF):
                        f.read(3); hgt,wid=struct.unpack(">HH",f.read(4)); r=(wid,hgt); break
                    ln=struct.unpack(">H",f.read(2))[0]; f.seek(ln-2,1)
    except Exception: r=None
    _size_cache[fname]=r; return r

def thumb_src(fname):
    """assets/thumbs/ に縮小版があればそれを使う"""
    return f"/assets/thumbs/{fname}" if fname and os.path.exists(os.path.join(ROOT,"assets","thumbs",fname)) else f"/assets/{fname}"

def img_attrs(fname):
    r=img_size(fname)
    return f' width="{r[0]}" height="{r[1]}"' if r else ""

def mixed(title):
    """欧文の連なりを <span class=lt> で包む（和欧混植用）"""
    return re.sub(r"([A-Za-z0-9][A-Za-z0-9 &'\u2019\-\u2014:.,!?/]*[A-Za-z0-9.!?]|[A-Za-z0-9])", r'<span class="lt">\1</span>', title)

def header_brand(head):
    name = head.get("hero_name", "堺 崇行")
    return f'<a class="brand" href="/" aria-label="{name} / Takayuki Sakai — Home"><span class="nm">{name}</span><span class="brand-roman">TAKAYUKI SAKAI</span></a>'

def render_work_page(h, s, style, ga, all_works=None, site_head=None):
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
<meta name="theme-color" content="#f6f5f0">
{HEAD_COMMON}
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
  .wlayout{{max-width:1240px;margin:0 auto}}
  .wpage{{width:100%;max-width:1120px;margin:0 auto;padding:48px var(--gut) 64px;min-width:0}}
  .wpage h1{{font:500 clamp(32px,5vw,52px)/1.4 var(--mincho);letter-spacing:.03em}}
  .wpage .dyr{{font-size:13px;letter-spacing:.12em;color:var(--soft);margin:12px 0 32px}}
  .wpage .hero-img{{margin-bottom:32px}}
  .wpage .hero-img img{{width:100%;height:auto;max-height:85vh;object-fit:contain}}
  .wpage .fact{{margin:26px auto 40px}}
  .wpage .dbody,.wpage .process,.wpage .work-contact{{max-width:740px;margin-left:auto;margin-right:auto}}
  .wside{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0 28px;border-top:1px solid var(--line);margin:0 var(--gut);padding:30px 0 48px}}
  .wside .slabel{{grid-column:1/-1;font-size:12px;letter-spacing:.12em;color:var(--soft);margin-bottom:20px}}
  .wside a{{display:flex;align-items:center;gap:12px;padding:12px 0;text-decoration:none;font-size:14px;line-height:1.7;color:var(--soft);border-bottom:1px solid var(--line)}}
  .wside a:hover,.wside a.cur{{color:var(--ink)}}
  .wside img,.wside .ni{{width:48px;height:36px;object-fit:cover;flex:none;background:#e6e9e1}}
  .wside .ni{{display:grid;place-items:center;font-family:var(--gothic)}}
  @media(max-width:700px){{.wpage{{padding-top:28px}}.wside{{grid-template-columns:1fr 1fr}}}}
  @media(max-width:420px){{.wside{{grid-template-columns:1fr}}}}
</style>
</head>
<body data-lang="ja">
<div class="top">
  {header_brand(site_head or {})}
  <div class="nav">
    <a href="/#works"><span class="ja">作品</span><span class="en">Works</span></a>
    <a href="/contact/"><span class="ja">ご相談</span><span class="en">Contact</span></a>
    <button id="lang" aria-label="switch language">EN</button>
  </div>
</div>
<div class="wlayout">
<main class="wpage">""")
    parts.append('  <a class="back" href="/#works"><span class="ja">← 作品にもどる</span><span class="en">← back to works</span></a>')
    parts.append(f'  <h1>{mixed(title)}</h1>')
    parts.append(f'  <p class="dyr">{h.get("year_detail", h.get("year",""))}</p>')
    if h.get("video_file"):
        poster = h.get("video_poster") or img
        poster_attr = f' poster="/assets/{poster}"' if poster else ''
        parts.append(f'  <div class="video hero-film" style="view-transition-name:vt-{wid}"><video controls playsinline preload="metadata"{poster_attr} aria-label="{esc(title)} — film"><source src="/assets/{h["video_file"]}" type="video/mp4"></video></div>')
        if s.get("video_caption.ja") or s.get("video_caption.en"):
            parts.append(f'  <p class="film-caption">{bi(s.get("video_caption.ja",""),s.get("video_caption.en",""))}</p>')
    elif h.get("video") and video_embed(h["video"])[0]:
        emb,label=video_embed(h["video"]); poster=h.get("video_poster") or img
        pimg = f'<img src="/assets/{poster}" alt="{esc(title)}" fetchpriority="high" decoding="async"{img_attrs(poster)}>' if poster else ''
        sep = '&' if '?' in emb else '?'
        parts.append(f'  <div class="video yt hero-film" style="view-transition-name:vt-{wid}" data-src="{emb}{sep}autoplay=1&rel=0" data-title="{esc(title)} — film">{pimg}<button class="play" type="button" aria-label="{esc(title)} — 映像を再生"><span><i></i>Play — {label}</span></button></div>')
        if s.get("video_caption.ja") or s.get("video_caption.en"):
            parts.append(f'  <p class="film-caption">{bi(s.get("video_caption.ja",""),s.get("video_caption.en",""))}</p>')
    elif img:
        parts.append(f'  <div class="hero-img"><img src="/assets/{img}" alt="{esc(title)}" fetchpriority="high" decoding="async"{img_attrs(img)} style="view-transition-name:vt-{wid}"></div>')
    fact = bi(inline_md(s.get("fact.ja","")), inline_md(s.get("fact.en","")))
    if h.get("docs"):
        fact += f' ／ <a href="{h["docs"]}" target="_blank" rel="noopener">documentation ↗</a>'
    if fact: parts.append(f'  <p class="fact">{fact}</p>')
    if h.get("video"):
        emb,label=video_embed(h["video"])
        if False:
            poster = h.get("video_poster") or img
            pimg = f'<img src="/assets/{poster}" alt="" loading="lazy"{img_attrs(poster)}>' if poster else ''
            sep = '&' if '?' in emb else '?'
            parts.append(f'  <div class="video yt" data-src="{emb}{sep}autoplay=1&rel=0" data-title="{esc(title)} — film">{pimg}<button class="play" type="button" aria-label="{esc(title)} — 映像を再生"><span><i></i>Play — {label}</span></button></div>')
        if emb:
            parts.append(f'  <a class="vlink" href="{h["video"]}" target="_blank" rel="noopener">▶ <span class="ja">映像を見る（{label}）</span><span class="en">watch the film ({label})</span> ↗</a>')
    gallery_html = ""
    if h.get("gallery"):
        gis="".join(f'<div class="gi rv"><img src="/assets/{g.strip()}" alt="{esc(title)} — detail" loading="lazy" decoding="async"{img_attrs(g.strip())}></div>' for g in h["gallery"].split(","))
        gallery_html = f'  <div class="gallery">{gis}</div>'
        if s.get("gallery_caption.ja") or s.get("gallery_caption.en"):
            gallery_html += f'<p class="film-caption">{bi(s.get("gallery_caption.ja",""),s.get("gallery_caption.en",""))}</p>'
        if not s.get("process.ja") and not s.get("process.en"):
            parts.append(gallery_html)
    parts.append('  <div class="dbody">')
    parts.append('<div class="ja">'+block_md(s.get("detail.ja",""))+'</div>')
    parts.append('<div class="en den">'+block_md(s.get("detail.en",""))+'</div>')
    if s.get("note.ja") or s.get("note.en"):
        parts.append(f'    <p class="dlabel">{bi(inline_md(s.get("note.ja","")), inline_md(s.get("note.en","")))}</p>')
    parts.append('  </div>')
    if s.get("process.ja") or s.get("process.en"):
        parts.append('  <section class="process">')
        for language in ("ja", "en"):
            if s.get("process." + language):
                parts.append(f'    <div class="{language}">{block_md(s["process." + language])}</div>')
        parts.append('  </section>')
        if gallery_html:
            parts.append(gallery_html)
    parts.append('  <section class="work-contact"><h2><span class="ja">この作品から、話してみる。</span><span class="en">Start a conversation.</span></h2><p><span class="ja">気になったことや、一緒に試してみたいことがあれば。共同制作・展示について、お話しできればうれしいです。</span><span class="en">If this brings something to mind, or something you would like to try together, I would love to hear from you about a collaboration or exhibition.</span></p><a class="more" href="/contact/"><span class="ja">ご相談はこちら →</span><span class="en">Get in touch →</span></a></section>')
    parts.append('  </main>')
    if all_works:
        ids=[oh["id"] for oh,_ in all_works]; i=ids.index(wid) if wid in ids else 0
        prev_w=all_works[i-1][0]; next_w=all_works[(i+1)%len(all_works)][0]
        def pn(w,cls,lbl_ja,lbl_en):
            return (f'  <a class="{cls}" href="/works/{w["id"]}/" data-img="/assets/{w.get("image") or w.get("thumb") or ""}">'
                    f'<span class="lbl"><span class="ja">{lbl_ja}</span><span class="en">{lbl_en}</span></span><span class="t">{mixed(w["title"])}</span></a>')
        parts.append('<nav class="pn" aria-label="前後の作品">'+pn(prev_w,"prev","← 前の作品","← Previous")+pn(next_w,"next","次の作品 →","Next →")+'</nav>')
        side=['<aside class="wside">','  <p class="slabel"><span class="ja">作品　Works</span><span class="en">Works</span></p>']
        for oh,_os in all_works:
            oid=oh["id"]; cur=' class="cur"' if oid==wid else ''
            timg=oh.get("thumb") or oh.get("image")
            big=oh.get("image") or oh.get("thumb")
            tn=f'<img src="{thumb_src(timg)}" alt="" loading="lazy">' if timg else f'<span class="ni">{(oh["title"].strip()[:1]).upper()}</span>'
            dimg=f' data-img="/assets/{big}"' if big else ''
            side.append(f'  <a href="/works/{oid}/"{cur}{dimg}>{tn}<span>{mixed(oh["title"])}</span></a>')
        side.append('</aside>')
        parts.append("\n".join(side))
    parts.append("""</div>
<footer style="max-width:1240px;margin:0 auto;padding:30px var(--gut) 50px;border-top:0">
  <small>© 堺 崇行 / Takayuki Sakai — <a href="/" style="color:var(--soft);text-decoration:none">takayukisakai.com</a></small>
</footer>
<script src="/assets/site.js" defer></script>
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
        form_html=(f'<p class="fnote"><span class="ja">{dm} のDMからご連絡ください。</span>'
                   f'<span class="en">Get in touch via DM on {dm}.</span></p>')
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
<meta name="theme-color" content="#f6f5f0">
{HEAD_COMMON}
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE}/{slug}/">
<meta property="og:title" content="{esc(tja)} — 堺 崇行">
<meta property="og:description" content="{dja}">
<meta property="og:image" content="{SITE}/assets/og.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@tokeikun">
{ga}
<style>{style}
  .page{{max-width:1100px;margin:0 auto;padding:48px var(--gut) 80px}}
  .page h1{{font-family:var(--mincho);font-size:clamp(26px,4.5vw,40px);font-weight:600;letter-spacing:.05em;margin-bottom:6vh}}
  .page h2{{font-size:16px;letter-spacing:.08em;color:var(--soft);font-weight:400;margin:24px 0;display:flex;align-items:center;gap:16px}}
  .page .pblk{{padding:24px 0 0}}
  .page h2::after{{content:"";flex:1;height:1px;background:var(--line)}}
  .pblk:first-of-type h2{{margin-top:0}}
  .page p{{font-size:16px;line-height:2.2;max-width:38em;margin-bottom:1.4em;color:#2b2721}}
  .page ul{{list-style:none;margin:0 0 2em}}
  .page li{{font-size:16px;line-height:2;padding:10px 0;border-bottom:1px solid var(--line)}}
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
  {header_brand(site_head or {})}
  <div class="nav">
    <a href="/#works"><span class="ja">作品</span><span class="en">Works</span></a>
    <a href="/contact/"><span class="ja">ご相談</span><span class="en">Contact</span></a>
    <button id="lang" aria-label="switch language">EN</button>
  </div>
</div>
<main class="page">
{'  <p class="draft">DRAFT — 未公開（確認用）</p>' if draft else ''}
  <h1><span class="ja">{tja}</span><span class="en">{ten}</span></h1>
{chr(10).join(body)}
</main>
<footer style="max-width:720px;margin:0 auto;padding:0 var(--gut) 60px">
  <div class="links" style="display:flex;gap:24px;font-size:13px;letter-spacing:.08em;flex-wrap:wrap;margin-bottom:24px">{plinks}</div>
  <small style="font-size:10.5px;color:var(--soft);letter-spacing:.16em">© 堺 崇行 / Takayuki Sakai — <a href="/" style="color:var(--soft)">takayukisakai.com</a></small>
</footer>
<script src="/assets/site.js" defer></script>
</body>
</html>"""

def main():
    tpl = open(os.path.join(ROOT, "template.html"), encoding="utf-8").read()

    works = []
    for f in sorted(glob.glob(os.path.join(ROOT, "content/works/*.md"))):
        h, s = parse_md(f)
        if os.path.basename(f).startswith("_"): continue
        if not h.get("id") or not h.get("title"):
            print(f"!! {os.path.basename(f)}: id / title がありません。スキップ"); continue
        h.setdefault("year", "")
        h.setdefault("order", str((len(works)+1)*10))
        works.append((h, s))

    works.sort(key=lambda work: int(work[0].get("order", "999999")))

    featured_works = sorted(((h,s) for h,s in works if h.get("featured")), key=lambda work: int(work[0]["featured"]))
    lead = render_work_card(*featured_works[0], featured=True) if featured_works else ""
    cards = "\n\n".join(render_work_card(h, s, featured=True) for h, s in featured_works[1:])
    rows_items = [render_work_row(h, s) for h, s in works if h.get("card") == "row"]
    rows = ('\n    <div style="margin-top:8vh">\n' + "\n".join(rows_items) + "\n    </div>") if rows_items else ""
    details = "\n\n".join(render_detail(h, s) for h, s in works)
    index_items = []
    featured_ids = {h["id"] for h,_ in featured_works}
    for h, _s in works:
        href = "/works/"+h["id"]+"/"
        timg = h.get("thumb") or h.get("image")
        big = h.get("image") or h.get("thumb")
        initial = (h["title"].strip()[:1]).upper()
        vt = f' style="view-transition-name:vt-{h["id"]}"' if (timg and h["id"] not in featured_ids) else ''
        thumb = f'<img src="{thumb_src(timg)}" alt="" loading="lazy"{vt}>' if timg else f'<span class="noimg">{initial}</span>'
        dimg = f' data-img="/assets/{big}"' if big else ''
        index_items.append(f'      <a href="{href}"{dimg}>{thumb}<span class="t">{mixed(h["title"])}</span><span class="y">{h["year"]}</span></a>')
    windex = '<nav class="windex">\n' + "\n".join(index_items) + '\n    </nav>'

    sh, ss = parse_md(os.path.join(ROOT, "content/site.md"))

    essay = [f'      <p class="et">{ss.get("essay.title","")}</p>']
    essay.append('<div class="ja">'+block_md(ss.get("essay.ja",""))+'</div>')
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
    bio.append('<div class="ja">'+block_md(ss.get("bio.ja",""))+'</div>')
    bio.append('<div class="en">'+block_md(ss.get("bio.en",""))+'</div>')

    cred = bi(block_md(ss.get("cred.ja","")), block_md(ss.get("cred.en","")), "div")
    contact = bi(ss.get("contact.ja",""), ss.get("contact.en",""))

    out = tpl.replace("<!--HEADER_BRAND-->", header_brand(sh)).replace("<!--HEAD_COMMON-->", HEAD_COMMON)
    out = out.replace("<!--HERO_ROLE-->", sh.get("hero_role", "Artist / Design Engineer"))
    out = out.replace("<!--HERO_NAME-->", sh.get("hero_name", "堺 崇行"))
    out = out.replace("<!--HERO_SUB-->", bi(sh.get("hero_sub_ja", "Takayuki Sakai — Tokyo"), sh.get("hero_sub_en", "堺 崇行 — Tokyo")))
    intro = bi("".join(f'<p>{inline_md(p)}</p>' for p in paras(ss.get("intro.ja",""))), "".join(f'<p>{inline_md(p)}</p>' for p in paras(ss.get("intro.en",""))), "div")
    out = out.replace("<!--INTRO-->", intro)
    out = out.replace("<!--COLLAB_TITLE-->", bi(inline_md(ss.get("collaboration.title.ja","")),inline_md(ss.get("collaboration.title.en",""))))
    out = out.replace("<!--COLLAB-->", bi(inline_md(ss.get("collaboration.ja","")),inline_md(ss.get("collaboration.en",""))))
    out = out.replace("<!--CURRENT-->", bi(block_md(ss.get("current.ja","")), block_md(ss.get("current.en","")), "div"))
    out = out.replace("<!--INDEX-->", windex)
    out = out.replace("<!--LEAD_WORK-->", lead)
    out = out.replace("<!--WORKS-->", cards)
    out = out.replace("<!--ESSAY_TITLE-->", inline_md(ss.get("essay.title", "")))
    first_paragraph = next(iter(paras(ss.get("essay.ja", ""))), "")
    out = out.replace("<!--ESSAY_EXCERPT-->", bi(inline_md(first_paragraph), inline_md(ss.get("essay.note.en", "")), "div"))
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
        open(os.path.join(d,"index.html"),"w",encoding="utf-8").write(render_work_page(h,sec,style,ga,works,sh))
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
    print(f"OK: index.html（主な作品 {len(featured_works)} ／ 全作品 {len(works)}）+ works/{len(works)}ページ + pages/{len(pages)}（公開設定 {len(public_pages)}）+ sitemap.xml を再生成しました")

if __name__ == "__main__":
    main()
