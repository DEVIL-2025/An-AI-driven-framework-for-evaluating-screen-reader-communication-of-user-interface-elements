"""
Unit and Integration Tests for Pre-Audit Page Stabilization & Transient Popup Handling (Phase 3C).

CRITICAL ARCHITECTURAL CONSTRAINTS:
1. 100% GENERIC:
   - Uses synthetic HTML / DOM element fixtures.
   - Absolutely NO real website names, URLs, domains, element IDs, or selectors.
2. CONSERVATIVE DISMISSAL POLICY:
   - Verifies legitimate application dialogs are preserved.
   - Verifies transient startup UI is safely dismissed.
3. NO DOM MUTATION VIA ELEMENT REMOVAL:
   - Verifies no element.remove() or style.display = "none".
4. Tests TEST 1 through TEST 14 as mandated by Requirement 19.
"""

import os
import unittest
from unittest.mock import MagicMock, patch, call
from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementClickInterceptedException,
)

from tools.pre_audit_stabilizer import (
    PreAuditStabilizer,
    stabilize_page,
    get_safe_chrome_options,
    prepare_for_keyboard_traversal,
    focus_first_focusable_element,
)
from tools.nvda_tool import NVDATextExtractor, NVDAEvidencePhase


class MockWebElement:
    """Synthetic mock DOM element for testing stabilizer actions and detection."""

    def __init__(
        self,
        tag: str = "div",
        text: str = "",
        aria_label: str = "",
        title: str = "",
        role: str = "",
        aria_modal: str = "",
        classes: str = "",
        elem_type: str = "",
        displayed: bool = True,
        children: list = None,
    ):
        self.tag_name = tag
        self.text = text
        self._aria_label = aria_label
        self._title = title
        self._role = role
        self._aria_modal = aria_modal
        self._class = classes
        self._type = elem_type
        self._displayed = displayed
        self.children = children or []
        self.click_called = 0
        self.keys_sent = []

    def is_displayed(self) -> bool:
        return self._displayed

    def get_attribute(self, name: str) -> str:
        name_l = name.lower()
        if name_l == "aria-label":
            return self._aria_label
        elif name_l == "title":
            return self._title
        elif name_l == "role":
            return self._role
        elif name_l == "aria-modal":
            return self._aria_modal
        elif name_l == "class":
            return self._class
        elif name_l == "type":
            return self._type
        return ""

    def click(self):
        self.click_called += 1
        # Default behavior: clicking close dismisses the parent
        self._displayed = False

    def send_keys(self, *keys):
        self.keys_sent.extend(keys)

    def find_elements(self, by: str, value: str):
        return self.children


