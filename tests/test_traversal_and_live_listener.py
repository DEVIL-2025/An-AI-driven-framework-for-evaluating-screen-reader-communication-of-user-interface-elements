"""
Unit tests for collision-free traversal and live listener visual evidence integration.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import tempfile
import json
import shutil

from synchronisation.sync import get_traversal_element_identifier
from main import run_live_listener


class MockWebElement:
    """Mock Selenium WebElement with configurable W3C id and DOM attributes."""

    def __init__(self, elem_id, tag_name="input", text="", attrs=None):
        self.id = elem_id
        self.tag_name = tag_name
        self.text = text
        self.attrs = attrs or {}

    def get_attribute(self, name):
        return self.attrs.get(name)


class TestTraversalIdentifierAndStagnation(unittest.TestCase):
    """Verifies that element identification avoids collision on MakeMyTrip-like dynamic pages."""

    def test_distinct_elements_with_identical_classes_have_different_identifiers(self):
        """
        On MakeMyTrip, the 'From' and 'To' autosuggest inputs share identical class
        names ('react-autosuggest__input'), tag 'input', no DOM id, and empty text.
        Ensure that their traversal identifiers do NOT collide because of distinct W3C node IDs.
        """
        from_input = MockWebElement(
            elem_id="elem_from_001",
            tag_name="input",
            text="",
            attrs={
                "id": "",
                "name": "",
                "type": "text",
                "class": "react-autosuggest__input react-autosuggest__input--open react-autosuggest__input--focused",
                "placeholder": "From",
            },
        )
        to_input = MockWebElement(
            elem_id="elem_to_002",
            tag_name="input",
            text="",
            attrs={
                "id": "",
                "name": "",
                "type": "text",
                "class": "react-autosuggest__input react-autosuggest__input--open react-autosuggest__input--focused",
                "placeholder": "To",
            },
        )

        id1 = get_traversal_element_identifier(from_input)
        id2 = get_traversal_element_identifier(to_input)

        self.assertIsNotNone(id1)
        self.assertIsNotNone(id2)
        self.assertNotEqual(id1, id2, "Identifiers for From and To inputs must not collide!")
        self.assertEqual(id1[0], "elem_from_001")
        self.assertEqual(id2[0], "elem_to_002")

        visited = set()
        visited.add(from_input.id or id1)
        self.assertNotIn(to_input.id or id2, visited, "To input must not be considered already visited!")

    def test_generic_buttons_with_identical_text_and_class_have_unique_ids(self):
        """Next/Previous carousel buttons across different sections should not collide."""
        btn1 = MockWebElement(
            elem_id="carousel_next_1",
            tag_name="button",
            text="Next",
            attrs={"class": "carousel-nav-btn"},
        )
        btn2 = MockWebElement(
            elem_id="carousel_next_2",
            tag_name="button",
            text="Next",
            attrs={"class": "carousel-nav-btn"},
        )

        id1 = get_traversal_element_identifier(btn1)
        id2 = get_traversal_element_identifier(btn2)

        self.assertNotEqual(id1, id2)
        visited = {btn1.id}
        self.assertNotIn(btn2.id, visited)


class TestLiveListenerVisualEvidence(unittest.TestCase):
    """Verifies that run_live_listener captures, correlates, and dispatches visual evidence."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_live_listener_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch("tools.nvda_tool.NVDATextExtractor")
    @patch("tools.ai_agent.AIAccessibilityAnalyzer")
    def test_live_listener_with_existing_screenshot_passes_visual_evidence_to_ai(
        self, mock_analyzer_cls, mock_extractor_cls
    ):
        """
        Verify that in manual mode with a pre-existing screenshot, run_live_listener
        detects the screenshot, creates screenshot_metadata.json, assembles
        unified_evidence_package.json, and passes the screenshot to AIAccessibilityAnalyzer.
        """
        # Create a mock 1x1 PNG file in test_dir
        screenshot_path = os.path.join(self.test_dir, "webpage_screenshot.png")
        tiny_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
            b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        with open(screenshot_path, "wb") as f:
            f.write(tiny_png)

        # Mock extractor to immediately raise KeyboardInterrupt on get_new_text
        mock_extractor = MagicMock()
        mock_extractor.get_new_text.side_effect = KeyboardInterrupt
        mock_extractor_cls.return_value = mock_extractor

        # Mock AI analyzer
        mock_analyzer = MagicMock()
        mock_report = MagicMock()
        mock_report.analysis_status = "COMPLETED"
        mock_report.violations = []
        mock_report.recommendations = []
        mock_report.ai_metadata = {"model": "gemini-2.5-pro"}
        mock_report.to_dict.return_value = {
            "summary": {
                "compliance_score": 95.0,
                "total_elements_analyzed": 0,
                "total_violations": 0,
                "total_recommendations": 0,
                "severity_summary": {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "INFO": 0},
            }
        }
        mock_analyzer.analyze_synchronized_evidence.return_value = mock_report
        mock_analyzer_cls.return_value = mock_analyzer

        # Run live listener targeting test_dir
        run_live_listener(
            url=None,
            enable_ai=True,
            screenshot_path=screenshot_path,
            output_dir=self.test_dir,
        )

        # Assert visual artifacts were created
        meta_file = os.path.join(self.test_dir, "screenshot_metadata.json")
        dom_file = os.path.join(self.test_dir, "dom_snapshot.json")
        pkg_file = os.path.join(self.test_dir, "unified_evidence_package.json")
        sync_file = os.path.join(self.test_dir, "synchronized_output.json")
        rep_file = os.path.join(self.test_dir, "ai_accessibility_report.json")

        self.assertTrue(os.path.exists(meta_file), "screenshot_metadata.json must exist")
        self.assertTrue(os.path.exists(dom_file), "dom_snapshot.json must exist")
        self.assertTrue(os.path.exists(pkg_file), "unified_evidence_package.json must exist")
        self.assertTrue(os.path.exists(sync_file), "synchronized_output.json must exist")
        mock_analyzer.save_ai_report.assert_called_once_with(mock_report, rep_file)

        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual(meta.get("status"), "SUCCESS")
        self.assertEqual(meta.get("width"), 1)
        self.assertEqual(meta.get("height"), 1)

        with open(pkg_file, "r", encoding="utf-8") as f:
            pkg = json.load(f)
        self.assertIn("visual_evidence", pkg)
        self.assertEqual(pkg["visual_evidence"]["status"], "SUCCESS")

        # Verify AI analyzer received visual evidence arguments
        mock_analyzer.analyze_synchronized_evidence.assert_called_once()
        call_kwargs = mock_analyzer.analyze_synchronized_evidence.call_args.kwargs
        self.assertIsNotNone(call_kwargs.get("screenshot_path"), "screenshot_path must be passed to AI analyzer")
        self.assertIsNotNone(call_kwargs.get("screenshot_metadata"), "screenshot_metadata must be passed to AI analyzer")
        self.assertIsNotNone(call_kwargs.get("unified_package"), "unified_package must be passed to AI analyzer")

    @patch("selenium.webdriver.Chrome")
    @patch("tools.screenshot_capture.capture_webpage_screenshot")
    @patch("tools.dom_extractor.extract_dom_snapshot")
    @patch("tools.nvda_tool.NVDATextExtractor")
    @patch("tools.ai_agent.AIAccessibilityAnalyzer")
    def test_live_listener_with_url_captures_screenshot_and_dom(
        self, mock_analyzer_cls, mock_extractor_cls, mock_dom_snapshot, mock_screenshot_cap, mock_chrome
    ):
        """
        Verify that when a target URL is provided to run_live_listener,
        it initializes Chrome, navigates to the URL, drains pre-interaction speech,
        and upon KeyboardInterrupt captures screenshot & DOM snapshot before quitting.
        """
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        mock_screenshot_cap.return_value = {
            "status": "SUCCESS",
            "path": os.path.join(self.test_dir, "webpage_screenshot.png"),
            "filename": "webpage_screenshot.png",
            "width": 1280,
            "height": 800,
            "capture_mode": "FULL_PAGE",
            "has_fixed_elements": False,
        }
        mock_dom_snapshot.return_value = {
            "headings": [],
            "landmarks": [],
            "sections": [],
            "interactive_elements": [],
        }

        mock_extractor = MagicMock()
        mock_extractor.drain_initial_speech.return_value = ("MakeMyTrip Title", True)
        mock_extractor.get_new_text.side_effect = KeyboardInterrupt
        mock_extractor_cls.return_value = mock_extractor

        mock_analyzer = MagicMock()
        mock_report = MagicMock()
        mock_report.analysis_status = "COMPLETED"
        mock_report.violations = []
        mock_report.recommendations = []
        mock_report.ai_metadata = {"model": "gemini-2.5-pro"}
        mock_report.to_dict.return_value = {
            "summary": {
                "compliance_score": 100.0,
                "total_elements_analyzed": 0,
                "total_violations": 0,
                "total_recommendations": 0,
                "severity_summary": {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "INFO": 0},
            }
        }
        mock_analyzer.analyze_synchronized_evidence.return_value = mock_report
        mock_analyzer_cls.return_value = mock_analyzer

        run_live_listener(
            url="https://www.makemytrip.com/",
            enable_ai=True,
            output_dir=self.test_dir,
        )

        mock_driver.maximize_window.assert_called_once()
        mock_driver.get.assert_called_once_with("https://www.makemytrip.com/")
        mock_extractor.drain_initial_speech.assert_called_once_with(from_baseline=True)
        mock_screenshot_cap.assert_called_once()
        mock_dom_snapshot.assert_called_once_with(mock_driver)
        mock_driver.quit.assert_called_once()
        mock_analyzer.analyze_synchronized_evidence.assert_called_once()


