"""Single-page and recursive website discovery workers."""

from collections import deque
import logging
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from PyQt6.QtCore import QThread, pyqtSignal
import requests

from udm.constants import SPIDER_EXTENSIONS


class SpiderWorker(QThread):
    """Discover media and known downloadable links on one page."""

    found_link = pyqtSignal(str)
    completed = pyqtSignal()

    def __init__(self, start_url, extract_images=True, extract_videos=True):
        super().__init__()
        self.start_url = start_url
        self.extract_images = extract_images
        self.extract_videos = extract_videos
        self._cancelled = False

    def run(self):
        try:
            response = requests.get(
                self.start_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for link in self.extract_links(soup):
                if self._cancelled:
                    break
                self.found_link.emit(link)
        except requests.RequestException as error:
            logging.error("Spider error: %s", error)
        finally:
            self.completed.emit()

    def extract_links(self, soup):
        links = set()
        if self.extract_videos:
            for video in soup.find_all("video"):
                source = video.get("src")
                if not source and video.find("source"):
                    source = video.find("source").get("src")
                if source:
                    links.add(urljoin(self.start_url, source))

        if self.extract_images:
            for image in soup.find_all("img", src=True):
                links.add(urljoin(self.start_url, image["src"]))

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if urlparse(href).path.lower().endswith(SPIDER_EXTENSIONS):
                links.add(urljoin(self.start_url, href))
        return sorted(links)

    def cancel(self):
        self._cancelled = True


class BulkSpiderWorker(QThread):
    """Recursively discover selected file extensions on one domain."""

    found_link = pyqtSignal(str)
    progress = pyqtSignal(int)
    completed = pyqtSignal(int)

    def __init__(self, start_url, extensions):
        super().__init__()
        self.start_url = start_url
        self.extensions = {
            extension.strip().lower().lstrip(".")
            for extension in extensions
            if extension.strip()
        }
        self._cancelled = False

    def run(self):
        visited = set()
        queued = {self.start_url}
        queue = deque([self.start_url])
        collected = set()
        base_domain = urlparse(self.start_url).netloc

        while queue and not self._cancelled:
            current_url = queue.popleft()
            queued.discard(current_url)
            if current_url in visited:
                continue
            visited.add(current_url)
            total = len(visited) + len(queue)
            self.progress.emit(min(99, int(len(visited) / max(1, total) * 100)))

            try:
                response = requests.get(
                    current_url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=8,
                )
                response.raise_for_status()
                if "text/html" not in response.headers.get("content-type", ""):
                    continue
                soup = BeautifulSoup(response.text, "html.parser")
                self._collect_page(
                    soup,
                    current_url,
                    base_domain,
                    visited,
                    queued,
                    queue,
                    collected,
                )
            except requests.RequestException as error:
                logging.error("Bulk spider error at %s: %s", current_url, error)

        self.progress.emit(100)
        self.completed.emit(len(collected))

    def _collect_page(
        self,
        soup,
        current_url,
        base_domain,
        visited,
        queued,
        queue,
        collected,
    ):
        for anchor in soup.find_all("a", href=True):
            if self._cancelled:
                return
            full_url = urljoin(current_url, anchor["href"])
            parsed = urlparse(full_url)
            if parsed.netloc != base_domain:
                continue
            extension = PurePosixPath(parsed.path).suffix.lower().lstrip(".")
            if extension in self.extensions:
                if full_url not in collected:
                    collected.add(full_url)
                    self.found_link.emit(full_url)
            elif not extension and full_url not in visited and full_url not in queued:
                queued.add(full_url)
                queue.append(full_url)

    def cancel(self):
        self._cancelled = True
