import json
import urllib.parse
import urllib.request
from pathlib import Path

env = {}
# load .env manually
env = {}
root = Path(__file__).resolve().parent.parent
env_path = root / '.env'
for line in env_path.read_text(encoding='utf-8').splitlines():
    line=line.strip()
    if not line or line.startswith('#'):
        continue
    if '=' in line:
        k,v=line.split('=',1)
        env[k.strip()]=v.strip()

CLIENT_ID = env.get('GITHUB_CLIENT_ID')
CLIENT_SECRET = env.get('GITHUB_CLIENT_SECRET')
REDIRECT_URI = env.get('OAUTH_CALLBACK_URL','http://localhost:8000/auth/callback')

CB = Path(__file__).resolve().parent / 'oauth_callback_last.json'
if not CB.exists():
    print('callback file missing:', CB)
    raise SystemExit(1)

cb = json.loads(CB.read_text(encoding='utf-8'))
qs = cb.get('query',{})
code = qs.get('code',[None])[0]
state = qs.get('state',[None])[0]
print('code=',code,'state=',state)

if not code:
    print('no code in callback')
    raise SystemExit(1)

post_url = 'https://github.com/login/oauth/access_token'
data = {
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'code': code,
    'redirect_uri': REDIRECT_URI,
    'state': state
}
headers = {'Accept': 'application/json'}
req = urllib.request.Request(post_url, data=urllib.parse.urlencode(data).encode('utf-8'), headers=headers)
with urllib.request.urlopen(req) as resp:
    body = resp.read()
    try:
        out = json.loads(body)
    except Exception:
        out = {'raw': body.decode('utf-8')}

Path('oauth_token.json').write_text(json.dumps({'request':data,'response':out},ensure_ascii=False,indent=2),encoding='utf-8')
print('wrote ops/oauth_token.json')