class TestEvidenceDeliveryToGemini(unittest.TestCase):
    """
    Verifies that all three evidence modalities (synchronized interaction,
    DOM & structural snapshot, and visual screenshot) are correctly assembled
    and transmitted to Gemini for accessibility evaluation.
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_gemini_evidence_")
        self.tiny_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
            b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        self.screenshot_path = os.path.join(self.test_dir, "webpage_screenshot.png")
        with open(self.screenshot_path, "wb") as f:
            f.write(self.tiny_png)

        self.dom_snapshot = {
            "landmarks": [
                {"role": "banner", "tag": "header", "label": "Site Header"},
                {"role": "main", "tag": "main", "label": "Booking Content"},
            ],
            "headings": [
                {"level": 1, "text": "Book Flights and Hotels", "tag": "h1"},
                {"level": 2, "text": "Featured Offers", "tag": "h2"},
            ],
            "context_blocks": [
                {"block_id": "blk-1", "block_type": "nav", "heading": "Main Navigation"}
            ],
            "forms": [
                {"id": "flight-search-form", "name": "flightSearch", "label": "Search Flights", "field_count": 3}
            ],
            "images": [
                {
                    "tag": "img",
                    "src": "/images/logo.png",
                    "alt": "MakeMyTrip Logo",
                    "aria_label": None,
                    "role": "img",
                    "is_decorative": False,
                    "parent_context": "header",
                    "nearby_text": "Flight Booking",
                }
            ],
            "interactive_elements": [
                {"tag": "input", "text": "From City", "id": "fromCity"},
                {"tag": "button", "text": "Search Flights", "id": "searchBtn"},
            ],
        }

        self.sync_output = {
            "url": "https://www.makemytrip.com/",
            "forward": [
                {
                    "step": 1,
                    "selenium": {
                        "tag": "input",
                        "text": "",
                        "aria-label": "From City",
                        "id": "fromCity",
                        "name": "fromCity",
                        "class": "react-autosuggest__input",
                        "role": "combobox",
                        "type": "text",
                    },
                    "nvda": {
                        "role": "edit",
                        "name": "From City",
                        "value": "Delhi",
                        "raw_text": "From City edit Delhi",
                    },
                    "comparison": {
                        "status": "MATCH",
                        "name_match": True,
                        "role_match": True,
                    },
                },
                {
                    "step": 2,
                    "selenium": {
                        "tag": "button",
                        "text": "Search Flights",
                        "aria-label": "Search Flights",
                        "id": "searchBtn",
                        "name": "",
                        "class": "primaryBtn",
                        "role": "button",
                    },
                    "nvda": {
                        "role": "button",
                        "name": "Search Flights",
                        "raw_text": "Search Flights button",
                    },
                    "comparison": {
                        "status": "MATCH",
                        "name_match": True,
                        "role_match": True,
                    },
                },
            ],
            "backward": [
                {
                    "step": 1,
                    "selenium": {
                        "tag": "button",
                        "text": "Search Flights",
                        "aria-label": "Search Flights",
                        "id": "searchBtn",
                        "class": "primaryBtn",
                        "role": "button",
                    },
                    "nvda": {
                        "role": "button",
                        "name": "Search Flights",
                        "raw_text": "Search Flights button",
                    },
                    "comparison": {
                        "status": "MATCH",
                        "name_match": True,
                        "role_match": True,
                    },
                },
                {
                    "step": 2,
                    "selenium": {
                        "tag": "a",
                        "text": "Special Offers",
                        "aria-label": "Special Offers",
                        "id": "offersLink",
                        "class": "navLink",
                        "role": "link",
                        "href": "/offers",
                    },
                    "nvda": {
                        "role": "link",
                        "name": "Special Offers",
                        "raw_text": "Special Offers link",
                    },
                    "comparison": {
                        "status": "MATCH",
                        "name_match": True,
                        "role_match": True,
                    },
                },
            ],
        }

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_multimodal_evidence_streams_delivered_to_mock_gemini(self):
        """
        Verify that MockLLMProvider receives all 3 modalities:
        - Modality 1: Synchronized interaction elements (both forward and backward).
        - Modality 2: DOM & structural evidence (landmarks, headings, images, forms).
        - Modality 3: Visual evidence status & inline base64 image data.
        """
        from tools.ai_agent import AIAccessibilityAnalyzer
        from tools.ai_providers import MockLLMProvider
        from tools.evidence_correlator import assemble_unified_evidence_package

        screenshot_meta = {
            "status": "SUCCESS",
            "path": self.screenshot_path,
            "filename": "webpage_screenshot.png",
            "width": 1280,
            "height": 800,
            "capture_mode": "FULL_PAGE",
            "has_fixed_elements": False,
        }

        unified_package = assemble_unified_evidence_package(
            url="https://www.makemytrip.com/",
            synchronized_output=self.sync_output,
            dom_snapshot=self.dom_snapshot,
            screenshot_metadata=screenshot_meta,
        )

        mock_provider = MockLLMProvider(mode="zero_violations")
        analyzer = AIAccessibilityAnalyzer(provider=mock_provider)

        report = analyzer.analyze_synchronized_evidence(
            self.sync_output,
            unified_package=unified_package,
            screenshot_path=self.screenshot_path,
            screenshot_metadata=screenshot_meta,
            output_dir=self.test_dir,
        )

        self.assertEqual(report.analysis_status, "NO_VIOLATIONS")
        self.assertEqual(mock_provider.call_count, 1)

        # 1. Verify Modality 3: Visual Image Part
        self.assertIsNotNone(mock_provider.last_image_data, "Inline image part must be passed to provider")
        self.assertIn("inline_data", mock_provider.last_image_data)
        self.assertEqual(mock_provider.last_image_data["inline_data"]["mime_type"], "image/png")
        import base64
        self.assertEqual(
            base64.b64decode(mock_provider.last_image_data["inline_data"]["data"]),
            self.tiny_png,
            "Image bytes delivered to provider must match original screenshot"
        )

        # 2. Verify Modality 1, 2, and 3 in user_prompt
        prompt = mock_provider.last_user_prompt
        self.assertIn("EVIDENCE MODALITY 1: SYNCHRONIZED INTERACTION EVIDENCE", prompt)
        self.assertIn("From City", prompt)
        self.assertIn("Search Flights", prompt)
        # Verify backward element present
        self.assertIn("Special Offers", prompt)

        self.assertIn("EVIDENCE MODALITY 2: DOM & STRUCTURAL EVIDENCE", prompt)
        self.assertIn("Book Flights and Hotels", prompt)
        self.assertIn("Featured Offers", prompt)
        self.assertIn("Site Header", prompt)
        self.assertIn("MakeMyTrip Logo", prompt)

        self.assertIn("EVIDENCE MODALITY 3: VISUAL EVIDENCE (RENDERED WEBPAGE SCREENSHOT)", prompt)
        self.assertIn('"status": "AVAILABLE"', prompt)
        self.assertIn('"delivery": "Attached as an inline image part in this request"', prompt)

        # 3. Verify report metadata
        modalities = report.ai_metadata["evidence_modalities"]
        self.assertTrue(modalities["synchronized"])
        self.assertTrue(modalities["dom"])
        self.assertTrue(modalities["visual"])

    @patch("requests.post")
    def test_gemini_rest_request_payload_contains_all_three_modalities(self, mock_post):
        """
        Verify the exact HTTP request payload sent over the wire to Gemini API endpoint:
        - System instruction
        - Part 0: Complete 3-modality prompt
        - Part 1: Inline base64 PNG data
        - Generation config requesting JSON output
        """
        import base64
        from tools.ai_agent import AIAccessibilityAnalyzer
        from tools.ai_providers import GeminiLLMProvider
        from tools.evidence_correlator import assemble_unified_evidence_package

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps({
                                    "analysis_status": "NO_VIOLATIONS",
                                    "summary": {
                                        "total_elements_analyzed": 3,
                                        "total_violations": 0,
                                        "total_recommendations": 0,
                                        "compliance_score": 100.0,
                                        "severity_summary": {
                                            "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "INFO": 0
                                        },
                                    },
                                    "violations": [],
                                    "recommendations": [],
                                })
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_resp

        screenshot_meta = {
            "status": "SUCCESS",
            "path": self.screenshot_path,
            "filename": "webpage_screenshot.png",
            "width": 1280,
            "height": 800,
            "capture_mode": "FULL_PAGE",
        }

        unified_package = assemble_unified_evidence_package(
            url="https://www.makemytrip.com/",
            synchronized_output=self.sync_output,
            dom_snapshot=self.dom_snapshot,
            screenshot_metadata=screenshot_meta,
        )

        gemini_provider = GeminiLLMProvider(api_key="TEST_API_KEY", model_name="gemini-2.5-pro")
        analyzer = AIAccessibilityAnalyzer(provider=gemini_provider)

        report = analyzer.analyze_synchronized_evidence(
            self.sync_output,
            unified_package=unified_package,
            screenshot_path=self.screenshot_path,
            screenshot_metadata=screenshot_meta,
            output_dir=self.test_dir,
        )

        self.assertEqual(report.analysis_status, "NO_VIOLATIONS")
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]

        # Check Gemini REST payload schema
        self.assertIn("contents", payload)
        self.assertIn("system_instruction", payload)
        self.assertIn("generationConfig", payload)
        self.assertEqual(payload["generationConfig"]["response_mime_type"], "application/json")

        parts = payload["contents"][0]["parts"]
        self.assertEqual(len(parts), 2, "Gemini contents parts must contain exactly prompt text and image data")

        user_prompt_sent = parts[0]["text"]
        self.assertIn("EVIDENCE MODALITY 1: SYNCHRONIZED INTERACTION EVIDENCE", user_prompt_sent)
        self.assertIn("EVIDENCE MODALITY 2: DOM & STRUCTURAL EVIDENCE", user_prompt_sent)
        self.assertIn("EVIDENCE MODALITY 3: VISUAL EVIDENCE (RENDERED WEBPAGE SCREENSHOT)", user_prompt_sent)

        image_part_sent = parts[1]
        self.assertIn("inline_data", image_part_sent)
        self.assertEqual(image_part_sent["inline_data"]["mime_type"], "image/png")
        self.assertEqual(image_part_sent["inline_data"]["data"], base64.b64encode(self.tiny_png).decode("ascii"))

    def test_auto_discovery_from_output_dir_delivers_all_modalities(self):
        """
        Verify that when screenshot_path and unified_package are omitted,
        analyze_synchronized_evidence discovers webpage_screenshot.png,
        dom_snapshot.json, and screenshot_metadata.json from output_dir and
        delivers them to Gemini.
        """
        from tools.ai_agent import AIAccessibilityAnalyzer
        from tools.ai_providers import MockLLMProvider

        # Save artifacts into test_dir
        with open(os.path.join(self.test_dir, "dom_snapshot.json"), "w", encoding="utf-8") as f:
            json.dump(self.dom_snapshot, f)
        with open(os.path.join(self.test_dir, "screenshot_metadata.json"), "w", encoding="utf-8") as f:
            json.dump({
                "status": "SUCCESS",
                "path": self.screenshot_path,
                "width": 1280,
                "height": 800,
                "capture_mode": "FULL_PAGE",
            }, f)

        mock_provider = MockLLMProvider(mode="zero_violations")
        analyzer = AIAccessibilityAnalyzer(provider=mock_provider)

        # Call with only sync_output and output_dir
        report = analyzer.analyze_synchronized_evidence(
            self.sync_output,
            output_dir=self.test_dir,
        )

        self.assertEqual(report.analysis_status, "NO_VIOLATIONS")
        self.assertIsNotNone(mock_provider.last_image_data, "Discovered screenshot must be delivered to Gemini")
        self.assertTrue(report.ai_metadata["evidence_modalities"]["visual"])
        self.assertTrue(report.ai_metadata["evidence_modalities"]["dom"])
        prompt = mock_provider.last_user_prompt
        self.assertIn("Book Flights and Hotels", prompt, "Discovered DOM snapshot must be in user prompt")
        self.assertIn('"status": "AVAILABLE"', prompt, "Visual evidence status must be AVAILABLE")


if __name__ == "__main__":
    unittest.main()

