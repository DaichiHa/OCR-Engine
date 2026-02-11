import json
import urllib.request
from pathlib import Path

# Load token
tok = json.loads(Path(__file__).resolve().parent.joinpath('.secrets','oauth_token.json').read_text(encoding='utf-8'))
access = tok['response'].get('access_token')
if not access:
    print('no access token')
    raise SystemExit(1)

owner = 'DaichiHa'
repo = 'OCR-Engine'
url = f'https://api.github.com/repos/{owner}/{repo}/issues'
body = json.dumps({'title':'Test issue from demo','body':'This is a permissions test.'}).encode('utf-8')
req = urllib.request.Request(url, data=body, headers={'Authorization':f'token {access}','User-Agent':'OCR-Engine','Accept':'application/vnd.github+json'})
try:
    with urllib.request.urlopen(req) as r:
        print('Created issue:', r.status)
        print(r.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print('HTTPError', e.code, e.reason)
    print(e.read().decode('utf-8'))
