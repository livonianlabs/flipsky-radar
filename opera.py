"""
Europe's radar now (EUMETNET OPERA rain-rate composite, CC BY 4.0) as FlipSky's radar frames: a lat/lon grid
(plate carree, as the app's map) in one 8-bit PNG per frame, 0 no radar, 1 dry, 2-255 rain rate on a log scale
(rate = 0.05 * 2 ** ((v - 2) / 25) mm/h, up to ~50 mm/h); plus index.json listing the frames, newest last.

  python opera.py OUT_DIR [--hours 2]
Fetches the frames of the last [hours] not yet in OUT_DIR, deletes older ones, rewrites index.json.
"""
import io, json, math, os, sys, datetime as dt, urllib.request
import numpy as np, h5py
from pyproj import Transformer
from PIL import Image

LON0, LON1, LAT0, LAT1, STEP = -25.0, 45.0, 31.0, 71.5, 0.025
SRC = 'https://object-store.os-api.cci1.ecmwf.int/openradar-24h-backup/{y:04d}/{m:02d}/{d:02d}/OPERA/COMP/OPERA@{y:04d}{m:02d}{d:02d}T{H:02d}{M:02d}@0@RATE.h5'
UA = {'User-Agent': 'FlipSky radar (livonianlabs.github.io)'}

_grid = None
def grid(where):
    """For each output pixel, its row and column in the composite (or -1 outside it); computed once."""
    global _grid
    if _grid is None:
        lons = np.arange(LON0 + STEP / 2, LON1, STEP)
        lats = np.arange(LAT1 - STEP / 2, LAT0, -STEP)
        lo, la = np.meshgrid(lons, lats)
        t = Transformer.from_proj('EPSG:4326', where['projdef'].decode(), always_xy=True)
        x, y = t.transform(lo, la)
        # ODIM: the projected grid's upper left from the corner coordinates.
        ux, uy = t.transform(where['UL_lon'], where['UL_lat'])
        col = np.floor((x - ux) / where['xscale']).astype(np.int32)
        row = np.floor((uy - y) / where['yscale']).astype(np.int32)
        bad = (col < 0) | (row < 0) | (col >= where['xsize']) | (row >= where['ysize'])
        col[bad] = -1; row[bad] = -1
        _grid = (row, col)
    return _grid

def encode(rate, nodata, undetect):
    out = np.zeros(rate.shape, np.uint8)
    have = rate != nodata
    out[have] = 1
    wet = have & (rate != undetect) & (rate >= 0.05)
    v = 2 + 25 * np.log2(rate[wet] / 0.05)
    out[wet] = np.clip(np.round(v), 2, 255).astype(np.uint8)
    return out

def frame(t):
    url = SRC.format(y=t.year, m=t.month, d=t.day, H=t.hour, M=t.minute)
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
    except Exception:
        return None
    f = h5py.File(io.BytesIO(raw), 'r')
    where = dict(f['where'].attrs)
    what = dict(f['dataset1/data1/what'].attrs)
    data = f['dataset1/data1/data'][:] * what['gain'] + what['offset']
    enc = encode(data, what['nodata'] * what['gain'] + what['offset'], what['undetect'] * what['gain'] + what['offset'])
    row, col = grid(where)
    img = np.zeros(row.shape, np.uint8)
    ok = row >= 0
    img[ok] = enc[row[ok], col[ok]]
    return img

def main():
    out = sys.argv[1]; hours = float(sys.argv[sys.argv.index('--hours') + 1]) if '--hours' in sys.argv else 2.0
    os.makedirs(out, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(hours=hours)
    # Every 15 minutes (the rain-rate composite's step), the last ones possibly not out yet.
    t = start.replace(minute=start.minute // 15 * 15, second=0, microsecond=0)
    want = []
    while t <= now:
        want.append(t); t += dt.timedelta(minutes=15)
    names = {}
    for t in want:
        name = t.strftime('eu_%Y%m%dT%H%MZ.png')
        p = os.path.join(out, name)
        if not os.path.exists(p):
            img = frame(t)
            if img is None: continue
            Image.fromarray(img, 'L').save(p, optimize=True)
        names[name] = int(t.timestamp())
    for f in os.listdir(out):
        if f.startswith('eu_') and f.endswith('.png') and f not in names:
            os.remove(os.path.join(out, f))
    idx = {'region': 'eu', 'bbox': [LON0, LAT0, LON1, LAT1], 'step': STEP,
           'encoding': 'v: 0 none, 1 dry, 2-255 rate = 0.05*2^((v-2)/25) mm/h',
           'attribution': 'Radar: EUMETNET OPERA, CC BY 4.0',
           'frames': [{'t': ts, 'f': n} for n, ts in sorted(names.items(), key=lambda x: x[1])]}
    json.dump(idx, open(os.path.join(out, 'eu.json'), 'w'), separators=(',', ':'))
    print(len(idx['frames']), 'frames')

if __name__ == '__main__':
    main()
