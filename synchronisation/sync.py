import sys
import os
import time
import json
import re

# Allow Python to find the tools folder from subdirectories
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException

from tools.nvda_tool import NVDATextExtractor
from tools.nvda_filter import NVDAFilter
from tools.nvda_parser import NVDAParser

# Target URL (can be provided via command-line argument: python sync.py <URL> or TARGET_URL env)
DEFAULT_URL = os.environ.get("TARGET_URL", "")
URL = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

TAB_LIMIT = int(os.environ.get("TAB_LIMIT", 100))
READ_DELAY = float(os.environ.get("READ_DELAY", 2.0))
POLL_DELAY = float(os.environ.get("POLL_DELAY", 0.2))

# Mapping standard HTML tags/types to expected accessibility roles
TAG_TO_EXPECTED_ROLES = {
    "a": {"link", "graphic link", "button"},
    "button": {"button", "menu button"},
    "textarea": {"edit"},
    "select": {"combo box"},
    "img": {"graphic", "image", "graphic link"},
    "h1": {"heading"},
    "h2": {"heading"},
    "h3": {"heading"},
    "h4": {"heading"},
    "h5": {"heading"},
    "h6": {"heading"},
    "nav": {"landmark", "navigation"},
    "main": {"landmark", "main"},
    "header": {"landmark", "banner"},
}

INPUT_TYPE_TO_ROLES = {
    "text": {"edit"},
    "password": {"edit"},
    "email": {"edit"},
    "search": {"edit"},
    "number": {"edit", "spin button"},
    "checkbox": {"checkbox"},
    "radio": {"radio button"},
    "submit": {"button"},
    "button": {"button"},
    "reset": {"button"},
    "range": {"slider"},
}


def normalize_text(text):
    """Normalize text for consistent comparison."""
    if not text:
        return ""
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def get_element_details(element):
    """Extract accessible DOM properties safely from the focused Selenium element."""
    try:
        tag = (element.tag_name or "").lower()
        input_type = (element.get_attribute("type") or "").lower() if tag == "input" else None
        explicit_role = element.get_attribute("role")

        if explicit_role:
            expected_roles = {explicit_role.lower()}
        elif tag == "input" and input_type in INPUT_TYPE_TO_ROLES:
            expected_roles = INPUT_TYPE_TO_ROLES[input_type]
        else:
            expected_roles = TAG_TO_EXPECTED_ROLES.get(tag, set())

        return {
            "tag": tag,
            "id": element.get_attribute("id") or "",
            "name": element.get_attribute("name") or "",
            "text": (element.text or "").strip(),
            "role": explicit_role,
            "type": input_type,
            "tabindex": element.get_attribute("tabindex"),
            "aria-label": element.get_attribute("aria-label"),
            "title": element.get_attribute("title"),
            "alt": element.get_attribute("alt"),
            "placeholder": element.get_attribute("placeholder"),
            "value": element.get_attribute("value"),
            "href": element.get_attribute("href"),
            "class": element.get_attribute("class") or "",
            "expected_roles": list(expected_roles),
        }
    except StaleElementReferenceException:
        return {
            "tag": "unknown",
            "id": "",
            "name": "",
            "text": "",
            "role": None,
            "type": None,
            "tabindex": None,
            "aria-label": None,
            "title": None,
            "alt": None,
            "placeholder": None,
            "value": None,
            "href": None,
            "class": "",
            "expected_roles": [],
        }


def get_candidate_names(selenium_element):
    """Return all possible accessible names associated with the DOM element."""
    candidates = []
    for key in ("aria-label", "text", "alt", "title", "placeholder", "value", "name"):
        val = selenium_element.get(key)
        if val and str(val).strip():
            candidates.append(normalize_text(str(val)))
    return candidates


