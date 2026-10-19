"""Page fetcher with SSRF protection"""
import re
import asyncio
from typing import Optional
import aiohttp
from src.application.ports import PageFetcher


PRIVATE_IP_PATTERNS = [
    r"^127\.",  # localhost
    r"^10\.",  # private range
    r"^172\.(1[6-9]|2[0-9]|3[01])\.",  # private range
    r"^192\.168\.",  # private range
    r"^169\.254\.",  # link-local
    r"^localhost$",
]


class SafePageFetcher(PageFetcher):
    """Fetch URLs with SSRF validation"""

    @staticmethod
    def _is_private_ip(url: str) -> bool:
        """Check if URL points to private IP"""
        # Extract hostname from URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            hostname = parsed.netloc.split(":")[0]
        except:
            return False

        for pattern in PRIVATE_IP_PATTERNS:
            if re.match(pattern, hostname):
                return True
        return False

    async def fetch(self, url: str, timeout: int = 10) -> Optional[str]:
        """
        Fetch page content with safety checks
        - Block private IPs (SSRF protection)
        - Enforce timeout
        - Include User-Agent header
        """
        if self._is_private_ip(url):
            raise ValueError(f"Cannot fetch from private IP: {url}")

        if not url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL scheme: {url}")

        try:
            headers = {"User-Agent": "Melos-Recipe-Fetcher/1.0"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout, headers=headers) as response:
                    if response.status == 200:
                        return await response.text()
                    return None
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request timeout after {timeout}s")
        except Exception as e:
            raise RuntimeError(f"Failed to fetch URL: {e}")
