from pywinauto import Desktop


class NVDATextExtractor:

    def __init__(self):
        self.window = Desktop(backend="win32").window(title="NVDA Speech Viewer")
        self.rich_edit = self.window.child_window(class_name="RICHEDIT50W")

        # Ignore existing Speech Viewer content
        self.previous_text = self.get_text()

    def get_text(self):
        """Return the current contents of the Speech Viewer."""

        return self.rich_edit.window_text()

    def get_new_text(self):
        """Return only the newly added Speech Viewer text."""

        current = self.get_text()

        if current.startswith(self.previous_text):
            new = current[len(self.previous_text):]
        else:
            # Speech Viewer was cleared
            new = current

        self.previous_text = current

        return new.strip()