# Uploads a folder's radar frames, then indexes, to the R2 bucket (keys from R2_KEYS, default r2.txt).
import re, hashlib, hmac, datetime, urllib.request, sys, os
t = open(os.environ.get('R2_KEYS', 'r2.txt'), encoding='utf-8-sig').read()
url = re.search(r'https://([a-f0-9]+)\.r2\.cloudflarestorage\.com', t)
hexes = re.findall(r'\b[a-f0-9]{32,64}\b', t)
kid = next(h for h in hexes if len(h) == 32 and h != url.group(1)); sec = next(h for h in hexes if len(h) == 64)
host = url.group(0)[8:]
def sign(k, m): return hmac.new(k, m.encode(), hashlib.sha256).digest()
def put(path, name, ctype, cache):
    body = open(path, 'rb').read()
    now = datetime.datetime.now(datetime.timezone.utc); amz = now.strftime('%Y%m%dT%H%M%SZ'); d = now.strftime('%Y%m%d')
    ph = hashlib.sha256(body).hexdigest()
    hdr = {'cache-control': cache, 'content-type': ctype, 'host': host, 'x-amz-content-sha256': ph, 'x-amz-date': amz}
    sh = ';'.join(sorted(hdr)); ch = ''.join(f"{k}:{hdr[k]}\n" for k in sorted(hdr))
    canon = f"PUT\n/flipsky-radar/{name}\n\n{ch}\n{sh}\n{ph}"
    scope = f"{d}/auto/s3/aws4_request"
    sts = f"AWS4-HMAC-SHA256\n{amz}\n{scope}\n" + hashlib.sha256(canon.encode()).hexdigest()
    k = sign(sign(sign(sign(('AWS4' + sec).encode(), d), 'auto'), 's3'), 'aws4_request')
    sig = hmac.new(k, sts.encode(), hashlib.sha256).hexdigest()
    h = {k2: v for k2, v in hdr.items() if k2 != 'host'}
    h['Authorization'] = f"AWS4-HMAC-SHA256 Credential={kid}/{scope}, SignedHeaders={sh}, Signature={sig}"
    urllib.request.urlopen(urllib.request.Request(f"https://{host}/flipsky-radar/{name}", data=body, headers=h, method='PUT'), timeout=60)
d = sys.argv[1]
fs = sorted(os.listdir(d))
for f in [x for x in fs if x.endswith('.png')] + [x for x in fs if x.endswith('.json')]:
    put(os.path.join(d, f), f, 'image/png' if f.endswith('.png') else 'application/json', 'public, max-age=86400' if f.endswith('.png') else 'public, max-age=120')
print('uploaded', len(fs))
