#!/usr/bin/env python3
"""Fetch YouTube channel statistics via YouTube Data API v3."""

import requests
import json
import os
import sys
from datetime import datetime

# Read API key from .env file
env_path = os.path.expanduser("~/.hermes/.env")
api_key = None
with open(env_path, 'r') as f:
    for line in f:
        line = line.strip()
        if line.startswith('GOOGLE_API_KEY='):
            api_key = line.split('=', 1)[1]
            print(f"Found GOOGLE_API_KEY (len={len(api_key)})")
            break

if not api_key:
    # Try GEMINI_API_KEY
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('GEMINI_API_KEY='):
                api_key = line.split('=', 1)[1]
                print(f"Found GEMINI_API_KEY (len={len(api_key)})")
                break

if not api_key:
    print("ERROR: No API key found")
    sys.exit(1)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

# Channels from composio_bridge.py
channels = [
    {
        "composio_id": "youtube_cully-gelada",
        "alias": "DORE Studio TAM",
        "channel_name": "Hakan ALANYALI",
        "channel_id": None,
        "handle": "HakanALANYALI"
    },
    {
        "composio_id": "youtube_amen-valyl",
        "alias": None,
        "channel_name": "Azultv Kids",
        "channel_id": None,
        "handle": "AzultvKids"
    },
    {
        "composio_id": "youtube_filled-glummy",
        "alias": None,
        "channel_name": "Night History Archive",
        "channel_id": None,
        "handle": "NightHistoryArchive"
    },
    {
        "composio_id": "youtube_hexact-wide",
        "alias": "World Time Capsule",
        "channel_name": "World Time Capsule",
        "channel_id": None,
        "handle": "WorldTimeCapsuleYT"
    },
    {
        "composio_id": "youtube_baglamaci",
        "alias": "Baglamacı Lab",
        "channel_name": "Baglamacı Lab",
        "channel_id": "UCQUrKnft1TsIwJA9EXSZc6g",
        "handle": None
    },
    {
        "composio_id": "youtube_valhaven",
        "alias": "Valhaven",
        "channel_name": "Valhaven",
        "channel_id": "UCq6trIBd0xuNZM6U2DNudzA",
        "handle": None
    },
    {
        "composio_id": "youtube_darkblues",
        "alias": "Dark Blues Music Lab",
        "channel_name": "Dark Blues Music Lab",
        "channel_id": "UCzifmnvKT612eVmz2e72oCw",
        "handle": None
    },
]


def api_get(endpoint, params):
    """Make a YouTube API request."""
    params["key"] = api_key
    url = f"{YOUTUBE_API_BASE}/{endpoint}"
    resp = requests.get(url, params=params)
    data = resp.json()
    if "error" in data:
        err = data["error"]
        raise Exception(f"API error {resp.status_code}: {err.get('message', str(err))}")
    return data


