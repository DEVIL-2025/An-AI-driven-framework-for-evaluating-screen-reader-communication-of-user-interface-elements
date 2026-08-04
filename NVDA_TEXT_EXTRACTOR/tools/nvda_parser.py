import re

class AccessibilityEvent:

    def __init__(
        self,
        name,
        role,
        raw_text=None,
        value=None,
        description=None,
        level=None,
        attributes=None,
    ):
        self.name = name
        self.role = role
        self.value = value
        self.description = description
        self.level = level
        self.attributes = attributes or []

    def __repr__(self):
        return (
            f"AccessibilityEvent("
            f"name='{self.name}', "
            f"role='{self.role}', "
            f"level={repr(self.level)}, "
            f"value={repr(self.value)}, "
            f"description={repr(self.description)}, "
            f"attributes={self.attributes})"
        )


class NVDAParser:

    def __init__(self):

        self.roles = {
            "button",
            "link",
            "edit",
            "checkbox",
            "combo box",
            "document",
            "heading",
            "landmark",
        }

        self.attributes = {
            "blank",
            "collapsed",
            "expanded",
            "selected",
            "checked",
            "unchecked",
            "pressed",
            "unavailable",
            "required",
            "multi line",
            "has auto complete",
            "clickable",
        }

        # Multi-word phrases to preserve while tokenizing
        self.multi_word_tokens = sorted(
            [
                token
                for token in (self.roles | self.attributes)
                if " " in token
            ],
            key=len,
            reverse=True,
        )

    # Tokenizer
    def tokenize(self, line):

        text = line

        for phrase in self.multi_word_tokens:
            text = text.replace(
                phrase,
                phrase.replace(" ", "_")
            )

        tokens = text.split()

        return [
            token.replace("_", " ")
            for token in tokens
        ]
        
    def classify(self, tokens):

        classified = []

        for token in tokens:

            token_lower = token.lower()

            if token_lower in self.roles:
                token_type = "ROLE"

            elif token_lower in self.attributes:
                token_type = "ATTRIBUTE"

            else:
                token_type = "TEXT"

            classified.append({
                "type": token_type,
                "value": token
            })

        return classified

    # Main parser

    def parse(self, lines):

        events = []

        for line in lines:
            events.extend(self.parse_line(line))

        return events
    

    # Parse one NVDA announcement
    def parse_line(self, line):

        READING_NAME = 0
        ROLE_ASSIGNED = 1
        
        tokens = self.classify(
            self.tokenize(line)
        )

        events = []

        current_event = self.create_event()

        state = READING_NAME

        pending_name = []

        i = 0

        while i < len(tokens):

            token = tokens[i]

            token_type = token["type"]
            token_value = token["value"]

            if state == READING_NAME:

                if token_type == "TEXT":

                    current_event["name"].append(token_value)

                elif token_type == "ROLE":

                    current_event["role"] = token_value.lower()
                    state = ROLE_ASSIGNED

                elif token_type == "ATTRIBUTE":

                    current_event["attributes"].append(
                        token_value.lower()
                    )

            else:
                
                if token_type == "ATTRIBUTE":

                    current_event["attributes"].append(
                        token_value.lower()
                    )

                elif token_type == "ROLE":

                    self.emit_event(events, current_event)

                    current_event = self.create_event()
                    current_event["role"] = token_value.lower()

                    pending_name = []

                elif token_type == "TEXT":

                    pending_name = [token_value]

                    j = i + 1

                    while (
                        j < len(tokens)
                        and tokens[j]["type"] == "TEXT"
                    ):

                        pending_name.append(
                            tokens[j]["value"]
                        )

                        j += 1

                    if (
                        j < len(tokens)
                        and tokens[j]["type"] == "ROLE"
                    ):

                        self.emit_event(events, current_event)

                        current_event = self.create_event()
                        current_event["name"] = pending_name.copy()

                        state = READING_NAME

                        pending_name = []

                        i = j - 1

                    else:

                        current_event["name"].extend(
                            pending_name
                        )

                        pending_name = []

                        i = j - 1

            i += 1

        self.emit_event(events, current_event)

        return events
    
    def enrich_event(self, event):

        if event.role == "combo box":
            self.enrich_combo_box(event)

        elif event.role == "link":
            self.enrich_link(event)

        elif event.role == "heading":
            self.enrich_heading(event)

        return event
    
    def enrich_link(self, event):

        prefixes = [
            "list with",
        ]

        lower = event.name.lower()

        for prefix in prefixes:

            if lower.startswith(prefix):

                words = event.name.split()

                # Find the first capitalized word after the container text
                for i, word in enumerate(words):

                    if word[0].isupper():
                        event.name = " ".join(words[i:])
                        break
    
    def enrich_combo_box(self, event):

        words = event.name.split()

        if len(words) < 4:
            return

        if words[0].lower() == "search" and words[1].lower() == "in":

            event.name = "Search in"

            remaining = words[2:]

            # First two words become value
            if len(remaining) >= 2:

                event.value = " ".join(remaining[:2])

                if len(remaining) > 2:
                    event.description = " ".join(remaining[2:])
                    
    def enrich_heading(self, event):

        if event.role != "heading":
            return

        match = re.search(
            r"\blevel\s+(\d+)\b",
            event.name,
            flags=re.IGNORECASE
        )

        if match:

            event.level = int(match.group(1))

            event.name = re.sub(
                r"\blevel\s+\d+\b",
                "",
                event.name,
                flags=re.IGNORECASE
            ).strip()
        
    def create_event(self):
        return {
            "name": [],
            "role": None,
            "value": None,
            "description": None,
            "attributes": []
        }
    
    def emit_event(self, events, current_event):

        if not current_event["name"] and not current_event["role"]:
            return
        
        event = AccessibilityEvent(
            name=self.clean_name(current_event["name"]),
            role=current_event["role"] if current_event["role"] else "unknown",
            value=current_event.get("value"),
            description=current_event.get("description"),
            level=None,
            attributes=current_event["attributes"],
        )

        event = self.enrich_event(event)

        events.append(event)
        
    def clean_name(self, words):

        name = " ".join(words).strip()

        if not name:
            return ""

        # Remove duplicated names
        split = name.split()

        if len(split) % 2 == 0:

            half = len(split) // 2

            if split[:half] == split[half:]:
                return " ".join(split[:half])

        return name