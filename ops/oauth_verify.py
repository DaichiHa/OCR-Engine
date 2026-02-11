import json
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parent.parent
tok = json.loads((root / 'oauth_token.json').read_text(encoding='utf-8'))
access = tok['response'].get('access_token')
if not access:
    print('no access token')
    raise SystemExit(1)

req = urllib.request.Request('https://api.github.com/user', headers={'Authorization': f'token {access}', 'User-Agent':'OCR-Engine'})
with urllib.request.urlopen(req) as r:
    out = r.read().decode('utf-8')
    Path(__file__).resolve().parent.joinpath('oauth_user.json').write_text(out,encoding='utf-8')
    print('wrote ops/oauth_user.json')
