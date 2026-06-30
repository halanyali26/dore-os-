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


# ─── Dashboard HTML ────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dore OS v2.0 — Dashboard</title>
<style>
:root {
  --bg: #0a0a0f; --card: #12121a; --border: #1e1e2e;
  --text: #cdd6f4; --muted: #6c7086; --accent: #7c3aed;
  --green: #10b981; --yellow: #f59e0b; --red: #ef4444; --blue: #3b82f6;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,sans-serif; padding:24px; }
h1 { font-size:28px; margin-bottom:4px; }
h1 span { color:var(--accent); }
.subtitle { color:var(--muted); margin-bottom:24px; font-size:14px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:16px; }
.card { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:16px; }
.card h3 { font-size:16px; margin-bottom:12px; display:flex; justify-content:space-between; }
.card h3 .count { color:var(--muted); font-weight:400; }
.release { display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--border); }
.release:last-child { border-bottom:0; }
.release .title { font-size:14px; font-weight:500; }
.release .meta { font-size:11px; color:var(--muted); }
.state-badge { font-size:10px; padding:2px 8px; border-radius:10px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; }
.state-IDEA { background:#1e1b4b; color:#818cf8; }
.state-PRODUCTION { background:#172554; color:#60a5fa; }
.state-MASTERED { background:#1a2e05; color:#a3e635; }
.state-PACKAGED { background:#2e1065; color:#c084fc; }
.state-DISTRIBUTED { background:#1e3a5f; color:#38bdf8; }
.state-LIVE { background:#064e3b; color:#34d399; }
.state-MONETIZED { background:#4a1d96; color:#fbbf24; }
.quick-stats { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:24px; }
.stat { background:var(--card); border:1px solid var(--border); border-radius:10px; padding:14px; text-align:center; }
.stat .value { font-size:28px; font-weight:700; color:var(--accent); }
.stat .label { font-size:11px; color:var(--muted); margin-top:4px; text-transform:uppercase; }
.alert-box { margin-top:16px; background:var(--card); border:1px solid var(--border); border-radius:12px; padding:16px; max-height:200px; overflow-y:auto; }
.alert-box h4 { margin-bottom:8px; font-size:14px; }
.alert-box pre { font-size:12px; color:var(--muted); white-space:pre-wrap; font-family:inherit; }
.refresh { color:var(--muted); font-size:11px; text-align:right; margin-top:16px; }
.isrc { font-family:monospace; font-size:10px; color:var(--muted); }
</style>
</head>
<body>
<h1>Dore <span>OS</span> v2.0</h1>
<p class="subtitle">AI Music Label Pipeline — Brain Dashboard</p>

<div class="quick-stats" id="stats"></div>

<div class="grid" id="artists"></div>

<div class="alert-box" id="alerts">
  <h4>🔍 Guardian Alerts</h4>
  <pre id="alert-content">Loading...</pre>
</div>

<p class="refresh">Auto-refresh every 10s · <span id="clock"></span></p>

<script>
const S = {
  IDEA:'#818cf8', PRODUCTION:'#60a5fa', MASTERED:'#a3e635',
  PACKAGED:'#c084fc', DISTRIBUTED:'#38bdf8', LIVE:'#34d399', MONETIZED:'#fbbf24'
};

async function load() {
  try {
    const [artists, alerts, log] = await Promise.all([
      fetch('/api/artists').then(r=>r.json()),
      fetch('/api/lint').then(r=>r.json()),
      fetch('/api/log?limit=5').then(r=>r.json())
    ]);

    let totalReleases = 0, stateCount = {};
    artists.forEach(a => {
      totalReleases += a.total;
      a.releases.forEach(r => {
        stateCount[r.state] = (stateCount[r.state]||0) + 1;
      });
    });

    document.getElementById('stats').innerHTML = `
      <div class="stat"><div class="value">${artists.length}</div><div class="label">Artists</div></div>
      <div class="stat"><div class="value">${totalReleases}</div><div class="label">Releases</div></div>
      <div class="stat"><div class="value">${stateCount.PACKAGED||0}</div><div class="label">Packaged</div></div>
      <div class="stat"><div class="value">${stateCount.LIVE||0}</div><div class="label">Live</div></div>
    `;

    let html = '';
    artists.forEach(a => {
      html += `<div class="card">
        <h3>${a.name} <span class="count">${a.total} release</span></h3>`;
      if (a.releases.length === 0) {
        html += '<p style="color:var(--muted);font-size:13px;">No releases yet</p>';
      }
      a.releases.forEach(r => {
        html += `<div class="release">
          <div>
            <div class="title">${r.title || r.slug}</div>
            <div class="meta">${r.genre||''} ${r.isrc ? '· <span class=isrc>'+r.isrc+'</span>' : ''}</div>
          </div>
          <span class="state-badge state-${r.state}">${r.state}</span>
        </div>`;
      });
      html += '</div>';
    });
    document.getElementById('artists').innerHTML = html;

    document.getElementById('alert-content').textContent = alerts.content || 'No alerts';
    document.getElementById('clock').textContent = new Date().toLocaleTimeString('tr-TR');
  } catch(e) {
    console.error(e);
  }
}

load();
setInterval(load, 10000);
</script>
</body>
</html>
""")


def main():
    print("Dore OS Dashboard → http://localhost:8700")
    uvicorn.run(app, host="0.0.0.0", port=8700, log_level="warning")


if __name__ == "__main__":
    main()