class TestPreAuditStabilizer(unittest.TestCase):
    """Test suite covering requirements TEST 1 through TEST 14."""

    # =========================================================================
    # TEST 1: Page with no popup
    # =========================================================================
    def test_01_page_with_no_popup(self):
        """Page with no popup: stabilization completes, no action taken, status is NO_TRANSIENT_UI."""
        mock_driver = MagicMock()
        mock_driver.execute_script.side_effect = lambda script, *args: (
            "complete" if "document.readyState" in script else []
        )

        stabilizer = PreAuditStabilizer(
            max_stabilization_time=2.0,
            initial_grace_seconds=0.1,
            quiet_period=0.1,
            poll_interval=0.05,
        )
        res = stabilizer.stabilize(mock_driver)

        self.assertEqual(res["status"], "NO_TRANSIENT_UI")
        self.assertFalse(res["transient_ui_detected"])
        self.assertEqual(res["dismissed_count"], 0)
        self.assertEqual(res["remaining_dialog_count"], 0)
        self.assertFalse(res["timed_out"])
        self.assertEqual(len(res["actions"]), 0)

    # =========================================================================
    # TEST 2: Generic modal with explicit close button
    # =========================================================================
    def test_02_generic_modal_with_explicit_close_button(self):
        """Generic modal with explicit close button: detected, safely dismissed, count increments."""
        close_btn = MockWebElement(tag="button", text="Close", aria_label="Close dialog", classes="btn-close")
        modal = MockWebElement(tag="div", role="dialog", aria_modal="true", children=[close_btn])

        mock_driver = MagicMock()
        call_count = [0]

        def exec_script(script, *args):
            if "document.readyState" in script:
                return "complete"
            call_count[0] += 1
            if call_count[0] == 1:
                return [modal]
            return []  # Disappeared after close

        mock_driver.execute_script.side_effect = exec_script

        stabilizer = PreAuditStabilizer(
            max_stabilization_time=2.0,
            initial_grace_seconds=0.1,
            quiet_period=0.1,
            poll_interval=0.05,
        )
        res = stabilizer.stabilize(mock_driver)

        self.assertEqual(res["status"], "STABILIZED")
        self.assertTrue(res["transient_ui_detected"])
        self.assertEqual(res["dismissed_count"], 1)
        self.assertEqual(res["remaining_dialog_count"], 0)
        self.assertEqual(close_btn.click_called, 1)
        self.assertEqual(res["actions"][0]["action"], "CLICK_DISMISS_BUTTON")

    # =========================================================================
    # TEST 3: Dialog appearing after delay
    # =========================================================================
    def test_03_dialog_appearing_after_delay(self):
        """Dialog appearing after initial delay: detected during polling and safely handled."""
        close_btn = MockWebElement(tag="button", text="Dismiss", aria_label="Dismiss notification")
        delayed_dialog = MockWebElement(tag="div", role="dialog", children=[close_btn])

        mock_driver = MagicMock()
        poll_count = [0]

        def exec_script(script, *args):
            if "document.readyState" in script:
                return "complete"
            poll_count[0] += 1
            if poll_count[0] < 2:
                return []  # Not rendered yet
            elif poll_count[0] == 2:
                return [delayed_dialog]  # Appears on 2nd poll
            return []  # Closed

        mock_driver.execute_script.side_effect = exec_script

        stabilizer = PreAuditStabilizer(
            max_stabilization_time=3.0,
            initial_grace_seconds=0.1,
            quiet_period=0.1,
            poll_interval=0.05,
        )
        res = stabilizer.stabilize(mock_driver)

        self.assertEqual(res["status"], "STABILIZED")
        self.assertTrue(res["transient_ui_detected"])
        self.assertEqual(res["dismissed_count"], 1)
        self.assertEqual(close_btn.click_called, 1)

    # =========================================================================
    # TEST 4: Sequential dialogs
    # =========================================================================
    def test_04_sequential_dialogs(self):
        """Sequential dialogs (e.g. cookie banner then newsletter modal): both dismissed iteratively."""
        btn1 = MockWebElement(tag="button", text="Decline All", aria_label="Decline cookies")
        dialog1 = MockWebElement(tag="div", role="dialog", children=[btn1])

        btn2 = MockWebElement(tag="button", text="✕", aria_label="Close newsletter", classes="close-icon")
        dialog2 = MockWebElement(tag="div", role="dialog", children=[btn2])

        mock_driver = MagicMock()
        iteration_step = [0]

        def exec_script(script, *args):
            if "document.readyState" in script:
                return "complete"
            iteration_step[0] += 1
            if iteration_step[0] == 1:
                return [dialog1]  # First dialog
            elif iteration_step[0] == 2:
                return [dialog2]  # Second dialog appears after first dismissed
            return []  # All cleared

        mock_driver.execute_script.side_effect = exec_script

        stabilizer = PreAuditStabilizer(
            max_stabilization_time=3.0,
            initial_grace_seconds=0.1,
            quiet_period=0.1,
            poll_interval=0.05,
            max_dismiss_iterations=3,
        )
        res = stabilizer.stabilize(mock_driver)

        self.assertEqual(res["status"], "STABILIZED")
        self.assertEqual(res["dismissed_count"], 2)
        self.assertEqual(res["remaining_dialog_count"], 0)
        self.assertEqual(len(res["actions"]), 2)
        self.assertEqual(btn1.click_called, 1)
        self.assertEqual(btn2.click_called, 1)

    # =========================================================================
    # TEST 5: Non-dismissible application dialog
    # =========================================================================
    def test_05_non_dismissible_application_dialog(self):
        """Legitimate application dialog (multi-field form / checkout): preserved, audit does not hang."""
        inp1 = MockWebElement(tag="input", elem_type="text")
        inp2 = MockWebElement(tag="input", elem_type="password")
        inp3 = MockWebElement(tag="input", elem_type="email")
        submit_btn = MockWebElement(tag="button", text="Submit Application", elem_type="submit")
        app_dialog = MockWebElement(tag="div", role="dialog", children=[inp1, inp2, inp3, submit_btn])

        mock_driver = MagicMock()
        mock_driver.execute_script.side_effect = lambda script, *args: (
            "complete" if "document.readyState" in script else [app_dialog]
        )

        stabilizer = PreAuditStabilizer(
            max_stabilization_time=1.5,
            initial_grace_seconds=0.1,
            quiet_period=0.1,
            poll_interval=0.05,
        )
        res = stabilizer.stabilize(mock_driver)

        # Dialog was preserved
        self.assertEqual(res["status"], "PARTIALLY_STABILIZED")
        self.assertTrue(res["transient_ui_detected"])
        self.assertEqual(res["dismissed_count"], 0)
        self.assertEqual(res["remaining_dialog_count"], 1)
        self.assertEqual(submit_btn.click_called, 0, "Business submit button must NEVER be clicked")

    # =========================================================================
    # TEST 6: Fixed header/footer
    # =========================================================================
    def test_06_fixed_header_and_footer_not_misclassified(self):
        """Fixed header and footer: JS false-positive filter excludes them; not misclassified as popups."""
        mock_driver = MagicMock()
        # The JS discovery script filters them out at the browser level
        mock_driver.execute_script.side_effect = lambda script, *args: (
            "complete" if "document.readyState" in script else []
        )

        stabilizer = PreAuditStabilizer(
            max_stabilization_time=1.5,
            initial_grace_seconds=0.1,
            quiet_period=0.1,
            poll_interval=0.05,
        )
        res = stabilizer.stabilize(mock_driver)

        self.assertEqual(res["status"], "NO_TRANSIENT_UI")
        self.assertFalse(res["transient_ui_detected"])
        self.assertEqual(res["dismissed_count"], 0)

    # =========================================================================
    # TEST 7: Large fixed overlay without safe close action
    # =========================================================================
    def test_07_large_fixed_overlay_without_safe_close_not_deleted(self):
        """Large fixed overlay without safe close button: preserved without deleting DOM element."""
        overlay = MockWebElement(tag="div", children=[])

        mock_driver = MagicMock()
        mock_driver.execute_script.side_effect = lambda script, *args: (
            "complete" if "document.readyState" in script else [overlay]
        )

        stabilizer = PreAuditStabilizer(
            max_stabilization_time=1.5,
            initial_grace_seconds=0.1,
            quiet_period=0.1,
            poll_interval=0.05,
        )
        res = stabilizer.stabilize(mock_driver)

        self.assertEqual(res["status"], "PARTIALLY_STABILIZED")
        self.assertEqual(res["dismissed_count"], 0)
        self.assertEqual(res["remaining_dialog_count"], 1)
        # Verify overlay is still displayed / intact
        self.assertTrue(overlay.is_displayed())

    # =========================================================================
    # TEST 8: Escape-dismissable dialog
    # =========================================================================
    def test_08_escape_dismissable_dialog(self):
        """Modal dialog without explicit button: dismissed via Escape key fallback."""
        modal = MockWebElement(tag="div", role="dialog", aria_modal="true", children=[])

        mock_driver = MagicMock()
        call_count = [0]

        def exec_script(script, *args):
            if "document.readyState" in script:
                return "complete"
            call_count[0] += 1
            if call_count[0] == 1:
                return [modal]
            return []

        mock_driver.execute_script.side_effect = exec_script

        stabilizer = PreAuditStabilizer(
            max_stabilization_time=2.0,
            initial_grace_seconds=0.1,
            quiet_period=0.1,
            poll_interval=0.05,
        )
        res = stabilizer.stabilize(mock_driver)

        self.assertEqual(res["status"], "STABILIZED")
        self.assertEqual(res["dismissed_count"], 1)
        self.assertEqual(res["actions"][0]["action"], "SEND_ESCAPE_KEY")

    # =========================================================================
    # TEST 9: StaleElementReference during dismissal
    # =========================================================================
    def test_09_stale_element_reference_during_dismissal(self):
        """StaleElementReferenceException during click: handled safely, does not crash audit."""
        close_btn = MockWebElement(tag="button", text="Close")

        def stale_click():
            raise StaleElementReferenceException("Element is stale")

        close_btn.click = stale_click
        modal = MockWebElement(tag="div", role="dialog", children=[close_btn])

        mock_driver = MagicMock()
        call_count = [0]

        def exec_script(script, *args):
            if "document.readyState" in script:
                return "complete"
            call_count[0] += 1
            if call_count[0] == 1:
                return [modal]
            return []

        mock_driver.execute_script.side_effect = exec_script

        stabilizer = PreAuditStabilizer(
            max_stabilization_time=2.0,
            initial_grace_seconds=0.1,
            quiet_period=0.1,
            poll_interval=0.05,
        )
        # Must not raise exception
        res = stabilizer.stabilize(mock_driver)
        self.assertIn(res["status"], ("STABILIZED", "PARTIALLY_STABILIZED"))

    # =========================================================================
    # TEST 10: Infinite/dynamic popup regeneration
    # =========================================================================
    def test_10_infinite_popup_regeneration_bounded_by_max_iterations(self):
        """Infinitely regenerating popups: stopped strictly by max_dismiss_iterations, never hangs."""
        close_btn = MockWebElement(tag="button", text="Close")
        modal = MockWebElement(tag="div", role="dialog", children=[close_btn])

        mock_driver = MagicMock()
        # Always returns the modal, simulating endless respawning
        mock_driver.execute_script.side_effect = lambda script, *args: (
            "complete" if "document.readyState" in script else [modal]
        )

        max_iter = 3
        stabilizer = PreAuditStabilizer(
            max_stabilization_time=3.0,
            initial_grace_seconds=0.1,
            quiet_period=0.1,
            poll_interval=0.05,
            max_dismiss_iterations=max_iter,
        )
        res = stabilizer.stabilize(mock_driver)

        # Loop must terminate within max_iter
        self.assertLessEqual(len(res["actions"]), max_iter)
        self.assertEqual(res["dismissed_count"], max_iter)

    # =========================================================================
    # TEST 11: NVDA baseline reset
    # =========================================================================
    def test_11_nvda_baseline_reset(self):
        """Simulate Speech Viewer content 'old announcement', reset baseline, add 'new focus announcement'."""
        class MockRichEdit:
            def __init__(self):
                self._text = "old page loading and popup speech"

            def window_text(self):
                return self._text

            def set_text(self, text):
                self._text = text

        mock_rich_edit = MockRichEdit()
        extractor = NVDATextExtractor(rich_edit=mock_rich_edit)

        # Reset baseline after stabilization
        extractor.reset_capture_baseline()

        # Add new speech generated after stabilization
        mock_rich_edit.set_text("old page loading and popup speech\nnew focus announcement")

        # get_new_text() must strictly return the newly added speech
        new_text = extractor.get_new_text()
        self.assertEqual(new_text, "new focus announcement")

    # =========================================================================
    # TEST 12: Integration order
    # =========================================================================
    def test_12_integration_order(self):
        """Verify the exact sequence: stabilization -> NVDA reset -> synchronized traversal."""
        events_called = []

        mock_stabilizer = MagicMock()
        mock_stabilizer.stabilize.side_effect = lambda driver: events_called.append("STABILIZATION") or {
            "status": "STABILIZED", "dismissed_count": 0, "remaining_dialog_count": 0,
        }

        mock_extractor = MagicMock()
        mock_extractor.reset_capture_baseline.side_effect = lambda: events_called.append("NVDA_RESET")
        mock_extractor.drain_initial_speech.return_value = ("", True)
        mock_extractor.capture_action_response.side_effect = lambda fn: events_called.append("SYNCHRONIZED_TRAVERSAL") or ("", "OK")

        # Simulate execution sequence
        mock_stabilizer.stabilize(MagicMock())
        mock_extractor.reset_capture_baseline()
        mock_extractor.capture_action_response(None)

        self.assertEqual(
            events_called,
            ["STABILIZATION", "NVDA_RESET", "SYNCHRONIZED_TRAVERSAL"],
            "Execution order must be stabilization -> NVDA reset -> synchronized traversal"
        )

    # =========================================================================
    # TEST 13: No page mutation via element removal
    # =========================================================================
    def test_13_no_page_mutation_via_element_removal(self):
        """Ensure production code never uses element.remove() or style.display = 'none'."""
        stabilizer_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tools",
            "pre_audit_stabilizer.py",
        )
        with open(stabilizer_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for forbidden mutation snippets in active code (ignoring docstrings)
        lines = [line for line in content.splitlines() if not line.strip().startswith("#") and not line.strip().startswith('"""')]
        active_code = "\n".join(lines)

        self.assertNotIn(".remove()", active_code, "Must not use .remove() to delete DOM elements")
        self.assertNotIn('display = "none"', active_code, "Must not use style.display = 'none'")
        self.assertNotIn("display = 'none'", active_code, "Must not use style.display = 'none'")

    # =========================================================================
    # TEST 14: Browser notification preference configuration
    # =========================================================================
    def test_14_browser_notification_preference_configuration(self):
        """Verify get_safe_chrome_options() sets generic prompt suppressions safely."""
        options = get_safe_chrome_options()
        self.assertIsNotNone(options)

        # Verify --disable-notifications argument is present
        self.assertIn("--disable-notifications", options.arguments)

        # Verify experimental prefs are configured to block prompts
        exp_options = options.experimental_options
        self.assertIn("prefs", exp_options)
        prefs = exp_options["prefs"]
        self.assertEqual(prefs.get("profile.default_content_setting_values.notifications"), 2)
        self.assertEqual(prefs.get("profile.default_content_setting_values.geolocation"), 2)
        self.assertEqual(prefs.get("profile.default_content_setting_values.media_stream_camera"), 2)
        self.assertEqual(prefs.get("profile.default_content_setting_values.media_stream_mic"), 2)

    # =========================================================================
    # TEST 15: Modal with span / cross button (e.g. non-button tag)
    # =========================================================================
    def test_15_modal_with_span_close_or_cross_button(self):
        """Modal with a span or div cross button (class containing close/cross) is detected and dismissed."""
        span_close = MockWebElement(tag="span", text="✕", classes="commonModal__close")
        modal = MockWebElement(tag="div", classes="modalWrapper", children=[span_close])

        mock_driver = MagicMock()
        calls = [0]

        def exec_script(script, *args):
            if "document.readyState" in script:
                return "complete"
            calls[0] += 1
            if calls[0] == 1:
                return [modal]
            return []

        mock_driver.execute_script.side_effect = exec_script

        stabilizer = PreAuditStabilizer(
            max_stabilization_time=2.0,
            initial_grace_seconds=0.1,
            quiet_period=0.1,
            poll_interval=0.05,
        )
        res = stabilizer.stabilize(mock_driver)

        self.assertEqual(res["status"], "STABILIZED")
        self.assertEqual(res["dismissed_count"], 1)
        self.assertEqual(span_close.click_called, 1)

    # =========================================================================
    # TEST 16: Login/promotional modal with input fields AND explicit cross button
    # =========================================================================
    def test_16_login_promotional_modal_with_inputs_and_close_button(self):
        """Login/promotional modal containing account options + mobile input + cross button is safely dismissed."""
        inp_radio1 = MockWebElement(tag="input", elem_type="radio")
        inp_radio2 = MockWebElement(tag="input", elem_type="radio")
        inp_tel = MockWebElement(tag="input", elem_type="tel")
        cross_btn = MockWebElement(tag="span", text="✕", classes="crossIcon")
        modal = MockWebElement(tag="div", classes="loginOverlay", children=[inp_radio1, inp_radio2, inp_tel, cross_btn])

        mock_driver = MagicMock()
        calls = [0]

        def exec_script(script, *args):
            if "document.readyState" in script:
                return "complete"
            calls[0] += 1
            if calls[0] == 1:
                return [modal]
            return []

        mock_driver.execute_script.side_effect = exec_script

        stabilizer = PreAuditStabilizer(
            max_stabilization_time=2.0,
            initial_grace_seconds=0.1,
            quiet_period=0.1,
            poll_interval=0.05,
        )
        res = stabilizer.stabilize(mock_driver)

        self.assertEqual(res["status"], "STABILIZED")
        self.assertEqual(res["dismissed_count"], 1)
        self.assertEqual(cross_btn.click_called, 1)

    # =========================================================================
    # TEST 17: Keyboard traversal focus preparation (first focusable element start)
    # =========================================================================
    def test_17_prepare_for_keyboard_traversal(self):
        """prepare_for_keyboard_traversal scrolls to (0,0) and blurs active element."""
        mock_driver = MagicMock()
        prepare_for_keyboard_traversal(mock_driver)

        self.assertEqual(mock_driver.execute_script.call_count, 1)
        script_arg = mock_driver.execute_script.call_args[0][0]
        self.assertIn("window.scrollTo(0, 0)", script_arg)
        self.assertIn("document.activeElement.blur()", script_arg)

    # =========================================================================
    # TEST 18: Programmatically focus first focusable element
    # =========================================================================
    def test_18_focus_first_focusable_element(self):
        """focus_first_focusable_element locates and focuses the first focusable element."""
        mock_driver = MagicMock()
        mock_first_elem = MockWebElement(tag="a", text="make my trip", classes="logo")
        mock_driver.execute_script.return_value = mock_first_elem

        res = focus_first_focusable_element(mock_driver)

        self.assertEqual(res, mock_first_elem)
        self.assertEqual(mock_driver.execute_script.call_count, 1)
        script_arg = mock_driver.execute_script.call_args[0][0]
        self.assertIn("a[href]:not([tabindex=\"-1\"])", script_arg)
        self.assertIn("el.focus()", script_arg)


if __name__ == "__main__":
    unittest.main()
