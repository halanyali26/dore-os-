"""
Dore OS v2.0 — ISRC & UPC Generator
Generates standards-compliant ISRC (ISO 3901) and UPC codes.
"""
import hashlib
import random
from datetime import datetime
from typing import Tuple


class ISRCGenerator:
    """Generates ISRC codes in format: CC-XXX-YY-NNNNN

    CC = Country code (2 chars)
    XXX = Registrant code (3 chars)
    YY = Year (2 digits)
    NNNNN = Designation (5 digits)
    """

    COUNTRY_CODE = "TR"  # Turkey
    REGISTRANT = "DRS"   # Dore Studio

    def __init__(self, country: str = None, registrant: str = None):
        self.country = country or self.COUNTRY_CODE
        self.registrant = registrant or self.REGISTRANT
        self._counter = 1

    def generate(self, artist_id: str, release_slug: str) -> str:
        """Generate a unique ISRC for a release."""
        seed = f"{artist_id}:{release_slug}:{self._counter}"
        designation = self._hash_to_digits(seed, 5)
        year = datetime.now().strftime("%y")
        isrc = f"{self.country}-{self.registrant}-{year}-{designation}"
        self._counter += 1
        return isrc

    @staticmethod
    def _hash_to_digits(seed: str, length: int) -> str:
        h = hashlib.sha256(seed.encode()).hexdigest()
        return str(int(h, 16))[-length:].zfill(length)

    @staticmethod
    def validate(isrc: str) -> bool:
        """Validate ISRC format: CC-XXX-YY-NNNNN"""
        parts = isrc.split("-")
        if len(parts) != 4:
            return False
        if len(parts[0]) != 2 or not parts[0].isalpha():
            return False
        if len(parts[1]) != 3 or not parts[1].isalnum():
            return False
        if len(parts[2]) != 2 or not parts[2].isdigit():
            return False
        if len(parts[3]) != 5 or not parts[3].isdigit():
            return False
        return True


class UPCGenerator:
    """Generates UPC-A barcode numbers for albums."""

    PREFIX = "859700"  # Dore Studio prefix (fictional, for internal use)

    def __init__(self):
        self._counter = 1

    def generate(self, album_slug: str) -> str:
        """Generate UPC-A: 12 digits with check digit."""
        seed = f"{self.PREFIX}{self._counter:05d}{album_slug}"
        base = hashlib.md5(seed.encode()).hexdigest()
        digits = "".join(c for c in base if c.isdigit())[:11].zfill(11)
        check = self._calculate_check_digit(digits)
        self._counter += 1
        return digits + str(check)

    @staticmethod
    def _calculate_check_digit(digits: str) -> int:
        total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(digits))
        return (10 - (total % 10)) % 10
