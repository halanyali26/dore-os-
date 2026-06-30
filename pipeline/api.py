"""
Dore OS v2.0 — Web Dashboard API
FastAPI server for real-time pipeline monitoring.
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

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


@app.get("/api/status")
def get_status():
    """Live agent status from vault + system checks."""
    agents = {}
    if ARTISTS.exists():
        for ad in sorted(ARTISTS.iterdir()):
            if not ad.is_dir() or ad.name.startswith("_"):
                continue
            rels_dir = ad / "releases"
            if not rels_dir.exists():
                continue
            for rd in sorted(rels_dir.iterdir()):
                sf = rd / "state.json"
                if sf.exists():
                    state = json.loads(sf.read_text())
                    s = state.get("state", "IDEA")
                    agents.setdefault(s, 0)
                    agents[s] = agents[s] + 1

    lint_path = VAULT / "alerts" / "ALERTS.md"
    lint_issues = 0
    if lint_path.exists():
        lint_issues = lint_path.read_text().count("\n- **[")

    log_path = VAULT / "log.md"
    log_count = 0
    last_log = None
    if log_path.exists():
        lines = [l for l in log_path.read_text().split("\n") if l.startswith("## [")]
        log_count = len(lines)
        if lines:
            last_log = lines[-1].strip("# [] ")

    return {
        "agents": [
            {"name": "CURATOR", "status": "online" if agents.get("IDEA", 0) > 0 else "idle",
             "task": f"{agents.get('IDEA', 0)} ideas" if agents.get("IDEA", 0) else "waiting"},
            {"name": "PACKAGER", "status": "online" if agents.get("PACKAGED", 0) > 0 else "idle",
             "task": f"{agents.get('PACKAGED', 0)} packaged" if agents.get("PACKAGED", 0) else "ISRC ready"},
            {"name": "DISTRIBUTOR", "status": "online" if agents.get("DISTRIBUTED", 0) > 0 else "idle",
             "task": f"{agents.get('DISTRIBUTED', 0)} distributed" if agents.get("DISTRIBUTED", 0) else "waiting upload"},
            {"name": "GUARDIAN", "status": "online" if lint_issues == 0 else "online",
             "task": f"{lint_issues} issues" if lint_issues else "0 issues"},
        ],
        "states": agents,
        "lint_issues": lint_issues,
        "log_count": log_count,
        "last_log": last_log,
    }


@app.get("/api/platforms")
def get_platforms():
    """Live platform data from Composio bridge accounts (cached 5 min)."""
    from pipeline.platform_cache import get_platform_cache
    from pipeline.composio_bridge import COMPOSIO_CAPABILITIES

    cache = get_platform_cache()

    def build_platform_data():
        yt_config = COMPOSIO_CAPABILITIES.get("youtube", {})
        sp_config = COMPOSIO_CAPABILITIES.get("spotify", {})

        youtube_channels = []
        total_subs = 0
        total_views = 0

        for acc in yt_config.get("accounts", []):
            subs = acc.get("subs", 0)
            channel_data = {
                "name": acc.get("channel", acc.get("alias", acc["id"])),
                "handle": acc.get("alias") or acc.get("channel", ""),
                "subs": subs,
                "videos": acc.get("videos", 0),
                "views": acc.get("views", 0),
                "url": acc.get("url", f"https://youtube.com/@{acc.get('alias', '')}" if acc.get("alias") else ""),
            }
            youtube_channels.append(channel_data)
            total_subs += subs
            total_views += acc.get("views", 0)

        spotify_artists = []
        for acc in sp_config.get("accounts", []):
            spotify_artists.append({
                "name": acc.get("alias", acc.get("id", "Unknown")),
                "id": acc.get("id", ""),
                "url": acc.get("external_url", f"https://open.spotify.com/artist/{acc.get('id', '')}"),
            })

        return {
            "youtube": youtube_channels,
            "spotify": spotify_artists,
            "total_subs": total_subs,
            "total_views": total_views,
            "updated": datetime.now(tz=timezone.utc).isoformat(),
        }

    return cache.get_or_set("platforms", build_platform_data)


@app.get("/api/platform-cache-stats")
def get_platform_cache_stats():
    """Get platform cache statistics."""
    from pipeline.platform_cache import get_platform_cache, get_composio_cache
    return {
        "platform": get_platform_cache().stats,
        "composio": get_composio_cache().stats,
    }


@app.get("/api/composio")
def get_composio():
    """All Composio connected apps and agent capabilities."""
    try:
        from pipeline.composio_bridge import COMPOSIO_CAPABILITIES, AGENT_COMPOSIO_MAP
        apps = {}
        for name, cfg in COMPOSIO_CAPABILITIES.items():
            apps[name] = {
                "accounts": len(cfg["accounts"]),
                "read_tools": len(cfg["tools"].get("read", [])),
                "write_tools": len(cfg["tools"].get("write", [])),
                "agent_actions": list(cfg["agent_actions"].keys()),
            }
        return {
            "apps": apps,
            "agents": {n: list(c.keys()) for n, c in AGENT_COMPOSIO_MAP.items()},
            "total_accounts": sum(len(c["accounts"]) for c in COMPOSIO_CAPABILITIES.values()),
            "total_tools": sum(len(c["tools"].get("read",[]))+len(c["tools"].get("write",[])) for c in COMPOSIO_CAPABILITIES.values()),
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Dashboard HTML ────────────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DORE/OS :: AGENT ROOMS</title>
<style>
@font-face{font-family:'JetBrains Mono';src:local('JetBrains Mono'),local('Menlo'),local('Consolas'),local('monospace')}
:root{
  --bg:#06060c; --bg2:#0c0c18; --panel:rgba(16,16,32,0.85);
  --border:rgba(255,255,255,0.06); --border-glow:rgba(212,132,42,0.15);
  --text:#c4c4d0; --dim:#555570; --bright:#e8e8f0;
  --amber:#d4842a; --amber-glow:#d4842a55; --amber-dim:rgba(212,132,42,0.12);
  --green:#3a8; --green-glow:#3a8866; --red:#c44; --blue:#557799; --cyan:#3aa; --purple:#7c5ce7;
  --font:'JetBrains Mono','Menlo','Consolas',monospace;
  --radius:12px; --radius-sm:6px;
}
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:var(--bg);
  color:var(--text);
  font-family:var(--font);
  font-size:11px;
  line-height:1.5;
  min-height:100vh;
  position:relative;
  overflow-x:hidden;
}
body::before{
  content:'';position:fixed;inset:0;
  background:
    radial-gradient(ellipse at 20% 0%, rgba(124,92,231,0.06) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 100%, rgba(212,132,42,0.04) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 50%, rgba(58,136,102,0.03) 0%, transparent 70%);
  pointer-events:none;z-index:0;
}
.container{max-width:1300px;margin:0 auto;padding:24px 20px;position:relative;z-index:1}

/* Header */
.header{
  display:flex;justify-content:space-between;align-items:flex-end;
  padding-bottom:16px;margin-bottom:20px;
  border-bottom:1px solid var(--border);
}
.header h1{font-size:20px;font-weight:400;letter-spacing:6px;color:var(--amber);text-transform:uppercase}
.header h1 span{color:var(--dim);letter-spacing:2px}
.header h1 .sub{font-size:9px;letter-spacing:3px;display:block;margin-top:2px;color:var(--dim)}
.status-line{font-size:9px;color:var(--dim);text-align:right;text-transform:uppercase;letter-spacing:2px}
.status-line .live{color:var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}

/* Stats Row */
.stats-row{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:20px}
.stat-card{
  background:var(--panel);border:1px solid var(--border);
  border-radius:var(--radius);padding:16px;
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  text-align:center;transition:border-color 0.3s;
}
.stat-card:hover{border-color:var(--border-glow)}
.stat-card .value{font-size:28px;font-weight:300;color:var(--amber);letter-spacing:2px}
.stat-card .label{font-size:8px;text-transform:uppercase;letter-spacing:3px;color:var(--dim);margin-top:4px}

/* ─── AGENT ROOMS ──────────────────────── */
.section-label{
  font-size:9px;text-transform:uppercase;letter-spacing:4px;
  color:var(--dim);margin-bottom:12px;display:flex;align-items:center;gap:8px;
}
.section-label::after{content:'';flex:1;height:1px;background:var(--border)}
.rooms-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:20px}
.agent-room{
  background:var(--panel);border:1px solid var(--border);
  border-radius:var(--radius);padding:18px;
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  position:relative;overflow:hidden;
  transition:all 0.3s;
}
.agent-room::before{
  content:'';position:absolute;top:0;left:0;width:3px;height:100%;
  background:var(--border-glow);opacity:0;transition:opacity 0.3s;
}
.agent-room:hover{border-color:var(--border-glow);transform:translateY(-1px)}
.agent-room:hover::before{opacity:1}
.agent-room.online{border-left:2px solid var(--green)}
.agent-room.idle{border-left:2px solid var(--dim)}
.room-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.room-agent{display:flex;align-items:center;gap:10px}
.room-avatar{
  width:32px;height:32px;border-radius:var(--radius-sm);
  display:flex;align-items:center;justify-content:center;font-size:16px;
  border:1px solid var(--border);
}
.av-curator{background:rgba(124,92,231,0.15);border-color:rgba(124,92,231,0.3)}
.av-packager{background:rgba(212,132,42,0.15);border-color:rgba(212,132,42,0.3)}
.av-distributor{background:rgba(58,136,102,0.15);border-color:rgba(58,136,102,0.3)}
.av-guardian{background:rgba(85,119,153,0.15);border-color:rgba(85,119,153,0.3)}
.room-name{font-size:10px;text-transform:uppercase;letter-spacing:3px;color:var(--text)}
.room-status{font-size:7px;letter-spacing:2px;text-transform:uppercase;display:flex;align-items:center;gap:4px}
.room-status .dot{width:5px;height:5px;border-radius:50%}
.room-status .dot.online{background:var(--green);box-shadow:0 0 8px var(--green)}
.room-status .dot.idle{background:var(--dim)}
.room-status .task{color:var(--dim)}
.room-body{display:flex;flex-wrap:wrap;gap:4px}
.room-tag{
  font-size:7px;padding:3px 8px;border-radius:10px;
  letter-spacing:1px;text-transform:uppercase;
  border:1px solid var(--border);
}
.room-tag.action{background:var(--amber-dim);border-color:rgba(212,132,42,0.2);color:var(--amber)}

/* ─── PIPELINE KANBAN ──────────────────── */
.kanban{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:20px}
.kanban-col{
  background:var(--panel);border:1px solid var(--border);
  border-radius:var(--radius);padding:12px;
  backdrop-filter:blur(12px);
}
.kanban-col h4{font-size:8px;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid var(--border)}
.kanban-col h4.idea{color:var(--dim)}
.kanban-col h4.production{color:var(--blue)}
.kanban-col h4.mastered{color:var(--cyan)}
.kanban-col h4.packaged{color:var(--amber)}
.kanban-col h4.distributed{color:var(--green)}
.kanban-item{
  background:rgba(255,255,255,0.02);border:1px solid var(--border);
  border-radius:var(--radius-sm);padding:8px 10px;margin-bottom:4px;
  font-size:9px;transition:all 0.2s;
}
.kanban-item:hover{background:rgba(255,255,255,0.04);border-color:var(--border-glow)}
.kanban-item .ki-title{color:var(--text);margin-bottom:2px}
.kanban-item .ki-meta{font-size:7px;color:var(--dim)}
.kanban-empty{font-size:8px;color:var(--dim);text-align:center;padding:12px 0;opacity:0.5}

/* ─── PLATFORM BAR ─────────────────────── */
.platform-bar{display:grid;grid-template-columns:2fr 1fr 1fr;gap:10px;margin-bottom:20px}
.plat-panel{
  background:var(--panel);border:1px solid var(--border);
  border-radius:var(--radius);padding:14px;
  backdrop-filter:blur(12px);
}
.plat-panel h5{font-size:8px;text-transform:uppercase;letter-spacing:2px;color:var(--dim);margin-bottom:10px}
.plat-item{display:flex;justify-content:space-between;padding:4px 0;font-size:8px;border-bottom:1px solid rgba(255,255,255,0.02)}
.plat-item:last-child{border-bottom:0}
.plat-item .key{color:var(--dim)}
.plat-item .val{color:var(--amber)}

/* ─── ACTIVITY FEED ────────────────────── */
.activity{
  background:var(--panel);border:1px solid var(--border);
  border-radius:var(--radius);padding:16px;
  backdrop-filter:blur(12px);margin-bottom:20px;
}
.activity h4{font-size:9px;text-transform:uppercase;letter-spacing:3px;color:var(--dim);margin-bottom:10px}
.activity .log-line{
  font-size:9px;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.02);
  color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.activity .log-line .ts{color:var(--dim);margin-right:8px}

/* Footer */
.footer{
  text-align:right;font-size:8px;color:var(--dim);
  letter-spacing:1px;text-transform:uppercase;
  border-top:1px solid var(--border);padding-top:12px;
}
.footer .blink{animation:blink 1s steps(1) infinite}
@keyframes blink{50%{visibility:hidden}}

@media(max-width:900px){
  .kanban{grid-template-columns:repeat(3,1fr)}
  .rooms-grid{grid-template-columns:1fr}
  .platform-bar{grid-template-columns:1fr}
  .stats-row{grid-template-columns:repeat(2,1fr)}
}
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>DORE<span>/</span>OS <span class="sub">AI MUSIC LABEL :: MULTI-AGENT ROOMS</span></h1>
  <div class="status-line">
    <span class="live">●</span> SYSTEM ONLINE<br>
    <span id="clock"></span>
  </div>
</div>

<div class="stats-row" id="stats"></div>

<div class="section-label">▸ AGENT ROOMS</div>
<div class="rooms-grid" id="agent-rooms"></div>

<div class="section-label">▸ PIPELINE :: KANBAN BOARD</div>
<div class="kanban" id="kanban"></div>

<div class="section-label">▸ CONNECTED PLATFORMS</div>
<div class="platform-bar" id="platforms"></div>

<div class="section-label">▸ ACTIVITY FEED</div>
<div class="activity" id="activity">
  <div class="log-line"><span class="ts">--:--</span> loading...</div>
</div>

<div class="footer">
  DORE/OS v2.0 &nbsp;|&nbsp; AGENT ROOMS &nbsp;|&nbsp; REFRESH 10s &nbsp;|&nbsp; <span id="clock2"></span><span class="blink">_</span>
</div>

</div>

<script>
const AGENT_ICONS={CURATOR:'🎨',PACKAGER:'📦',DISTRIBUTOR:'🚀',GUARDIAN:'🛡️'};
const AGENT_AVATAR={CURATOR:'av-curator',PACKAGER:'av-packager',DISTRIBUTOR:'av-distributor',GUARDIAN:'av-guardian'};
const KANBAN_COLS=['IDEA','PRODUCTION','MASTERED','PACKAGED','DISTRIBUTED'];
const COL_CLASS={IDEA:'idea',PRODUCTION:'production',MASTERED:'mastered',PACKAGED:'packaged',DISTRIBUTED:'distributed'};

async function load(){
  try{
    const[A,L,P,S]=await Promise.all([
      fetch('/api/artists').then(r=>r.json()),
      fetch('/api/lint').then(r=>r.json()),
      fetch('/api/platforms').then(r=>r.json()),
      fetch('/api/status').then(r=>r.json())
    ]);

    // Stats
    let tr=0;
    A.forEach(a=>{tr+=a.total});
    document.getElementById('stats').innerHTML=`
      <div class="stat-card"><div class="value">${String(A.length).padStart(2,'0')}</div><div class="label">Artists</div></div>
      <div class="stat-card"><div class="value">${String(tr).padStart(2,'0')}</div><div class="label">Releases</div></div>
      <div class="stat-card"><div class="value">${String(P.total_subs).replace(/(\\d)(?=(\\d{3})+$)/g,'$1 ')}</div><div class="label">YT Subscribers</div></div>
      <div class="stat-card"><div class="value">${String(P.total_views).replace(/(\\d)(?=(\\d{3})+$)/g,'$1 ')}</div><div class="label">YT Views</div></div>`;

    // Agent Rooms
    let liveAgents=S.agents||[{name:'CURATOR',status:'online',task:'waiting'},{name:'PACKAGER',status:'idle',task:'ISRC ready'},{name:'DISTRIBUTOR',status:'idle',task:'waiting upload'},{name:'GUARDIAN',status:'online',task:'0 issues'}];
    let roomsHTML='';
    liveAgents.forEach(a=>{
      let actions=[];
      if(a.name==='CURATOR') actions=['discover_trends','generate_idea'];
      if(a.name==='PACKAGER') actions=['generate_isrc','generate_metadata','store_assets'];
      if(a.name==='DISTRIBUTOR') actions=['youtube_upload','spotify_playlist','notify_email'];
      if(a.name==='GUARDIAN') actions=['check_youtube','check_spotify','lint_vault'];
      roomsHTML+=`<div class="agent-room ${a.status}">
        <div class="room-header">
          <div class="room-agent">
            <div class="room-avatar ${AGENT_AVATAR[a.name]||'av-curator'}">${AGENT_ICONS[a.name]||'🤖'}</div>
            <div class="room-name">${a.name}</div>
          </div>
          <div class="room-status">
            <span class="dot ${a.status}"></span>
            <span class="task">${a.task}</span>
          </div>
        </div>
        <div class="room-body">
          ${actions.map(act=>`<span class="room-tag action">${act}</span>`).join('')}
        </div>
      </div>`;
    });
    document.getElementById('agent-rooms').innerHTML=roomsHTML;

    // Pipeline Kanban
    let kanbanHTML='';
    KANBAN_COLS.forEach(col=>{
      let items=A.flatMap(a=>a.releases.filter(r=>r.state===col).map(r=>({...r,artist:a.name})));
      kanbanHTML+=`<div class="kanban-col"><h4 class="${COL_CLASS[col]||'idea'}">${col}</h4>`;
      if(items.length===0){
        kanbanHTML+=`<div class="kanban-empty">— empty —</div>`;
      }else{
        items.forEach(it=>{
          kanbanHTML+=`<div class="kanban-item">
            <div class="ki-title">${it.title||it.slug}</div>
            <div class="ki-meta">${it.artist} · ${it.genre||''}</div>
          </div>`;
        });
      }
      kanbanHTML+=`</div>`;
    });
    document.getElementById('kanban').innerHTML=kanbanHTML;

    // Platforms
    let ph='';
    let yt=P.youtube.slice(0,4);
    ph+=`<div class="plat-panel"><h5>▸ YOUTUBE</h5>`;
    yt.forEach(c=>{ph+=`<div class="plat-item"><span class="key">${c.name}</span><span class="val">${c.subs} sub</span></div>`});
    ph+=`</div>`;
    ph+=`<div class="plat-panel"><h5>▸ SPOTIFY</h5>`;
    P.spotify.forEach(s=>{ph+=`<div class="plat-item"><span class="key">${s.name}</span><span class="val" style="color:var(--green)">ACTIVE</span></div>`});
    if(!P.spotify.length) ph+=`<div class="plat-item"><span class="key">No artists</span><span class="val">--</span></div>`;
    ph+=`</div>`;
    ph+=`<div class="plat-panel"><h5>▸ GUARDIAN</h5>
      <div class="plat-item"><span class="key">Lint Issues</span><span class="val" style="color:${S.lint_issues>0?'var(--red)':'var(--green)'}">${S.lint_issues||0}</span></div>
      <div class="plat-item"><span class="key">Log Entries</span><span class="val">${S.log_count||0}</span></div>
      ${S.last_log?`<div class="plat-item"><span class="key">Last</span><span class="val" style="font-size:7px">${S.last_log.substring(0,40)}</span></div>`:''}
    </div>`;
    document.getElementById('platforms').innerHTML=ph;

    // Activity Feed
    let logHTML='';
    let logs=[];
    if(S.last_log) logs.push({ts:'now',text:S.last_log});
    A.forEach(a=>{a.releases.forEach(r=>{logs.push({ts:r.state,text:`${a.name}/${r.slug}: ${r.state} · ${r.genre||''}`})})});
    logs=logs.slice(0,8);
    if(logs.length===0) logs=[{ts:'--:--',text:'No activity yet'}];
    logs.forEach(l=>{logHTML+=`<div class="log-line"><span class="ts">${l.ts}</span>${l.text}</div>`});
    document.getElementById('activity').innerHTML='<h4>▸ ACTIVITY FEED</h4>'+logHTML;

    const t=new Date().toLocaleTimeString('tr-TR',{hour12:false});
    document.getElementById('clock').textContent=t;
    document.getElementById('clock2').textContent=t;
  }catch(e){console.error(e)}
}
load();
setInterval(load,10000);
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(DASHBOARD_HTML)


def main():
    print("Dore OS Dashboard → http://localhost:8700")
    uvicorn.run(app, host="0.0.0.0", port=8700, log_level="warning")


if __name__ == "__main__":
    main()
