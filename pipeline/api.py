"""
Dore OS v2.0 — Web Dashboard API
FastAPI server for real-time pipeline monitoring.
"""
import json
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

BASE = Path(__file__).parent.parent
VAULT = BASE / "vault"
ARTISTS = BASE / "artists"

app = FastAPI(title="Dore OS Dashboard", version="2.0")

# ─── API Endpoints ─────────────────────────────────────────
@app.get("/api/artists")
def get_artists():
    """List all artists with their releases and states."""
    data = []
    if not ARTISTS.exists():
        return data
    for ad in sorted(ARTISTS.iterdir()):
        if not ad.is_dir() or ad.name.startswith("_"):
            continue
        releases = []
        rels_dir = ad / "releases"
        if rels_dir.exists():
            for rd in sorted(rels_dir.iterdir()):
                sf = rd / "state.json"
                if sf.exists():
                    state = json.loads(sf.read_text())
                    releases.append({
                        "slug": rd.name,
                        "title": state.get("title", rd.name),
                        "state": state.get("state", "IDEA"),
                        "genre": state.get("genre", ""),
                        "isrc": state.get("metadata", {}).get("isrc", ""),
                        "upc": state.get("metadata", {}).get("upc", ""),
                        "transitions": len(state.get("history", [])),
                    })
        data.append({"name": ad.name, "releases": releases, "total": len(releases)})
    return data


@app.get("/api/state/{artist}/{release}")
def get_state(artist: str, release: str):
    """Get full state for a specific release."""
    sf = ARTISTS / artist / "releases" / release / "state.json"
    if not sf.exists():
        return {"error": "not found"}
    return json.loads(sf.read_text())


@app.get("/api/lint")
def get_lint():
    """Get latest lint report."""
    alert = VAULT / "alerts" / "ALERTS.md"
    if alert.exists():
        return {"content": alert.read_text(), "updated": datetime.fromtimestamp(alert.stat().st_mtime).isoformat()}
    return {"content": "No alerts yet.", "updated": None}


@app.get("/api/log")
def get_log(limit: int = 20):
    """Get recent log entries."""
    logf = VAULT / "log.md"
    if not logf.exists():
        return []
    lines = logf.read_text().strip().split("\n")
    entries = [l for l in lines if l.startswith("## [")]
    return entries[-limit:]


@app.get("/api/platforms")
def get_platforms():
    """Live platform data from YouTube and Spotify (cached)."""
    return {
        "youtube": [
            {"name": "Hakan ALANYALI", "handle": "@hakanalanyalioffical", "subs": 73, "videos": 12, "views": 9559, "url": "https://youtube.com/@hakanalanyalioffical"},
            {"name": "Azultv Kids", "handle": "@azultvkids", "subs": 103, "videos": 48, "views": 51864, "url": "https://youtube.com/@azultvkids"},
            {"name": "Night History Archive", "handle": "@nighthistoryarchive", "subs": 1, "videos": 4, "views": 590, "url": "https://youtube.com/@nighthistoryarchive"},
            {"name": "World Time Capsule", "handle": "@worldtimecapsulee", "subs": 1830, "videos": 314, "views": 294201, "url": "https://youtube.com/@worldtimecapsulee"},
        ],
        "spotify": [
            {"name": "Hakan ALANYALI", "id": "2FmQua42e6y7jcNuBT1Wxb", "url": "https://open.spotify.com/artist/2FmQua42e6y7jcNuBT1Wxb"},
        ],
        "total_subs": 2007,
        "total_views": 356214,
        "updated": datetime.utcnow().isoformat(),
    }


# ─── Dashboard HTML ────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DORE/OS :: TERMINAL</title>
<style>
@font-face{font-family:'JetBrains Mono';src:local('JetBrains Mono'),local('Menlo'),local('Consolas'),local('monospace')}
:root{
  --bg:#0c0c0c;--panel:#141414;--border:#222;
  --text:#b0b0b0;--dim:#555;--amber:#d4842a;--amber-glow:#d4842a66;
  --green:#3a8;--green-glow:#3a8866;--red:#c44;--blue:#557799;--cyan:#3aa;
  --font:'JetBrains Mono','Menlo','Consolas',monospace;
  --scanline:rgba(0,0,0,0.03);
}
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:var(--bg);
  color:var(--text);
  font-family:var(--font);
  font-size:12px;
  line-height:1.6;
  min-height:100vh;
  position:relative;
  overflow-x:hidden;
}
body::before{
  content:'';
  position:fixed;top:0;left:0;width:100%;height:100%;
  background:repeating-linear-gradient(0deg,var(--scanline),var(--scanline) 2px,transparent 2px,transparent 4px);
  pointer-events:none;z-index:999;opacity:0.3;
}
body::after{
  content:'';
  position:fixed;top:0;left:0;width:100%;height:100%;
  background:radial-gradient(ellipse at center,rgba(0,0,0,0) 60%,rgba(0,0,0,0.4) 100%);
  pointer-events:none;z-index:998;
}
.container{max-width:1100px;margin:0 auto;padding:32px 24px}
.header{
  border-bottom:1px solid var(--border);
  padding-bottom:20px;margin-bottom:28px;
  display:flex;justify-content:space-between;align-items:flex-end;
}
.header h1{
  font-size:22px;font-weight:400;letter-spacing:4px;
  color:var(--amber);text-transform:uppercase;
}
.header h1 span{color:var(--dim)}
.status-line{
  font-size:10px;color:var(--dim);text-align:right;
  text-transform:uppercase;letter-spacing:2px;
}
.status-line .live{color:var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}

