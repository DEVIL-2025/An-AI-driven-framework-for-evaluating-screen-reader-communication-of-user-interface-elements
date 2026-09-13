import unittest
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.nvda_tool import NVDATextExtractor, NVDAEvidencePhase
from tools.nvda_filter import NVDAFilter
from tools.nvda_parser import NVDAParser
from synchronisation.sync import (
    capture_synchronized_element,
    find_matching_nvda_event,
    compare_selenium_and_nvda,
)
from tools.evidence_correlator import assemble_unified_evidence_package


class MockRichEdit:
    """Mock pywinauto edit control simulating text stream over time."""

    def __init__(self, initial_text=""):
        self._text = initial_text

    def window_text(self):
        return self._text

    def append_text(self, new_text):
        self._text += new_text

    def set_text(self, text):
        self._text = text


class TestNVDASynchronizationLifecycle(unittest.TestCase):
    """
    Automated test suite verifying the 8-state NVDA traversal synchronization
    and pre-traversal page initialization speech draining pipeline.
    """

    def setUp(self):
        self.filter = NVDAFilter()
        self.parser = NVDAParser()

    # Scenario 1: Pre-traversal speech buffer contains large page reading
    def test_pre_traversal_speech_buffered_and_drained(self):
        mock_edit = MockRichEdit(
            "banner landmark\nUniversity Main Website\nMEMBER'S AREA\nLETTERS & NOTICES\n"
        )
        extractor = NVDATextExtractor(rich_edit=mock_edit)
        
        # Drain initial speech
        initial_speech, is_settled = extractor.drain_initial_speech(
            max_timeout=0.2, settle_interval=0.05, poll_interval=0.01
        )
        self.assertIn("University Main Website", initial_speech)
        self.assertIn("LETTERS & NOTICES", initial_speech)
        self.assertTrue(is_settled)
        
        # After draining, baseline is established; fresh text should be empty
        fresh_speech = extractor.get_new_text()
        self.assertEqual(fresh_speech, "")

    # Scenario 2: Traversal step 1 after draining receives only fresh keystroke speech
    def test_step_1_receives_only_fresh_speech_after_drain(self):
        mock_edit = MockRichEdit("banner landmark\nMain heading level 1\nNavigation landmark\n")
        extractor = NVDATextExtractor(rich_edit=mock_edit)
        
        # Drain pre-traversal speech
        initial_speech, _ = extractor.drain_initial_speech(max_timeout=0.1, settle_interval=0.02)
        
        # Action TAB triggers fresh announcement
        def tab_action():
            mock_edit.append_text("Search edit blank\n")

        speech, status = extractor.capture_action_response(
            tab_action, timeout=0.2, poll_interval=0.01, settle_interval=0.02
        )
        self.assertEqual(status, "OK")
        self.assertIn("Search edit blank", speech)
        self.assertNotIn("banner landmark", speech)
        self.assertNotIn("Main heading level 1", speech)

    # Scenario 3: Traversal step 2 receives only step 2 speech
    def test_step_2_receives_only_step_2_speech(self):
        mock_edit = MockRichEdit("")
        extractor = NVDATextExtractor(rich_edit=mock_edit)
        extractor.mark_baseline()

        # Step 1
        def tab_1():
            mock_edit.append_text("First link\n")

        s1, st1 = extractor.capture_action_response(tab_1, timeout=0.1, poll_interval=0.01)
        self.assertIn("First link", s1)

        # Step 2
        def tab_2():
            mock_edit.append_text("Second button\n")

        s2, st2 = extractor.capture_action_response(tab_2, timeout=0.1, poll_interval=0.01)
        self.assertEqual(st2, "OK")
        self.assertIn("Second button", s2)
        self.assertNotIn("First link", s2)

    # Scenario 4: Multiple rapid NVDA speech events during page load
    def test_rapid_speech_events_settle_adaptively(self):
        mock_edit = MockRichEdit("Part 1: Header\n")
        extractor = NVDATextExtractor(rich_edit=mock_edit)

        def slowly_stream_speech():
            time.sleep(0.02)
            mock_edit.append_text("Part 2: Body text\n")
            time.sleep(0.02)
            mock_edit.append_text("Part 3: Footer\n")

        import threading
        t = threading.Thread(target=slowly_stream_speech)
        t.start()

        initial_speech, is_settled = extractor.drain_initial_speech(
            max_timeout=0.5, settle_interval=0.08, poll_interval=0.01
        )
        t.join()

        self.assertIn("Part 1: Header", initial_speech)
        self.assertIn("Part 2: Body text", initial_speech)
        self.assertIn("Part 3: Footer", initial_speech)
        self.assertTrue(is_settled)

    # Scenario 5: Silent focusable element (timeout handling)
    def test_silent_focusable_element_timeout(self):
        mock_edit = MockRichEdit("")
        extractor = NVDATextExtractor(rich_edit=mock_edit)
        extractor.mark_baseline()

        def silent_tab():
            pass

        speech, status = extractor.capture_action_response(
            silent_tab, timeout=0.05, poll_interval=0.01, settle_interval=0.01
        )
        self.assertEqual(status, "NVDA_CAPTURE_TIMEOUT")
        self.assertEqual(speech, "")

        selenium_details = {
            "tag": "div",
            "id": "focusable-container",
            "name": "",
            "text": "",
            "role": None,
            "type": None,
            "tabindex": "0",
            "aria-label": None,
            "title": None,
            "alt": None,
            "placeholder": None,
            "value": None,
            "href": None,
            "class": "custom-box",
            "expected_roles": [],
        }
        res = capture_synchronized_element(
            extractor, self.filter, self.parser, selenium_details,
            captured_speech=speech, capture_status=status
        )
        self.assertEqual(res["comparison"]["status"], "NVDA_CAPTURE_TIMEOUT")
        self.assertIsNone(res["nvda"])
        self.assertEqual(res["selenium"]["id"], "focusable-container")

    # Scenario 6: Re-focusing an element produces fresh announcement
    def test_refocusing_element_produces_fresh_announcement(self):
        mock_edit = MockRichEdit("")
        extractor = NVDATextExtractor(rich_edit=mock_edit)
        extractor.mark_baseline()

        # Forward tab focuses button
        extractor.capture_action_response(
            lambda: mock_edit.append_text("Submit button\n"),
            timeout=0.1, poll_interval=0.01
        )

        # Tab next to link
        extractor.capture_action_response(
            lambda: mock_edit.append_text("Help link\n"),
            timeout=0.1, poll_interval=0.01
        )

        # Shift+Tab back to button
        speech, status = extractor.capture_action_response(
            lambda: mock_edit.append_text("Submit button\n"),
            timeout=0.1, poll_interval=0.01
        )
        self.assertEqual(status, "OK")
        self.assertIn("Submit button", speech)
        self.assertNotIn("Help link", speech)

    # Scenario 7: Backward Shift+Tab traversal after forward traversal
    def test_backward_traversal_boundaries_independent(self):
        mock_edit = MockRichEdit("")
        extractor = NVDATextExtractor(rich_edit=mock_edit)
        extractor.mark_baseline()

        # Forward
        s_fwd, _ = extractor.capture_action_response(
            lambda: mock_edit.append_text("Link 1\n"),
            timeout=0.1, poll_interval=0.01
        )
        self.assertEqual(s_fwd.strip(), "Link 1")

        # Backward
        s_bwd, _ = extractor.capture_action_response(
            lambda: mock_edit.append_text("Back to Start link\n"),
            timeout=0.1, poll_interval=0.01
        )
        self.assertEqual(s_bwd.strip(), "Back to Start link")
        self.assertNotIn("Link 1", s_bwd)

    # Scenario 8: Non-empty Speech Viewer before audit starts
    def test_preexisting_buffer_drained_at_start(self):
        mock_edit = MockRichEdit("Old text from 10 minutes ago\nOther application speech\n")
        extractor = NVDATextExtractor(rich_edit=mock_edit)

        drained, _ = extractor.drain_initial_speech(max_timeout=0.05, settle_interval=0.01)
        self.assertIn("Old text from 10 minutes ago", drained)

        speech, _ = extractor.capture_action_response(
            lambda: mock_edit.append_text("New element edit\n"),
            timeout=0.1, poll_interval=0.01
        )
        self.assertEqual(speech.strip(), "New element edit")

    # Scenario 9: Multi-line announcement for a single element
    def test_multiline_announcement_settles_and_parses_together(self):
        mock_edit = MockRichEdit("")
        extractor = NVDATextExtractor(rich_edit=mock_edit)
        extractor.mark_baseline()

        def emit_multiline():
            mock_edit.append_text("Terms and Conditions checkbox not checked\n")
            mock_edit.append_text("required\n")

        speech, status = extractor.capture_action_response(
            emit_multiline, timeout=0.2, poll_interval=0.01, settle_interval=0.03
        )
        self.assertEqual(status, "OK")
        cleaned = self.filter.clean(speech)
        events = self.parser.parse(cleaned)
        self.assertTrue(len(events) >= 1)
        self.assertEqual(events[0].name, "Terms and Conditions")
        self.assertEqual(events[0].role, "checkbox")

    # Scenario 10: Dynamic content announcement
    def test_dynamic_announcement_captured_causally(self):
        mock_edit = MockRichEdit("")
        extractor = NVDATextExtractor(rich_edit=mock_edit)
        extractor.mark_baseline()

        def dynamic_action():
            mock_edit.append_text("Alert: Session expiring in 2 minutes\nOK button\n")

        speech, status = extractor.capture_action_response(
            dynamic_action, timeout=0.1, poll_interval=0.01
        )
        self.assertIn("Alert: Session expiring", speech)
        self.assertIn("OK button", speech)

    # Scenario 11: Slow-loading page settling within max_settle_timeout
    def test_slow_page_load_settles_within_max_timeout(self):
        mock_edit = MockRichEdit("Initial banner\n")
        extractor = NVDATextExtractor(rich_edit=mock_edit)

        initial_speech, is_settled = extractor.drain_initial_speech(
            max_timeout=0.1, settle_interval=0.02, poll_interval=0.01
        )
        self.assertTrue(is_settled)
        self.assertIn("Initial banner", initial_speech)

    # Scenario 12: Page never stops speaking (settle timeout fallback)
    def test_page_infinite_speech_terminates_at_max_timeout(self):
        mock_edit = MockRichEdit("")
        extractor = NVDATextExtractor(rich_edit=mock_edit)

        stop_flag = False
        def continuous_speech():
            while not stop_flag:
                mock_edit.append_text("continuous ticker item...\n")
                time.sleep(0.01)

        import threading
        t = threading.Thread(target=continuous_speech)
        t.start()

        initial_speech, is_settled = extractor.drain_initial_speech(
            max_timeout=0.08, settle_interval=0.05, poll_interval=0.01
        )
        stop_flag = True
        t.join()

        self.assertFalse(is_settled)
        self.assertTrue(len(initial_speech) > 0)
        self.assertIsNotNone(extractor.last_mark)

    # Scenario 13: Correlation summary and initialization metadata validation
    def test_initialization_block_in_unified_package(self):
        dom_snapshot = {
            "headings": [],
            "landmarks": [],
            "interactive_elements": [
                {
                    "tag": "a",
                    "id": "nav-link",
                    "name": "",
                    "type": None,
                    "text": "About Us",
                    "href": "https://example.com/about",
                    "role": None,
                    "tabindex": 0,
                    "aria_label": None,
                    "parent_section": "Navigation",
                    "parent_landmark": "navigation",
                    "nearest_heading": None,
                    "nearest_heading_level": None,
                    "surrounding_text": "Header bar",
                    "css_path": "nav > a#nav-link",
                }
            ],
        }

        synchronized_output = {
            "url": "https://example.com/test",
            "initialization": {
                "phase": "PAGE_INITIALIZATION",
                "raw_speech": "banner landmark\nExample Home\n",
                "events": [{"name": "Example Home", "role": "link"}],
                "settled": True,
            },
            "forward": [
                {
                    "step": 1,
                    "selenium": {
                        "tag": "a",
                        "id": "nav-link",
                        "name": "",
                        "text": "About Us",
                        "role": None,
                        "type": None,
                        "tabindex": "0",
                        "aria-label": None,
                        "title": None,
                        "alt": None,
                        "placeholder": None,
                        "value": None,
                        "href": "https://example.com/about",
                        "class": "nav",
                        "expected_roles": ["link"],
                    },
                    "nvda": {
                        "name": "About Us",
                        "role": "link",
                        "value": "",
                        "attributes": [],
                        "raw_text": "About Us link",
                    },
                    "comparison": {
                        "name_match": True,
                        "role_match": True,
                        "status": "MATCH",
                    },
                }
            ],
            "backward": [],
        }

        unified = assemble_unified_evidence_package(
            url="https://example.com/test",
            synchronized_output=synchronized_output,
            dom_snapshot=dom_snapshot,
            screenshot_metadata={"status": "SKIPPED"},
        )

        self.assertIn("initialization", unified["synchronized_evidence"])
        init_ev = unified["synchronized_evidence"]["initialization"]
        self.assertEqual(init_ev["phase"], "PAGE_INITIALIZATION")
        self.assertEqual(init_ev["settled"], True)
        self.assertIn("banner landmark", init_ev["raw_speech"])
        self.assertEqual(unified["correlation_summary"]["matched_count"], 1)


if __name__ == "__main__":
    unittest.main()
