"""Fetch the frames already published (from the Worker) into OUT_DIR, so a run only processes new ones."""
import json, os, sys, urllib.request
BASE = os.environ.get('RADAR_BASE', 'https://flipsky-radar.livonianlabs.workers.dev')
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
for region in ('eu', 'us'):
    try:
        idx = json.load(urllib.request.urlopen(f'{BASE}/{region}.json', timeout=30))
    except Exception as e:
        print(region, 'no index:', e); continue
    for f in idx.get('frames', []):
        p = os.path.join(out, f['f'])
        if not os.path.exists(p):
            try: open(p, 'wb').write(urllib.request.urlopen(f"{BASE}/{f['f']}", timeout=60).read())
            except Exception as e: print('skip', f['f'], e)
    print(region, len(idx.get('frames', [])), 'published frames seeded')
