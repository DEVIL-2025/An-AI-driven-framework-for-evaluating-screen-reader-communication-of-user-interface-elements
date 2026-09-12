"""
Unit tests for tools/evidence_correlator.py (Phase 3A).
Tests correlation algorithms, multi-signal matching, ambiguity handling,
context attachment, package schema, and evidence-only non-judgment guarantees.
"""

import copy
import unittest
from tools.evidence_correlator import (
    calculate_candidate_score,
    correlate_single_element,
    correlate_direction_elements,
    assemble_unified_evidence_package,
    extract_dom_context,
    normalize_text,
    normalize_href,
)


class TestEvidenceCorrelator(unittest.TestCase):

    def setUp(self):
        # Sample synthetic DOM interactive elements
        self.sample_dom_elements = [
            {
                "tag": "a",
                "id": "nav-home",
                "name": "",
                "type": None,
                "text": "Home Page",
                "href": "https://example.com/",
                "role": None,
                "tabindex": 0,
                "aria_label": "Home",
                "aria_labelledby": None,
                "aria_labelledby_text": None,
                "aria_describedby": None,
                "aria_expanded": None,
                "aria_hidden": False,
                "parent_section_id": "sec-header",
                "parent_section": "Site Header",
                "parent_landmark": "banner",
                "nearest_heading": "Welcome",
                "nearest_heading_level": 1,
                "surrounding_text": "Main navigation area",
                "css_path": "header > nav > a:first-child",
            },
            {
                "tag": "button",
                "id": "btn-search",
                "name": "search_action",
                "type": "submit",
                "text": "Search Products",
                "href": None,
                "role": "button",
                "tabindex": 0,
                "aria_label": None,
                "aria_labelledby": None,
                "aria_labelledby_text": None,
                "aria_describedby": None,
                "aria_expanded": None,
                "aria_hidden": False,
                "parent_section_id": "sec-search",
                "parent_section": "Search Bar",
                "parent_landmark": "search",
                "nearest_heading": "Find Items",
                "nearest_heading_level": 2,
                "surrounding_text": "Search input and submit button",
                "css_path": "form#search-form > button",
            },
            {
                "tag": "button",
                "id": "btn-cancel-1",
                "name": "cancel",
                "type": "button",
                "text": "Cancel",
                "href": None,
                "role": "button",
                "tabindex": 0,
                "aria_label": None,
                "aria_labelledby": None,
                "aria_labelledby_text": None,
                "aria_describedby": None,
                "aria_expanded": None,
                "aria_hidden": False,
                "parent_section_id": "modal-1",
                "parent_section": "Modal Dialog",
                "parent_landmark": None,
                "nearest_heading": "Confirm Action",
                "nearest_heading_level": 2,
                "surrounding_text": "Do you want to proceed?",
                "css_path": "div.modal > button:first-child",
            },
            {
                "tag": "button",
                "id": "btn-cancel-2",
                "name": "cancel",
                "type": "button",
                "text": "Cancel",
                "href": None,
                "role": "button",
                "tabindex": 0,
                "aria_label": None,
                "aria_labelledby": None,
                "aria_labelledby_text": None,
                "aria_describedby": None,
                "aria_expanded": None,
                "aria_hidden": False,
                "parent_section_id": "drawer-1",
                "parent_section": "Slide Drawer",
                "parent_landmark": None,
                "nearest_heading": "Drawer Options",
                "nearest_heading_level": 3,
                "surrounding_text": "Drawer footer buttons",
                "css_path": "div.drawer > button:first-child",
            },
        ]

    def test_exact_strong_match(self):
        """1. Exact strong match using matching tag, matching ID, and matching text."""
        selenium_el = {
            "tag": "button",
            "id": "btn-search",
            "name": "search_action",
            "type": "submit",
            "text": "Search Products",
            "class": "btn btn-primary",
        }
        res = correlate_single_element(selenium_el, self.sample_dom_elements)

        self.assertEqual(res["status"], "MATCHED")
        self.assertGreaterEqual(res["confidence"], 0.85)
        self.assertEqual(res["dom_element_index"], 1)
        self.assertIsNotNone(res["dom_context"])
        self.assertEqual(res["dom_context"]["parent_landmark"], "search")
        self.assertEqual(res["dom_context"]["nearest_heading"], "Find Items")

    def test_match_using_multiple_weaker_signals(self):
        """2. Match using weaker signals when ID is empty (text + href + tag match)."""
        selenium_el = {
            "tag": "a",
            "id": "",  # Empty ID
            "name": "",
            "type": None,
            "text": "Home Page",
            "href": "https://example.com",
            "class": "nav-link",
        }
        res = correlate_single_element(selenium_el, self.sample_dom_elements)

        self.assertEqual(res["status"], "MATCHED")
        self.assertGreaterEqual(res["confidence"], 0.70)
        self.assertEqual(res["dom_element_index"], 0)
        self.assertEqual(res["dom_context"]["parent_section"], "Site Header")

    def test_duplicate_candidates_resulting_in_ambiguous(self):
        """3. Duplicate candidates with identical text, tag, and type produce AMBIGUOUS."""
        # Focus element has no unique ID or distinctive href
        selenium_el = {
            "tag": "button",
            "id": "",  # No ID to separate the two cancel buttons
            "name": "cancel",
            "type": "button",
            "text": "Cancel",
            "class": "btn btn-default",
        }
        res = correlate_single_element(selenium_el, self.sample_dom_elements)

        self.assertEqual(res["status"], "AMBIGUOUS")
        self.assertGreaterEqual(res["confidence"], 0.55)
        self.assertIsNone(res["dom_element_index"])
        self.assertIsNone(res["dom_context"])
        # Both cancel buttons (indices 2 and 3) should be listed
        self.assertIn(2, res["candidate_indices"])
        self.assertIn(3, res["candidate_indices"])

    def test_no_candidate_resulting_in_unmatched(self):
        """4. Element not present in the DOM snapshot reports UNMATCHED."""
        selenium_el = {
            "tag": "input",
            "id": "email-input",
            "name": "email",
            "type": "email",
            "text": "",
        }
        res = correlate_single_element(selenium_el, self.sample_dom_elements)

        self.assertEqual(res["status"], "UNMATCHED")
        self.assertEqual(res["confidence"], 0.0)
        self.assertIsNone(res["dom_element_index"])
        self.assertIsNone(res["dom_context"])
        self.assertEqual(res["candidate_indices"], [])

    def test_empty_ids_and_text_handled_correctly(self):
        """5. Graphic links/buttons with empty IDs and text are not falsely matched or crash."""
        dom_with_icon = [
            {
                "tag": "a",
                "id": "",
                "name": "",
                "type": None,
                "text": "",
                "href": "https://example.com/logo",
                "class": "brand-logo",
                "css_path": "header > a.brand-logo",
            },
            {
                "tag": "a",
                "id": "",
                "name": "",
                "type": None,
                "text": "",
                "href": "https://example.com/other",
                "class": "social-icon",
                "css_path": "footer > a.social-icon",
            }
        ]

        selenium_el = {
            "tag": "a",
            "id": "",
            "name": "",
            "text": "",
            "href": "https://example.com/logo",
            "class": "brand-logo",
        }

        res = correlate_single_element(selenium_el, dom_with_icon)
        self.assertEqual(res["status"], "MATCHED")
        self.assertEqual(res["dom_element_index"], 0)

    def test_css_path_is_not_used_as_sole_identity(self):
        """6. Elements with matching CSS path but conflicting tags or IDs must NOT match."""
        selenium_el = {
            "tag": "input",
            "id": "other-id",
            "text": "Submit",
            "css_path": "form#search-form > button",  # Same CSS path as button in DOM
        }
        # Incompatible tag (input vs button)
        score = calculate_candidate_score(selenium_el, self.sample_dom_elements[1])
        self.assertEqual(score, 0.0)

    def test_forward_and_backward_evidence_preserved(self):
        """7 & 8. Forward and backward evidence steps are correlated and fully preserved."""
        sync_output = {
            "url": "https://example.com",
            "forward": [
                {
                    "step": 1,
                    "selenium": {"tag": "a", "text": "Home Page", "href": "https://example.com/"},
                    "nvda": {"role": "link", "name": "Home Page"},
                    "comparison": {"status": "MATCH"},
                }
            ],
            "backward": [
                {
                    "step": 1,
                    "selenium": {"tag": "button", "text": "Search Products", "type": "submit"},
                    "nvda": {"role": "button", "name": "Search Products"},
                    "comparison": {"status": "MATCH"},
                }
            ]
        }

        dom_snapshot = {
            "interactive_elements": self.sample_dom_elements,
            "landmarks": [],
            "headings": [],
            "sections": [],
        }

        screenshot_meta = {
            "status": "SUCCESS",
            "path": "webpage_screenshot.png",
            "format": "png",
            "width": 1900,
            "height": 1080,
            "capture_mode": "FULL_PAGE",
            "fixed_position_elements_possible": False,
        }

        pkg = assemble_unified_evidence_package(
            url="https://example.com",
            synchronized_output=sync_output,
            dom_snapshot=dom_snapshot,
            screenshot_metadata=screenshot_meta,
        )

        # Structure checks
        self.assertEqual(pkg["schema_version"], "1.0")
        self.assertEqual(pkg["url"], "https://example.com")
        self.assertEqual(len(pkg["synchronized_evidence"]["forward"]), 1)
        self.assertEqual(len(pkg["synchronized_evidence"]["backward"]), 1)
        self.assertEqual(len(pkg["correlated_elements"]), 2)

        # Forward element verified
        f_el = pkg["correlated_elements"][0]
        self.assertEqual(f_el["direction"], "forward")
        self.assertEqual(f_el["step"], 1)
        self.assertEqual(f_el["correlation"]["status"], "MATCHED")
        self.assertEqual(f_el["dom_context"]["nearest_heading"], "Welcome")
        self.assertEqual(f_el["synchronized_element"]["nvda"]["name"], "Home Page")

        # Backward element verified
        b_el = pkg["correlated_elements"][1]
        self.assertEqual(b_el["direction"], "backward")
        self.assertEqual(b_el["step"], 1)
        self.assertEqual(b_el["correlation"]["status"], "MATCHED")
        self.assertEqual(b_el["dom_context"]["nearest_heading"], "Find Items")

    def test_dom_contextual_information_attached(self):
        """9. Correlated element has full structural DOM context attached."""
        ctx = extract_dom_context(self.sample_dom_elements[0])
        self.assertEqual(ctx["parent_landmark"], "banner")
        self.assertEqual(ctx["parent_section"], "Site Header")
        self.assertEqual(ctx["parent_section_id"], "sec-header")
        self.assertEqual(ctx["nearest_heading"], "Welcome")
        self.assertEqual(ctx["nearest_heading_level"], 1)
        self.assertEqual(ctx["surrounding_text"], "Main navigation area")

    def test_screenshot_metadata_included_in_package(self):
        """10. Screenshot visual evidence is referenced cleanly in the package."""
        screenshot_meta = {
            "status": "SUCCESS",
            "path": "custom_screenshot.png",
            "format": "png",
            "width": 1440,
            "height": 2800,
            "capture_mode": "FULL_PAGE",
            "fixed_position_elements_possible": True,
        }
        pkg = assemble_unified_evidence_package(
            url="https://example.com",
            synchronized_output={"forward": [], "backward": []},
            dom_snapshot={},
            screenshot_metadata=screenshot_meta,
        )

        self.assertEqual(pkg["visual_evidence"]["status"], "SUCCESS")
        self.assertEqual(pkg["visual_evidence"]["screenshot"]["path"], "custom_screenshot.png")
        self.assertEqual(pkg["visual_evidence"]["screenshot"]["width"], 1440)
        self.assertTrue(pkg["visual_evidence"]["screenshot"]["fixed_position_elements_possible"])

    def test_missing_screenshot_metadata_handled_explicitly(self):
        """11. Missing or None screenshot metadata is handled explicitly without crashing."""
        pkg = assemble_unified_evidence_package(
            url="https://example.com",
            synchronized_output={"forward": [], "backward": []},
            dom_snapshot={},
            screenshot_metadata=None,
        )

        self.assertEqual(pkg["visual_evidence"]["status"], "UNAVAILABLE")
        self.assertIsNone(pkg["visual_evidence"]["screenshot"])

    def test_no_wcag_or_accessibility_judgment_produced(self):
        """12. Correlator must never output WCAG violations, severities, or compliance scores."""
        sync_output = {
            "forward": [
                {
                    "step": 1,
                    "selenium": {"tag": "a", "text": "", "href": "#"},
                    "nvda": {"role": "link", "name": "unlabelled"},
                    "comparison": {"status": "ROLE_MATCH_NAME_UNLABELLED"},
                }
            ],
            "backward": []
        }
        pkg = assemble_unified_evidence_package("https://test.com", sync_output, {"interactive_elements": []})

        # Verify no analyzer or WCAG terms in package keys
        self.assertNotIn("violations", pkg)
        self.assertNotIn("compliance_score", pkg)
        self.assertNotIn("severity_summary", pkg)
        self.assertNotIn("wcag_rules", pkg)


if __name__ == "__main__":
    unittest.main()
