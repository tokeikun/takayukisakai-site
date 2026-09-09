#!/usr/bin/env python3
"""A loopback-only writing desk for the existing static portfolio."""
import argparse, errno, hashlib, importlib.util, json, os, re, secrets, shutil, subprocess, sys, tempfile, threading, time, urllib.parse, urllib.request, uuid, webbrowser
from http import cookies
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / '.editor'
LOCK = threading.RLock()
SESSION = secrets.token_urlsafe(32)
CSRF = secrets.token_urlsafe(32)
APP_ID = hashlib.sha256(str(ROOT).encode()).hexdigest()[:16]
COOKIE = 'portfolio_editor_' + APP_ID
MAX_BODY = 32 * 1024 * 1024
RESERVED = {'assets','editor','edit','api','content','works','.git','.editor'}
spec = importlib.util.spec_from_file_location('portfolio_build', ROOT / 'build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class Problem(Exception):
    def __init__(self, message, status=400): self.message, self.status = message, status

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        if tmp.exists(): tmp.unlink()

def source_paths():
    return [ROOT / 'content/site.md', *sorted((ROOT/'content/works').glob('*.md')), *sorted((ROOT/'content/pages').glob('*.md'))]

def document_path(rel):
    if not isinstance(rel, str) or not re.fullmatch(r'content/(site\.md|(?:works|pages)/[a-zA-Z0-9_-]+\.md)', rel):
        raise Problem('このページは編集できません。')
    path = ROOT / rel
    if path.is_symlink() or ROOT not in path.resolve().parents: raise Problem('無効な保存先です。')
    return path

def draft():
    path = STATE/'draft.json'
    if not path.exists(): return {'revision': 0, 'entries': {}, 'updated': None}
    return json.loads(path.read_text(encoding='utf-8'))

def state_payload():
    docs=[]
    for p in source_paths():
        if p.name.startswith('_'): continue
        docs.append({'path':str(p.relative_to(ROOT)), 'text':p.read_text(encoding='utf-8'), 'sha':digest(p)})
    assets=[]
    for p in sorted((ROOT/'assets').rglob('*')):
        if p.is_file() and not p.is_symlink() and p.suffix.lower() in ('.jpg','.jpeg','.png','.webp','.gif','.mp4','.mov'):
            assets.append({'name':str(p.relative_to(ROOT/'assets')), 'url':'/assets/'+urllib.parse.quote(str(p.relative_to(ROOT/'assets'))), 'video':p.suffix.lower() in ('.mp4','.mov')})
    return {'csrf':CSRF,'documents':docs,'assets':assets,'draft':draft(),'mode':'local'}

def validate_text(rel, text):
    if not isinstance(text,str) or len(text.encode('utf-8'))>500_000: raise Problem('文章が長すぎます。')
    if re.search(r'<\s*(script|iframe|object|embed|svg|style)\b|\bon\w+\s*=|javascript\s*:',text,re.I):
        raise Problem('埋め込みコードは使えません。リンクや画像の追加を使ってください。')
    # Parse in an isolated temporary file using the site's own format reader.
    STATE.mkdir(exist_ok=True)
    fd,tmp=tempfile.mkstemp(suffix='.md',dir=STATE)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:f.write(text)
        head,sections=builder.parse_md(tmp)
    finally: os.unlink(tmp)
    for key,value in head.items():
        if '<' in value or '>' in value: raise Problem('タイトルや設定にHTMLは使えません。')
    if '/works/' in rel:
        if not head.get('title','').strip():raise Problem('作品のタイトルを入れてください。')
        if not re.fullmatch(r'[a-z0-9-]+',head.get('id','')):raise Problem('作品の識別情報が正しくありません。')
        for key in ('order','featured'):
            if head.get(key) and not re.fullmatch(r'[1-9]\d{0,5}',head[key]):raise Problem('作品の並び順が正しくありません。')
        old=document_path(rel)
        if old.exists() and builder.parse_md(old)[0].get('id')!=head['id']:raise Problem('既存作品のURLは変更できません。')
    if '/pages/' in rel:
        slug=head.get('slug','')
        if not re.fullmatch(r'[a-z0-9-]+',slug) or slug in RESERVED:raise Problem('ページのURLが正しくありません。')
        old=document_path(rel)
        if old.exists() and builder.parse_md(old)[0].get('slug')!=slug:raise Problem('既存ページのURLは変更できません。')
    return head

def save_draft(data):
    current=draft()
    if data.get('revision')!=current['revision']:raise Problem('別の編集画面で下書きが更新されました。書きかけはこのブラウザに残しています。画面を開き直し、復元して内容を確認してください。',409)
    entries=data.get('entries')
    if not isinstance(entries,dict) or len(entries)>300:raise Problem('下書きの形式が正しくありません。')
    for rel,entry in entries.items():
        path=document_path(rel)
        if not isinstance(entry,dict) or not isinstance(entry.get('text'),str):raise Problem('下書きの形式が正しくありません。')
        if len(entry['text'].encode('utf-8'))>500_000:raise Problem('文章が長すぎます。')
        if entry.get('base_sha') is not None and not re.fullmatch('[0-9a-f]{64}',str(entry['base_sha'])):raise Problem('保存情報が正しくありません。')
        if not path.exists() and not rel.startswith('content/works/'):raise Problem('新しく追加できるのは作品ページです。')
    saved={'revision':current['revision']+1,'entries':entries,'updated':time.time()}
    atomic(STATE/'draft.json',json.dumps(saved,ensure_ascii=False).encode())
    return saved

def apply_draft(data):
    watched=[*source_paths(), ROOT/'build.py', ROOT/'template.html']
    source_snapshot={str(p):digest(p) for p in watched}
    current=draft()
    if data.get('revision')!=current['revision']:raise Problem('下書きが更新されています。保存完了後にもう一度お試しください。',409)
    entries=current['entries']
    if not entries:return {'revision':current['revision'],'applied':0}
    for rel,entry in entries.items():
        path=document_path(rel)
        if digest(path)!=entry.get('base_sha'):raise Problem('元のページが別の場所で更新されています。下書きは保存されています。内容を確認してから反映してください。',409)
        validate_text(rel,entry['text'])
    STATE.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='build-',dir=STATE) as folder:
        stage=Path(folder)
        shutil.copy2(ROOT/'build.py',stage/'build.py');shutil.copy2(ROOT/'template.html',stage/'template.html')
        shutil.copytree(ROOT/'content',stage/'content')
        for rel,entry in entries.items():
            p=stage/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(entry['text'],encoding='utf-8')
        works=[builder.parse_md(p)[0] for p in (stage/'content/works').glob('*.md') if not p.name.startswith('_')]
        ids=[h.get('id') for h in works]
        if len(ids)!=len(set(ids)):raise Problem('同じURLの作品が重複しています。')
        for h in works:
            refs=[h.get(k) for k in ('image','thumb','video_file','video_poster') if h.get(k)] + [s.strip() for s in h.get('gallery','').split(',') if s.strip()]
            for ref in refs:
                p=(ROOT/'assets'/ref).resolve()
                if ROOT/'assets' not in p.parents or not p.is_file():raise Problem('画像または動画が見つかりません。選び直してください。')
        try:
            subprocess.run([sys.executable,str(stage/'build.py')],cwd=stage,check=True,capture_output=True,timeout=30)
        except (subprocess.SubprocessError,OSError):raise Problem('ページを作成できませんでした。下書きは保存されています。',422)
        changes={rel:entry['text'].encode('utf-8') for rel,entry in entries.items()}
        for p in stage.rglob('*.html'):
            rel=str(p.relative_to(stage))
            if rel=='template.html':continue
            changes[rel]=p.read_bytes()
        changes['sitemap.xml']=(stage/'sitemap.xml').read_bytes()
        # Recheck all sources after building, including documents this draft did not edit.
        if source_snapshot != {str(p):digest(p) for p in [*source_paths(), ROOT/'build.py', ROOT/'template.html']}:
            raise Problem('反映中にサイトが別の場所で更新されました。下書きは保持しています。',409)
        for rel,entry in entries.items():
            if digest(document_path(rel))!=entry.get('base_sha'):raise Problem('反映中に元のページが更新されました。下書きは保持しています。',409)
        history=STATE/'history'/(time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]);history.mkdir(parents=True)
        originals={}
        for rel in changes:
            p=ROOT/rel;originals[rel]=p.read_bytes() if p.exists() else None
            if p.exists():
                q=history/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
        (history/'manifest.json').write_text(json.dumps({rel:val is not None for rel,val in originals.items()}))
        saved={'revision':current['revision']+1,'entries':{},'updated':time.time()}
        written=[]
        try:
            for rel,content in changes.items():atomic(ROOT/rel,content);written.append(rel)
            atomic(STATE/'draft.json',json.dumps(saved).encode())
        except OSError:
            for rel in reversed(written):
                if originals[rel] is None:(ROOT/rel).unlink(missing_ok=True)
                else:atomic(ROOT/rel,originals[rel])
            raise Problem('保存できませんでした。変更前の状態に戻しました。下書きは残っています。',500)
    return {'revision':saved['revision'],'applied':len(entries)}

