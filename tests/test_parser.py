import unittest
import sys
import os

# Add root directory to path so tests can run standalone
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.nvda_parser import NVDAParser, AccessibilityEvent
from tools.nvda_filter import NVDAFilter
from synchronisation.sync import compare_selenium_and_nvda


class TestNVDAParserGeneric(unittest.TestCase):

    def setUp(self):
        self.parser = NVDAParser()
        self.filter = NVDAFilter()

    def test_submit_button(self):
        events = self.parser.parse(["Submit button"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Submit")
        self.assertEqual(events[0].role, "button")
        self.assertEqual(events[0].attributes, [])
        self.assertEqual(events[0].raw_text, "Submit button")

    def test_username_edit_blank(self):
        events = self.parser.parse(["Username edit blank"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Username")
        self.assertEqual(events[0].role, "edit")
        self.assertIn("blank", events[0].attributes)

    def test_country_combo_box_expanded(self):
        events = self.parser.parse(["Country combo box India expanded"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Country")
        self.assertEqual(events[0].role, "combo box")
        self.assertEqual(events[0].value, "India")
        self.assertIn("expanded", events[0].attributes)

    def test_search_in_combo_box_generic(self):
        """Test that former Amazon test case works completely generically without hardcoded rules."""
        events = self.parser.parse(["Search in combo box All Categories collapsed"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Search in")
        self.assertEqual(events[0].role, "combo box")
        self.assertEqual(events[0].value, "All Categories")
        self.assertIn("collapsed", events[0].attributes)

    def test_remember_me_checkbox_checked(self):
        events = self.parser.parse(["Remember me checkbox checked"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Remember me")
        self.assertEqual(events[0].role, "checkbox")
        self.assertIn("checked", events[0].attributes)

    def test_radio_button(self):
        events = self.parser.parse(["Male radio button checked"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Male")
        self.assertEqual(events[0].role, "radio button")
        self.assertIn("checked", events[0].attributes)

    def test_switch(self):
        events = self.parser.parse(["Dark mode switch checked"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Dark mode")
        self.assertEqual(events[0].role, "switch")
        self.assertIn("checked", events[0].attributes)

    def test_slider(self):
        events = self.parser.parse(["Volume slider 80%"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Volume")
        self.assertEqual(events[0].role, "slider")
        self.assertEqual(events[0].value, "80%")

    def test_heading_level_extraction(self):
        events = self.parser.parse(["Top Stories heading level 2"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Top Stories")
        self.assertEqual(events[0].role, "heading")
        self.assertEqual(events[0].level, 2)

    def test_navigation_landmark(self):
        events = self.parser.parse(["Navigation landmark"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Navigation")
        self.assertEqual(events[0].role, "landmark")

    def test_main_landmark(self):
        events = self.parser.parse(["Main landmark"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Main")
        self.assertEqual(events[0].role, "landmark")

    def test_search_landmark(self):
        events = self.parser.parse(["Search landmark"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Search")
        self.assertEqual(events[0].role, "landmark")

    def test_banner_landmark(self):
        events = self.parser.parse(["Banner landmark"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Banner")
        self.assertEqual(events[0].role, "landmark")

    def test_graphic_link(self):
        events = self.parser.parse(["Company logo graphic link"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Company logo")
        self.assertEqual(events[0].role, "graphic link")

    def test_open_menu_button_collapsed(self):
        events = self.parser.parse(["Options menu button collapsed"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Options")
        self.assertEqual(events[0].role, "menu button")
        self.assertIn("collapsed", events[0].attributes)

    def test_unlabelled_graphic_link_with_system_description(self):
        """Test graphic link with NVDA helper description: 'visited same page Unlabelled graphic logo. To get missing image descriptions, open the context menu. link'"""
        raw = "visited same page Unlabelled graphic logo. To get missing image descriptions, open the context menu. link"
        events = self.parser.parse([raw])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].role, "graphic link")
        self.assertIn("logo", events[0].name)
        self.assertIn("visited", events[0].attributes)
        self.assertIn("same page", events[0].attributes)
        self.assertIsNotNone(events[0].description)

    def test_link_unlabelled_graphic(self):
        events = self.parser.parse(["link Unlabelled graphic logo"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].role, "graphic link")
        self.assertEqual(events[0].name, "logo")

    def test_tab_search_button(self):
        events = self.parser.parse(["Tab search button collapsed"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].role, "button")
        self.assertEqual(events[0].name, "Tab search")
        self.assertIn("collapsed", events[0].attributes)

    def test_bookmark_this_tab_button(self):
        events = self.parser.parse(["Bookmark this tab button"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].role, "button")
        self.assertEqual(events[0].name, "Bookmark this tab")

    def test_search_edit_has_auto_complete_blank(self):
        events = self.parser.parse(["Search Amazon.in edit has auto complete blank"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Search Amazon.in")
        self.assertEqual(events[0].role, "edit")
        self.assertIn("has auto complete", events[0].attributes)
        self.assertIn("blank", events[0].attributes)

    def test_next_page_link_unavailable(self):
        events = self.parser.parse(["Next page link unavailable"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Next page")
        self.assertEqual(events[0].role, "link")
        self.assertIn("unavailable", events[0].attributes)

    def test_multi_line_required_edit(self):
        events = self.parser.parse(["Comments edit multi line required"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Comments")
        self.assertEqual(events[0].role, "edit")
        self.assertIn("multi line", events[0].attributes)
        self.assertIn("required", events[0].attributes)

    def test_dialog_alert(self):
        events = self.parser.parse(["Session Expired alert"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Session Expired")
        self.assertEqual(events[0].role, "alert")

    def test_punctuation_tolerance(self):
        events = self.parser.parse(["Submit button,"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Submit")
        self.assertEqual(events[0].role, "button")

    def test_makaut_test_announcements(self):
        """Test real announcements from the test environment to ensure generic correctness."""
        e1 = self.parser.parse(["STUDENT Click here to Login Portal visited same page link"])
        self.assertEqual(len(e1), 1)
        self.assertEqual(e1[0].role, "link")
        self.assertEqual(e1[0].name, "STUDENT Click here to Login Portal")
        self.assertIn("visited", e1[0].attributes)
        self.assertIn("same page", e1[0].attributes)

        e2 = self.parser.parse(["RESULT Click Here to See Result Details .... link"])
        self.assertEqual(len(e2), 1)
        self.assertEqual(e2[0].role, "link")
        self.assertEqual(e2[0].name, "RESULT Click Here to See Result Details ....")

    def test_unknown_announcement(self):
        events = self.parser.parse(["Just some informational text without role"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Just some informational text without role")
        self.assertEqual(events[0].role, "unknown")
        self.assertIsNone(events[0].level)

    def test_filter_single_character_preservation(self):
        """Ensure valid single-character items (like 'X' close button or '1' link) are NOT discarded by filter."""
        cleaned = self.filter.clean("X\ntab\nClose button\nspace\n1")
        self.assertIn("X", cleaned)
        self.assertIn("Close button", cleaned)
        self.assertIn("1", cleaned)
        self.assertNotIn("tab", cleaned)
        self.assertNotIn("space", cleaned)

    def test_selenium_nvda_comparison_exact_match(self):
        selenium_details = {
            "tag": "button",
            "text": "Submit",
            "role": None,
            "aria-label": None,
            "expected_roles": ["button"],
        }
        event = AccessibilityEvent(name="Submit", role="button")
        comp = compare_selenium_and_nvda(selenium_details, event)
        self.assertTrue(comp["name_match"])
        self.assertTrue(comp["role_match"])
        self.assertEqual(comp["status"], "MATCH")

    def test_selenium_nvda_comparison_unlabelled_graphic(self):
        selenium_details = {
            "tag": "a",
            "text": "",
            "role": None,
            "aria-label": None,
            "expected_roles": ["link", "graphic link"],
        }
        event = AccessibilityEvent(name="logo", role="graphic link")
        comp = compare_selenium_and_nvda(selenium_details, event)
        self.assertFalse(comp["name_match"])
        self.assertTrue(comp["role_match"])
        self.assertEqual(comp["status"], "ROLE_MATCH_NAME_UNLABELLED")


if __name__ == "__main__":
    unittest.main()
