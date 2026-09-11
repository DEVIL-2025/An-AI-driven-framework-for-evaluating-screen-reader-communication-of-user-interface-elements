class NVDAFilter:
    """
    Filters out system-level keystrokes and NVDA Speech Viewer UI announcements
    from the raw captured text stream.
    """

    def __init__(self):
        # Standalone keystroke announcements that are not accessibility content
        self.ignore_exact = {
            "space",
            "tab",
            "enter",
            "shift",
            "control",
            "alt",
            "escape",
            "backspace",
            "carriage return",
            "caps lock",
            "num lock",
        }

        # Substrings indicating NVDA UI / Speech Viewer window operations
        self.ignore_contains = {
            "nvda speech viewer",
            "show speech viewer on startup",
            "closes the window",
            "running window",
        }

    def should_ignore(self, line):
        """Return True if the line represents keystroke or Speech Viewer noise."""
        if not line:
            return True

        line_clean = line.strip()
        if not line_clean:
            return True

        line_lower = line_clean.lower()

        # Ignore single standalone key echoes
        if line_lower in self.ignore_exact:
            return True

        # Ignore NVDA Speech Viewer window controls
        for phrase in self.ignore_contains:
            if phrase in line_lower:
                return True

        return False

    def clean(self, text):
        """Remove ignored lines from the NVDA speech text stream."""
        if not text:
            return []

        cleaned = []
        for line in text.splitlines():
            line_clean = line.strip()
            if not self.should_ignore(line_clean):
                cleaned.append(line_clean)

        return cleaned