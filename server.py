"""Acente prototypes: mobile voice assistant and existing local desk."""
import base64
import io
import json
import os
import re
import sqlite3
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import assistant

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('ACENTE_DB', str(ROOT / 'data' / 'acente.db')))
BRANCHES = ['Trafik', 'Kasko', 'Sağlık', 'DASK', 'Konut', 'Diğer']


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute('CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, customer TEXT NOT NULL, branch TEXT NOT NULL, detail TEXT NOT NULL, status TEXT NOT NULL DEFAULT \'Bekliyor\', created TEXT DEFAULT CURRENT_TIMESTAMP)')
    return con


def extract_document(name, encoded):
    raw = base64.b64decode(encoded, validate=True)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError('Dosya en fazla 8 MB olabilir.')
    if name.lower().endswith('.pdf'):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        if len(reader.pages) > 100:
            raise ValueError('En fazla 100 sayfalık teklif yükleyin.')
        pages = [p.extract_text() or '' for p in reader.pages]
    elif name.lower().endswith('.txt'):
        pages = [raw.decode('utf-8-sig')]
    else:
        raise ValueError('Bu sürüm PDF veya UTF-8 TXT kabul ediyor.')
    if not ''.join(pages).strip():
        raise ValueError('Metin okunamadı. Taranmış PDF için OCR henüz bağlı değil.')
    categories = {
        'Prim / ödeme': r'prim|taksit|ödeme|odeme',
        'Muafiyet': r'muaf|tenzili|müşterek|musterek',
        'Teminat / limit': r'teminat|limit|bedel',
        'İstisna / özel şart': r'istisna|hariç|haric|özel şart|ozel sart|bekleme',
        'Hizmet / kapsam': r'ikame|asistans|servis|network|anlaşmalı|anlasmali|deprem|sel|cam|çekici',
    }
    findings = {k: [] for k in categories}
    for number, page in enumerate(pages, 1):
        for line in page.splitlines():
            line = line.strip()
            if not line:
                continue
            for category, pattern in categories.items():
                if re.search(pattern, line, re.I) and len(findings[category]) < 40:
                    findings[category].append({'page': number, 'text': line[:1200]})
    return {'name': Path(name).name, 'pages': len(pages), 'findings': findings,
            'notice': 'Anahtar kelimeyle bulunan belge alıntılarıdır. Yapay zekâ değerlendirmesi veya kapsam garantisi değildir. Bulunamayan bilgi, teminatın olmadığı anlamına gelmez.'}


