"""
Dore OS v2.0 — Guardian Linter
Health checks: Spotify-wiki sync, stale distributions, orphan files, consistency.
"""
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List


class GuardianLinter:
    """Periodic health check system for Dore OS vault."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.artists_path = vault_path.parent / "artists"

    def full_check(self) -> Dict:
        """Run all lint checks and return report."""
        issues = []

        issues += self.check_wiki_spotify_sync()
        issues += self.check_stale_distributions(hours=48)
        issues += self.check_orphan_files()
        issues += self.check_missing_isrc()
        issues += self.check_cross_references()
        issues += self.check_audio_files()

        # Generate report
        report = self._generate_report(issues)

        # Write alerts
        alert_path = self.vault_path / "alerts" / "ALERTS.md"
        alert_path.parent.mkdir(parents=True, exist_ok=True)

        content = f"# Dore OS Guardian Report — {datetime.now():%Y-%m-%d %H:%M}\n\n"
        content += f"**Issues found:** {len(issues)}\n\n"

        by_severity = {"critical": [], "high": [], "medium": [], "low": []}
        for issue in issues:
            by_severity.setdefault(issue["severity"], []).append(issue)

        for sev in ["critical", "high", "medium", "low"]:
            if by_severity[sev]:
                content += f"## {sev.upper()} ({len(by_severity[sev])})\n\n"
                for issue in by_severity[sev]:
                    content += f"- [{issue['type']}] {issue['message']}\n"

        if not issues:
            content += "✅ All systems healthy.\n"

        alert_path.write_text(content)

        return report

    def check_wiki_spotify_sync(self) -> List[Dict]:
        """Find releases on Spotify not in wiki, and wiki entries not on Spotify."""
        issues = []
        index_path = self.vault_path / "index.md"
        if not index_path.exists():
            return [{"type": "wiki_spotify_sync", "severity": "medium",
                     "message": "index.md not found — wiki not initialized"}]

        # Collect wiki sources
        sources_path = self.vault_path / "sources"
        wiki_slugs = set()
        if sources_path.exists():
            for src in sources_path.glob("*.md"):
                wiki_slugs.add(src.stem)

        # Check artists against wiki
        if self.artists_path.exists():
            for artist_dir in self.artists_path.iterdir():
                if not artist_dir.is_dir() or artist_dir.name.startswith("_"):
                    continue
                releases_path = artist_dir / "releases"
                if not releases_path.exists():
                    continue
                for rel_dir in releases_path.iterdir():
                    expected_slug = f"{artist_dir.name}-{rel_dir.name}"
                    if expected_slug not in wiki_slugs:
                        issues.append({
                            "type": "missing_wiki_source",
                            "severity": "medium",
                            "message": f"{artist_dir.name}/{rel_dir.name}: no vault/sources/{expected_slug}.md"
                        })

        # Check wiki entries without artist/release
        for slug in wiki_slugs:
            if "-" in slug:
                parts = slug.split("-", 1)
                artist_name, release_name = parts[0], parts[1]
                state_path = self.artists_path / artist_name / "releases" / release_name / "state.json"
                if not state_path.exists():
                    issues.append({
                        "type": "orphan_wiki_source",
                        "severity": "low",
                        "message": f"vault/sources/{slug}.md: no matching release directory"
                    })

        return issues

    def check_stale_distributions(self, hours: int = 48) -> List[Dict]:
        """Find releases stuck in DISTRIBUTED state for too long."""
        issues = []
        if not self.artists_path.exists():
            return issues

        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)

        for artist_dir in self.artists_path.iterdir():
            if not artist_dir.is_dir() or artist_dir.name.startswith("_"):
                continue
            releases_path = artist_dir / "releases"
            if not releases_path.exists():
                continue

            for rel_dir in releases_path.iterdir():
                state_file = rel_dir / "state.json"
                if not state_file.exists():
                    issues.append({
                        "type": "missing_state",
                        "severity": "high",
                        "message": f"{artist_dir.name}/{rel_dir.name}: no state.json"
                    })
                    continue

                state = json.loads(state_file.read_text())
                if state["state"] == "DISTRIBUTED":
                    history = state.get("history", [])
                    if history:
                        last_ts = history[-1]["timestamp"]
                        last_time = datetime.fromisoformat(last_ts)
                        if last_time < cutoff:
                            issues.append({
                                "type": "stale_distribution",
                                "severity": "medium",
                                "message": f"{artist_dir.name}/{rel_dir.name}: DISTRIBUTED since {last_ts} (> {hours}h)"
                            })

        return issues

    def check_orphan_files(self) -> List[Dict]:
        """Find files not referenced in index.md."""
        issues = []
        wiki_path = self.vault_path / "wiki"
        if not wiki_path.exists():
            return issues

        index_content = ""
        index_path = self.vault_path / "index.md"
        if index_path.exists():
            index_content = index_path.read_text()

        for md_file in wiki_path.rglob("*.md"):
            filename = md_file.stem
            if filename not in index_content:
                issues.append({
                    "type": "orphan_file",
                    "severity": "low",
                    "message": f"wiki/{md_file.relative_to(wiki_path)}: not referenced in index.md"
                })

        return issues

    def check_missing_isrc(self) -> List[Dict]:
        """Find releases without ISRC codes."""
        issues = []
        if not self.artists_path.exists():
            return issues

        for artist_dir in self.artists_path.iterdir():
            if not artist_dir.is_dir() or artist_dir.name.startswith("_"):
                continue
            releases_path = artist_dir / "releases"
            if not releases_path.exists():
                continue

            for rel_dir in releases_path.iterdir():
                state_file = rel_dir / "state.json"
                if not state_file.exists():
                    continue
                state = json.loads(state_file.read_text())
                if state["state"] in ["PACKAGED", "DISTRIBUTED", "LIVE", "MONETIZED"]:
                    metadata = state.get("metadata", {})
                    if "isrc" not in metadata:
                        issues.append({
                            "type": "missing_isrc",
                            "severity": "high",
                            "message": f"{artist_dir.name}/{rel_dir.name}: no ISRC in PACKAGED+ state"
                        })

        return issues

    def check_cross_references(self) -> List[Dict]:
        """Check wiki page cross-references for dead links."""
        issues = []
        wiki_path = self.vault_path
        if not wiki_path.exists():
            return issues

        # Build set of all valid wiki page paths (relative to vault)
        valid_pages = set()
        for md_file in wiki_path.rglob("*.md"):
            rel = str(md_file.relative_to(wiki_path))
            valid_pages.add(rel)
            valid_pages.add(md_file.stem)  # bare [[page]] links

        # Scan for [[links]] and check
        import re
        link_pattern = re.compile(r'\[\[([^\]]+)\]\]')
        for md_file in wiki_path.rglob("*.md"):
            try:
                content = md_file.read_text()
                for match in link_pattern.finditer(content):
                    target = match.group(1)
                    # Strip alias: [[page|alias]]
                    target = target.split("|")[0].strip()
                    if target not in valid_pages and not target.startswith("http"):
                        # Check with extension
                        if f"{target}.md" not in valid_pages:
                            issues.append({
                                "type": "dead_link",
                                "severity": "low",
                                "message": f"{md_file.relative_to(wiki_path)} → [[{target}]]: page not found"
                            })
            except Exception:
                pass

        return issues

    def check_audio_files(self) -> List[Dict]:
        """Verify audio files exist and are valid formats."""
        issues = []
        if not self.artists_path.exists():
            return issues

        valid_formats = {".wav", ".flac", ".mp3", ".m4a", ".aiff"}
        for audio_file in self.artists_path.rglob("*"):
            if audio_file.suffix.lower() in valid_formats:
                if audio_file.stat().st_size < 1024:  # < 1KB = corrupt
                    issues.append({
                        "type": "corrupt_audio",
                        "severity": "high",
                        "message": f"{audio_file.relative_to(self.artists_path)}: file too small ({audio_file.stat().st_size} bytes)"
                    })

        return issues

    def _generate_report(self, issues: List[Dict]) -> Dict:
        sev_count = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in issues:
            sev_count.setdefault(issue["severity"], 0)
            sev_count[issue["severity"]] += 1

        return {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "total_issues": len(issues),
            "by_severity": sev_count,
            "issues": issues,
        }
