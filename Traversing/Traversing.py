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
        "tag": element.tag_name.lower(),
        "id": element.get_attribute("id") or "",
        "name": element.get_attribute("name") or "",
        "text": element.text.strip(),
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

        for i in range(TAB_LIMIT):
            body.send_keys(Keys.TAB)
            time.sleep(WAIT_TIME)

            active = driver.switch_to.active_element
            identifier = (
                active.tag_name,
                active.get_attribute("id"),
                active.get_attribute("name"),
                active.get_attribute("href"),
                active.get_attribute("class"),
                active.text.strip(),
            )

            if identifier in visited:
                print("\nReached an already focused element.")
                print("Forward traversal completed.")
                break

            visited.add(identifier)

            if active.tag_name.lower() == "body":
                continue

            details = get_element_details(active)
            forward_order.append(details)
            print_element(i + 1, details)

        # BACKWARD SHIFT + TAB TRAVERSAL
        body = reset_page()

        print("\n" + "=" * 60)
        print("SHIFT + TAB TRAVERSAL")
        print("=" * 60)

        visited_backward = set()
        actions = ActionChains(driver)

        for i in range(TAB_LIMIT):
            actions.key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT).perform()
            time.sleep(WAIT_TIME)

            active = driver.switch_to.active_element
            identifier = (
                active.tag_name,
                active.get_attribute("id"),
                active.get_attribute("name"),
                active.get_attribute("href"),
                active.get_attribute("class"),
                active.text.strip(),
            )

            if identifier in visited_backward:
                print("\nReached an already focused element.")
                print("Backward traversal completed.")
                break

            visited_backward.add(identifier)

            if active.tag_name.lower() == "body":
                continue

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