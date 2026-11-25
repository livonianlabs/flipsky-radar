"""
The USA's radar now (NEXRAD base reflectivity composite, NOAA via the Iowa Environmental Mesonet, public domain)
as FlipSky's radar frames, the same as opera.py: a lat/lon grid at 0.025 deg in one 8-bit PNG per 15 minutes,
1 dry, 2-255 rain rate on the log scale (rate = 0.05 * 2 ** ((v - 2) / 25) mm/h, from Z = 200 R^1.6).

  python us.py OUT_DIR [--hours 2]
"""
import io, json, os, sys, datetime as dt, urllib.request
import numpy as np
from PIL import Image

# IEM's composite: 0.005 deg cells from 126 W, 50 N (n0q: dBZ = v * 0.5 - 32).
SRC = 'https://mesonet.agron.iastate.edu/archive/data/{y:04d}/{m:02d}/{d:02d}/GIS/uscomp/n0q_{y:04d}{m:02d}{d:02d}{H:02d}{M:02d}.png'
LON0, LAT1, CELL, K = -126.0, 50.0, 0.005, 5
UA = {'User-Agent': 'FlipSky radar (livonianlabs.github.io)'}

def frame(t):
    url = SRC.format(y=t.year, m=t.month, d=t.day, H=t.hour, M=t.minute)
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
    except Exception:
        return None
    a = np.array(Image.open(io.BytesIO(raw)))
    h, w = a.shape[0] // K * K, a.shape[1] // K * K
    # The strongest echo of each 5 x 5 block (0.025 deg).
    a = a[:h, :w].reshape(h // K, K, w // K, K).max(axis=(1, 3)).astype(np.float32)
    dbz = a * 0.5 - 32
    rate = (10 ** (dbz / 10) / 200) ** (1 / 1.6)
    out = np.ones(a.shape, np.uint8)
    # Under 20 dBZ the raw composite is mostly clutter and clear-air echo, not rain.
    wet = (dbz >= 20) & (rate >= 0.05)
    out[wet] = np.clip(np.round(2 + 25 * np.log2(rate[wet] / 0.05)), 2, 255).astype(np.uint8)
    return out

def main():
    out = sys.argv[1]; hours = float(sys.argv[sys.argv.index('--hours') + 1]) if '--hours' in sys.argv else 2.0
    os.makedirs(out, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(hours=hours)
    t = start.replace(minute=start.minute // 15 * 15, second=0, microsecond=0)
    names, shape = {}, None
    while t <= now:
        name = t.strftime('us_%Y%m%dT%H%MZ.png'); p = os.path.join(out, name)
        if not os.path.exists(p):
            img = frame(t)
            if img is not None: Image.fromarray(img, 'L').save(p, optimize=True)
        if os.path.exists(p):
            names[name] = int(t.timestamp())
            shape = shape or Image.open(p).size
        t += dt.timedelta(minutes=15)
    for f in os.listdir(out):
        if f.startswith('us_') and f.endswith('.png') and f not in names: os.remove(os.path.join(out, f))
    if shape is None: return
    w, h = shape
    step = CELL * K
    idx = {'region': 'us', 'bbox': [LON0, LAT1 - h * step, LON0 + w * step, LAT1], 'step': step,
           'encoding': 'v: 0 none, 1 dry, 2-255 rate = 0.05*2^((v-2)/25) mm/h',
           'attribution': 'Radar: NOAA NEXRAD via Iowa Environmental Mesonet',
           'frames': [{'t': ts, 'f': n} for n, ts in sorted(names.items(), key=lambda x: x[1])]}
    json.dump(idx, open(os.path.join(out, 'us.json'), 'w'), separators=(',', ':'))
    print(len(idx['frames']), 'frames')

if __name__ == '__main__':
    main()