class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
    def host_ok(self):return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
    def session_ok(self):
        c=cookies.SimpleCookie()
        try:c.load(self.headers.get('Cookie',''))
        except cookies.CookieError:return False
        return COOKIE in c and secrets.compare_digest(c[COOKIE].value,SESSION)
    def reply(self,code,data):
        body=json.dumps(data,ensure_ascii=False).encode();self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
    def send_file(self,path,editor=False):
        data=path.read_bytes();self.send_response(200)
        self.send_header('Content-Type',self.guess_type(str(path))+ ('; charset=utf-8' if path.suffix in ('.html','.js','.css') else ''))
        self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store' if editor or path.suffix=='.html' else 'no-cache')
        self.send_header('X-Content-Type-Options','nosniff')
        if editor:
            self.send_header('Set-Cookie',f'{COOKIE}={SESSION}; HttpOnly; SameSite=Strict; Path=/')
            self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; media-src 'self' blob:; frame-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        if self.command!='HEAD':self.wfile.write(data)
    def do_GET(self):
        if not self.host_ok():return self.reply(403,{'error':'アクセスできません。'})
        route=urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
        if route=='/api/health':return self.reply(200,{'editor':APP_ID})
        if route=='/api/state':
            if not self.session_ok():return self.reply(403,{'error':'編集画面を開き直してください。'})
            with LOCK:return self.reply(200,state_payload())
        if route in ('/edit','/edit/'):
            return self.send_file(ROOT/'editor/index.html',editor=True)
        if route.startswith('/editor/'):
            name=route.removeprefix('/editor/')
            if name not in ('editor.css','editor.js'):return self.reply(404,{'error':'Not found'})
            return self.send_file(ROOT/'editor'/name)
        parts=Path(route.lstrip('/')).parts
        if '..' in parts or any(p.startswith('.') for p in parts):return self.reply(404,{'error':'Not found'})
        candidate=ROOT/route.lstrip('/')
        if candidate.is_symlink() or any(p.is_symlink() for p in candidate.parents if p!=ROOT and ROOT in p.parents):return self.reply(404,{'error':'Not found'})
        path=candidate.resolve()
        if path.is_dir():path=path/'index.html'
        allowed=path==ROOT/'index.html' or path==ROOT/'sitemap.xml' or path==ROOT/'robots.txt' or (parts and parts[0] in ('assets','works','contact','press'))
        if not allowed or ROOT not in path.parents or not path.is_file():return self.reply(404,{'error':'Not found'})
        # Range responses let the browser seek through locally hosted films.
        match=re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers.get('Range',''))
        if match:
            size=path.stat().st_size;start=int(match[1]);end=min(int(match[2]) if match[2] else size-1,size-1)
            if start> end:
                self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return
            self.send_response(206);self.send_header('Content-Type',self.guess_type(str(path)));self.send_header('Content-Range',f'bytes {start}-{end}/{size}');self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes');self.end_headers()
            with path.open('rb') as f:f.seek(start);self.wfile.write(f.read(end-start+1))
        else:self.send_file(path)
    def do_POST(self):
        if not self.host_ok() or not self.session_ok():return self.reply(403,{'error':'編集画面を開き直してください。'})
        origin=self.headers.get('Origin')
        if origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}') or not secrets.compare_digest(self.headers.get('X-Editor-CSRF',''),CSRF):return self.reply(403,{'error':'この画面からは保存できません。'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<=0 or size>MAX_BODY:raise Problem('ファイルは32MB以内にしてください。',413)
            body=self.rfile.read(size)
            if len(body)!=size:raise Problem('受信できませんでした。')
            route=urllib.parse.urlsplit(self.path).path
            with LOCK:
                if route=='/api/upload':
                    mime=self.headers.get('Content-Type','')
                    kinds=[('image/jpeg','.jpg',body[:3]==b'\xff\xd8\xff'),('image/png','.png',body[:8]==b'\x89PNG\r\n\x1a\n'),('image/webp','.webp',body[:4]==b'RIFF' and body[8:12]==b'WEBP'),('image/gif','.gif',body[:6] in (b'GIF87a',b'GIF89a')),('video/mp4','.mp4',body[4:8]==b'ftyp')]
                    ext=next((ext for kind,ext,valid in kinds if kind==mime and valid),None)
                    if not ext:raise Problem('JPEG・PNG・WebP・GIF画像、またはMP4動画を選んでください。')
                    name='upload-'+time.strftime('%Y%m%d')+'-'+uuid.uuid4().hex[:12]+ext
                    atomic(ROOT/'assets'/name,body)
                    return self.reply(200,{'name':name,'url':'/assets/'+name,'video':ext=='.mp4'})
                data=json.loads(body)
                if route=='/api/draft':return self.reply(200,save_draft(data))
                if route=='/api/apply':return self.reply(200,apply_draft(data))
                raise Problem('Not found',404)
        except Problem as e:self.reply(e.status,{'error':e.message})
        except (ValueError,TypeError):self.reply(400,{'error':'保存する内容を確認してください。'})
        except OSError:self.reply(500,{'error':'保存できませんでした。空き容量やフォルダを確認してください。'})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8766);parser.add_argument('--open',action='store_true');args=parser.parse_args()
    STATE.mkdir(exist_ok=True)
    try:
        server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    except OSError as e:
        if e.errno!=errno.EADDRINUSE:raise
        existing=f'http://127.0.0.1:{args.port}'
        try:
            with urllib.request.urlopen(existing+'/api/health',timeout=2) as response: running=json.load(response)
        except Exception:running={}
        if running.get('editor')==APP_ID:
            print('編集画面: '+existing+'/edit/',flush=True)
            if args.open:webbrowser.open(existing+'/edit/')
            sys.exit(0)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    url=f'http://127.0.0.1:{server.server_port}/edit/'
    print('編集画面: '+url,flush=True)
    if args.open:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
