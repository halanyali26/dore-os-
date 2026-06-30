"""
Dore OS v2.0 — Auth Setup
Google OAuth 2.0 flow for YouTube Data API v3.
Token storage, refresh, and credential management.
"""
import os
import json
import pickle
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# YouTube upload scope
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

# Default token storage path
TOKEN_DIR = Path(os.getenv("DORE_OS_HOME", Path(__file__).parent.parent)) / ".tokens"
CREDENTIALS_FILE = Path(os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json"))


def get_token_path(account_id: str) -> Path:
    """Get the file path for a specific account's token."""
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    return TOKEN_DIR / f"youtube_{account_id}.pickle"


def get_credentials(account_id: str = "default") -> Optional[Credentials]:
    """
    Load saved credentials from disk. Returns None if not found or expired without refresh.
    Attempts to refresh if expired.
    """
    token_path = get_token_path(account_id)
    creds = None

    if token_path.exists():
        with open(token_path, "rb") as token:
            creds = pickle.load(token)

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_credentials(creds, account_id)
        except Exception:
            return None

    return creds


def save_credentials(creds: Credentials, account_id: str = "default"):
    """Save credentials to disk."""
    token_path = get_token_path(account_id)
    with open(token_path, "wb") as token:
        pickle.dump(creds, token)


def run_oauth_flow(account_id: str = "default", port: int = 8080) -> Credentials:
    """
    Run the interactive OAuth 2.0 flow.
    Opens browser → user authorizes → token saved.
    """
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Google credentials file not found: {CREDENTIALS_FILE}\n"
            "Download from: https://console.cloud.google.com/apis/credentials\n"
            "Place as 'credentials.json' in project root."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_FILE), SCOPES
    )

    # Use loopback server for local auth (no browser on headless — use console auth)
    creds = flow.run_local_server(
        port=port,
        prompt="consent",
        authorization_prompt_message="Go to this URL in your browser: {url}",
        success_message="✅ Auth complete! Token saved.",
        open_browser=True,
    )

    save_credentials(creds, account_id)
    return creds


def get_or_create_credentials(account_id: str = "default") -> Credentials:
    """
    Get existing credentials (with refresh) or run OAuth flow.
    Primary entry point for YouTube API auth.
    """
    creds = get_credentials(account_id)

    if not creds or not creds.valid:
        print(f"🔑 YouTube OAuth required for account: {account_id}")
        creds = run_oauth_flow(account_id)

    return creds


def build_youtube_client(account_id: str = "default"):
    """
    Build an authorized YouTube API client.
    Returns googleapiclient.discovery.Resource.
    """
    from googleapiclient.discovery import build

    creds = get_or_create_credentials(account_id)
    return build("youtube", "v3", credentials=creds)


def status(account_id: str = "default") -> Dict:
    """Check OAuth token status for an account."""
    token_path = get_token_path(account_id)
    creds = get_credentials(account_id)

    info = {
        "account_id": account_id,
        "has_token": token_path.exists(),
        "valid": creds.valid if creds else False,
        "expired": creds.expired if creds else None,
        "has_refresh_token": bool(creds.refresh_token) if creds else False,
        "expiry": creds.expiry.isoformat() if creds and creds.expiry else None,
        "scopes": creds.scopes if creds else [],
    }
    return info


def upload_video(
    video_path: str,
    title: str,
    description: str = "",
    tags: list = None,
    category_id: str = "10",  # Music
    privacy_status: str = "private",
    account_id: str = "default",
) -> Dict:
    """
    Upload a video to YouTube using OAuth credentials.

    Args:
        video_path: Path to the video file (MP4 recommended)
        title: Video title
        description: Video description
        tags: List of tag strings
        category_id: YouTube category ID (10 = Music)
        privacy_status: 'private', 'unlisted', or 'public'
        account_id: OAuth account identifier

    Returns:
        Dict with status and video details
    """
    video_file = Path(video_path)
    if not video_file.exists():
        return {
            "status": "error",
            "message": f"Video file not found: {video_path}",
        }

    try:
        yt = build_youtube_client(account_id)
    except Exception as e:
        return {
            "status": "error",
            "message": f"OAuth failed: {e}",
            "hint": "Run: python pipeline/auth_setup.py --account {account_id}",
        }

    body = {
        "snippet": {
            "title": title[:100],  # YouTube title limit
            "description": description[:5000],
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    try:
        # Use resumable upload
        from googleapiclient.http import MediaFileUpload

        media = MediaFileUpload(
            str(video_file),
            mimetype="video/*",
            resumable=True,
        )

        request = yt.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status_chunk, response = request.next_chunk()

        return {
            "status": "ok",
            "video_id": response["id"],
            "url": f"https://youtube.com/watch?v={response['id']}",
            "title": response["snippet"]["title"],
            "privacy": response["status"]["privacyStatus"],
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Upload failed: {e}",
        }


# ─── CLI ────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Dore OS YouTube OAuth Setup")
    sub = parser.add_subparsers(dest="command")

    # auth → run OAuth flow
    p_auth = sub.add_parser("auth", help="Run OAuth flow and save token")
    p_auth.add_argument("--account", default="default", help="Account identifier")
    p_auth.add_argument("--port", type=int, default=8080, help="Local server port")

    # status → check token status
    p_status = sub.add_parser("status", help="Check OAuth token status")
    p_status.add_argument("--account", default="default", help="Account identifier")

    # upload → upload a video
    p_upload = sub.add_parser("upload", help="Upload a video to YouTube")
    p_upload.add_argument("--video", required=True, help="Path to video file")
    p_upload.add_argument("--title", required=True, help="Video title")
    p_upload.add_argument("--description", default="", help="Video description")
    p_upload.add_argument("--tags", nargs="*", default=[], help="Video tags")
    p_upload.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    p_upload.add_argument("--account", default="default", help="Account identifier")

    args = parser.parse_args()

    if args.command == "auth":
        creds = run_oauth_flow(args.account, args.port)
        print(json.dumps(status(args.account), indent=2, default=str))

    elif args.command == "status":
        print(json.dumps(status(args.account), indent=2, default=str))

    elif args.command == "upload":
        result = upload_video(
            args.video, args.title, args.description,
            args.tags, privacy_status=args.privacy,
            account_id=args.account,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        parser.print_help()
