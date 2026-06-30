"""
Dore OS v2.0 — DDEX ERN XML Generator
Generates DDEX Electronic Release Notification (ERN) v4.3 XML
for enterprise music distribution.
"""
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Optional


class DDEXGenerator:
    """Generates DDEX ERN 4.3 compliant XML for music distribution."""

    ERN_NAMESPACE = "http://ddex.net/xml/ern/43"
    XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"

    def __init__(self):
        ET.register_namespace("ern", self.ERN_NAMESPACE)
        ET.register_namespace("xsi", self.XSI_NAMESPACE)

    def generate_release(self, release_data: Dict) -> str:
        """Generate DDEX ERN NewReleaseMessage XML.

        Args:
            release_data: Dict with keys:
                - release_reference: Unique release ID
                - title: Release title
                - artist_name: Primary artist
                - label_name: Record label name
                - release_date: ISO date string
                - tracks: List of track dicts {title, isrc, duration_iso, audio_file_path}
                - upc: UPC/EAN code (optional)
                - genre: Primary genre (optional)
                - copyright_year: int (optional)
        """
        root = ET.Element("NewReleaseMessage", {
            "xmlns": self.ERN_NAMESPACE,
            "xmlns:xsi": self.XSI_NAMESPACE,
            "MessageSchemaVersionId": "ern/43",
            "LanguageAndScriptCode": "en",
        })

        # Header
        header = ET.SubElement(root, "MessageHeader")
        ET.SubElement(header, "MessageId").text = release_data.get("release_reference", f"DORE-{datetime.now():%Y%m%d%H%M%S}")
        ET.SubElement(header, "MessageSender").text = "Dore Studio"
        ET.SubElement(header, "MessageRecipient").text = release_data.get("distributor", "DistroKid")
        ET.SubElement(header, "MessageCreatedDateTime").text = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Release
        release_list = ET.SubElement(root, "ReleaseList")
        release = ET.SubElement(release_list, "Release")
        ET.SubElement(release, "ReleaseReference").text = release_data["release_reference"]
        ET.SubElement(release, "ReleaseType").text = "Album" if len(release_data.get("tracks", [])) > 3 else "Single"

        # Release details
        details = ET.SubElement(release, "ReleaseDetailsByTerritory")
        ET.SubElement(details, "TerritoryCode").text = "Worldwide"
        ET.SubElement(details, "Title").text = release_data["title"]
        ET.SubElement(details, "DisplayArtistName").text = release_data["artist_name"]
        ET.SubElement(details, "LabelName").text = release_data.get("label_name", "Dore Studio")

        if release_data.get("genre"):
            ET.SubElement(details, "Genre").text = release_data["genre"]

        if release_data.get("release_date"):
            ET.SubElement(details, "OriginalReleaseDate").text = release_data["release_date"]

        # Resource list (audio files)
        resource_list = ET.SubElement(release, "ResourceList")
        for i, track in enumerate(release_data.get("tracks", []), 1):
            sound_rec = ET.SubElement(resource_list, "SoundRecording")
            ET.SubElement(sound_rec, "ResourceReference").text = f"T{i:04d}"
            ET.SubElement(sound_rec, "Title").text = track["title"]
            ET.SubElement(sound_rec, "Duration").text = track.get("duration_iso", "PT3M30S")
            if track.get("isrc"):
                ET.SubElement(sound_rec, "ISRC").text = track["isrc"]

        # Release resource references (track listing)
        release_resource_list = ET.SubElement(release, "ReleaseResourceReferenceList")
        for i, track in enumerate(release_data.get("tracks", []), 1):
            ref = ET.SubElement(release_resource_list, "ReleaseResourceReference")
            ET.SubElement(ref, "ResourceReference").text = f"T{i:04d}"
            ET.SubElement(ref, "SequenceNumber").text = str(i)

        # Copyright
        if release_data.get("copyright_year"):
            rights = ET.SubElement(release, "ReleaseRightsControllerList")
            rc = ET.SubElement(rights, "ReleaseRightsController")
            ET.SubElement(rc, "RightsControllerName").text = release_data.get("label_name", "Dore Studio")
            ET.SubElement(rc, "CopyrightYear").text = str(release_data["copyright_year"])

        # Pretty print
        return self._pretty_print(root)

    def _pretty_print(self, element: ET.Element) -> str:
        """Pretty-print XML with proper indentation."""
        import xml.dom.minidom
        rough = ET.tostring(element, encoding="unicode")
        return xml.dom.minidom.parseString(rough).toprettyxml(indent="  ")