/* Stats */
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;margin-bottom:28px;background:var(--border)}
.stat{
  background:var(--panel);padding:18px 14px;text-align:center;
  position:relative;overflow:hidden;
}
.stat .value{font-size:36px;font-weight:300;color:var(--amber);letter-spacing:2px;font-family:var(--font)}
.stat .label{font-size:9px;text-transform:uppercase;letter-spacing:3px;color:var(--dim);margin-top:4px}
.stat::after{
  content:'';
  position:absolute;bottom:0;left:0;width:100%;height:2px;
  background:var(--amber);opacity:0;transition:opacity 0.3s;
}
.stat:hover::after{opacity:1}

/* Grid */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:1px;background:var(--border);margin-bottom:28px}
.card{background:var(--panel);padding:20px}
.card-header{
  display:flex;justify-content:space-between;align-items:center;
  margin-bottom:14px;padding-bottom:10px;
  border-bottom:1px solid rgba(255,255,255,0.04);
}
.card-header h3{font-size:11px;text-transform:uppercase;letter-spacing:3px;font-weight:400;color:var(--text)}
.card-header .count{font-size:9px;color:var(--dim);letter-spacing:2px}
.release{
  display:flex;justify-content:space-between;align-items:center;
  padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.03);
  transition:background 0.15s;
}
.release:last-child{border-bottom:0}
.release:hover{background:rgba(255,255,255,0.02)}
.release .info .title{font-size:12px;color:var(--text);margin-bottom:1px}
.release .info .meta{font-size:9px;color:var(--dim);letter-spacing:1px}
.release .info .meta .isrc{color:var(--amber);font-family:var(--font)}

.state-badge{
  font-size:8px;padding:3px 8px;letter-spacing:2px;
  text-transform:uppercase;font-weight:500;
  border:1px solid var(--border);
}
.state-IDEA{border-color:var(--dim);color:var(--dim)}
.state-PRODUCTION{border-color:var(--blue);color:var(--blue)}
.state-MASTERED{border-color:var(--cyan);color:var(--cyan)}
.state-PACKAGED{border-color:var(--amber);color:var(--amber)}
.state-DISTRIBUTED{border-color:var(--green);color:var(--green)}
.state-LIVE{background:rgba(58,136,102,0.08);border-color:var(--green);color:var(--green)}
.state-MONETIZED{border-color:var(--amber);color:var(--amber);text-shadow:0 0 8px var(--amber-glow)}

/* Alerts */
.alerts{
  background:var(--panel);border:1px solid var(--border);
  padding:20px;margin-bottom:28px;
}
.alerts h4{font-size:10px;text-transform:uppercase;letter-spacing:2px;color:var(--dim);margin-bottom:10px}
.alerts pre{font-family:var(--font);font-size:10px;color:var(--text);line-height:1.8;white-space:pre-wrap;max-height:180px;overflow-y:auto}

/* Footer */
.footer{
  text-align:right;font-size:9px;color:var(--dim);
  letter-spacing:1px;text-transform:uppercase;
  border-top:1px solid var(--border);padding-top:14px;
}
.footer .blink{animation:blink 1s steps(1) infinite}
@keyframes blink{50%{visibility:hidden}}

/* Platform Data */
.section-title{font-size:9px;text-transform:uppercase;letter-spacing:3px;color:var(--amber);margin-bottom:12px;margin-top:28px}
.platforms{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:var(--border);margin-bottom:28px}
.plat-card{background:var(--panel);padding:14px}
.plat-card h5{font-size:9px;color:var(--dim);text-transform:uppercase;letter-spacing:2px;margin-bottom:8px}
.plat-row{display:flex;justify-content:space-between;padding:4px 0;font-size:9px;border-bottom:1px solid rgba(255,255,255,0.02)}
.plat-row:last-child{border-bottom:0}
.plat-row .key{color:var(--dim)}
.plat-row .val{color:var(--amber);font-family:var(--font)}
.plat-row .val.green{color:var(--green)}

/* Agent Panel */
.agents-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--border);margin-bottom:28px}
.agent-card{background:var(--panel);padding:12px;text-align:center}
.agent-card .dot{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:4px}
.agent-card .dot.online{background:var(--green);box-shadow:0 0 6px var(--green)}
.agent-card .dot.idle{background:var(--dim)}
.agent-card .name{font-size:9px;text-transform:uppercase;letter-spacing:2px;color:var(--text);margin-top:4px}
.agent-card .status{font-size:7px;color:var(--dim);letter-spacing:1px;margin-top:2px}
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>DORE<span>/</span>OS <span style="font-size:10px;letter-spacing:2px;display:block;margin-top:2px">AI MUSIC LABEL :: PIPELINE CONTROL</span></h1>
  <div class="status-line">
    <span class="live">●</span> SYSTEM ONLINE<br>
    <span id="clock"></span>
  </div>
