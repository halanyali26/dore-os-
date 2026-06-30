"""
Dore OS v2.0 — Vault Manager
Obsidian vault integration: state.json read/write, wiki maintenance.
"""
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List


class VaultManager:
    """Manages the Obsidian vault structure and state files."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.vault_path = base_path / "vault"
        self.artists_path = base_path / "artists"

    # ─── State Management ───────────────────────────────────
    def get_state(self, artist_id: str, release_slug: str) -> Dict:
        path = self.artists_path / artist_id / "releases" / release_slug / "state.json"
        if not path.exists():
            return {"state": "IDEA", "history": [], "metadata": {}}
        return json.loads(path.read_text())

    def set_state(self, artist_id: str, release_slug: str,
                  new_state: str, agent: str, metadata: Dict = None) -> bool:
        path = self.artists_path / artist_id / "releases" / release_slug / "state.json"
        path.parent.mkdir(parents=True, exist_ok=True)

        current = self.get_state(artist_id, release_slug)
        old_state = current["state"]
        current["state"] = new_state
        current["history"].append({
            "from": old_state, "to": new_state,
            "agent": agent, "timestamp": datetime.utcnow().isoformat(),
        })
        if metadata:
            current.setdefault("metadata", {}).update(metadata)

        path.write_text(json.dumps(current, indent=2, ensure_ascii=False))
        return True

    # ─── Wiki Operations ────────────────────────────────────
    def write_wiki_page(self, category: str, slug: str, content: str,
                        frontmatter: Dict = None) -> Path:
        """Write a wiki page with YAML frontmatter."""
        path = self.vault_path / category / f"{slug}.md"
        path.parent.mkdir(parents=True, exist_ok=True)

        fm = frontmatter or {}
        fm.setdefault("title", slug.replace("-", " ").title())
        fm.setdefault("date", datetime.now().strftime("%Y-%m-%d"))
        fm.setdefault("tags", [])

        fm_str = "---\n" + "\n".join(f"{k}: {v}" for k, v in fm.items()) + "\n---\n\n"
        path.write_text(fm_str + content)
        return path

    def update_index(self, category: str, slug: str, summary: str):
        """Add entry to index.md."""
        index_path = self.vault_path / "index.md"
        index_path.parent.mkdir(parents=True, exist_ok=True)

        existing = index_path.read_text() if index_path.exists() else "# Dore OS Wiki Index\n\n"

        entry = f"- [[{category}/{slug}]] — {summary}\n"
        section = f"## {category}\n"

        if section not in existing:
            existing += f"\n{section}"
        existing += entry
        index_path.write_text(existing)

    def append_log(self, operation: str, details: str):
        """Append to log.md."""
        log_path = self.vault_path / "log.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        entry = f"## [{datetime.now():%Y-%m-%d %H:%M}] {operation} | {details}\n"
        with open(log_path, "a") as f:
            f.write(entry + "\n")

    # ─── Analytics ──────────────────────────────────────────
    def save_analytics(self, artist_id: str, data: Dict, data_type: str):
        """Save analytics data as JSON."""
        path = self.vault_path / "analytics" / f"{artist_id}_{data_type}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def load_analytics(self, artist_id: str, data_type: str) -> Dict:
        path = self.vault_path / "analytics" / f"{artist_id}_{data_type}.json"
        if path.exists():
            return json.loads(path.read_text())
        return {}

    # ─── Query & Filed-Back ─────────────────────────────────
    def search_wiki(self, query: str) -> list:
        """Search wiki pages for a query. Returns matching file paths."""
        results = []
        for md_file in self.vault_path.rglob("*.md"):
            if "raw/" in str(md_file) or "alerts/" in str(md_file):
                continue
            try:
                content = md_file.read_text()
                if query.lower() in content.lower():
                    rel = str(md_file.relative_to(self.vault_path))
                    results.append({"path": rel, "title": md_file.stem, "size": len(content)})
            except:
                pass
        return sorted(results, key=lambda x: x["size"], reverse=True)

    def file_back_query(self, question: str, answer: str, sources: list):
        """File a query answer back into syntheses/ as a new wiki page."""
        from datetime import datetime
        slug = question.lower().replace(" ", "-").replace("?", "")[:40]
        ts = datetime.now().strftime("%Y-%m-%d")
        fm = {"title": question, "tags": ["query", "synthesis"], "date": ts, "status": "complete"}
        content = f"# {question}\n\n{answer}\n\n## Sources\n"
        for s in sources:
            content += f"- [[{s}]]\n"
        path = self.write_wiki_page("syntheses", f"{ts}-{slug}", content, fm)
        self.update_index("syntheses", f"{ts}-{slug}", question[:60])
        self.append_log("query", f'Filed-back: "{question[:50]}" → syntheses/{ts}-{slug}.md')
        return path

    # ─── Alerts ─────────────────────────────────────────────
    def create_alert(self, severity: str, message: str, source: str = ""):
        alert_path = self.vault_path / "alerts" / "ALERTS.md"
        alert_path.parent.mkdir(parents=True, exist_ok=True)

        entry = f"- **[{datetime.now():%Y-%m-%d %H:%M}] [{severity.upper()}]** {message}"
        if source:
            entry += f" (source: {source})"
        entry += "\n"

        with open(alert_path, "a") as f:
            f.write(entry)

    # ─── Release Bootstrap ─────────────────────────────────
    def bootstrap_release(self, artist_id: str, release_slug: str,
                          title: str, genre: str = "electronic") -> Dict:
        """Create a new release with all necessary files."""
        base = self.artists_path / artist_id / "releases" / release_slug
        base.mkdir(parents=True, exist_ok=True)

        state = {
            "state": "IDEA",
            "title": title,
            "genre": genre,
            "created_at": datetime.utcnow().isoformat(),
            "history": [],
            "metadata": {},
        }
        (base / "state.json").write_text(json.dumps(state, indent=2))

        # Create wiki page
        self.write_wiki_page("sources", f"{artist_id}-{release_slug}",
                            f"# {title}\n\nArtist: {artist_id}\nGenre: {genre}\nStatus: IDEA\n",
                            {"title": title, "tags": [genre, artist_id, "release"]})

        self.update_index("sources", f"{artist_id}-{release_slug}", title)
        self.append_log("bootstrap", f"New release: {artist_id}/{release_slug}")

        return state
