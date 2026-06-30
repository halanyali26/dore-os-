"""
Dore OS v2.0 — YouTube Extractor & Distributor
Fetches YouTube analytics via Data API v3, uploads videos.
"""
import json
import os
from pathlib import Path
from datetime import datetime, timezone
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
            "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
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
        """Upload video to YouTube via OAuth 2.0."""
        video_path = task.get("video_path", "")
        if not video_path:
            # Try default path
            from ..vault_manager import VaultManager
            vm = VaultManager(self.vault_path.parent)
            default_video = self.vault_path.parent / "artists" / artist_id / "releases" / release_slug / "video.mp4"
            if default_video.exists():
                video_path = str(default_video)
            else:
                return {
                    "status": "error",
                    "message": f"Video file not found. Place video at: artists/{artist_id}/releases/{release_slug}/video.mp4",
                }

        if not Path(video_path).exists():
            return {
                "status": "error",
                "message": f"Video file not found: {video_path}",
                "hint": f"Place video in artists/{artist_id}/releases/{release_slug}/video.mp4"
            }

        # Use OAuth-based upload
        try:
            from ..auth_setup import upload_video as oauth_upload

            title = task.get("title", f"{artist_id} — {release_slug}")
            description = task.get("description", f"Dore OS release: {artist_id}/{release_slug}")
            tags = task.get("tags", [artist_id, release_slug, "dore-os", "ai-music"])
            privacy = task.get("privacy", "private")

            # Map account from task if specified
            account_id = task.get("youtube_account", "default")

            result = oauth_upload(
                video_path=video_path,
                title=title,
                description=description,
                tags=tags,
                privacy_status=privacy,
                account_id=account_id,
            )

            if result.get("status") == "ok":
                # Save upload record to analytics
                analytics_path = self.vault_path / "analytics"
                analytics_path.mkdir(parents=True, exist_ok=True)
                import json
                from datetime import datetime, timezone
                record = {
                    "type": "youtube_upload",
                    "artist_id": artist_id,
                    "release_slug": release_slug,
                    "video_id": result.get("video_id"),
                    "url": result.get("url"),
                    "uploaded_at": datetime.now(tz=timezone.utc).isoformat(),
                }
                (analytics_path / f"{artist_id}_{release_slug}_youtube_upload.json").write_text(
                    json.dumps(record, indent=2, ensure_ascii=False)
                )

            return result

        except ImportError:
            return {
                "status": "pending_oauth",
                "message": "YouTube upload requires OAuth setup. Run: python pipeline/auth_setup.py auth --account default",
                "video_path": video_path,
                "artist_id": artist_id,
                "release_slug": release_slug,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Upload failed: {e}",
                "video_path": video_path,
            }
