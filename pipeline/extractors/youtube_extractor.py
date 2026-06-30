"""
Dore OS v2.0 — YouTube Extractor & Distributor
Fetches YouTube analytics via Data API v3, uploads videos.
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


class YouTubeExtractor:
    """Fetches YouTube channel analytics and video stats."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.youtube = None

    def _get_client(self):
        if self.youtube is None:
            from googleapiclient.discovery import build
            self.youtube = build("youtube", "v3",
                                developerKey=os.getenv("YOUTUBE_API_KEY", ""))
        return self.youtube

    def get_channel_stats(self, channel_id: str) -> Dict:
        """Get channel statistics."""
        yt = self._get_client()
        request = yt.channels().list(part="statistics,snippet", id=channel_id)
        response = request.execute()

        if not response.get("items"):
            return {"error": f"Channel not found: {channel_id}"}

        channel = response["items"][0]
        data = {
            "title": channel["snippet"]["title"],
            "subscribers": int(channel["statistics"].get("subscriberCount", 0)),
            "views": int(channel["statistics"].get("viewCount", 0)),
            "videos": int(channel["statistics"].get("videoCount", 0)),
            "fetched_at": datetime.utcnow().isoformat(),
        }

        analytics_path = self.vault_path / "analytics"
        analytics_path.mkdir(parents=True, exist_ok=True)
        slug = data["title"].lower().replace(" ", "_")
        (analytics_path / f"{slug}_youtube.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False)
        )

        return data

    def search_channel(self, query: str) -> list:
        """Search for channels by name."""
        yt = self._get_client()
        request = yt.search().list(part="snippet", q=query, type="channel", maxResults=5)
        response = request.execute()
        return [
            {"title": item["snippet"]["title"], "channel_id": item["snippet"]["channelId"]}
            for item in response.get("items", [])
        ]


class YouTubeDistributor:
    """Uploads videos to YouTube via Data API v3 (OAuth required)."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path

    def upload(self, artist_id: str, release_slug: str, task: Dict) -> Dict:
        """Placeholder for YouTube upload via OAuth."""
        video_path = task.get("video_path", "")
        if not video_path or not Path(video_path).exists():
            return {
                "status": "error",
                "message": f"Video file not found: {video_path}",
                "hint": "Place video in artists/{artist_id}/releases/{release_slug}/video.mp4"
            }

        # TODO: Implement OAuth-based YouTube upload
        # Requires: google-auth-oauthlib flow, token storage
        return {
            "status": "pending_oauth",
            "message": "YouTube upload requires OAuth setup. Run: python pipeline/auth_setup.py youtube",
            "video_path": video_path,
            "artist_id": artist_id,
            "release_slug": release_slug,
        }
