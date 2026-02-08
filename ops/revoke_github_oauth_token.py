import json
import base64
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parent.parent
# load .env
env = {}
for line in (root / '.env').read_text(encoding='utf-8').splitlines():
    line=line.strip()
    if not line or line.startswith('#'):
        continue
    if '=' in line:
        k,v=line.split('=',1)
        env[k.strip()] = v.strip()

client_id = env.get('GITHUB_CLIENT_ID')
client_secret = env.get('GITHUB_CLIENT_SECRET')
if not client_id or not client_secret:
    print('Missing client_id or client_secret in .env')
    raise SystemExit(1)

token_file = Path(__file__).resolve().parent.joinpath('.secrets','oauth_token.json')
if not token_file.exists():
    print('Token file not found:', token_file)
    raise SystemExit(1)

tok_json = json.loads(token_file.read_text(encoding='utf-8'))
access = tok_json.get('response',{}).get('access_token')
if not access:
    print('Access token missing in token file')
    raise SystemExit(1)

url = f'https://api.github.com/applications/{client_id}/token'
body = json.dumps({'access_token': access}).encode('utf-8')
req = urllib.request.Request(url, data=body, method='DELETE')
req.add_header('Accept','application/vnd.github+json')
req.add_header('Content-Type','application/json')
# Basic auth with client_id:client_secret
creds = f'{client_id}:{client_secret}'
req.add_header('Authorization','Basic ' + base64.b64encode(creds.encode()).decode())

out_path = Path(__file__).resolve().parent.joinpath('revoke_result.json')
try:
    with urllib.request.urlopen(req) as r:
        resp = r.read().decode('utf-8')
        code = r.getcode()
except urllib.error.HTTPError as e:
    resp = e.read().decode('utf-8')
    code = e.code

out_path.write_text(json.dumps({'status': code, 'response': resp}, ensure_ascii=False, indent=2), encoding='utf-8')
print('Wrote', out_path)
