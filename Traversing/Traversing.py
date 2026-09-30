import sys
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

import os

# Target URL (can be provided via command-line argument: python Traversing.py <URL> or TARGET_URL env)
DEFAULT_URL = os.environ.get("TARGET_URL", "")
URL = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

TAB_LIMIT = int(os.environ.get("TAB_LIMIT", 100))  # Maximum number of Tab presses
WAIT_TIME = float(os.environ.get("WAIT_TIME", 1.0))  # Delay after each key press


def get_element_details(element):
    """Return useful accessibility information about the currently focused element."""
    return {
        "tag": (element.tag_name or "").lower(),
        "id": element.get_attribute("id") or "",
        "name": element.get_attribute("name") or "",
        "text": (element.text or "").strip(),
        "role": element.get_attribute("role"),
        "type": element.get_attribute("type"),
        "tabindex": element.get_attribute("tabindex"),
        "aria-label": element.get_attribute("aria-label"),
        "title": element.get_attribute("title"),
        "alt": element.get_attribute("alt"),
        "placeholder": element.get_attribute("placeholder"),
        "value": element.get_attribute("value"),
        "href": element.get_attribute("href"),
        "class": element.get_attribute("class") or "",
    }


def get_traversal_element_identifier(element):
    """
    Construct a collision-free identifier for DOM elements during keyboard traversal.
    Uses Selenium W3C element node ID as primary unique key, supplemented with
    DOM attributes (tag, id, name, type, placeholder, aria-label, href, class, text, value).
    """
    try:
        elem_id = getattr(element, "id", None) or ""
        tag = (element.tag_name or "").lower()
        dom_id = element.get_attribute("id") or ""
        name = element.get_attribute("name") or ""
        input_type = (element.get_attribute("type") or "").lower() if tag == "input" else ""
        placeholder = element.get_attribute("placeholder") or ""
        aria_label = element.get_attribute("aria-label") or ""
        title = element.get_attribute("title") or ""
        href = element.get_attribute("href") or ""
        cls = element.get_attribute("class") or ""
        text = (element.text or "").strip()
        val = element.get_attribute("value") or ""
        return (elem_id, tag, dom_id, name, input_type, placeholder, aria_label, title, href, cls, text, val)
    except Exception:
        return None


def print_element(index, details):
    print(f"\nElement {index}")
    print("-" * 40)
    for key, value in details.items():
        if value:
            print(f"{key:12}: {value}")


if __name__ == "__main__":
    if not URL:
        print("Error: No target URL provided.")
        print("Usage: python Traversing.py <URL>")
        sys.exit(1)

    print(f"Target URL: {URL}")

    driver = webdriver.Chrome()
    forward_order = []
    backward_order = []

    try:
        driver.maximize_window()

        def reset_page():
            """Reload the page and place focus on the body."""
            driver.get(URL)
            time.sleep(WAIT_TIME)

            body = driver.find_element(By.TAG_NAME, "body")
            body.click()
            return body

        # FORWARD TAB TRAVERSAL
        body = reset_page()

        print("\n" + "=" * 60)
        print("FORWARD TAB TRAVERSAL")
        print("=" * 60)

        visited = set()
        first_focused_forward = None
        prev_forward_id = None
        forward_stagnant_count = 0
        actions = ActionChains(driver)

        for i in range(TAB_LIMIT):
            actions.send_keys(Keys.TAB).perform()
            time.sleep(WAIT_TIME)

            try:
                active = driver.switch_to.active_element
            except Exception:
                continue

            elem_id = getattr(active, "id", None)
            identifier = get_traversal_element_identifier(active)
            if not identifier:
                continue

            tag = (active.tag_name or "").lower()
            if tag in ("body", "html"):
                prev_forward_id = elem_id
                forward_stagnant_count = 0
                continue

            # Stagnation detection (focus stayed on the exact same element)
            if elem_id and elem_id == prev_forward_id:
                forward_stagnant_count += 1
                if forward_stagnant_count == 1:
                    try:
                        actions.send_keys(Keys.ESCAPE).perform()
                        time.sleep(0.3)
                    except Exception:
                        pass
                elif forward_stagnant_count >= 3:
                    print(f"\nFocus trapped on element <{tag}> for {forward_stagnant_count} consecutive steps. Forward traversal completed.")
                    break
            else:
                forward_stagnant_count = 0

            prev_forward_id = elem_id

            # Loop detection: only if focus returns to the first focused element after visiting >= 5 distinct elements
            if first_focused_forward and elem_id == first_focused_forward and len(visited) >= 5:
                print("\nReached wrap-around back to initial element.")
                print("Forward traversal completed.")
                break

            if first_focused_forward is None:
                first_focused_forward = elem_id

            visited.add(elem_id or identifier)

            details = get_element_details(active)
            forward_order.append(details)
            print_element(i + 1, details)

        # BACKWARD SHIFT + TAB TRAVERSAL
        body = reset_page()

        print("\n" + "=" * 60)
        print("SHIFT + TAB TRAVERSAL")
        print("=" * 60)

        visited_backward = set()
        first_focused_backward = None
        prev_backward_id = None
        backward_stagnant_count = 0

        for i in range(TAB_LIMIT):
            actions.key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT).perform()
            time.sleep(WAIT_TIME)

            try:
                active = driver.switch_to.active_element
            except Exception:
                continue

            elem_id = getattr(active, "id", None)
            identifier = get_traversal_element_identifier(active)
            if not identifier:
                continue

            tag = (active.tag_name or "").lower()
            if tag in ("body", "html"):
                prev_backward_id = elem_id
                backward_stagnant_count = 0
                continue

            # Stagnation detection (focus stayed on the exact same element)
            if elem_id and elem_id == prev_backward_id:
                backward_stagnant_count += 1
                if backward_stagnant_count == 1:
                    try:
                        actions.send_keys(Keys.ESCAPE).perform()
                        time.sleep(0.3)
                    except Exception:
                        pass
                elif backward_stagnant_count >= 3:
                    print(f"\nFocus trapped on element <{tag}> for {backward_stagnant_count} consecutive steps. Backward traversal completed.")
                    break
            else:
                backward_stagnant_count = 0

            prev_backward_id = elem_id

            # Loop detection: only if focus returns to the first backward element after visiting >= 5 distinct elements
            if first_focused_backward and elem_id == first_focused_backward and len(visited_backward) >= 5:
                print("\nReached wrap-around back to initial element.")
                print("Backward traversal completed.")
                break

            if first_focused_backward is None:
                first_focused_backward = elem_id

            visited_backward.add(elem_id or identifier)

            details = get_element_details(active)
            backward_order.append(details)
            print_element(i + 1, details)

    finally:
        print("\nTraversal finished. Closing browser...")
        try:
            driver.quit()
        except Exception:
            pass

    # SUMMARY
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Forward Tab Order : {len(forward_order)} elements")
    print(f"Backward Tab Order: {len(backward_order)} elements")

    if len(forward_order) != len(backward_order):
        print("\nWarning: Different number of elements detected.")
        print("This may indicate a keyboard navigation issue.")
    else:
        print("\nForward and backward traversal contain the same number of elements.")

    traversal_output = {
        "url": URL,
        "forward": forward_order,
        "backward": backward_order,
    }

    with open("traversal_output.json", "w", encoding="utf-8") as file:
        json.dump(traversal_output, file, indent=4, ensure_ascii=False)

    print("\nTraversal output saved to traversal_output.json")