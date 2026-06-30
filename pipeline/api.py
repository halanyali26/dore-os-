"""
Dore OS v2.0 — Web Dashboard API
FastAPI server for real-time pipeline monitoring.
"""
import json, sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).parent.parent))
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

BASE = Path(__file__).parent.parent
VAULT = BASE / "vault"
ARTISTS = BASE / "artists"
app = FastAPI(title="Dore OS Dashboard", version="2.0")

@app.get("/api/artists")
def get_artists():
    data = []
    if not ARTISTS.exists(): return data
    for ad in sorted(ARTISTS.iterdir()):
        if not ad.is_dir() or ad.name.startswith("_"): continue
        releases = []
        rels_dir = ad / "releases"
        if rels_dir.exists():
            for rd in sorted(rels_dir.iterdir()):
                sf = rd / "state.json"
                if sf.exists():
                    s = json.loads(sf.read_text())
                    releases.append({"slug": rd.name, "title": s.get("title", rd.name),
                        "state": s.get("state", "IDEA"), "genre": s.get("genre", ""),
                        "isrc": s.get("metadata", {}).get("isrc", "")})
        info = {}
        if (ad / "info.json").exists(): info = json.loads((ad / "info.json").read_text())
        data.append({"name": ad.name.replace("-", " ").title(), "slug": ad.name,
            "releases": releases, "total": len(releases), "platform": info.get("platform", "dore-os"),
            "spotify_streams": info.get("streams_28d", 0)})
    return data

@app.get("/api/lint")
def get_lint():
    alert = VAULT / "alerts" / "ALERTS.md"
    if alert.exists(): return {"content": alert.read_text(), "updated": datetime.fromtimestamp(alert.stat().st_mtime).isoformat()}
    return {"content": "No alerts yet.", "updated": None}

@app.get("/api/status")
def get_status():
    agents = {}
    if ARTISTS.exists():
        for ad in sorted(ARTISTS.iterdir()):
            if not ad.is_dir() or ad.name.startswith("_"): continue
            rels_dir = ad / "releases"
            if not rels_dir.exists(): continue
            for rd in sorted(rels_dir.iterdir()):
                sf = rd / "state.json"
                if sf.exists():
                    s = json.loads(sf.read_text()).get("state", "IDEA")
                    agents[s] = agents.get(s, 0) + 1
    lint_issues = (VAULT / "alerts" / "ALERTS.md").read_text().count("\n- **[") if (VAULT / "alerts" / "ALERTS.md").exists() else 0
    log_count, last_log = 0, None
    if (VAULT / "log.md").exists():
        lines = [l for l in (VAULT / "log.md").read_text().split("\n") if l.startswith("## [")]
        log_count = len(lines)
        if lines: last_log = lines[-1].strip("# [] ")
    return {"agents": [
        {"name": "CURATOR", "status": "online" if agents.get("IDEA", 0) > 0 else "idle", "task": f"{agents.get('IDEA', 0)} ideas"},
        {"name": "PACKAGER", "status": "online" if agents.get("PACKAGED", 0) > 0 else "idle", "task": f"{agents.get('PACKAGED', 0)} packaged"},
        {"name": "DISTRIBUTOR", "status": "online" if agents.get("DISTRIBUTED", 0) > 0 else "idle", "task": f"{agents.get('DISTRIBUTED', 0)} distributed"},
        {"name": "GUARDIAN", "status": "online", "task": f"{lint_issues} issues" if lint_issues else "clean"}],
        "states": agents, "lint_issues": lint_issues, "log_count": log_count, "last_log": last_log}

@app.get("/api/platforms")
def get_platforms():
    from pipeline.platform_cache import get_platform_cache
    from pipeline.composio_bridge import COMPOSIO_CAPABILITIES
    cache = get_platform_cache()
    def build():
        yt_config = COMPOSIO_CAPABILITIES.get("youtube", {})
        youtube, total_subs = [], 0
        for acc in yt_config.get("accounts", []):
            subs = acc.get("subs", 0)
            youtube.append({"name": acc.get("channel", acc.get("alias", "")), "handle": acc.get("alias", ""),
                "subs": subs, "videos": acc.get("videos", 0), "views": acc.get("views", 0),
                "url": acc.get("url", ""), "channel_id": acc.get("channel_id", "")})
            total_subs += subs
        sp = [{"name": a.get("alias", a["id"]), "id": a["id"]} for a in COMPOSIO_CAPABILITIES.get("spotify", {}).get("accounts", [])]
        return {"youtube": youtube, "spotify": sp, "total_subs": total_subs,
                "total_yt_channels": len(youtube), "updated": datetime.now(tz=timezone.utc).isoformat()}
    return cache.get_or_set("platforms", build)

