from pywinauto import Desktop
import re


class NVDATextExtractor:
    """
    Connects to the running NVDA Speech Viewer window and captures
    spoken text output in real-time.
    """

    def __init__(self):
        # Attempt 1: Standard win32 exact title
        try:
            self.window = Desktop(backend="win32").window(title_re=".*Speech Viewer.*")
            self.rich_edit = self.window.child_window(class_name="RICHEDIT50W")
            self.previous_text = self.get_text()
            return
        except Exception:
            pass

        # Attempt 2: Search all top-level windows for Speech Viewer
        try:
            desktop = Desktop(backend="win32")
            for win in desktop.windows():
                title = win.window_text()
                if "speech viewer" in title.lower():
                    self.window = win
                    self.rich_edit = win.child_window(class_name="RICHEDIT50W")
                    self.previous_text = self.get_text()
                    return
        except Exception:
            pass

        # Attempt 3: Direct fallback
        self.window = Desktop(backend="win32").window(title="NVDA Speech Viewer")
        self.rich_edit = self.window.child_window(class_name="RICHEDIT50W")
        self.previous_text = self.get_text()

    def get_text(self):
        """Return the current contents of the Speech Viewer."""
        try:
            return self.rich_edit.window_text()
        except Exception:
            return ""

    def get_new_text(self):
        """Return only the newly added Speech Viewer text."""
        current = self.get_text()

        if current.startswith(self.previous_text):
            new = current[len(self.previous_text):]
        else:
            # Speech Viewer was cleared or updated
            new = current

        self.previous_text = current
        return new.strip()