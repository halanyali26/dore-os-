"""
Dore OS v2.0 — AI Music Label Operating System
================================================
Pipeline modules for the autonomous music label.

Modules:
    core        — Pipeline core: agents, state machine, LLM router
    state_machine — Finite state machine for release lifecycle
    vault_manager — Obsidian vault integration: wiki, state, analytics
    isrc        — ISRC (ISO 3901) and UPC-A code generation
    linter      — Guardian health checks: Spotify sync, orphans, ISRC
    ddex        — DDEX ERN 4.3 XML generation for enterprise distribution
    musicbrainz — MusicBrainz API: artist/recording MBID lookup
    ffmpeg_pipeline — Audio processing: normalize, convert, master-prep
    observability — LangFuse tracing for LLM calls and agent actions
    distributor — DistroKid upload automation via Playwright
    composio_bridge — Composio MCP capability registry and agent mapping
    extractors  — YouTube & Spotify data extraction
"""

__version__ = "2.0.0"

from pipeline.core import (
    PipelineRunner,
    BaseAgent,
    CuratorAgent,
    PackagerAgent,
    DistributorAgent,
    GuardianAgent,
    LLMRouter,
    ReleaseState,
    VALID_TRANSITIONS,
)

from pipeline.state_machine import StateMachine, State, Transition
from pipeline.vault_manager import VaultManager
from pipeline.isrc import ISRCGenerator, UPCGenerator
from pipeline.linter import GuardianLinter
from pipeline.ddex import DDEXGenerator
from pipeline.musicbrainz import MusicBrainzClient
from pipeline.ffmpeg_pipeline import FFmpegPipeline
from pipeline.observability import Observability, get_observability
from pipeline.composio_bridge import (
    COMPOSIO_CAPABILITIES,
    AGENT_COMPOSIO_MAP,
    get_agent_capabilities,
    get_all_capabilities_summary,
)
from pipeline.platform_cache import (
    TTLCache,
    platform_cache,
    composio_cache,
    short_cache,
    get_platform_cache,
    get_composio_cache,
)

__all__ = [
    "PipelineRunner",
    "BaseAgent",
    "CuratorAgent",
    "PackagerAgent",
    "DistributorAgent",
    "GuardianAgent",
    "LLMRouter",
    "ReleaseState",
    "VALID_TRANSITIONS",
    "StateMachine",
    "State",
    "Transition",
    "VaultManager",
    "ISRCGenerator",
    "UPCGenerator",
    "GuardianLinter",
    "DDEXGenerator",
    "MusicBrainzClient",
    "FFmpegPipeline",
    "Observability",
    "get_observability",
    "COMPOSIO_CAPABILITIES",
    "AGENT_COMPOSIO_MAP",
    "get_agent_capabilities",
    "get_all_capabilities_summary",
    "TTLCache",
    "platform_cache",
    "composio_cache",
    "short_cache",
    "get_platform_cache",
    "get_composio_cache",
    "__version__",
]