def find_matching_nvda_event(selenium_element, events):
    """
    Correlate a Selenium focused element with an NVDA event using
    generic text, label, and role heuristics.
    """
    candidates = get_candidate_names(selenium_element)
    expected_roles = set(selenium_element.get("expected_roles", []))

    # Pass 1: Match on accessible name and expected role
    for event in events:
        nvda_name = normalize_text(event.name)
        if nvda_name:
            for cand in candidates:
                if cand == nvda_name or cand in nvda_name or nvda_name in cand:
                    return event

    # Pass 2: Role-based match if element has no visible text (e.g. icon/image link)
    if not candidates:
        for event in events:
            nvda_role = (event.role or "").lower()
            if nvda_role in expected_roles:
                return event

    # Pass 3: If only one event was announced in this step, pair it
    if len(events) == 1:
        return events[0]

    return None


def compare_selenium_and_nvda(selenium_details, matched_event):
    """
    Perform an honest comparison between Selenium DOM data and the NVDA event.
    """
    if not matched_event:
        return {
            "name_match": False,
            "role_match": False,
            "status": "NO_NVDA_MATCH",
        }

    candidates = get_candidate_names(selenium_details)
    nvda_name = normalize_text(matched_event.name)
    nvda_role = (matched_event.role or "").lower()
    expected_roles = set(selenium_details.get("expected_roles", []))

    # Name matching
    name_match = False
    if nvda_name and candidates:
        name_match = any(
            cand == nvda_name or cand in nvda_name or nvda_name in cand
            for cand in candidates
        )

    # Role matching
    role_match = False
    if selenium_details.get("role"):
        role_match = (selenium_details["role"].lower() == nvda_role)
    elif expected_roles:
        role_match = (nvda_role in expected_roles)

    # Determine honest status
    if name_match and role_match:
        status = "MATCH"
    elif name_match and not role_match:
        status = "NAME_MATCH_ROLE_MISMATCH"
    elif not name_match and role_match:
        status = "ROLE_MATCH_NAME_UNLABELLED" if not candidates else "ROLE_MATCH_NAME_MISMATCH"
    else:
        status = "MISMATCH"

    return {
        "name_match": name_match,
        "role_match": role_match,
        "status": status,
    }


def capture_synchronized_element(
    extractor,
    nvda_filter,
    parser,
    selenium_details,
    max_wait=None,
    captured_speech=None,
    capture_status="OK",
):
    """
    Capture NVDA announcement for the newly focused Selenium element
    and compute comparison.
    Uses causal action speech if provided, or polls extractor adaptively.
    """
    if captured_speech is not None:
        nvda_text = captured_speech
    else:
        timeout = max_wait if max_wait is not None else READ_DELAY
        time.sleep(timeout)
        nvda_text = extractor.get_new_text()

    events = []
    if nvda_text:
        cleaned = nvda_filter.clean(nvda_text)
        if cleaned:
            events = parser.parse(cleaned)

    matched_event = find_matching_nvda_event(selenium_details, events)
    comparison = compare_selenium_and_nvda(selenium_details, matched_event)

    if capture_status == "NVDA_CAPTURE_TIMEOUT" and not matched_event:
        comparison["status"] = "NVDA_CAPTURE_TIMEOUT"

    result = {
        "selenium": selenium_details,
        "nvda": matched_event.to_dict() if matched_event else None,
        "comparison": comparison,
    }

    return result


