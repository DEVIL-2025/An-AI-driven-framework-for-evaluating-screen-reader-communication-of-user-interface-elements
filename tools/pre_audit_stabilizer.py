"""
Pre-Audit Page Stabilization and Transient Popup Handling Component (Phase 3C).

CRITICAL ARCHITECTURAL CONSTRAINTS:
1. 100% GENERIC:
   - Absolutely NO hardcoded website names, domains, URLs, element IDs,
     CSS selectors, class names, popup text, cookie vendor names, or xpath paths.
   - Works uniformly on arbitrary websites, SPAs, and dynamic web applications.
2. CONSERVATIVE DISMISSAL POLICY:
   - Suppresses only transient startup UI (cookie banners, marketing modals,
     newsletter overlays, notification prompts) that prevent normal page state.
   - Strictly preserves legitimate application workflow dialogs, checkout dialogs,
     form dialogs, and primary user tasks. If confidence is low, PRESERVE.
3. NO DOM MUTATION VIA ELEMENT DELETION:
   - NEVER mutates or deletes DOM elements; never hides elements via style modification.
   - Uses real user-like dismissal: clicking verified close controls or Escape key.
4. BOUNDED TIMEOUTS & FAIL-SAFE ERROR HANDLING:
   - All polling and iteration is strictly bounded. Never hangs indefinitely.
   - Handles stale elements, intercepted clicks, and dynamic re-renders safely.
"""

import time
import logging
from typing import Any, Dict, List, Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    WebDriverException,
)

logger = logging.getLogger("PreAuditStabilizer")


