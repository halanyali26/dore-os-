"""
Dore OS v2.0 — MusicBrainz Integration
Artist/Recording MBID lookup and metadata enrichment.
"""
import musicbrainzngs
from typing import Dict, Optional, List
from datetime import datetime


class MusicBrainzClient:
    """MusicBrainz API wrapper for artist and recording metadata."""

    def __init__(self, app_name: str = "DoreOS", app_version: str = "2.0"):
        musicbrainzngs.set_useragent(app_name, app_version,
                                     "https://github.com/dorestudio/dore-os")
        self._rate_limit_delay = 1.0  # MusicBrainz rate limit: ~1 req/sec

    def search_artist(self, name: str, limit: int = 5) -> List[Dict]:
        """Search for artist by name, return MBID candidates."""
        result = musicbrainzngs.search_artists(artist=name, limit=limit)
        artists = []
        for a in result.get("artist-list", []):
            artists.append({
                "mbid": a.get("id"),
                "name": a.get("name"),
                "type": a.get("type", "unknown"),
                "country": a.get("country", "unknown"),
                "tags": [t["name"] for t in a.get("tag-list", [])],
                "life_span": a.get("life-span", {}),
            })
        return artists

    def get_artist_by_mbid(self, mbid: str) -> Dict:
        """Get detailed artist info by MBID."""
        result = musicbrainzngs.get_artist_by_id(
            mbid, includes=["tags", "aliases", "url-rels", "recordings"]
        )
        artist = result.get("artist", {})
        return {
            "mbid": artist.get("id"),
            "name": artist.get("name"),
            "sort_name": artist.get("sort-name"),
            "type": artist.get("type", "unknown"),
            "country": artist.get("country", "unknown"),
            "tags": [t["name"] for t in artist.get("tag-list", [])],
            "aliases": [a["alias"] for a in artist.get("alias-list", [])],
            "recordings": len(artist.get("recording-list", [])),
        }

    def search_recording(self, title: str, artist: str = "", limit: int = 5) -> List[Dict]:
        """Search for recording by title/artist."""
        query = title
        if artist:
            query = f'recording:"{title}" AND artist:"{artist}"'
        result = musicbrainzngs.search_recordings(query=query, limit=limit)
        recordings = []
        for r in result.get("recording-list", []):
            recordings.append({
                "mbid": r.get("id"),
                "title": r.get("title"),
                "artist": r.get("artist-credit-phrase", "unknown"),
                "length_ms": int(r.get("length", 0)) if r.get("length") else 0,
                "isrcs": r.get("isrc-list", []),
                "tags": [t["name"] for t in r.get("tag-list", [])],
            })
        return recordings

    def get_recording_by_mbid(self, mbid: str) -> Dict:
        """Get detailed recording info by MBID."""
        result = musicbrainzngs.get_recording_by_id(
            mbid, includes=["artists", "tags", "isrcs", "releases", "url-rels"]
        )
        rec = result.get("recording", {})
        return {
            "mbid": rec.get("id"),
            "title": rec.get("title"),
            "artist": rec.get("artist-credit-phrase", "unknown"),
            "length_ms": int(rec.get("length", 0)) if rec.get("length") else 0,
            "isrcs": rec.get("isrc-list", []),
            "tags": [t["name"] for t in rec.get("tag-list", [])],
            "releases": [
                {"title": r.get("title"), "date": r.get("date", "")}
                for r in rec.get("release-list", [])
            ],
        }

    def register_recording(self, title: str, artist: str, isrc: str,
                           length_ms: int = 0) -> Dict:
        """Note: MusicBrainz is community-edited. This creates a TODO note for manual entry.

        MusicBrainz doesn't have a write API for automated mass-submission.
        This method generates the URL for manual submission.
        """
        return {
            "status": "manual_submission_required",
            "title": title,
            "artist": artist,
            "isrc": isrc,
            "submit_url": "https://musicbrainz.org/recording/create",
            "note": "MusicBrainz requires manual entry via web interface. Use the URL above."
        }
