import json, os, hashlib, datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path,data):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def env():
 p=ROOT/'.env'
 if p.exists():
  for line in p.read_text(encoding='utf-8').splitlines():
   if '=' in line and not line.startswith('#'):
    k,v=line.split('=',1);os.environ.setdefault(k.strip(),v.strip())
 return os.environ