def fetch_channel_by_id(channel_id):
    """Fetch channel stats by channel ID."""
    data = api_get("channels", {
        "part": "statistics,snippet,contentDetails",
        "id": channel_id,
    })
    if "items" in data and len(data["items"]) > 0:
        item = data["items"][0]
        stats = item.get("statistics", {})
        snippet = item.get("snippet", {})
        return {
            "channel_id": channel_id,
            "title": snippet.get("title", ""),
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "view_count": int(stats.get("viewCount", 0)),
            "published_at": snippet.get("publishedAt", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
            "custom_url": snippet.get("customUrl", ""),
            "country": snippet.get("country", ""),
        }
    return None


def fetch_channel_by_handle(handle):
    """Fetch channel stats by @handle."""
    clean = handle.replace("@", "")
    data = api_get("channels", {
        "part": "statistics,snippet,contentDetails",
        "forHandle": clean,
    })
    if "items" in data and len(data["items"]) > 0:
        item = data["items"][0]
        stats = item.get("statistics", {})
        snippet = item.get("snippet", {})
        return {
            "channel_id": item.get("id", ""),
            "title": snippet.get("title", ""),
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "view_count": int(stats.get("viewCount", 0)),
            "published_at": snippet.get("publishedAt", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
            "custom_url": snippet.get("customUrl", ""),
            "country": snippet.get("country", ""),
        }
    return None


def search_channel(query):
    """Search for channel by name."""
    data = api_get("search", {
        "part": "snippet",
        "q": query,
        "type": "channel",
        "maxResults": 5,
    })
    results = []
    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        results.append({
            "channel_id": snippet.get("channelId", ""),
            "title": snippet.get("title", ""),
            "description": snippet.get("description", "")[:120],
        })
    return results


def get_latest_video(channel_id):
    """Get the most recent video from a channel."""
    data = api_get("search", {
        "part": "snippet",
        "channelId": channel_id,
        "order": "date",
        "maxResults": 1,
        "type": "video",
    })
    if "items" in data and len(data["items"]) > 0:
        snippet = data["items"][0].get("snippet", {})
        vid = data["items"][0].get("id", {})
        return {
            "video_id": vid.get("videoId", ""),
            "title": snippet.get("title", ""),
            "published_at": snippet.get("publishedAt", ""),
        }
    return None


def get_video_details(video_id):
    """Get video statistics."""
    data = api_get("videos", {
        "part": "statistics,snippet",
        "id": video_id,
    })
    if "items" in data and len(data["items"]) > 0:
        item = data["items"][0]
        stats = item.get("statistics", {})
        return {
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
            "comment_count": int(stats.get("commentCount", 0)),
        }
    return None


# Process all channels
all_results = []

for ch in channels:
    print(f"\n{'='*60}")
    print(f"Processing: {ch['channel_name']} ({ch['composio_id']})")
    result = {
        "composio_id": ch["composio_id"],
        "alias": ch["alias"],
        "channel_name": ch["channel_name"],
    }
    
    stats = None
    
    # Try channel_id first
    if ch.get("channel_id"):
        print(f"  Trying channel_id: {ch['channel_id']}")
        try:
            stats = fetch_channel_by_id(ch["channel_id"])
        except Exception as e:
            print(f"  Error: {e}")
            stats = None
    
    # Try handle
    if not stats and ch.get("handle"):
        print(f"  Trying handle: @{ch['handle']}")
        try:
            stats = fetch_channel_by_handle(ch["handle"])
        except Exception as e:
            print(f"  Error: {e}")
            stats = None
    
    # Try search as last resort
    if not stats:
        print(f"  Trying search for: {ch['channel_name']}")
        try:
            search_results = search_channel(ch["channel_name"])
            print(f"  Search returned {len(search_results)} results")
            for sr in search_results:
                print(f"    - {sr['title']} ({sr['channel_id']}): {sr['description']}")
            if search_results:
                stats = fetch_channel_by_id(search_results[0]["channel_id"])
        except Exception as e:
            print(f"  Search error: {e}")
            stats = None
    
    if stats:
        result.update(stats)
        # Get latest video
        try:
            latest = get_latest_video(stats["channel_id"])
            if latest:
                result["latest_video_date"] = latest["published_at"]
                result["latest_video_title"] = latest["title"]
                result["latest_video_id"] = latest["video_id"]
                print(f"  ✓ {stats['title']}: {stats['subscriber_count']} subs, {stats['view_count']} views, {stats['video_count']} videos")
                print(f"    Latest: {latest['published_at']} - {latest['title'][:60]}")
            else:
                result["latest_video_date"] = None
                print(f"  ✓ {stats['title']}: {stats['subscriber_count']} subs, {stats['view_count']} views, {stats['video_count']} videos")
        except Exception as e:
            result["latest_video_date"] = None
            print(f"  Latest video error: {e}")
    else:
        result["error"] = "Channel not found"
        print(f"  ✗ Channel not found")
    
    all_results.append(result)


# Build output
output = {
    "fetched_at": datetime.utcnow().isoformat() + "Z",
    "api_version": "v3",
    "total_channels": len(all_results),
    "successful": sum(1 for r in all_results if "error" not in r),
    "failed": sum(1 for r in all_results if "error" in r),
    "channels": all_results
}

# Write to file
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vault", "analytics")
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "youtube_live_stats.json")
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
print(f"\n\n✓ Wrote results to: {output_path}")

# Print summary
print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
for r in all_results:
    if "error" not in r:
        print(f"  {r['title']}: {r['subscriber_count']:,} subs | {r['view_count']:,} views | {r['video_count']} videos")
        if r.get("latest_video_date"):
            print(f"    Last video: {r['latest_video_date']}")
    else:
        print(f"  {r['channel_name']}: ✗ {r['error']}")

# Also print raw JSON for composio_bridge update
print(f"\n{'='*60}")
print("COMPOSIO BRIDGE UPDATE DATA")
print(f"{'='*60}")
for r in all_results:
    if "error" not in r:
        print(f"  {r['composio_id']}: subs={r['subscriber_count']}, views={r['view_count']}, videos={r['video_count']}, channel_id={r['channel_id']}")