@app.get("/api/composio")
def get_composio():
    try:
        from pipeline.composio_bridge import COMPOSIO_CAPABILITIES, AGENT_COMPOSIO_MAP
        apps = {}
        for name, cfg in COMPOSIO_CAPABILITIES.items():
            apps[name] = {"accounts": len(cfg["accounts"]), "read_tools": len(cfg["tools"].get("read", [])),
                         "write_tools": len(cfg["tools"].get("write", [])), "actions": list(cfg["agent_actions"].keys())}
        return {"apps": apps, "agents": {n: list(c.keys()) for n, c in AGENT_COMPOSIO_MAP.items()},
                "total_accounts": sum(len(c["accounts"]) for c in COMPOSIO_CAPABILITIES.values()),
                "total_tools": sum(len(c["tools"].get("read",[]))+len(c["tools"].get("write",[])) for c in COMPOSIO_CAPABILITIES.values())}
    except Exception as e: return {"error": str(e)}

@app.get("/api/mapping")
def get_mapping():
    mf = VAULT / "analytics" / "artist_mapping.json"
    if mf.exists(): return json.loads(mf.read_text())
    from pipeline.composio_bridge import COMPOSIO_CAPABILITIES
    artists_map = {}
    for d in sorted(ARTISTS.iterdir()):
        if d.is_dir() and not d.name.startswith("_"):
            artists_map[d.name] = {"name": d.name.replace("-", " ").title()}
    for acc in COMPOSIO_CAPABILITIES.get("youtube", {}).get("accounts", []):
        ch = acc.get("channel", "").lower()
        for slug in artists_map:
            if slug.replace("-", " ")[:6] in ch or ch[:6] in slug.replace("-", " "):
                artists_map[slug]["youtube_channel_id"] = acc.get("channel_id", "")
    return {"artists": artists_map}

