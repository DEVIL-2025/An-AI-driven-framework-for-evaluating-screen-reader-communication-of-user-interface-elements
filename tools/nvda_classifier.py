import json
import re


class NVDAClassifier:
    """
    Deduplicates and stores unique website accessibility elements,
    filtering out desktop application and browser chrome controls.
    """

    def __init__(self):
        # Set of (role, normalized_name) keys for deduplication
        self.seen = set()

        # List of unique website elements
        self.website_elements = []

        # Generic browser chrome and operating system container elements to ignore
        self.ignore_contains = {
            "address and search bar",
            "bookmark this tab",
            "view site information",
            "tab search",
            "new tab",
            "speech viewer",
        }

        self.ignore_exact = {
            "panel",
            "application",
            "tool bar",
            "new tab",
        }

    def should_ignore(self, event):
        """Return True if the event is generic browser chrome or desktop noise."""
        name = (event.name or "").strip().lower()

        if not name and event.role == "unknown":
            return True

        if name in self.ignore_exact:
            return True

        for phrase in self.ignore_contains:
            if phrase in name:
                return True

        return False

    def normalize_name(self, name):
        """Normalize element names for consistent deduplication."""
        if not name:
            return ""

        name = name.strip()
        name = re.sub(r"\bvisited\b", "", name, flags=re.IGNORECASE)
        name = re.sub(r"\s+", " ", name)
        return name.strip()

    def classify(self, events):
        """Filter browser chrome noise and collect unique elements."""
        for event in events:
            if self.should_ignore(event):
                continue

            normalized_name = self.normalize_name(event.name)
            key = (event.role, normalized_name.lower())

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
                "raw_text": event.raw_text,
            })

        return self.website_elements

    def save(self, filename="website_elements.json"):
        """Save unique website elements to a JSON file."""
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(
                self.website_elements,
                file,
                indent=4,
                ensure_ascii=False,
            )