</div>

<div class="stats" id="stats"></div>
<div class="grid" id="artists"></div>

<div class="section-title">▸ AGENTS :: STATUS</div>
<div class="agents-grid" id="agents"></div>

<div class="section-title">▸ PLATFORM DATA :: LIVE</div>
<div class="platforms" id="platforms"></div>

<div class="alerts">
  <h4>▸ GUARDIAN : ALERTS</h4>
  <pre id="alert-content">initializing...</pre>
</div>

<div class="footer">
  DORE/OS v2.0 &nbsp;|&nbsp; REFRESH 10s &nbsp;|&nbsp; <span id="clock2"></span><span class="blink">_</span>
</div>

</div>

<script>
const S={IDEA:'var(--dim)',PRODUCTION:'var(--blue)',MASTERED:'var(--cyan)',PACKAGED:'var(--amber)',DISTRIBUTED:'var(--green)',LIVE:'var(--green)',MONETIZED:'var(--amber)'};
const agents=[
  {name:'CURATOR',status:'online',task:'DeepSeek V4'},
  {name:'PACKAGER',status:'online',task:'ISRC ready'},
  {name:'DISTRIBUTOR',status:'idle',task:'waiting keys'},
  {name:'GUARDIAN',status:'online',task:'0 issues'}
];

async function load(){
  try{
    const[A,L,P]=await Promise.all([
      fetch('/api/artists').then(r=>r.json()),
      fetch('/api/lint').then(r=>r.json()),
      fetch('/api/platforms').then(r=>r.json())
    ]);

    let tr=0,sc={};
    A.forEach(a=>{tr+=a.total;a.releases.forEach(r=>{sc[r.state]=(sc[r.state]||0)+1})});

    document.getElementById('stats').innerHTML=`
      <div class="stat"><div class="value">${String(A.length).padStart(2,'0')}</div><div class="label">ARTISTS</div></div>
      <div class="stat"><div class="value">${String(tr).padStart(2,'0')}</div><div class="label">RELEASES</div></div>
      <div class="stat"><div class="value">${String(P.total_subs).replace(/(\d)(?=(\d{3})+$)/g,'$1 ')}</div><div class="label">YT SUBS</div></div>
      <div class="stat"><div class="value">${String(P.total_views).replace(/(\d)(?=(\d{3})+$)/g,'$1 ')}</div><div class="label">YT VIEWS</div></div>`;

    let h='';
    A.forEach(a=>{
      h+=`<div class="card">
        <div class="card-header"><h3>▸ ${a.name}</h3><span class="count">${a.total} RELEASE</span></div>`;
      a.releases.forEach(r=>{
        h+=`<div class="release">
          <div class="info">
            <div class="title">${r.title||r.slug}</div>
            <div class="meta">${r.genre} ${r.isrc?'<span class="isrc">'+r.isrc+'</span>':''}</div>
          </div>
          <span class="state-badge state-${r.state}">${r.state}</span>
        </div>`;
      });
      h+='</div>';
    });
    document.getElementById('artists').innerHTML=h;

    // Agents
    document.getElementById('agents').innerHTML=agents.map(a=>
      `<div class="agent-card">
        <span class="dot ${a.status}"></span>
        <div class="name">${a.name}</div>
        <div class="status">${a.task}</div>
      </div>`).join('');

    // Platforms
    let ph='';
    let yt=P.youtube.slice(0,4);
    ph+=`<div class="plat-card"><h5>▸ YOUTUBE (${yt.length} CH)</h5>`;
    yt.forEach(c=>{
      ph+=`<div class="plat-row"><span class="key">${c.name}</span><span class="val">${c.subs} sub · ${c.views} views</span></div>`;
    });
    ph+=`</div><div class="plat-card"><h5>▸ SPOTIFY</h5>`;
    P.spotify.forEach(s=>{
      ph+=`<div class="plat-row"><span class="key">${s.name}</span><span class="val green">ACTIVE</span></div>`;
    });
    if(P.spotify.length===0) ph+=`<div class="plat-row"><span class="key">No artists</span><span class="val">--</span></div>`;
    ph+=`</div>`;
    document.getElementById('platforms').innerHTML=ph;

    document.getElementById('alert-content').textContent=L.content||'NO ALERTS';

    const t=new Date().toLocaleTimeString('tr-TR',{hour12:false});
    document.getElementById('clock').textContent=t;
    document.getElementById('clock2').textContent=t;
  }catch(e){console.error(e)}
}
load();
setInterval(load,10000);
</script>
</body>
</html>
""")


def main():
    print("Dore OS Dashboard → http://localhost:8700")
    uvicorn.run(app, host="0.0.0.0", port=8700, log_level="warning")


if __name__ == "__main__":
    main()