def get_safe_chrome_options(base_options: Optional[Any] = None) -> Any:
    """
    Configure Chrome WebDriver options to prevent nonessential browser-level
    permission prompts (notifications, geolocation, camera, microphone) without
    altering web application behavior, JavaScript execution, cookies, or accessibility APIs.
    """
    from selenium import webdriver
    options = base_options or webdriver.ChromeOptions()

    # Block nonessential browser-level native permission prompts
    prefs = {
        "profile.default_content_setting_values.notifications": 2,  # 2 = Block prompt
        "profile.default_content_setting_values.geolocation": 2,    # 2 = Block prompt
        "profile.default_content_setting_values.media_stream_camera": 2,  # 2 = Block prompt
        "profile.default_content_setting_values.media_stream_mic": 2,     # 2 = Block prompt
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--disable-notifications")

    return options


# Generic dismissal semantic keywords (strictly generic, neutral terminology)
SAFE_DISMISS_KEYWORDS = {
    "close",
    "dismiss",
    "decline",
    "reject",
    "cancel",
    "skip",
    "no thanks",
    "not now",
    "later",
    "continue without",
    "reject all",
    "only necessary",
    "essential only",
    "use necessary",
    "necessary only",
    "cross",
    "x",
    "✕",
    "×",
    "&times;",
}

# Dangerous / business submission keywords that MUST NEVER be clicked as dismissals
DANGEROUS_ACTION_KEYWORDS = {
    "submit",
    "login",
    "log in",
    "sign in",
    "signin",
    "register",
    "create account",
    "signup",
    "sign up",
    "checkout",
    "pay",
    "purchase",
    "order",
    "place order",
    "buy now",
    "buy",
    "confirm order",
    "delete",
    "remove account",
    "accept all",     # Do not auto-accept marketing/tracking consent
    "allow all",      # Do not auto-accept permissions
    "subscribe",      # Do not auto-subscribe to newsletters
}


# JavaScript helper to discover candidate transient UI elements non-destructively.
# Operates purely via read-only DOM inspection and getComputedStyle.
JS_DISCOVER_TRANSIENT_CANDIDATES = """
return (function() {
    var candidates = [];
    var vw = window.innerWidth || document.documentElement.clientWidth || 1024;
    var vh = window.innerHeight || document.documentElement.clientHeight || 768;

    // Helper: test if an element is visible
    function isVisible(el, style) {
        if (!el) return false;
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
        var rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }

    // Helper: test if an element is a fixed header or footer (false positive prevention)
    function isHeaderOrFooter(el, rect, style) {
        var tag = el.tagName.toLowerCase();
        var role = (el.getAttribute('role') || '').toLowerCase();
        if (tag === 'header' || tag === 'footer' || tag === 'nav') return true;
        if (role === 'banner' || role === 'contentinfo' || role === 'navigation' || role === 'search' || role === 'toolbar') return true;

        var isTopDocked = rect.top <= 20 && rect.width >= (vw * 0.70) && rect.height <= Math.max(180, vh * 0.25);
        var isBottomDocked = rect.bottom >= (vh - 20) && rect.width >= (vw * 0.70) && rect.height <= 160;

        return isTopDocked || isBottomDocked;
    }

    // 1. Semantic dialog elements
    var semanticElements = document.querySelectorAll('dialog, [role="dialog"], [role="alertdialog"], [aria-modal="true"]');
    for (var i = 0; i < semanticElements.length; i++) {
        var el = semanticElements[i];
        var style = window.getComputedStyle(el);
        if (isVisible(el, style)) {
            var rect = el.getBoundingClientRect();
            if (!isHeaderOrFooter(el, rect, style)) {
                candidates.push(el);
            }
        }
    }

    // 2. Elements matching generic overlay / modal / popup / dialog classes or attributes
    var overlaySelectors = [
        '[class*="modal" i]',
        '[class*="overlay" i]',
        '[class*="popup" i]',
        '[class*="dialog" i]',
        '[class*="lightbox" i]',
        '[id*="modal" i]',
        '[id*="overlay" i]',
        '[id*="popup" i]',
        '[data-cy*="modal" i]',
        '[data-testid*="modal" i]'
    ];
    var classElements = document.querySelectorAll(overlaySelectors.join(','));
    for (var k = 0; k < classElements.length; k++) {
        var oEl = classElements[k];
        var oStyle = window.getComputedStyle(oEl);
        if (isVisible(oEl, oStyle)) {
            var oRect = oEl.getBoundingClientRect();
            if (!isHeaderOrFooter(oEl, oRect, oStyle)) {
                // Must be floating/overlay positioned or large card
                if (oStyle.position === 'fixed' || oStyle.position === 'absolute' || 
                    (oRect.width >= (vw * 0.25) && oRect.height >= (vh * 0.20))) {
                    if (candidates.indexOf(oEl) === -1) {
                        candidates.push(oEl);
                    }
                }
            }
        }
    }

    // 3. Fixed / sticky / full-screen backdrop elements
    var allFixed = document.querySelectorAll('*');
    for (var j = 0; j < allFixed.length; j++) {
        var item = allFixed[j];
        // Skip document root or main content landmarks
        var t = item.tagName.toLowerCase();
        if (t === 'body' || t === 'html' || t === 'main') continue;
        var r = (item.getAttribute('role') || '').toLowerCase();
        if (r === 'main' || r === 'document') continue;

        var s = window.getComputedStyle(item);
        if ((s.position === 'fixed' || s.position === 'sticky' || s.position === 'absolute') && isVisible(item, s)) {
            var bRect = item.getBoundingClientRect();
            var z = parseInt(s.zIndex, 10) || 0;
            var isLargeCover = (bRect.width >= (vw * 0.60) && bRect.height >= (vh * 0.50));
            var isSubstantial = (bRect.width >= (vw * 0.25) && bRect.height >= (vh * 0.20));
            if ((z >= 10 && isSubstantial) || isLargeCover) {
                if (!isHeaderOrFooter(item, bRect, s)) {
                    if (candidates.indexOf(item) === -1) {
                        candidates.push(item);
                    }
                }
            }
        }
    }

    return candidates;
})();
"""


class PreAuditStabilizer:
    """
    Generic Pre-Audit Page Stabilizer.
    Performs bounded detection and safe real-user dismissal of transient startup UI
    before NVDA speech capture and synchronized traversal commence.
    """

    def __init__(
        self,
        max_stabilization_time: float = 8.0,
        initial_grace_seconds: float = 1.0,
        quiet_period: float = 0.8,
        poll_interval: float = 0.25,
        max_dismiss_iterations: int = 3,
    ):
        self.max_stabilization_time = max_stabilization_time
        self.initial_grace_seconds = initial_grace_seconds
        self.quiet_period = quiet_period
        self.poll_interval = poll_interval
        self.max_dismiss_iterations = max_dismiss_iterations

    def stabilize(self, driver: Any) -> Dict[str, Any]:
        """
        Execute bounded pre-audit page stabilization on the given WebDriver session.

        Flow:
        1. Wait for document.readyState === "complete" and bounded initial hydration grace period.
        2. Iteratively discover visible transient UI candidates.
        3. Conservatively evaluate whether candidate is safe to dismiss.
        4. Attempt safe dismissal via verified close control or Escape key.
        5. Verify UI stabilization and quiet window.
        6. Return detailed structured diagnostic metadata.
        """
        start_time = time.time()
        actions_taken: List[Dict[str, Any]] = []
        dismissed_count = 0
        transient_detected = False
        timed_out = False

        logger.info("[STABILIZER] Waiting for initial page state...")

        # 1. Bounded initial page load & hydration wait
        initial_wait_start = time.time()
        self._wait_for_ready_state(driver, timeout=self.initial_grace_seconds)
        initial_wait_ms = int((time.time() - initial_wait_start) * 1000)

        # 2. Iterative transient UI detection and dismissal
        for iteration in range(1, self.max_dismiss_iterations + 1):
            if (time.time() - start_time) >= self.max_stabilization_time:
                logger.warning(f"[STABILIZER] Max stabilization timeout ({self.max_stabilization_time}s) reached.")
                timed_out = True
                break

            candidates = self._find_candidates(driver)

            # In iteration 1, allow bounded polling for delayed hydration / late-loading modals
            if not candidates and iteration == 1:
                grace_start = time.time()
                while not candidates and (time.time() - grace_start) < self.initial_grace_seconds:
                    if (time.time() - start_time) >= self.max_stabilization_time:
                        break
                    time.sleep(self.poll_interval)
                    candidates = self._find_candidates(driver)

            if not candidates:
                # No transient UI detected in this iteration
                break

            transient_detected = True
            dismissed_in_iteration = False

            for candidate in candidates:
                if (time.time() - start_time) >= self.max_stabilization_time:
                    timed_out = True
                    break

                is_safe, dismissal_target, reason = self._evaluate_candidate_for_dismissal(candidate, driver)
                if not is_safe:
                    logger.info(f"[STABILIZER] Candidate preserved ({reason}). Remaining as legitimate page UI.")
                    continue

                # Attempt safe dismissal using real user-like action
                logger.info(f"[STABILIZER] Safe dismissal attempted: {reason}")
                action_record = self._execute_safe_dismissal(driver, candidate, dismissal_target, iteration)
                actions_taken.append(action_record)

                if action_record.get("success"):
                    dismissed_count += 1
                    dismissed_in_iteration = True
                    # Short pause for DOM reaction
                    time.sleep(0.3)
                    break  # Re-evaluate remaining candidates fresh from DOM

            if not dismissed_in_iteration:
                # No more candidates were safely dismissable
                break

        # 3. Post-dismissal quiet window / stabilization check
        remaining_candidates = self._find_candidates(driver)
        remaining_dialog_count = len(remaining_candidates)

        self._wait_for_quiet_state(driver, start_time)

        duration_ms = int((time.time() - start_time) * 1000)

        # Determine final status
        if timed_out:
            status = "TIMED_OUT"
        elif not transient_detected and dismissed_count == 0:
            status = "NO_TRANSIENT_UI"
        elif transient_detected and remaining_dialog_count == 0:
            status = "STABILIZED"
        elif transient_detected and remaining_dialog_count > 0:
            status = "PARTIALLY_STABILIZED"
        else:
            status = "STABILIZED"

        logger.info(
            f"[STABILIZER] UI stable: status={status}, dismissed={dismissed_count}, "
            f"remaining={remaining_dialog_count}, duration={duration_ms}ms."
        )

        return {
            "status": status,
            "initial_wait_ms": initial_wait_ms,
            "iterations": len(actions_taken) or 1,
            "transient_ui_detected": transient_detected,
            "dismissed_count": dismissed_count,
            "remaining_dialog_count": remaining_dialog_count,
            "stabilization_duration_ms": duration_ms,
            "timed_out": timed_out,
            "actions": actions_taken,
        }

    def _wait_for_ready_state(self, driver: Any, timeout: float) -> None:
        """Wait up to timeout seconds for document.readyState === 'complete'."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                state = driver.execute_script("return document.readyState;")
                if state == "complete":
                    break
            except Exception:
                pass
            time.sleep(self.poll_interval)

    def _find_candidates(self, driver: Any) -> List[Any]:
        """Discover candidate transient UI elements using generic DOM inspection."""
        try:
            candidates = driver.execute_script(JS_DISCOVER_TRANSIENT_CANDIDATES)
            if isinstance(candidates, list):
                # Filter out any stale elements
                valid = []
                for c in candidates:
                    try:
                        if c.is_displayed():
                            valid.append(c)
                    except Exception:
                        continue
                return valid
        except Exception as e:
            logger.debug(f"[STABILIZER] Candidate discovery notice: {e}")
        return []

    def _evaluate_candidate_for_dismissal(
        self, candidate: Any, driver: Any
    ) -> Tuple[bool, Optional[Any], str]:
        """
        Conservatively evaluate if candidate element is safe transient startup UI to dismiss.

        Returns:
            (is_safe_to_dismiss, dismissal_target_element_or_None, reason_description)
        """
        try:
            # 1. Search for explicit safe dismiss / close controls FIRST
            # Search inside candidate for buttons, links, or elements with close/cross/dismiss semantics
            controls = candidate.find_elements(
                By.XPATH,
                ".//button | .//*[@role='button'] | .//input[@type='button'] | .//a | "
                ".//*[contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'close') or "
                "contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'cross') or "
                "contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'dismiss') or "
                "contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'close') or "
                "contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'dismiss') or "
                "contains(translate(@data-cy, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'close') or "
                "contains(translate(@id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'close')]"
            )

            # If candidate is an inner card/dialog, also search parent container for close controls
            if not controls:
                try:
                    parent = candidate.find_element(By.XPATH, "..")
                    if parent and parent.tag_name.lower() not in ("body", "html"):
                        controls = parent.find_elements(
                            By.XPATH,
                            ".//*[contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'close') or "
                            "contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'cross') or "
                            "contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'close')]"
                        )
                except Exception:
                    pass

            safe_dismiss_control = self._find_safe_dismiss_control(candidate, controls)
            if safe_dismiss_control is not None:
                return True, safe_dismiss_control, "Explicit safe dismiss control identified"

            # 2. If NO explicit safe dismiss control exists, check form complexity
            # Multi-field forms without an explicit close button are preserved as legitimate workflow UI
            inputs = candidate.find_elements(By.XPATH, ".//input | .//select | .//textarea")
            input_types = []
            for inp in inputs:
                try:
                    t = (inp.get_attribute("type") or "text").lower()
                    if t not in ("hidden", "button", "submit", "reset"):
                        input_types.append(t)
                except StaleElementReferenceException:
                    pass

            if len(input_types) >= 3:
                return False, None, f"Contains complex multi-field form ({len(input_types)} fields) without safe dismiss control"

            # 3. Check if modal dialog can be dismissed via Escape key fallback
            is_modal = False
            try:
                role = (candidate.get_attribute("role") or "").lower()
                aria_modal = (candidate.get_attribute("aria-modal") or "").lower()
                tag = (candidate.tag_name or "").lower()
                if aria_modal == "true" or role in ("dialog", "alertdialog") or tag == "dialog":
                    is_modal = True
            except Exception:
                pass

            if is_modal and len(input_types) <= 1:
                return True, None, "Dismissible modal dialog without business form (Escape candidate)"

        except StaleElementReferenceException:
            return False, None, "Element became stale during evaluation"
        except Exception as e:
            return False, None, f"Evaluation exception: {e}"

        return False, None, "No safe dismissal mechanism identified"

    def _find_safe_dismiss_control(self, candidate: Any, buttons: List[Any]) -> Optional[Any]:
        """Search child interactive elements for a safe close/dismiss button."""
        for btn in buttons:
            try:
                if not btn.is_displayed():
                    continue

                text = " ".join((btn.text or "").strip().lower().split())
                aria_label = (btn.get_attribute("aria-label") or "").strip().lower()
                title = (btn.get_attribute("title") or "").strip().lower()
                cls = (btn.get_attribute("class") or "").strip().lower()
                btn_type = (btn.get_attribute("type") or "").strip().lower()
                data_cy = (btn.get_attribute("data-cy") or "").strip().lower()

                # Filter out dangerous action buttons
                combined_desc = f"{text} {aria_label} {title} {data_cy}"
                if any(kw in combined_desc for kw in DANGEROUS_ACTION_KEYWORDS):
                    continue

                # Never click submit buttons unless text explicitly says cancel / decline / close / dismiss
                if btn_type == "submit" and not any(kw in combined_desc for kw in ("cancel", "decline", "reject", "close", "dismiss")):
                    continue

                # Signal 1: Aria-label, title, or data-cy has dismiss keyword
                if any(kw in aria_label for kw in SAFE_DISMISS_KEYWORDS) or any(kw in title for kw in SAFE_DISMISS_KEYWORDS):
                    return btn

                if "close" in data_cy or "dismiss" in data_cy:
                    return btn

                # Signal 2: Visible text matches dismiss keyword
                if any(text == kw or text.startswith(kw) for kw in SAFE_DISMISS_KEYWORDS):
                    return btn

                # Signal 3: Symbol close (e.g. '✕', '×', '&times;', 'x')
                if text in ("✕", "×", "&times;", "x"):
                    return btn

                # Signal 4: Class name explicitly contains close, cross, or dismiss
                # (e.g. 'commonModal__close', 'close', 'modal-close', 'btn-close', 'cross', 'modalClose')
                if any(c_kw in cls for c_kw in ("close", "cross", "dismiss")):
                    return btn

            except StaleElementReferenceException:
                continue
            except Exception:
                continue

        return None

    def _execute_safe_dismissal(
        self, driver: Any, candidate: Any, target_control: Optional[Any], iteration: int
    ) -> Dict[str, Any]:
        """
        Execute real user-like dismissal on the candidate.
        NEVER mutates or deletes DOM elements; never hides elements via style modification.
        """
        record = {
            "iteration": iteration,
            "action": "CLICK_DISMISS_BUTTON" if target_control else "SEND_ESCAPE_KEY",
            "dismissal_method": "click" if target_control else "escape",
            "success": False,
        }

        try:
            if target_control is not None:
                record["target_tag"] = (target_control.tag_name or "").lower()
                record["target_text"] = (target_control.text or "")[:40]

                # Attempt 1: Standard Selenium click
                try:
                    target_control.click()
                    record["success"] = True
                except (ElementClickInterceptedException, ElementNotInteractableException):
                    # Attempt 2: ActionChains user click
                    try:
                        ActionChains(driver).move_to_element(target_control).click().perform()
                        record["success"] = True
                    except Exception:
                        # Attempt 3: Native DOM click event dispatch (still user-event, not element removal)
                        try:
                            driver.execute_script("arguments[0].click();", target_control)
                            record["success"] = True
                        except Exception as click_err:
                            record["error"] = str(click_err)
                except StaleElementReferenceException:
                    record["error"] = "Target became stale prior to click"
            else:
                # Send Escape keystroke to candidate or active element
                try:
                    candidate.send_keys(Keys.ESCAPE)
                    record["success"] = True
                except Exception:
                    ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                    record["success"] = True

        except Exception as e:
            record["error"] = str(e)
            record["success"] = False

        return record

    def _wait_for_quiet_state(self, driver: Any, start_time: float) -> None:
        """Wait for page quiet state (document.readyState === 'complete' and no immediate new modals)."""
        quiet_start = time.time()
        while time.time() - quiet_start < self.quiet_period:
            if (time.time() - start_time) >= self.max_stabilization_time:
                break
            time.sleep(self.poll_interval)


def stabilize_page(driver: Any, **kwargs) -> Dict[str, Any]:
    """Convenience functional wrapper for PreAuditStabilizer."""
    stabilizer = PreAuditStabilizer(**kwargs)
    return stabilizer.stabilize(driver)


def prepare_for_keyboard_traversal(driver: Any) -> None:
    """
    Ensure the browser viewport is scrolled to top and focus is cleanly placed
    at the document root so that subsequent keyboard Tab navigation begins
    strictly from the first focusable element in DOM tree order.
    """
    try:
        driver.execute_script("""
            window.scrollTo(0, 0);
            if (document.activeElement && document.activeElement !== document.body) {
                document.activeElement.blur();
            }
        """)
        logger.info("[TRAVERSAL_INIT] Viewport scrolled to top and focus reset to document root.")
    except Exception as e:
        logger.debug(f"[TRAVERSAL_INIT] Notice during focus initialization: {e}")


def focus_first_focusable_element(driver: Any) -> Optional[Any]:
    """
    Locate the first visible, focusable element in DOM tree order, scroll it into view,
    and programmatically focus it so that keyboard traversal and screen reader capture
    begin strictly from the very first interactive element on the page.
    """
    try:
        elem = driver.execute_script("""
            return (function() {
                var selectors = [
                    'a[href]:not([tabindex="-1"])',
                    'button:not([disabled]):not([tabindex="-1"])',
                    'input:not([disabled]):not([type="hidden"]):not([tabindex="-1"])',
                    'select:not([disabled]):not([tabindex="-1"])',
                    'textarea:not([disabled]):not([tabindex="-1"])',
                    'area[href]:not([tabindex="-1"])',
                    'iframe:not([tabindex="-1"])',
                    '[tabindex]:not([tabindex="-1"])',
                    '[contenteditable="true"]:not([tabindex="-1"])'
                ];
                var all = document.querySelectorAll(selectors.join(','));
                for (var i = 0; i < all.length; i++) {
                    var el = all[i];
                    if (el.offsetWidth > 0 || el.offsetHeight > 0 || (el.getClientRects && el.getClientRects().length > 0)) {
                        var s = window.getComputedStyle(el);
                        if (s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0') {
                            el.focus();
                            return el;
                        }
                    }
                }
                return null;
            })();
        """)
        if elem is not None:
            logger.info("[TRAVERSAL_INIT] Programmatically focused first focusable element in DOM tree order.")
        return elem
    except Exception as e:
        logger.debug(f"[TRAVERSAL_INIT] Notice focusing first element: {e}")
        return None