@app.get("/api/composio-status")
def get_composio_status():
    sf = VAULT / "analytics" / "composio_status.json"
    if sf.exists():
        d = json.loads(sf.read_text())
        return {"status": d.get("composio_mcp", {}).get("status", "unknown"),
                "tools": d.get("composio_mcp", {}).get("tools_discovered", 0),
                "updated": d.get("generated_at", "")}
    return {"status": "not connected", "tools": 0}

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>DORE/OS :: CONTROL CENTER</title>
<style>
@font-face{font-family:'JetBrains Mono';src:local('JetBrains Mono'),local('Menlo'),local('Consolas'),local('monospace')}
:root{--bg:#050510;--panel:#0a0a1a;--border:#151530;--text:#a8a8c0;--dim:#4a4a60;--amber:#e89820;--amber-glow:#e8982033;--green:#2ecc71;--red:#e74c3c;--blue:#5b9bd5;--cyan:#1abc9c;--purple:#8e7cc3;--font:'JetBrains Mono','Menlo','Consolas',monospace;--radius:8px}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:var(--font);font-size:11px;line-height:1.5;min-height:100vh}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 50% 0%,rgba(142,124,195,0.04) 0%,transparent 60%),radial-gradient(ellipse at 80% 100%,rgba(232,152,32,0.03) 0%,transparent 50%);pointer-events:none;z-index:0}
.container{max-width:1440px;margin:0 auto;padding:20px;position:relative;z-index:1}
.header{display:flex;justify-content:space-between;align-items:flex-end;padding-bottom:14px;margin-bottom:16px;border-bottom:1px solid var(--border)}
.header h1{font-size:18px;font-weight:400;letter-spacing:4px;color:var(--amber)}
.status-line{font-size:9px;color:var(--dim);text-align:right}
.status-line .live{color:var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}
.stats-bar{display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin-bottom:16px}
.stat-box{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:12px 10px;text-align:center}
.stat-box .val{font-size:24px;font-weight:300;color:var(--amber)}
.stat-box .lbl{font-size:7px;text-transform:uppercase;letter-spacing:2px;color:var(--dim);margin-top:3px}
.section-title{font-size:9px;text-transform:uppercase;letter-spacing:3px;color:var(--dim);margin:16px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--border)}
.artists-table{width:100%;border-collapse:collapse;margin-bottom:16px}
.artists-table th{font-size:8px;text-transform:uppercase;letter-spacing:2px;color:var(--dim);text-align:left;padding:8px 10px;border-bottom:1px solid var(--border)}
.artists-table td{padding:7px 10px;font-size:9px;border-bottom:1px solid rgba(255,255,255,0.02)}
.artists-table tr:hover{background:rgba(255,255,255,0.01)}
.platform-badge{display:inline-block;font-size:7px;padding:1px 5px;border-radius:3px;margin:0 1px;letter-spacing:1px}
.badge-spotify{background:rgba(46,204,113,0.1);color:var(--green);border:1px solid rgba(46,204,113,0.2)}
.badge-apple{background:rgba(232,152,32,0.1);color:var(--amber);border:1px solid rgba(232,152,32,0.2)}
.badge-youtube{background:rgba(231,76,60,0.1);color:var(--red);border:1px solid rgba(231,76,60,0.2)}
.badge-amazon{background:rgba(91,155,213,0.1);color:var(--blue);border:1px solid rgba(91,155,213,0.2)}
.mapping-table{width:100%;border-collapse:collapse;margin-bottom:16px}
.mapping-table th{font-size:8px;text-transform:uppercase;letter-spacing:2px;color:var(--dim);text-align:left;padding:8px 10px;border-bottom:1px solid var(--border)}
.mapping-table td{padding:7px 10px;font-size:9px;border-bottom:1px solid rgba(255,255,255,0.02)}
.mapping-dot{display:inline-block;width:5px;height:5px;border-radius:50%;margin-right:4px}
.mapping-dot.green{background:var(--green);box-shadow:0 0 4px var(--green)}
.mapping-dot.dim{background:var(--dim)}
.mapping-id{font-size:8px}
.mapping-id.available{color:var(--green)}
.yt-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:16px}
.yt-card{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:12px}
.yt-card h4{font-size:9px;color:var(--text);margin-bottom:6px}
.yt-stat{display:flex;justify-content:space-between;font-size:8px;padding:2px 0}
.yt-stat .k{color:var(--dim)}.yt-stat .v{color:var(--amber)}
.bottom-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:16px}
.agent-row{display:flex;justify-content:space-between;align-items:center;background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:10px 14px;margin-bottom:4px}
.agent-row .dot{width:6px;height:6px;border-radius:50%;margin-right:8px}
.agent-row .dot.online{background:var(--green);box-shadow:0 0 6px var(--green)}
.agent-row .dot.idle{background:var(--dim)}
.agent-row .aname{font-size:9px;letter-spacing:2px;text-transform:uppercase}
.agent-row .atask{font-size:7px;color:var(--dim)}
.cron-card{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:12px;margin-bottom:4px}
.cron-name{font-size:8px;letter-spacing:1px;color:var(--text)}
.cron-sched{font-size:7px;color:var(--dim)}
.cron-status{font-size:7px;padding:1px 5px;border-radius:3px}
.cron-active{background:rgba(46,204,113,0.1);color:var(--green)}
.activity-log{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:12px;margin-bottom:16px}
.log-entry{font-size:8px;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.01);display:flex;gap:8px}
.log-ts{color:var(--dim);min-width:55px}
.log-msg{color:var(--text)}
.footer{text-align:right;font-size:7px;color:var(--dim);border-top:1px solid var(--border);padding-top:10px;margin-top:16px}
.composio-badge{display:inline-block;font-size:7px;padding:1px 6px;border-radius:3px;margin-left:6px}
.composio-ok{background:rgba(46,204,113,0.1);color:var(--green);border:1px solid rgba(46,204,113,0.2)}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <h1>DORE<span style="color:var(--dim)">/</span>OS <span style="font-size:8px;letter-spacing:2px;color:var(--dim);display:block">AI MUSIC LABEL CONTROL CENTER</span></h1>
  <div class="status-line"><span class="live">●</span> ONLINE &nbsp;|&nbsp; <span id="clock"></span>&nbsp;<span id="composio-badge"></span></div>
