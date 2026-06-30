"""
Dore OS v2.0 — Distributor Module
Handles distribution to platforms: DistroKid automation, Spotify for Artists.
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict


class DistroKidUploader:
    """Automates DistroKid uploads via Playwright browser automation."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.browser = None
        self.page = None

    async def _init_browser(self, headless: bool = False):
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.page = await self.browser.new_page()

    async def _close_browser(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def upload(self, artist_id: str, release_slug: str, task: Dict) -> Dict:
        """Automate DistroKid upload form."""
        distrokid_email = os.getenv("DISTROKID_EMAIL", "")
        distrokid_password = os.getenv("DISTROKID_PASSWORD", "")

        if not distrokid_email or not distrokid_password:
            return {
                "status": "error",
                "message": "DISTROKID_EMAIL and DISTROKID_PASSWORD env vars required"
            }

        try:
            await self._init_browser(headless=False)

            # Login
            await self.page.goto("https://distrokid.com/login")
            await self.page.fill('input[name="email"]', distrokid_email)
            await self.page.fill('input[name="password"]', distrokid_password)
            await self.page.click('button[type="submit"]')
            await self.page.wait_for_load_state("networkidle")

            # Navigate to upload
            await self.page.goto("https://distrokid.com/upload")
            await self.page.wait_for_load_state("networkidle")

            # Fill metadata from task
            metadata = task.get("metadata", {})
            if metadata.get("title"):
                await self.page.fill('input[name="songTitle"]', metadata["title"])
            if metadata.get("artist"):
                await self.page.fill('input[name="artistName"]', metadata["artist"])

            # Upload audio file
            audio_path = task.get("audio_path", "")
            if audio_path:
                await self.page.set_input_files('input[type="file"]', audio_path)

            # Screenshot for verification
            await self.page.screenshot(path=str(
                self.vault_path / "analytics" / f"distrokid_{release_slug}.png"
            ))

            return {
                "status": "form_filled",
                "message": "DistroKid form filled. Manual review needed before submit.",
                "screenshot": f"analytics/distrokid_{release_slug}.png",
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            await self._close_browser()

    def upload_sync(self, artist_id: str, release_slug: str, task: Dict) -> Dict:
        """Synchronous wrapper for upload."""
        import asyncio
        return asyncio.run(self.upload(artist_id, release_slug, task))
