from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time


URL = "https://makaut1.ucanapply.com/smartexam/public/student/dashboard"      
TAB_LIMIT = 100                  # Maximum number of Tab presses
WAIT_TIME = 0.3                  # Delay after each key press


def get_element_details(element):
    """Return useful information about the currently focused element."""
    return {
        "tag": element.tag_name,
        "id": element.get_attribute("id"),
        "name": element.get_attribute("name"),
        "text": element.text.strip(),
        "role": element.get_attribute("role"),
        "tabindex": element.get_attribute("tabindex"),
        "aria-label": element.get_attribute("aria-label"),
        "href": element.get_attribute("href"),
        "class": element.get_attribute("class")
    }


def print_element(index, details):
    print(f"\nElement {index}")
    print("-" * 40)
    for key, value in details.items():
        print(f"{key:12}: {value}")


driver = webdriver.Chrome()

driver.maximize_window()
driver.get(URL)
time.sleep(2)

body = driver.find_element(By.TAG_NAME, "body")
body.click()

print("=" * 60)
print("FORWARD TAB TRAVERSAL")
print("=" * 60)

visited = set()
forward_order = []

for i in range(TAB_LIMIT):

    body.send_keys(Keys.TAB)
    time.sleep(WAIT_TIME)

    active = driver.switch_to.active_element

    identifier = (
        active.tag_name,
        active.get_attribute("id"),
        active.get_attribute("name"),
        active.get_attribute("href")
    )

    if identifier in visited:
        print("\nReached the first focused element again.")
        print("Forward traversal completed.")
        break

    visited.add(identifier)

    details = get_element_details(active)
    forward_order.append(details)

    print_element(i + 1, details)

print("\n")
print("=" * 60)
print("SHIFT + TAB TRAVERSAL")
print("=" * 60)

visited_backward = set()
backward_order = []

actions = ActionChains(driver)

for i in range(TAB_LIMIT):

    actions.key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT).perform()
    time.sleep(WAIT_TIME)

    active = driver.switch_to.active_element

    identifier = (
        active.tag_name,
        active.get_attribute("id"),
        active.get_attribute("name"),
        active.get_attribute("href")
    )

    if identifier in visited_backward:
        print("\nReached the last focused element again.")
        print("Backward traversal completed.")
        break

    visited_backward.add(identifier)

    details = get_element_details(active)
    backward_order.append(details)

    print_element(i + 1, details)

print("\n")
print("=" * 60)
print("SUMMARY")
print("=" * 60)

print(f"Forward Tab Order : {len(forward_order)} elements")
print(f"Backward Tab Order: {len(backward_order)} elements")

if len(forward_order) != len(backward_order):
    print("\nWarning: Different number of elements detected.")
    print("This may indicate a keyboard navigation issue.")

print("\nPossible Focus Trap Check")

if len(visited) < TAB_LIMIT:
    print("No obvious focus trap detected.")
else:
    print("Possible focus trap or very large tab order.")

driver.quit()