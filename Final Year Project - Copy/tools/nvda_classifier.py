import json
import re


class NVDAClassifier:

    def __init__(self):
        # Used for duplicate removal
        self.seen = set()

        # Stores all unique website elements
        self.website_elements = []

        # Ignore browser / desktop UI
        self.ignore_contains = {
            # Chrome
            "google chrome",
            "tool bar",
            "bookmark this tab",
            "address and search bar",
            "view site information",
            "open gemini",
            "tab search",
            "new tab",
            "new tab new tab",

            # VS Code
            "visual studio code",
            "editor is not accessible",
            "terminal",
            "panel",
            "files explorer",
            "explorer tree",
            "test.py",
            "website_elements",

            # ChatGPT
            "chatgpt",
            "screen reader project flow",

            # Windows
            "harsh vardhan region",
            "zoom:",
            "application",

            # NVDA
            "speech viewer",
            "to get missing image descriptions",
            "listening...",
        }

        self.ignore_exact = {
            "panel",
            "application",
            "new tab",
            "first slide",
        }

        self.ignore_url_patterns = {
            "http://",
            "https://",
            "www.",
            "encoding=utf8",
            "encoding=utf-8",
            "ie=utf8",
            "ref=",
            "pd_rd_",
            "pf_rd_",
            "content-id=",
            "content_id=",
            "%2f",
            "%3a",
            "%3d",
            "&rh=",
            "&bbn=",
            "?encoding=",
        }

    def should_ignore(self, event):
        """Return True if the event is browser or system noise."""

        name = (event.name or "").strip().lower()

        if not name:
            return True

        if name in self.ignore_exact:
            return True

        for phrase in self.ignore_contains:
            if phrase in name:
                return True

        for pattern in self.ignore_url_patterns:
            if pattern in name:
                return True

        return False

    def normalize_name(self, name):
        """Normalize element names for duplicate detection."""

        if not name:
            return ""

        name = name.strip()

        # Remove standalone "visited"
        name = re.sub(r"\bvisited\b", "", name, flags=re.IGNORECASE)

        # Collapse multiple spaces
        name = re.sub(r"\s+", " ", name)

        return name.strip()

    def classify(self, events):

        for event in events:

            if self.should_ignore(event):
                continue

            normalized_name = self.normalize_name(event.name)

            key = (
                event.role,
                normalized_name.lower(),
            )

            if key in self.seen:
                continue

            self.seen.add(key)

            self.website_elements.append({
                "role": event.role,
                "name": normalized_name,
                "value": event.value,
                "description": event.description,
                "level": event.level,
                "attributes": event.attributes,
            })

        return self.website_elements

    def save(self, filename="website_elements.json"):

        with open(filename, "w", encoding="utf-8") as file:
            json.dump(
                self.website_elements,
                file,
                indent=4,
                ensure_ascii=False,
            )