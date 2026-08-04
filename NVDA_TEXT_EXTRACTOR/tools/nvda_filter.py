class NVDAFilter:

    def __init__(self):
        self.ignore_words = {
            "space",
            "tab",
            "enter",
            "shift",
            "control",
            "alt",
            "escape",
            "backspace",
            "carriage return",
        }

        self.ignore_contains = {
            "nvda speech viewer",
            "show speech viewer on startup",
            "closes the window",
        }

    def should_ignore(self, line):
        """Return True if the line is irrelevant NVDA output."""

        line = line.strip()
        line_lower = line.lower()

        if not line:
            return True

        if len(line) == 1:
            return True

        if line_lower in self.ignore_words:
            return True

        for phrase in self.ignore_contains:
            if phrase in line_lower:
                return True

        if "running window" in line_lower:
            return True

        if line_lower.endswith("pinned"):
            return True

        return False

    def clean(self, text):
        """Remove ignored lines from NVDA output."""

        cleaned = []

        for line in text.splitlines():

            line = line.strip()

            if self.should_ignore(line):
                continue

            cleaned.append(line)

        return cleaned