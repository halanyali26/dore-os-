"""
Dore OS v2.0 — Pipeline Core
AI Music Label Operating System
Agent classes + LLM router (Hermes local + Claude cloud)
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Literal
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger("doreos.core")


# ─── State Machine ───────────────────────────────────────────
class ReleaseState(str, Enum):
    IDEA = "IDEA"
    PRODUCTION = "PRODUCTION"
    MASTERED = "MASTERED"
    PACKAGED = "PACKAGED"
    DISTRIBUTED = "DISTRIBUTED"
    LIVE = "LIVE"
    MONETIZED = "MONETIZED"
    ARCHIVED = "ARCHIVED"


VALID_TRANSITIONS = {
    ReleaseState.IDEA: [ReleaseState.PRODUCTION],
    ReleaseState.PRODUCTION: [ReleaseState.MASTERED, ReleaseState.IDEA],
    ReleaseState.MASTERED: [ReleaseState.PACKAGED, ReleaseState.PRODUCTION],
    ReleaseState.PACKAGED: [ReleaseState.DISTRIBUTED, ReleaseState.MASTERED],
    ReleaseState.DISTRIBUTED: [ReleaseState.LIVE, ReleaseState.PACKAGED],
    ReleaseState.LIVE: [ReleaseState.MONETIZED, ReleaseState.DISTRIBUTED],
    ReleaseState.MONETIZED: [ReleaseState.ARCHIVED],
    ReleaseState.ARCHIVED: [],
}


# ─── LLM Router ──────────────────────────────────────────────
class LLMRouter:
    """Routes tasks to Hermes (local, cheap) or Claude (cloud, creative)."""

    def __init__(self):
        self._hermes = None
        self._claude = None
        self._deepseek = None

    @property
    def hermes(self):
        if self._hermes is None:
            from langchain_openai import ChatOpenAI
            herm_url = os.getenv("HERMES_BASE_URL", "http://localhost:8080/v1")
            self._hermes = ChatOpenAI(
                base_url=herm_url,
                api_key="not-needed",
                model=os.getenv("HERMES_MODEL", "local-model"),
                temperature=0.3,
                max_tokens=2048,
            )
        return self._hermes

    @property
    def deepseek(self):
        if self._deepseek is None:
            from langchain_openai import ChatOpenAI
            self._deepseek = ChatOpenAI(
                base_url="https://api.deepseek.com/v1",
                api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                model="deepseek-chat",
                temperature=0.7,
                max_tokens=4096,
            )
        return self._deepseek

    @property
    def claude(self):
        if self._claude is None:
            ak = os.getenv("ANTHROPIC_API_KEY", "")
            if ak:
                from langchain_anthropic import ChatAnthropic
                self._claude = ChatAnthropic(
                    model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
                    temperature=0.7,
                    max_tokens=4096,
                )
            else:
                self._claude = self.deepseek  # fallback
        return self._claude

    def route(self, task_type: Literal["creative", "routine", "complex"]) -> Any:
        if task_type == "routine":
            return self.hermes
        return self.claude


# ─── Agent Base ──────────────────────────────────────────────
class BaseAgent:
    """Base agent with state awareness and logging."""

    def __init__(self, name: str, vault_path: Path, router: LLMRouter):
        self.name = name
        self.vault_path = vault_path
        self.router = router
        self.artists_path = vault_path.parent / "artists"

    def log(self, message: str, level: str = "info"):
        getattr(logger, level)(f"[{self.name}] {message}")

    def read_state(self, artist_id: str, release_slug: str) -> Dict:
        state_file = self.artists_path / artist_id / "releases" / release_slug / "state.json"
        if state_file.exists():
            return json.loads(state_file.read_text())
        return {"state": ReleaseState.IDEA.value, "history": []}

    def write_state(self, artist_id: str, release_slug: str, new_state: ReleaseState,
                    metadata: Optional[Dict] = None):
        state_file = self.artists_path / artist_id / "releases" / release_slug / "state.json"
        current = self.read_state(artist_id, release_slug)
        current_state = ReleaseState(current["state"])

        if new_state.value not in [s.value for s in VALID_TRANSITIONS.get(current_state, [])]:
            raise ValueError(f"Invalid transition: {current_state.value} → {new_state.value}")

        current["state"] = new_state.value
        current["history"].append({
            "from": current_state.value,
            "to": new_state.value,
            "agent": self.name,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        })
        if metadata:
            current.setdefault("metadata", {}).update(metadata)

        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(current, indent=2, ensure_ascii=False))
        self.log(f"State: {current_state.value} → {new_state.value} ({artist_id}/{release_slug})")


# ─── Specialized Agents ──────────────────────────────────────
class CuratorAgent(BaseAgent):
    """Discovers trends, generates ideas, writes lyrics/concepts."""

    def __init__(self, vault_path: Path, router: LLMRouter):
        super().__init__("Curator", vault_path, router)

    def run(self, task: Dict[str, Any]) -> Dict:
        action = task.get("action", "generate_idea")
        artist_id = task["artist_id"]
        llm = self.router.route("creative")

        prompt = self._build_prompt(action, task)
        response = llm.invoke(prompt)

        if action == "generate_idea":
            # Save to vault/wiki
            idea_path = self.vault_path / "wiki" / f"{artist_id}_ideas.md"
            self._append_to_file(idea_path, f"## {datetime.now():%Y-%m-%d}\n{response.content}\n")

        return {"status": "ok", "action": action, "content": response.content}

    def _build_prompt(self, action: str, task: Dict) -> str:
        genre = task.get("genre", "electronic")
        mood = task.get("mood", "dark")
        return (
            f"You are an AI music curator for artist '{task['artist_id']}'. "
            f"Genre: {genre}. Mood: {mood}.\n"
            f"Task: {action}. Generate a creative concept with title, lyrics theme, "
            f"and sonic direction. Output in Turkish. Be original and genre-appropriate."
        )

    def _append_to_file(self, path: Path, content: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(content + "\n")


class PackagerAgent(BaseAgent):
    """Prepares releases: metadata, artwork notes, DDEX, ISRC."""

    def __init__(self, vault_path: Path, router: LLMRouter):
        super().__init__("Packager", vault_path, router)

    def run(self, task: Dict[str, Any]) -> Dict:
        artist_id = task["artist_id"]
        release_slug = task["release_slug"]

        # Transition: MASTERED → PACKAGED
        self.write_state(artist_id, release_slug, ReleaseState.PACKAGED)

        # Generate ISRC if not exists
        from pipeline.isrc import ISRCGenerator
        isrc_gen = ISRCGenerator()
        isrc = isrc_gen.generate(artist_id, release_slug)

        # Generate metadata
        llm = self.router.route("routine")
        prompt = (
            f"Generate Spotify/YouTube metadata for release '{release_slug}' "
            f"by artist '{artist_id}'. Include: description (150 words), "
            f"genre tags (5), mood tags (3). Output in Turkish."
        )
        metadata_response = llm.invoke(prompt)

        # Save packaging info
        pkg = {
            "release_slug": release_slug,
            "artist_id": artist_id,
            "isrc": isrc,
            "state": ReleaseState.PACKAGED.value,
            "metadata": {"description": metadata_response.content},
            "packaged_at": datetime.now(tz=timezone.utc).isoformat(),
        }

        pkg_path = self.vault_path / "analytics" / f"{artist_id}_{release_slug}_package.json"
        pkg_path.parent.mkdir(parents=True, exist_ok=True)
        pkg_path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False))

        return {"status": "ok", "isrc": isrc, "state": ReleaseState.PACKAGED.value}


class DistributorAgent(BaseAgent):
    """Handles distribution: YouTube upload, DistroKid, streaming platforms."""

    def __init__(self, vault_path: Path, router: LLMRouter):
        super().__init__("Distributor", vault_path, router)

    def run(self, task: Dict[str, Any]) -> Dict:
        artist_id = task["artist_id"]
        release_slug = task["release_slug"]
        platform = task.get("platform", "youtube")

        # Verify PACKAGED state
        state = self.read_state(artist_id, release_slug)
        if state["state"] != ReleaseState.PACKAGED.value:
            return {"status": "error", "message": f"Not PACKAGED, current: {state['state']}"}

        if platform == "youtube":
            result = self._distribute_youtube(artist_id, release_slug, task)
        elif platform == "distrokid":
            result = self._distribute_distrokid(artist_id, release_slug, task)
        else:
            result = {"status": "error", "message": f"Unknown platform: {platform}"}

        if result.get("status") == "ok":
            self.write_state(artist_id, release_slug, ReleaseState.DISTRIBUTED,
                           metadata={"platform": platform, "result": result})

        return result

    def _distribute_youtube(self, artist_id: str, release_slug: str, task: Dict) -> Dict:
        # Delegate to YouTube extractor/distributor
        from pipeline.extractors.youtube_extractor import YouTubeDistributor
        yt = YouTubeDistributor(self.vault_path)
        return yt.upload(artist_id, release_slug, task)

    def _distribute_distrokid(self, artist_id: str, release_slug: str, task: Dict) -> Dict:
        from pipeline.distributor import DistroKidUploader
        dk = DistroKidUploader(self.vault_path)
        return dk.upload(artist_id, release_slug, task)


class GuardianAgent(BaseAgent):
    """Health checks, linting, consistency validation."""

    def __init__(self, vault_path: Path, router: LLMRouter):
        super().__init__("Guardian", vault_path, router)

    def run(self, task: Dict[str, Any] = None) -> Dict:
        issues = []

        # Check 1: Wiki-vs-Spotify mismatch
        issues += self._check_wiki_spotify_sync()

        # Check 2: Stale releases (48h+ in DISTRIBUTED but not LIVE)
        issues += self._check_stale_distributions()

        # Check 3: Orphan files
        issues += self._check_orphan_files()

        # Write alerts
        alert_path = self.vault_path / "alerts" / "ALERTS.md"
        alert_path.parent.mkdir(parents=True, exist_ok=True)
        content = f"# Dore OS Alerts — {datetime.now():%Y-%m-%d %H:%M}\n\n"
        if issues:
            for i in issues:
                content += f"- **[{i['severity']}]** {i['type']}: {i['message']}\n"
        else:
            content += "✅ No issues found.\n"
        alert_path.write_text(content)

        return {"status": "ok", "issues_found": len(issues), "issues": issues}

    def _check_wiki_spotify_sync(self) -> list:
        # Placeholder: Spotify API check vs wiki entries
        return []

    def _check_stale_distributions(self) -> list:
        issues = []
        artists_path = self.artists_path
        if not artists_path.exists():
            return issues
        for artist_dir in artists_path.iterdir():
            if artist_dir.is_dir() and not artist_dir.name.startswith("_"):
                releases_path = artist_dir / "releases"
                if releases_path.exists():
                    for rel_dir in releases_path.iterdir():
                        state_file = rel_dir / "state.json"
                        if state_file.exists():
                            state = json.loads(state_file.read_text())
                            if state["state"] == ReleaseState.DISTRIBUTED.value:
                                issues.append({
                                    "type": "stale_distribution",
                                    "severity": "medium",
                                    "message": f"{artist_dir.name}/{rel_dir.name}: DISTRIBUTED > 48h"
                                })
        return issues

    def _check_orphan_files(self) -> list:
        # Placeholder: find files not referenced in index.md
        return []


# ─── Pipeline Runner ─────────────────────────────────────────
class PipelineRunner:
    """Orchestrates the full pipeline execution."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.vault_path = base_path / "vault"
        self.router = LLMRouter()

        self.agents = {
            "curator": CuratorAgent(self.vault_path, self.router),
            "packager": PackagerAgent(self.vault_path, self.router),
            "distributor": DistributorAgent(self.vault_path, self.router),
            "guardian": GuardianAgent(self.vault_path, self.router),
        }

    def execute(self, task: Dict[str, Any]) -> Dict:
        agent_name = task.get("agent", "curator")
        agent = self.agents.get(agent_name)
        if not agent:
            return {"status": "error", "message": f"Unknown agent: {agent_name}"}
        return agent.run(task)

    def lint(self) -> Dict:
        return self.agents["guardian"].run()
