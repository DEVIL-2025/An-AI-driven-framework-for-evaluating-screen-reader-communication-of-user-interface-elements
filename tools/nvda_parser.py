import re


class AccessibilityEvent:
    """Represents a structured, website-independent accessibility event."""

    def __init__(
        self,
        name="",
        role="unknown",
        value=None,
        description=None,
        level=None,
        attributes=None,
        raw_text=None,
    ):
        self.name = name or ""
        self.role = role or "unknown"
        self.value = value
        self.description = description
        self.level = level
        self.attributes = attributes or []
        self.raw_text = raw_text

    def to_dict(self):
        """Serialize event to a dictionary."""
        return {
            "name": self.name,
            "role": self.role,
            "value": self.value,
            "description": self.description,
            "level": self.level,
            "attributes": self.attributes,
            "raw_text": self.raw_text,
        }

    def __repr__(self):
        return (
            f"AccessibilityEvent("
            f"name={repr(self.name)}, "
            f"role={repr(self.role)}, "
            f"value={repr(self.value)}, "
            f"description={repr(self.description)}, "
            f"level={repr(self.level)}, "
            f"attributes={self.attributes}, "
            f"raw_text={repr(self.raw_text)})"
        )


class NVDAParser:
    """
    Generic parser for converting NVDA speech announcements into
    structured AccessibilityEvent objects.
    """

    def __init__(self):
        # Standard primary accessibility roles announced by NVDA
        self.roles = {
            "button",
            "link",
            "edit",
            "checkbox",
            "combo box",
            "document",
            "heading",
            "landmark",
            "graphic",
            "image",
            "toolbar",
            "list",
            "list item",
            "menu",
            "menu item",
            "tab",
            "tab list",
            "radio button",
            "switch",
            "slider",
            "dialog",
            "alert",
            "status",
            "progress bar",
            "tree view",
            "tree item",
            "table",
            "row",
            "column",
            "grid",
            "spin button",
            "separator",
        }

        # Compound role combinations that represent a single accessibility concept
        self.compound_roles = {
            "graphic link",
            "image link",
            "link graphic",
            "link image",
            "banner landmark",
            "navigation landmark",
            "main landmark",
            "search landmark",
            "complementary landmark",
            "contentinfo landmark",
            "menu button",
            "unlabelled graphic",
            "unlabeled graphic",
        }

        # Standard accessibility states and attributes announced by screen readers
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
            "read only",
            "has popup",
            "disabled",
            "invalid",
            "modal",
            "focused",
            "visited",
            "same page",
        }

        # Roles that complement each other when describing a single UI element
        self.complementary_roles = {
            "graphic": {"link"},
            "image": {"link"},
            "unlabelled graphic": {"link"},
            "unlabeled graphic": {"link"},
            "link": {"graphic", "image", "unlabelled graphic", "unlabeled graphic"},
            "menu": {"button"},
        }

        # Standard NVDA guidance / system helper phrases to extract as description
        self.system_descriptions = [
            "to get missing image descriptions, open the context menu",
            "to get missing image descriptions open the context menu",
            "press tab then enter to ask ai mode",
        ]

        # All multi-word keywords sorted descending by length to prevent partial tokenization
        all_phrases = self.roles | self.compound_roles | self.attributes
        self.multi_word_tokens = sorted(
            [phrase for phrase in all_phrases if " " in phrase],
            key=len,
            reverse=True,
        )

    def tokenize(self, line):
        """
        Tokenize an NVDA announcement while preserving compound multi-word tokens.
        """
        if not line or not line.strip():
            return []

        text = line.strip()

        # Temporarily encode multi-word phrases with underscores
        for phrase in self.multi_word_tokens:
            pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
            text = pattern.sub(phrase.replace(" ", "_"), text)

        tokens = text.split()

        # Restore underscores to spaces in each token
        return [token.replace("_", " ") for token in tokens]

    def classify(self, tokens):
        """
        Classify each token into ROLE, COMPOUND_ROLE, ATTRIBUTE, or TEXT.
        Punctuation is normalized for classification while preserving token value.
        """
        classified = []

        for token in tokens:
            cleaned = token.strip().strip(",.:;").lower()

            if cleaned in self.compound_roles:
                token_type = "COMPOUND_ROLE"
            elif cleaned in self.roles:
                token_type = "ROLE"
            elif cleaned in self.attributes:
                token_type = "ATTRIBUTE"
            else:
                token_type = "TEXT"

            classified.append({
                "type": token_type,
                "value": token,
                "cleaned": cleaned,
            })

        return classified

    def parse(self, lines):
        """Parse multiple cleaned lines of NVDA speech."""
        events = []
        for line in lines:
            if isinstance(line, str) and line.strip():
                events.extend(self.parse_line(line))
        return events

    def parse_line(self, line):
        """
        Parse a single NVDA announcement string into one or more AccessibilityEvent objects.
        Generic Structure: [Prefix/Container] [Name] [Role(s)] [Value] [Attributes...]
        """
        if not line or not line.strip():
            return []

        raw_text = line.strip()

        # Extract standard system guidance description if present
        extracted_description = None
        cleaned_line = raw_text
        for sys_desc in self.system_descriptions:
            if sys_desc in cleaned_line.lower():
                extracted_description = "To get missing image descriptions, open the context menu."
                cleaned_line = re.sub(
                    re.escape(sys_desc),
                    "",
                    cleaned_line,
                    flags=re.IGNORECASE,
                )
                cleaned_line = re.sub(r"\.\s*\.", ".", cleaned_line).strip()

        tokens = self.classify(self.tokenize(cleaned_line))
        if not tokens:
            return []

        # Check if line contains any role or compound role
        role_indices = [
            i for i, t in enumerate(tokens)
            if t["type"] in ("ROLE", "COMPOUND_ROLE")
        ]

        # Case 1: No recognized role -> emit unknown event with full text
        if not role_indices:
            name = self.clean_name([t["value"] for t in tokens])
            return [
                AccessibilityEvent(
                    name=name,
                    role="unknown",
                    description=extracted_description,
                    raw_text=raw_text,
                )
            ]

        # Case 2: Merge adjacent complementary roles into compound roles (e.g. "link" + "unlabelled graphic")
        merged_tokens = []
        i = 0
        while i < len(tokens):
            if i + 1 < len(tokens):
                t1 = tokens[i]["cleaned"]
                t2 = tokens[i + 1]["cleaned"]
                pair = f"{t1} {t2}"
                if pair in self.compound_roles or (t1 in self.complementary_roles and t2 in self.complementary_roles.get(t1, set())):
                    role_name = "graphic link" if ("link" in pair and ("graphic" in pair or "image" in pair)) else pair
                    merged_tokens.append({
                        "type": "COMPOUND_ROLE",
                        "value": f"{tokens[i]['value']} {tokens[i + 1]['value']}",
                        "cleaned": role_name,
                    })
                    i += 2
                    continue

            merged_tokens.append(tokens[i])
            i += 1

        tokens = merged_tokens

        # State Machine parsing across tokens
        events = []
        current_event = self._new_event_dict()
        state = "READING_NAME"

        for i, token in enumerate(tokens):
            t_type = token["type"]
            t_cleaned = token["cleaned"]
            t_value = token["value"]

            if state == "READING_NAME":
                if t_type in ("ROLE", "COMPOUND_ROLE"):
                    # Check if a primary interactive role follows in the immediate noun phrase
                    # (e.g. "Tab search button" or "Bookmark this tab button")
                    remaining_tokens = tokens[i + 1:]
                    has_later_primary_role = any(
                        t["type"] in ("ROLE", "COMPOUND_ROLE") and
                        not (t_cleaned in self.complementary_roles and t["cleaned"] in self.complementary_roles.get(t_cleaned, set()))
                        for t in remaining_tokens
                    )

                    if has_later_primary_role and not any(t["type"] == "ATTRIBUTE" for t in remaining_tokens[:1]):
                        # This role word is part of the accessible name of the subsequent role
                        current_event["name_tokens"].append(t_value)
                    else:
                        current_event["role"] = t_cleaned
                        state = "ROLE_ASSIGNED"

                elif t_type == "ATTRIBUTE":
                    current_event["attributes"].append(t_cleaned)
                else:
                    current_event["name_tokens"].append(t_value)

            elif state == "ROLE_ASSIGNED":
                if t_type == "ATTRIBUTE":
                    current_event["attributes"].append(t_cleaned)

                elif t_type in ("ROLE", "COMPOUND_ROLE"):
                    # Check if subsequent role is complementary to the current role (e.g. graphic + link)
                    curr_role = current_event["role"]
                    if curr_role and t_cleaned in self.complementary_roles.get(curr_role, set()):
                        if "link" in (curr_role, t_cleaned) and any(g in (curr_role, t_cleaned) for g in ("graphic", "image", "unlabelled graphic", "unlabeled graphic")):
                            current_event["role"] = "graphic link"
                        elif "button" in (curr_role, t_cleaned) and "menu" in (curr_role, t_cleaned):
                            current_event["role"] = "menu button"
                        else:
                            current_event["role"] = f"{curr_role} {t_cleaned}"
                    else:
                        # New object boundary reached
                        self._emit_event(events, current_event, raw_text, extracted_description)
                        current_event = self._new_event_dict()
                        current_event["role"] = t_cleaned
                        state = "ROLE_ASSIGNED"

                else:  # TEXT token after role
                    # Look ahead to check if a genuine new boundary role follows
                    curr_role = current_event.get("role")
                    has_subsequent_boundary_role = False

                    for t in tokens[i + 1:]:
                        if t["type"] in ("ROLE", "COMPOUND_ROLE"):
                            if curr_role and t["cleaned"] in self.complementary_roles.get(curr_role, set()):
                                continue
                            has_subsequent_boundary_role = True
                            break

                    if has_subsequent_boundary_role:
                        # This text belongs to the next element's name
                        self._emit_event(events, current_event, raw_text, extracted_description)
                        current_event = self._new_event_dict()
                        current_event["name_tokens"].append(t_value)
                        state = "READING_NAME"
                    else:
                        # Text belongs to this element: if no name yet, assign to name; else value
                        if not current_event["name_tokens"]:
                            current_event["name_tokens"].append(t_value)
                        else:
                            current_event["value_tokens"].append(t_value)

        self._emit_event(events, current_event, raw_text, extracted_description)
        return events

    def _new_event_dict(self):
        return {
            "name_tokens": [],
            "role": None,
            "value_tokens": [],
            "attributes": [],
        }

    def _emit_event(self, events, event_dict, raw_text, extracted_description=None):
        name_tokens = event_dict["name_tokens"]
        role = event_dict["role"]
        value_tokens = event_dict["value_tokens"]
        attributes = event_dict["attributes"]

        if not name_tokens and not role and not value_tokens:
            return

        cleaned_name = self.clean_name(name_tokens)
        value_str = " ".join(value_tokens).strip() if value_tokens else None

        # Normalize compound landmark names (e.g. role="navigation landmark" -> name="Navigation", role="landmark")
        if not cleaned_name and role:
            if "landmark" in role and role != "landmark":
                cleaned_name = role.replace("landmark", "").strip().title()
                role = "landmark"
            elif role in ("unlabelled graphic", "unlabeled graphic"):
                cleaned_name = "Unlabeled graphic"
                role = "graphic"

        event = AccessibilityEvent(
            name=cleaned_name,
            role=role or "unknown",
            value=value_str,
            description=extracted_description,
            level=None,
            attributes=attributes,
            raw_text=raw_text,
        )

        event = self.enrich_event(event)
        events.append(event)

    def clean_name(self, words):
        """
        Join and normalize name tokens, removing accidental stutter/duplicated speech.
        """
        if not words:
            return ""

        name = " ".join(words).strip()
        if not name:
            return ""

        # Remove repeated stuttered halves (e.g. "New Tab New Tab" -> "New Tab")
        split = name.split()
        if len(split) >= 2 and len(split) % 2 == 0:
            half = len(split) // 2
            if [w.lower() for w in split[:half]] == [w.lower() for w in split[half:]]:
                return " ".join(split[:half])

        return name

    def enrich_event(self, event):
        """
        Generic semantic enrichment dispatched by role.
        """
        if event.role == "heading":
            self.enrich_heading(event)
        elif event.role in ("link", "graphic link"):
            self.enrich_link(event)

        return event

    def enrich_heading(self, event):
        """
        Extract numeric heading level from heading name or raw text (e.g. 'heading level 2').
        """
        search_target = f"{event.name} {event.raw_text or ''}"
        match = re.search(r"\blevel\s+(\d+)\b", search_target, flags=re.IGNORECASE)
        if match:
            event.level = int(match.group(1))
            event.name = re.sub(r"\blevel\s+\d+\b", "", event.name, flags=re.IGNORECASE).strip()

    def enrich_link(self, event):
        """
        Generic link cleanup: remove container structural prefixes
        (e.g. 'list with 5 items Home' -> 'Home').
        """
        if not event.name:
            return

        # Strip standard container prefix 'list with X items'
        cleaned = re.sub(
            r"^list\s+with\s+\d+\s+items\s+",
            "",
            event.name,
            flags=re.IGNORECASE,
        ).strip()

        event.name = cleaned