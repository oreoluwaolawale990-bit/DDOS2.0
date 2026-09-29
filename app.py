from flask import Flask, request, jsonify
import requests
import threading
import time
from datetime import datetime

app = Flask(__name__)

MAX_RPS = 1000000
targets = []
logs = []
stats = {"total": 0, "ok": 0, "fail": 0, "current_rps": 0}

def log(msg, color="green"):
    logs.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": msg, "color": color})
    if len(logs) > 150:
        logs.pop(0)
    print(msg)

def ping(url):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Render-Keeper/1.0"})
        return True, r.status_code
    except Exception as e:
        return False, str(e)[:80]

def worker(target_id):
    while True:
        t = next((x for x in targets if x["id"] == target_id), None)
        if not t or not t["active"]:
            break
        ok, status = ping(t["url"])
        t["pings"] += 1
        stats["total"] += 1
        if ok:
            stats["ok"] += 1
            t["status"] = f"OK {status}"
            log(f"PING OK: {t['label'] or t['url']} -> {status} | {t['pings']}", "green")
        else:
            stats["fail"] += 1
            t["status"] = "FAIL"
            log(f"FAIL: {t['url']} -> {status}", "red")
        time.sleep(1.0 / max(1, t["rps"]))

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Render Keeper - Fixed</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#07080a;--card:#111317;--border:#1e2128;--green:#00ff88;--cyan:#00e5ff;--red:#ff2d55;--text:#e8e9ed;--muted:#8a8d97}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:'Space Grotesk',sans-serif;min-height:100vh}
.bg{position:fixed;inset:0;z-index:-1;background:radial-gradient(800px at 20% -10%, rgba(0,255,136,.15), transparent), radial-gradient(600px at 90% 10%, rgba(0,229,255,.12), transparent), var(--bg)}
.top{border-bottom:1px solid var(--border);background:rgba(7,8,10,.8);backdrop-filter:blur(20px);padding:14px 24px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
.logo{font-weight:700;display:flex;gap:10px;align-items:center}
.dot{width:10px;height:10px;background:var(--green);border-radius:50%;box-shadow:0 0 15px var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.wrap{max-width:1100px;margin:0 auto;padding:20px;display:grid;grid-template-columns:360px 1fr;gap:16px}
@media(max-width:900px){.wrap{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px}
.h{font-size:11px;letter-spacing:1.5px;color:var(--muted);margin-bottom:16px;text-transform:uppercase;font-weight:600;display:flex;justify-content:space-between}
.label{font-size:11px;color:var(--muted);margin:14px 0 6px;display:block;font-weight:600}
.input{width:100%;background:#080a0d;border:1px solid var(--border);color:var(--text);padding:12px 14px;border-radius:10px;font-family:'JetBrains Mono';font-size:13px;outline:none}
.input:focus{border-color:var(--green);box-shadow:0 0 0 4px rgba(0,255,136,.1)}
.range{width:100%;accent-color:var(--green);margin-top:8px}
.rps-display{font-family:'JetBrains Mono';font-size:22px;font-weight:700;color:var(--green);margin-top:6px}
.btn{border:1px solid var(--border);background:var(--card);color:var(--text);padding:12px 16px;border-radius:10px;font-size:12px;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px}
.btn:hover{border-color:var(--green);background:rgba(0,255,136,.06)}
.btn-primary{background:var(--green);color:#000;border-color:var(--green);font-weight:700}
.btn-danger{color:var(--red);border-color:rgba(255,45,85,.3)}
.list{display:grid;gap:10px;max-height:360px;overflow:auto}
.item{background:#0d0f13;border:1px solid var(--border);border-radius:12px;padding:14px;display:flex;justify-content:space-between;align-items:center}
.item-title{font-weight:600;font-size:13px}
.item-url{font-family:'JetBrains Mono';font-size:10px;color:var(--muted);margin-top:2px}
.badge{font-size:10px;padding:4px 10px;border-radius:20px;border:1px solid var(--border);font-weight:600;font-family:'JetBrains Mono'}
.badge-on{background:rgba(0,255,136,.15);color:var(--green);border-color:rgba(0,255,136,.3)}
.badge-off{background:#15181e;color:var(--muted)}
.terminal{background:#080a0d;border:1px solid var(--border);border-radius:16px;height:560px;display:flex;flex-direction:column;overflow:hidden}
.term-head{padding:14px 18px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;background:#0d0f13}
.term-body{flex:1;overflow:auto;padding:14px;font-family:'JetBrains Mono';font-size:11px;line-height:1.9;white-space:pre-wrap}
.log-ok{color:var(--green)} .log-fail{color:var(--red)} .log-info{color:var(--muted)}
.stats{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px;margin-top:14px}
.stat{background:#0d0f13;border:1px solid var(--border);border-radius:12px;padding:12px;text-align:center}
.stat b{font-size:18px;display:block;font-family:'JetBrains Mono'} .stat span{font-size:10px;color:var(--muted);text-transform:uppercase}
</style>
</head>
<body>
<div class="bg"></div>
<div class="top"><div class="logo"><span class="dot"></span> RENDER_KEEPER // FIXED</div><div style="font-size:11px;color:var(--muted)">Single file - no templates folder needed</div></div>
<div class="wrap">
<div>
<div class="card">
<div class="h">Add Target <span style="color:var(--green)">Server Mode</span></div>
<label>Target URL</label>
<input id="url" class="input" placeholder="https://ttdownloader-hraw.onrender.com">
<label>Label</label>
<input id="label" class="input" placeholder="TT Downloader">
<label>Requests Per Second</label>
<input id="rps" class="range" type="range" min="1" max="1000000" value="2" step="1">
<div class="rps-display" id="rpsVal">2 RPS</div>
<div style="margin-top:16px;display:grid;gap:8px">
<button class="btn btn-primary" onclick="add()">+ ADD TO SERVER</button>
<div style="display:flex;gap:8px"><button class="btn" style="flex:1" onclick="startAll()">▶ START ALL</button><button class="btn btn-danger" style="flex:1" onclick="stopAll()">■ STOP</button></div>
</div>
<div class="stats">
<div class="stat"><b id="total">0</b><span>Total</span></div>
<div class="stat"><b id="ok" style="color:var(--green)">0</b><span>OK</span></div>
<div class="stat"><b id="fail" style="color:var(--red)">0</b><span>Fail</span></div>
<div class="stat"><b id="curRps" style="color:var(--cyan)">0</b><span>RPS</span></div>
</div>
</div>
<div class="card" style="margin-top:14px">
<div class="h">Targets <span id="cnt">0</span></div>
<div id="list" class="list"></div>
</div>
</div>
<div class="card" style="padding:0;overflow:hidden;display:flex;flex-direction:column">
<div class="term-head"><span>Server Logs</span><button class="btn" style="padding:6px 12px;font-size:10px" onclick="load()">↻</button></div>
<div id="logs" class="term-body"></div>
</div>
</div>
<script>
async function api(p,m='GET',b=null){let o={method:m,headers:{'Content-Type':'application/json'}};if(b)o.body=JSON.stringify(b);let r=await fetch(p,o);return r.json()}
async function load(){
 let d=await api('/api/data');
 document.getElementById('cnt').innerText=d.targets.length;
 document.getElementById('total').innerText=d.stats.total;
 document.getElementById('ok').innerText=d.stats.ok;
 document.getElementById('fail').innerText=d.stats.fail;
 document.getElementById('curRps').innerText=d.stats.current_rps||0;
 document.getElementById('list').innerHTML=d.targets.map(t=>`
  <div class="item">
   <div><div class="item-title">${t.label||'Untitled'}</div><div class="item-url">${t.url} • ${t.rps} RPS • ${t.status} • ${t.pings}</div></div>
   <div style="display:flex;gap:6px;align-items:center"><span class="badge ${t.active?'badge-on':'badge-off'}">${t.active?t.rps+' RPS':'OFF'}</span><button class="btn" style="padding:6px 10px;font-size:10px" onclick="toggle(${t.id})">${t.active?'STOP':'START'}</button><button class="btn btn-danger" style="padding:6px 8px;font-size:10px" onclick="removeT(${t.id})">✕</button></div>
  </div>
 `).join('') || '<div style="text-align:center;padding:30px;opacity:.3">No targets</div>';
 document.getElementById('logs').innerHTML=d.logs.map(l=>`<div class="${l.color==='green'?'log-ok':l.color==='red'?'log-fail':'log-info'}">[${l.time}] ${l.msg}</div>`).join('');
 document.getElementById('logs').scrollTop=99999;
}
async function add(){
 let url=document.getElementById('url').value.trim(), label=document.getElementById('label').value.trim(), rps=document.getElementById('rps').value;
 if(!url){alert('Enter URL');return}
 await api('/api/add','POST',{url,label,rps});
 document.getElementById('url').value=''; load();
}
async function removeT(id){await api('/api/remove/'+id,'DELETE'); load()}
async function toggle(id){
 let d=await api('/api/data');
 let t=d.targets.find(x=>x.id===id);
 if(t.active) await api('/api/stop/'+id,'POST');
 else await api('/api/start/'+id,'POST');
 load();
}
async function startAll(){await api('/api/start_all','POST'); load()}
async function stopAll(){await api('/api/stop_all','POST'); load()}
document.getElementById('rps').addEventListener('input',e=>{document.getElementById('rpsVal').innerText=e.target.value+' RPS'});
setInterval(load,2000);
load();
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return HTML

@app.route("/api/data")
def get_data():
    active_rps = sum([t["rps"] for t in targets if t["active"]])
    stats["current_rps"] = active_rps
    return jsonify({"targets": targets, "logs": logs[-60:], "stats": stats})

@app.route("/api/add", methods=["POST"])
def add_target():
    data = request.json
    url = data.get("url", "").strip()
    label = data.get("label", "").strip()
    rps = int(data.get("rps", 2))
    rps = max(1, min(MAX_RPS, rps))
    if not url.startswith("http"):
        return jsonify({"error": "URL must start with https://"}), 400
    t = {"id": len(targets)+1, "url": url, "label": label, "rps": rps, "active": False, "pings": 0, "status": "idle"}
    targets.append(t)
    log(f"ADDED: {label or url} at {rps} RPS", "green")
    return jsonify({"ok": True})

@app.route("/api/start/<int:tid>", methods=["POST"])
def start_target(tid):
    t = next((x for x in targets if x["id"] == tid), None)
    if not t:
        return jsonify({"error": "not found"}), 404
    if t["active"]:
        return jsonify({"ok": True})
    t["active"] = True
    threading.Thread(target=worker, args=(t["id"],), daemon=True).start()
    log(f"STARTED: {t['label'] or t['url']} at {t['rps']} RPS", "green")
    return jsonify({"ok": True})

@app.route("/api/stop/<int:tid>", methods=["POST"])
def stop_target(tid):
    t = next((x for x in targets if x["id"] == tid), None)
    if t:
        t["active"] = False
        t["status"] = "stopped"
        log(f"STOPPED: {t['label'] or t['url']}", "yellow")
    return jsonify({"ok": True})

@app.route("/api/start_all", methods=["POST"])
def start_all():
    for t in targets:
        if not t["active"]:
            t["active"] = True
            threading.Thread(target=worker, args=(t["id"],), daemon=True).start()
    log(f"STARTED ALL {len(targets)}", "green")
    return jsonify({"ok": True})

@app.route("/api/stop_all", methods=["POST"])
def stop_all():
    for t in targets:
        t["active"] = False
        t["status"] = "stopped"
    log("STOPPED ALL", "yellow")
    return jsonify({"ok": True})

@app.route("/api/remove/<int:tid>", methods=["DELETE"])
def remove_target(tid):
    global targets
    t = next((x for x in targets if x["id"] == tid), None)
    if t:
        t["active"] = False
    targets = [x for x in targets if x["id"] != tid]
    log(f"REMOVED {tid}", "yellow")
    return jsonify({"ok": True})

if __name__ == "__main__":
    log("SERVER BOOTED - Fixed single file version", "green")
    app.run(host="0.0.0.0", port=10000)