if __name__ == "__main__":
    if not URL:
        print("Error: No target URL provided.")
        print("Usage: python sync.py <URL>")
        sys.exit(1)

    print(f"Target URL: {URL}")

    extractor = NVDATextExtractor()
    nvda_filter = NVDAFilter()
    parser = NVDAParser()

    driver = webdriver.Chrome()
    forward_results = []
    backward_results = []

    try:
        driver.maximize_window()
        print("\n[BROWSER] Navigating to target URL...")
        driver.get(URL)

        # Allow page-load speech to settle and establish clean baseline
        print("[NVDA] Page loading. Draining page initialization speech...")
        initial_speech, is_settled = extractor.drain_initial_speech()
        print(f"[NVDA] Baseline established. Initial speech length: {len(initial_speech)} chars (settled={is_settled}).")

        initial_events = []
        if initial_speech:
            cleaned_init = nvda_filter.clean(initial_speech)
            if cleaned_init:
                initial_events = [ev.to_dict() for ev in parser.parse(cleaned_init)]

        initialization_data = {
            "phase": "PAGE_INITIALIZATION",
            "raw_speech": initial_speech,
            "events": initial_events,
            "settled": is_settled,
        }

        actions = ActionChains(driver)

        # FORWARD TRAVERSAL
        visited_forward = set()

        print("\n" + "=" * 70)
        print("FORWARD SYNCHRONIZED TRAVERSAL (TRAVERSAL_READY)")
        print("=" * 70)

        for step in range(1, TAB_LIMIT + 1):
            print(f"\n[TRAVERSAL] Forward Step {step}: Action TAB...")

            def do_tab():
                actions.send_keys(Keys.TAB).perform()

            step_speech, capture_status = extractor.capture_action_response(do_tab)

            try:
                active = driver.switch_to.active_element
                identifier = (
                    active.tag_name,
                    active.get_attribute("id"),
                    active.get_attribute("name"),
                    active.get_attribute("href"),
                    active.get_attribute("class"),
                    (active.text or "").strip(),
                )
            except StaleElementReferenceException:
                continue

            if identifier in visited_forward:
                print("\nReached an already visited element. Forward traversal completed.")
                break

            visited_forward.add(identifier)

            if active.tag_name.lower() == "body":
                continue

            selenium_details = get_element_details(active)
            result = capture_synchronized_element(
                extractor,
                nvda_filter,
                parser,
                selenium_details,
                captured_speech=step_speech,
                capture_status=capture_status,
            )
            result["step"] = step
            forward_results.append(result)

            print(f"Tag   : {selenium_details['tag']}")
            print(f"Text  : {selenium_details['text'] or '(empty)'}")
            if result["nvda"]:
                print(f"NVDA  : role={result['nvda']['role']}, name={result['nvda']['name']}")
            else:
                print(f"NVDA  : (No NVDA event found - {capture_status})")
            print(f"Status: {result['comparison']['status']}")

        # BACKWARD TRAVERSAL
        visited_backward = set()

        print("\n\n" + "=" * 70)
        print("BACKWARD SYNCHRONIZED TRAVERSAL")
        print("=" * 70)

        for step in range(1, TAB_LIMIT + 1):
            print(f"\n[TRAVERSAL] Backward Step {step}: Action SHIFT+TAB...")

            def do_shift_tab():
                actions.key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT).perform()

            step_speech, capture_status = extractor.capture_action_response(do_shift_tab)

            try:
                active = driver.switch_to.active_element
                identifier = (
                    active.tag_name,
                    active.get_attribute("id"),
                    active.get_attribute("name"),
                    active.get_attribute("href"),
                    active.get_attribute("class"),
                    (active.text or "").strip(),
                )
            except StaleElementReferenceException:
                continue

            if identifier in visited_backward:
                print("\nReached an already visited element. Backward traversal completed.")
                break

            visited_backward.add(identifier)

            if active.tag_name.lower() == "body":
                continue

            selenium_details = get_element_details(active)
            result = capture_synchronized_element(
                extractor,
                nvda_filter,
                parser,
                selenium_details,
                captured_speech=step_speech,
                capture_status=capture_status,
            )
            result["step"] = step
            backward_results.append(result)

            print(f"Tag   : {selenium_details['tag']}")
            print(f"Text  : {selenium_details['text'] or '(empty)'}")
            if result["nvda"]:
                print(f"NVDA  : role={result['nvda']['role']}, name={result['nvda']['name']}")
            else:
                print(f"NVDA  : (No NVDA event found - {capture_status})")
            print(f"Status: {result['comparison']['status']}")

    finally:
        print("\nTraversal finished. Closing browser...")
        try:
            driver.quit()
        except Exception:
            pass

    final_output = {
        "url": URL,
        "initialization": initialization_data,
        "forward": forward_results,
        "backward": backward_results,
    }

    with open("synchronized_output.json", "w", encoding="utf-8") as file:
        json.dump(final_output, file, indent=4, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"Forward elements  : {len(forward_results)}")
    print(f"Backward elements : {len(backward_results)}")
    print("Output saved to synchronized_output.json")