</div>
<div class="stats-bar" id="stats-bar"></div>
<div class="section-title">▸ ARTISTS (12)</div>
<table class="artists-table"><thead><tr><th>#</th><th>Artist</th><th>Platforms</th><th>Releases</th><th>YT</th><th>SP</th></tr></thead><tbody></tbody></table>
<div class="section-title">▸ YOUTUBE CHANNELS (7)</div>
<div class="yt-grid" id="yt-grid"></div>
<div class="section-title">▸ CROSS-PLATFORM MAPPING</div>
<table class="mapping-table"><thead><tr><th>Artist</th><th>Spotify ID</th><th>Apple Music ID</th><th>YouTube Channel ID</th></tr></thead><tbody></tbody></table>
<div class="section-title">▸ SYSTEM</div>
<div class="bottom-grid">
  <div>
    <div style="font-size:8px;color:var(--dim);margin-bottom:6px;letter-spacing:2px">AGENTS</div><div id="agents-panel"></div>
    <div style="font-size:8px;color:var(--dim);margin:10px 0 6px;letter-spacing:2px">CRON JOBS</div><div id="cron-panel"></div>
  </div>
  <div>
    <div style="font-size:8px;color:var(--dim);margin-bottom:6px;letter-spacing:2px">ACTIVITY LOG</div><div class="activity-log" id="activity-log"></div>
  </div>