class Handler(BaseHTTPRequestHandler):
    chat_lock = threading.BoundedSemaphore(2)
    rate_lock = threading.Lock()
    chat_times = []

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Permissions-Policy', 'microphone=(self)')
        self.send_header('Content-Security-Policy', "default-src 'self'; connect-src 'self'; img-src 'self'; style-src 'self'; script-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        super().end_headers()

    def authorized(self):
        code = os.environ.get('ACENTE_ACCESS_CODE', '')
        return not code or secrets.compare_digest(self.headers.get('Authorization', '').encode(), ('Bearer ' + code).encode())

    def api_guard(self):
        if not self.authorized():
            self.send_json({'error': 'Erişim kodunu kontrol edin.'}, 401)
            return False
        if os.environ.get('ACENTE_PUBLIC_ORIGIN') and self.path not in ('/api/chat', '/api/config'):
            self.send_json({'error': 'Bu sürümde yalnızca sesli asistan açık.'}, 403)
            return False
        return True

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/api/config':
            return self.send_json({'ai_ready': assistant.configured(),
                                   'access_required': bool(os.environ.get('ACENTE_ACCESS_CODE'))})
        if self.path.startswith('/api/') and not self.api_guard():
            return
        if self.path == '/api/tasks':
            with connect() as con:
                rows = [dict(r) for r in con.execute('SELECT * FROM tasks ORDER BY id DESC')]
            return self.send_json(rows)
        routes = {'/': ('voice.html', 'text/html; charset=utf-8'),
                  '/voice.js': ('voice.js', 'text/javascript; charset=utf-8'),
                  '/voice.css': ('voice.css', 'text/css; charset=utf-8'),
                  '/manifest.webmanifest': ('manifest.webmanifest', 'application/manifest+json'),
                  '/icon.svg': ('icon.svg', 'image/svg+xml'),
                  '/desk': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if self.path not in routes:
            return self.send_json({'error': 'Bulunamadı'}, 404)
        name, mime = routes[self.path]
        body = (ROOT / 'static' / name).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            # Browser requests must originate from this instance.
            origin = self.headers.get('Origin')
            expected_origin = os.environ.get('ACENTE_PUBLIC_ORIGIN', 'http://' + self.headers.get('Host', ''))
            if origin and origin != expected_origin:
                return self.send_json({'error': 'Farklı kaynaktan işlem kabul edilmedi.'}, 403)
            if not self.api_guard():
                return
            size = int(self.headers.get('Content-Length', '0'))
            if size < 1 or size > 12 * 1024 * 1024:
                raise ValueError('İstek boyutu geçersiz.')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('Geçersiz istek.')
            if self.path == '/api/chat':
                if size > 90000:
                    raise ValueError('Mesaj çok uzun.')
                assistant.validate_messages(data.get('messages'))
                if not assistant.configured():
                    raise assistant.AssistantUnavailable('Yapay zekâ bağlantısı henüz etkin değil. Yönetici sunucuya API anahtarını eklemeli.')
                with self.rate_lock:
                    now = time.monotonic()
                    self.chat_times[:] = [t for t in self.chat_times if now - t < 60]
                    if len(self.chat_times) >= 12:
                        return self.send_json({'error': 'Çok sık istek gönderildi. Bir dakika bekleyin.'}, 429)
                    self.chat_times.append(now)
                if not self.chat_lock.acquire(blocking=False):
                    return self.send_json({'error': 'Asistan şu anda meşgul. Biraz sonra tekrar deneyin.'}, 429)
                try:
                    answer = assistant.chat(data['messages'])
                    return self.send_json({'answer': answer})
                finally:
                    self.chat_lock.release()
            if self.path == '/api/tasks':
                customer = str(data.get('customer', '')).strip()
                detail = str(data.get('detail', '')).strip()
                branch = data.get('branch')
                if not customer or not detail or branch not in BRANCHES:
                    raise ValueError('Müşteri, branş ve iş açıklaması gerekli.')
                if len(customer) > 200 or len(detail) > 5000:
                    raise ValueError('Müşteri veya açıklama çok uzun.')
                with connect() as con:
                    cur = con.execute('INSERT INTO tasks(customer,branch,detail) VALUES (?,?,?)', (customer, branch, detail))
                return self.send_json({'id': cur.lastrowid}, 201)
            if self.path == '/api/task-status':
                if data.get('status') not in ['Bekliyor', 'Çalışılıyor', 'Tamamlandı']:
                    raise ValueError('Geçersiz durum.')
                with connect() as con:
                    cur = con.execute('UPDATE tasks SET status=? WHERE id=?', (data['status'], int(data['id'])))
                    if cur.rowcount != 1:
                        raise ValueError('İş bulunamadı.')
                return self.send_json({'ok': True})
            if self.path == '/api/document':
                return self.send_json(extract_document(str(data['name']), data['content']))
            return self.send_json({'error': 'Bulunamadı'}, 404)
        except assistant.AssistantUnavailable as exc:
            self.send_json({'error': str(exc)}, 503)
        except ImportError:
            self.send_json({'error': 'PDF bağımlılığı eksik. requirements.txt paketlerini kurun.'}, 503)
        except Exception as exc:
            # Do not expose file paths or document content in error responses.
            message = str(exc) if isinstance(exc, ValueError) else 'İşlem tamamlanamadı. Dosya biçimini ve alanları kontrol edin.'
            self.send_json({'error': message}, 400)


if __name__ == '__main__':
    host = os.environ.get('ACENTE_HOST', '127.0.0.1')
    public = os.environ.get('ACENTE_PUBLIC_ORIGIN', '')
    if host not in ('127.0.0.1', 'localhost') or public:
        if len(os.environ.get('ACENTE_ACCESS_CODE', '')) < 16 or not public.startswith('https://'):
            raise SystemExit('Ağ erişimi için en az 16 karakterli ACENTE_ACCESS_CODE ve HTTPS ACENTE_PUBLIC_ORIGIN gerekli.')
    connect().close()
    print('Acente sesli asistanı başlatılıyor. Yerel geliştirme portu: 8765')
    ThreadingHTTPServer((host, int(os.environ.get('PORT', '8765'))), Handler).serve_forever()
