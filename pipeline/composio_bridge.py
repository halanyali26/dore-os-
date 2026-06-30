"""
Dore OS v2.0 — Composio Bridge
Maps Composio MCP tools to Dore OS agent actions.
All connected apps and their capabilities.
"""

COMPOSIO_CAPABILITIES = {
    "youtube": {
        "accounts": [
            {"id": "youtube_cully-gelada", "alias": "DORE Studio TAM", "channel": "Hakan ALANYALI", "subs": 73},
            {"id": "youtube_amen-valyl", "alias": None, "channel": "Azultv Kids", "subs": 103},
            {"id": "youtube_filled-glummy", "alias": None, "channel": "Night History Archive", "subs": 1},
            {"id": "youtube_hexact-wide", "alias": "World Time Capsule", "channel": "World Time Capsule", "subs": 1830},
        ],
        "tools": {
            "read": ["SEARCH", "LIST_CHANNEL_VIDEOS", "GET_VIDEO_DETAILS_BATCH",
                     "GET_CHANNEL_STATISTICS", "LIST_PLAYLIST_ITEMS",
                     "LIST_CAPTION_TRACK", "LIST_COMMENT_THREADS", "LIST_COMMENTS"],
            "write": ["CREATE_PLAYLIST", "POST_COMMENT"],
        },
        "agent_actions": {
            "distributor_upload": "UPLOAD_VIDEO (pending OAuth scope)",
            "distributor_metadata": "UPDATE_VIDEO_METADATA",
            "analytics": "GET_CHANNEL_STATISTICS + GET_VIDEO_DETAILS_BATCH",
            "engagement": "LIST_COMMENT_THREADS + POST_COMMENT",
        }
    },
    "spotify": {
        "accounts": [
            {"id": "spotify_taller-frown", "alias": "TamYetki"},
            {"id": "spotify_comino-tamp", "alias": "FullAccess"},
            {"id": "spotify_puture-beech", "alias": "Dore Full"},
        ],
        "tools": {
            "read": ["SEARCH", "GET_ARTIST", "GET_TOP_TRACKS", "GET_ALBUMS",
                     "GET_PLAYLIST", "GET_CURRENT_USER_PROFILE", "GET_PLAYLISTS"],
            "write": ["CREATE_PLAYLIST", "ADD_ITEMS_TO_PLAYLIST", "CHANGE_PLAYLIST_DETAILS"],
        },
        "agent_actions": {
            "curator_discover": "SEARCH + GET_ARTIST + GET_TOP_TRACKS",
            "distributor_publish": "CREATE_PLAYLIST + ADD_ITEMS_TO_PLAYLIST",
            "analytics": "GET_ARTIST (followers, popularity) + GET_TOP_TRACKS",
        }
    },
    "gmail": {
        "accounts": [
            {"id": "gmail_resaca-clout", "alias": "halanyali", "email": "azultvkid@gmail.com"},
            {"id": "gmail_toho-fuffy", "alias": None, "email": "halanyali@gmail.com"},
        ],
        "tools": {
            "read": ["FETCH_EMAILS", "LIST_DRAFTS", "GET_DRAFT", "LIST_SEND_AS"],
            "write": ["SEND_EMAIL", "CREATE_DRAFT", "SEND_DRAFT", "UPDATE_DRAFT", "REPLY_TO_THREAD"],
        },
        "agent_actions": {
            "distributor_notify": "SEND_EMAIL (release notifications)",
        }
    },
    "googledrive": {
        "accounts": [
            {"id": "googledrive_deride-rehook", "email": "halanyali@gmail.com"},
        ],
        "tools": {
            "read": ["FIND_FILE", "GET_FILE_METADATA", "GET_ABOUT", "LIST_SHARED_DRIVES"],
            "write": ["DOWNLOAD_FILE"],
        },
        "agent_actions": {
            "packager_assets": "UPLOAD (cover art, metadata files)",
            "analytics_backup": "FIND_FILE + DOWNLOAD_FILE",
        }
    },
}

# Agent-to-Composio action mapping
AGENT_COMPOSIO_MAP = {
    "curator": {
        "discover_trends": ("spotify", "SEARCH_FOR_ITEM + GET_ARTIST_TOP_TRACKS"),
        "generate_idea": "llm",  # Uses DeepSeek LLM
    },
    "packager": {
        "generate_metadata": "llm",
        "generate_isrc": "isrc",  # Local ISRC generator
        "store_assets": ("googledrive", "UPLOAD"),
    },
    "distributor": {
        "youtube_upload": ("youtube", "pending OAuth upload scope"),
        "youtube_metadata": ("youtube", "UPDATE_VIDEO"),
        "spotify_playlist": ("spotify", "CREATE_PLAYLIST + ADD_ITEMS"),
        "notify_email": ("gmail", "SEND_EMAIL"),
    },
    "guardian": {
        "check_youtube": ("youtube", "GET_CHANNEL_STATISTICS"),
        "check_spotify": ("spotify", "GET_ARTIST"),
        "lint_vault": "local",  # Local file checks
    },
}


def get_agent_capabilities(agent_name: str) -> dict:
    """Get available Composio actions for a specific agent."""
    return AGENT_COMPOSIO_MAP.get(agent_name, {})


def get_all_capabilities_summary() -> dict:
    """Return summary of all connected apps and agent capabilities."""
    apps = {}
    for app_name, cfg in COMPOSIO_CAPABILITIES.items():
        apps[app_name] = {
            "accounts": len(cfg["accounts"]),
            "read_tools": len(cfg["tools"].get("read", [])),
            "write_tools": len(cfg["tools"].get("write", [])),
            "agent_actions": list(cfg["agent_actions"].keys()),
        }
    return {
        "apps": apps,
        "agents": {
            name: list(caps.keys())
            for name, caps in AGENT_COMPOSIO_MAP.items()
        },
        "total_accounts": sum(len(c["accounts"]) for c in COMPOSIO_CAPABILITIES.values()),
        "total_tools": sum(
            len(c["tools"].get("read", [])) + len(c["tools"].get("write", []))
            for c in COMPOSIO_CAPABILITIES.values()
        ),
    }