</div>
<div class="footer">DORE/OS v2.0 · 12 ARTISTS · 7 YT CHANNELS · 7 CRON JOBS · <span id="clock2"></span></div>
</div>
<script>
const AGENT_ICONS={CURATOR:'🎨',PACKAGER:'📦',DISTRIBUTOR:'🚀',GUARDIAN:'🛡️'};
async function load(){
  try{
    const[A,P,S,M,CS]=await Promise.all([
      fetch('/api/artists').then(r=>r.json()),
      fetch('/api/platforms').then(r=>r.json()),
      fetch('/api/status').then(r=>r.json()),
      fetch('/api/mapping').then(r=>r.json()),
      fetch('/api/composio-status').then(r=>r.json())
    ]);
    // Composio badge
    document.getElementById('composio-badge').innerHTML=CS.status==='connected'?`<span class="composio-badge composio-ok">COMPOSIO ✓ ${CS.tools} tools</span>`:'';
    // Stats
    document.getElementById('stats-bar').innerHTML=`
      <div class="stat-box"><div class="val">${A.length}</div><div class="lbl">Artists</div></div>
      <div class="stat-box"><div class="val">${P.total_yt_channels||7}</div><div class="lbl">YT Channels</div></div>
      <div class="stat-box"><div class="val">${CS.tools||0}</div><div class="lbl">Composio Tools</div></div>
      <div class="stat-box"><div class="val">${S.lint_issues||0}</div><div class="lbl">Issues</div></div>
      <div class="stat-box"><div class="val">${S.log_count||0}</div><div class="lbl">Logs</div></div>
      <div class="stat-box"><div class="val">${CS.status==='connected'?'✓':'—'}</div><div class="lbl">Composio</div></div>`;
    // Artists table
    let rows=''; A.forEach((a,i)=>{
      let plats=[];
      if(a.platform==='spotify') plats.push('SP');
      if(a.platform==='apple_music') plats.push('AM');
      let ma=(M.artists||{})[a.slug]||{};
      if(ma.youtube_channel_id) plats.push('YT');
      let yt=P.youtube.find(y=>y.name&&y.name.toLowerCase().includes(a.slug.replace(/-/g,' ').substring(0,6)));
      rows+=`<tr><td>${String(i+1).padStart(2,'0')}</td><td><b>${a.name}</b></td>
        <td>${plats.map(p=>`<span class="platform-badge badge-${p==='SP'?'spotify':p==='AM'?'apple':'youtube'}">${p}</span>`).join(' ')}</td>
        <td>${a.total||'—'}</td><td>${yt?yt.subs:'—'}</td><td>${a.spotify_streams||'—'}</td></tr>`;
    });
    document.querySelector('#artists-table tbody').innerHTML=rows;
    // YouTube
    document.getElementById('yt-grid').innerHTML=P.youtube.map(c=>`<div class="yt-card"><h4>${c.name}</h4>
      <div class="yt-stat"><span class="k">Subs</span><span class="v">${c.subs||'—'}</span></div>
      <div class="yt-stat"><span class="k">Views</span><span class="v">${c.views||'—'}</span></div>
      ${c.channel_id?`<div class="yt-stat" style="font-size:6px"><span class="k">ID</span><span class="v">${c.channel_id.substring(0,14)}...</span></div>`:''}
    </div>`).join('');
    // Mapping
    let artistsList = M.artists || {};
    let mHTML='';
    A.forEach(a=>{
      let m=artistsList[a.slug]||{};
      let sp=m.spotify_id||m.spotify_url||'—', am=m.apple_music_id||m.apple_music_url||'—', yt=m.youtube_channel_id||'—';
      mHTML+=`<tr><td><b>${a.name}</b></td>
        <td>${sp!=='—'?'<span class="mapping-dot green"></span><span class="mapping-id available">'+sp.toString().substring(0,40)+'</span>':'<span class="mapping-dot dim"></span>—'}</td>
        <td>${am!=='—'?'<span class="mapping-dot green"></span><span class="mapping-id available">'+am.toString().substring(0,40)+'</span>':'<span class="mapping-dot dim"></span>—'}</td>
        <td>${yt!=='—'?'<span class="mapping-dot green"></span><span class="mapping-id available">'+yt.toString().substring(0,40)+'</span>':'<span class="mapping-dot dim"></span>—'}</td></tr>`;
    });
    document.querySelector('.mapping-table tbody').innerHTML=mHTML;
    // Agents
    document.getElementById('agents-panel').innerHTML=(S.agents||[]).map(a=>
      `<div class="agent-row"><div style="display:flex;align-items:center"><span class="dot ${a.status}"></span><span class="aname">${AGENT_ICONS[a.name]||''} ${a.name}</span></div><span class="atask">${a.task||'...'}</span></div>`).join('');
    // Cron (7 jobs, all active)
    document.getElementById('cron-panel').innerHTML=`
      <div class="cron-card"><span class="cron-name">🛡️ Guardian Devriye</span><span class="cron-status cron-active">every 30m</span><br><span class="cron-sched">Lint + ISRC + stale check</span></div>
      <div class="cron-card"><span class="cron-name">📊 Platform İzleme</span><span class="cron-status cron-active">every 1h</span><br><span class="cron-sched">Composio health + stats</span></div>
      <div class="cron-card"><span class="cron-name">📺 YouTube İzleme</span><span class="cron-status cron-active">every 6h</span><br><span class="cron-sched">Kanal istatistikleri</span></div>
      <div class="cron-card"><span class="cron-name">🎵 Spotify İzleme</span><span class="cron-status cron-active">every 2h</span><br><span class="cron-sched">Artist stats + new releases</span></div>
      <div class="cron-card"><span class="cron-name">🍎 Apple Music İzleme</span><span class="cron-status cron-active">every 3h</span><br><span class="cron-sched">Artist stats + trends</span></div>
      <div class="cron-card"><span class="cron-name">📋 Günlük Özet Raporu</span><span class="cron-status cron-active">daily 09:00</span><br><span class="cron-sched">Tüm platform özeti</span></div>
      <div class="cron-card"><span class="cron-name">📈 Haftalık Analytics</span><span class="cron-status cron-active">weekly Mon 10:00</span><br><span class="cron-sched">Detaylı haftalık rapor</span></div>`;
    // Activity
    let log='';
    if(S.last_log) log+=`<div class="log-entry"><span class="log-ts">now</span><span class="log-msg">${S.last_log}</span></div>`;
    A.forEach(a=>a.releases.forEach(r=>{log+=`<div class="log-entry"><span class="log-ts">${r.state}</span><span class="log-msg">${a.name} · ${r.title||r.slug} · ${r.genre||''}</span></div>`}));
    document.getElementById('activity-log').innerHTML=log||'<div class="log-entry"><span class="log-ts">--</span><span class="log-msg">No activity</span></div>';
    let t=new Date().toLocaleTimeString('tr-TR',{hour12:false});
    document.getElementById('clock').textContent=t;document.getElementById('clock2').textContent=t;
  }catch(e){console.error(e)}
}
load();setInterval(load,10000);
</script></body></html>"""

@app.get("/", response_class=HTMLResponse)
def dashboard(): return HTMLResponse(DASHBOARD_HTML)

def main():
    print("Dore OS Dashboard → http://localhost:8700")
    uvicorn.run(app, host="0.0.0.0", port=8700, log_level="warning")

if __name__ == "__main__": main()
