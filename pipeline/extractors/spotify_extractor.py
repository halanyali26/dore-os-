"""
Dore OS v2.0 — Spotify Extractor
Fetches Spotify data via Spotipy, processes with Hermes LLM.
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class SpotifyExtractor:
    """Extracts Spotify data: artist stats, track performance, playlists."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.spotify = None  # Lazy init

    def _get_client(self):
        if self.spotify is None:
            import spotipy
            from spotipy.oauth2 import SpotifyClientCredentials
            auth = SpotifyClientCredentials(
                client_id=os.getenv("SPOTIFY_CLIENT_ID", ""),
                client_secret=os.getenv("SPOTIFY_CLIENT_SECRET", ""),
            )
            self.spotify = spotipy.Spotify(auth_manager=auth)
        return self.spotify

    def get_artist_stats(self, artist_name: str) -> Dict:
        """Get artist metadata and top tracks."""
        sp = self._get_client()
        results = sp.search(q=artist_name, type="artist", limit=1)
        artists = results.get("artists", {}).get("items", [])

        if not artists:
            return {"error": f"Artist not found: {artist_name}"}

        artist = artists[0]
        top_tracks = sp.artist_top_tracks(artist["id"], country="TR")

        data = {
            "name": artist["name"],
            "spotify_id": artist["id"],
            "genres": artist.get("genres", []),
            "followers": artist.get("followers", {}).get("total", 0),
            "popularity": artist.get("popularity", 0),
            "top_tracks": [
                {"name": t["name"], "popularity": t["popularity"], "album": t["album"]["name"]}
                for t in top_tracks.get("tracks", [])[:5]
            ],
            "fetched_at": datetime.utcnow().isoformat(),
        }

        # Save to analytics
        analytics_path = self.vault_path / "analytics"
        analytics_path.mkdir(parents=True, exist_ok=True)
        slug = artist_name.lower().replace(" ", "_")
        (analytics_path / f"{slug}_spotify.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False)
        )

        return data

    def get_track_stats(self, track_name: str, artist_name: str) -> Dict:
        """Get specific track data."""
        sp = self._get_client()
        query = f"track:{track_name} artist:{artist_name}"
        results = sp.search(q=query, type="track", limit=1)
        tracks = results.get("tracks", {}).get("items", [])

        if not tracks:
            return {"error": f"Track not found: {track_name}"}

        track = tracks[0]
        return {
            "name": track["name"],
            "spotify_id": track["id"],
            "album": track["album"]["name"],
            "duration_ms": track["duration_ms"],
            "popularity": track["popularity"],
            "explicit": track["explicit"],
            "release_date": track["album"]["release_date"],
            "isrc": track.get("external_ids", {}).get("isrc", ""),
        }
