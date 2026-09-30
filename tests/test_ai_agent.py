"""
Unit Tests for AI Accessibility Analyzer Layer
Comprehensive test suite covering all 16 mandatory test requirements:
1. Fully accessible evidence -> zero violations
2. Unlabelled interactive element -> AI detects violation
3. NVDA/Selenium mismatch -> AI evaluates mismatch
4. Correctly labelled control -> no false positive
5. Form control with sufficient accessible labeling -> no false positive
6. Vague link -> AI evaluates context and link text
7. Heading structure issue -> AI evaluates page-level context
8. Multiple violations on page
9. Page-level violation support (scope: PAGE, element_reference: null)
10. Invalid AI JSON response handling
11. Provider network / timeout failure handling
12. Gemini unavailable -> explicit AI_ANALYSIS_UNAVAILABLE state
13. AI confidence validation (0.0 to 1.0)
14. Severity validation (CRITICAL, MAJOR, MINOR, INFO)
15. Ground-truth evidence preservation (DOM + NVDA)
16. Generic website independence (no hardcoded test sites)
"""

import unittest
import sys
import os
import json
import copy

# Add root directory to path so tests can run standalone
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.ai_providers import (
    MockLLMProvider,
    FallbackLLMProvider,
    GeminiLLMProvider,
    get_default_provider,
)
from tools.ai_agent import (
    AIAccessibilityAnalyzer,
    AIAccessibilityAgent,
    AIViolationFinding,
    AIRecommendation,
    AIAccessibilityAnalysisReport,
    extract_page_context,
    prepare_compact_evidence,
    calculate_ai_score,
    deduplicate_violations,
    deduplicate_recommendations,
    AI_ANALYZER_SYSTEM_PROMPT,
)


class TestAIAccessibilityAgent(unittest.TestCase):

    def setUp(self):
        # Sample synchronized dataset: Accessible element
        self.accessible_button_sync = {
            "step": 1,
            "selenium": {
                "tag": "button",
                "text": "Submit Application",
                "role": None,
                "type": "submit",
                "id": "btn-submit",
                "aria-label": None,
                "expected_roles": ["button"],
            },
            "nvda": {
                "name": "Submit Application",
                "role": "button",
                "value": None,
                "description": None,
                "level": None,
                "attributes": [],
                "raw_text": "Submit Application button",
            },
            "comparison": {
                "name_match": True,
                "role_match": True,
                "status": "MATCH",
            },
        }

        # Sample synchronized dataset: Unlabelled interactive link
        self.unlabelled_link_sync = {
            "step": 1,
            "selenium": {
                "tag": "a",
                "text": "",
                "role": None,
                "href": "/student/portal",
                "id": "logo-link",
                "aria-label": None,
                "expected_roles": ["link", "graphic link"],
            },
            "nvda": {
                "name": "",
                "role": "graphic link",
                "value": None,
                "description": "To get missing image descriptions, open the context menu.",
                "level": None,
                "attributes": ["same page"],
                "raw_text": "link Unlabeled graphic",
            },
            "comparison": {
                "name_match": False,
                "role_match": True,
                "status": "ROLE_MATCH_NAME_UNLABELLED",
            },
        }

        # Sample synchronized dataset: Role and Name mismatch
        self.mismatched_element_sync = {
            "step": 3,
            "selenium": {
                "tag": "div",
                "text": "Open Menu",
                "role": "button",
                "id": "div-toggle",
                "aria-label": None,
                "expected_roles": ["button"],
            },
            "nvda": {
                "name": "",
                "role": "section",
                "value": None,
                "description": None,
                "level": None,
                "attributes": [],
                "raw_text": "section",
            },
            "comparison": {
                "name_match": False,
                "role_match": False,
                "status": "MISMATCH",
            },
        }

        # Sample synchronized dataset: Form input with proper label
        self.labelled_input_sync = {
            "step": 4,
            "selenium": {
                "tag": "input",
                "text": "",
                "role": None,
                "type": "text",
                "id": "username-field",
                "aria-label": "Username",
                "placeholder": "Enter username",
                "expected_roles": ["edit"],
            },
            "nvda": {
                "name": "Username",
                "role": "edit",
                "value": "",
                "description": None,
                "level": None,
                "attributes": [],
                "raw_text": "Username edit",
            },
            "comparison": {
                "name_match": True,
                "role_match": True,
                "status": "MATCH",
            },
        }

        # Sample synchronized dataset: Vague link ("Click here")
        self.vague_link_sync = {
            "step": 3,
            "selenium": {
                "tag": "a",
                "text": "Click here",
                "role": None,
                "href": "/docs/guide.pdf",
                "id": "link-download",
                "aria-label": None,
                "expected_roles": ["link"],
            },
            "nvda": {
                "name": "Click here",
                "role": "link",
                "value": None,
                "description": None,
                "level": None,
                "attributes": [],
                "raw_text": "Click here link",
            },
            "comparison": {
                "name_match": True,
                "role_match": True,
                "status": "MATCH",
            },
        }

    # -------------------------------------------------------------------------
    # TEST 1: Fully accessible evidence -> zero violations
    # -------------------------------------------------------------------------
    def test_01_fully_accessible_evidence_zero_violations(self):
        accessible_data = {
            "url": "https://example.com/accessible-page",
            "forward": [self.accessible_button_sync, self.labelled_input_sync],
            "backward": [],
        }
        mock_provider = MockLLMProvider(mode="zero_violations")
        analyzer = AIAccessibilityAnalyzer(provider=mock_provider)

        report = analyzer.analyze_synchronized_evidence(accessible_data)

        self.assertIsInstance(report, AIAccessibilityAnalysisReport)
        self.assertEqual(report.analysis_status, "NO_VIOLATIONS")
        self.assertEqual(report.summary.total_violations, 0)
        self.assertEqual(len(report.violations), 0)
        self.assertEqual(report.summary.compliance_score, 100.0)
        self.assertEqual(report.summary.total_elements_analyzed, 2)
        self.assertEqual(mock_provider.call_count, 1)

    # -------------------------------------------------------------------------
    # TEST 2: Unlabelled interactive element -> AI identifies issue
    # -------------------------------------------------------------------------
    def test_02_unlabelled_interactive_element_violation(self):
        unlabelled_data = {
            "url": "https://example.com/login",
            "forward": [self.unlabelled_link_sync],
            "backward": [],
        }
        mock_provider = MockLLMProvider(mode="single_violation")
        analyzer = AIAccessibilityAnalyzer(provider=mock_provider)

        report = analyzer.analyze_synchronized_evidence(unlabelled_data)

        self.assertEqual(report.analysis_status, "COMPLETED")
        self.assertEqual(report.summary.total_violations, 1)
        self.assertEqual(len(report.violations), 1)

        v = report.violations[0]
        self.assertEqual(v.rule_id, "WCAG 4.1.2")
        self.assertEqual(v.severity, "CRITICAL")
        self.assertGreaterEqual(v.confidence, 0.8)
        self.assertIn("Unlabelled", v.title)
        self.assertEqual(v.element_reference, {"direction": "forward", "step": 1})

    # -------------------------------------------------------------------------
    # TEST 3: NVDA/Selenium mismatch -> AI evaluates the mismatch
    # -------------------------------------------------------------------------
    def test_03_nvda_selenium_mismatch_evaluation(self):
        mismatch_data = {
            "url": "https://example.com/portal",
            "forward": [self.mismatched_element_sync],
            "backward": [],
        }
        custom_resp = {
            "analysis_status": "COMPLETED",
            "summary": {
                "total_elements_analyzed": 1,
                "total_violations": 1,
                "compliance_score": 85.0,
                "severity_summary": {"CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0},
            },
            "violations": [
                {
                    "violation_id": "AI-003",
                    "scope": "ELEMENT",
                    "element_reference": {"direction": "forward", "step": 3},
                    "rule_id": "WCAG 4.1.2",
                    "rule_name": "Name, Role, Value",
                    "severity": "MAJOR",
                    "confidence": 0.92,
                    "title": "Role and Name Mismatch Between DOM and Screen Reader",
                    "description": "DOM element defines button role, but NVDA announced it as an unlabelled section.",
                    "ai_rationale": "DOM specifies role='button', but NVDA announced 'section' without an accessible name.",
                    "evidence": {},
                    "user_impact": "Assistive technology users will not receive interactive button semantics.",
                    "wcag_context": "WCAG 4.1.2 Level A requirement for proper role communication.",
                    "recommendation": "Use native <button> element instead of <div> with ARIA.",
                    "developer_guidance": '<button type="button">[Descriptive accessible name]</button>',
                }
            ],
        }
        mock_provider = MockLLMProvider(custom_response=custom_resp)
        analyzer = AIAccessibilityAnalyzer(provider=mock_provider)

        report = analyzer.analyze_synchronized_evidence(mismatch_data)

        self.assertEqual(report.summary.total_violations, 1)
        v = report.violations[0]
        self.assertEqual(v.severity, "MAJOR")
        self.assertEqual(v.rule_id, "WCAG 4.1.2")
        self.assertIn("Mismatch", v.title)

    # -------------------------------------------------------------------------
    # TEST 4: Correctly labelled control -> no false positive
    # -------------------------------------------------------------------------
    def test_04_correctly_labelled_control_no_false_positive(self):
        data = {
            "url": "https://example.com/accessible-button",
            "forward": [self.accessible_button_sync],
            "backward": [],
        }
        mock_provider = MockLLMProvider(mode="zero_violations")
        analyzer = AIAccessibilityAnalyzer(provider=mock_provider)

        report = analyzer.analyze_synchronized_evidence(data)

        self.assertEqual(report.summary.total_violations, 0)
        self.assertEqual(report.summary.compliance_score, 100.0)

    # -------------------------------------------------------------------------
    # TEST 5: Form control with sufficient accessible labeling -> no false positive
    # -------------------------------------------------------------------------
    def test_05_form_control_sufficient_labeling_no_false_positive(self):
        data = {
            "url": "https://example.com/accessible-form",
            "forward": [self.labelled_input_sync],
            "backward": [],
        }
        mock_provider = MockLLMProvider(mode="zero_violations")
        analyzer = AIAccessibilityAnalyzer(provider=mock_provider)

        report = analyzer.analyze_synchronized_evidence(data)

        self.assertEqual(report.summary.total_violations, 0)
        self.assertEqual(report.summary.compliance_score, 100.0)

    # -------------------------------------------------------------------------
    # TEST 6: Vague link -> AI evaluates link purpose
    # -------------------------------------------------------------------------
    def test_06_vague_link_purpose_evaluation(self):
        vague_data = {
            "url": "https://example.com/resources",
            "forward": [self.vague_link_sync],
            "backward": [],
        }
        custom_resp = {
            "analysis_status": "COMPLETED",
            "summary": {
                "total_elements_analyzed": 1,
                "total_violations": 1,
                "compliance_score": 92.0,
                "severity_summary": {"CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0},
            },
            "violations": [
                {
                    "violation_id": "AI-006",
                    "scope": "ELEMENT",
                    "element_reference": {"direction": "forward", "step": 3},
                    "rule_id": "WCAG 2.4.4",
                    "rule_name": "Link Purpose (In Context)",
                    "severity": "MAJOR",
                    "confidence": 0.90,
                    "title": "Ambiguous Non-Descriptive Link Text ('Click here')",
                    "description": "Link text 'Click here' does not convey destination out of context.",
                    "ai_rationale": "Link text 'Click here' provides zero contextual indication of destination when read by screen reader.",
                    "evidence": {},
                    "user_impact": "Screen reader users browsing links list cannot identify document destination.",
                    "wcag_context": "WCAG 2.4.4 Link Purpose (In Context) Level A.",
                    "recommendation": "Provide a descriptive destination in link text.",
                    "developer_guidance": '<a href="/docs/guide.pdf">[Descriptive document title] (PDF)</a>',
                }
            ],
        }
        mock_provider = MockLLMProvider(custom_response=custom_resp)
        analyzer = AIAccessibilityAnalyzer(provider=mock_provider)

        report = analyzer.analyze_synchronized_evidence(vague_data)

        self.assertEqual(report.summary.total_violations, 1)
        v = report.violations[0]
        self.assertEqual(v.rule_id, "WCAG 2.4.4")
        self.assertEqual(v.severity, "MAJOR")

    # -------------------------------------------------------------------------
    # TEST 7: Heading structure issue -> AI evaluates page context
    # -------------------------------------------------------------------------
    def test_07_heading_structure_page_context_evaluation(self):
        heading_data = {
            "url": "https://example.com/headings",
            "forward": [
                {
                    "step": 1,
                    "selenium": {"tag": "h1", "text": "Main Heading"},
                    "nvda": {"role": "heading", "name": "Main Heading", "level": 1},
                    "comparison": {"status": "MATCH"},
                },
                {
                    "step": 2,
                    "selenium": {"tag": "h4", "text": "Skipped Subheading"},
                    "nvda": {"role": "heading", "name": "Skipped Subheading", "level": 4},
                    "comparison": {"status": "MATCH"},
                },
            ],
            "backward": [],
        }
        custom_resp = {
            "analysis_status": "COMPLETED",
            "summary": {
                "total_elements_analyzed": 2,
                "total_violations": 1,
                "compliance_score": 97.0,
                "severity_summary": {"CRITICAL": 0, "MAJOR": 0, "MINOR": 1, "INFO": 0},
            },
            "violations": [
                {
                    "violation_id": "AI-007",
                    "scope": "PAGE",
                    "element_reference": None,
                    "rule_id": "WCAG 1.3.1",
                    "rule_name": "Info and Relationships",
                    "severity": "MINOR",
                    "confidence": 0.88,
                    "title": "Skipped Heading Level in Document Outline",
                    "description": "Heading hierarchy jumped directly from <h1> to <h4> without intermediate <h2> or <h3>.",
                    "ai_rationale": "Document hierarchy jumped from h1 to h4 as observed in page context heading outline.",
                    "evidence": {},
                    "user_impact": "Screen reader users navigating by headings experience a disorienting document outline.",
                    "wcag_context": "WCAG 1.3.1 Info and Relationships Level A.",
                    "recommendation": "Maintain linear heading hierarchy (h1 -> h2 -> h3).",
                    "developer_guidance": "<h2>[Descriptive Section Heading]</h2>",
                }
            ],
        }
        mock_provider = MockLLMProvider(custom_response=custom_resp)
        analyzer = AIAccessibilityAnalyzer(provider=mock_provider)

        report = analyzer.analyze_synchronized_evidence(heading_data)

        self.assertEqual(report.summary.total_violations, 1)
        v = report.violations[0]
        self.assertEqual(v.scope, "PAGE")
        self.assertIsNone(v.element_reference)
        self.assertEqual(v.severity, "MINOR")

    # -------------------------------------------------------------------------
    # TEST 8: Multiple violations on page
    # -------------------------------------------------------------------------
    def test_08_multiple_violations_detected(self):
        multi_data = {
            "url": "https://example.com/multi-defect",
            "forward": [self.unlabelled_link_sync, self.vague_link_sync],
            "backward": [],
        }
        mock_provider = MockLLMProvider(mode="multiple_violations")
        analyzer = AIAccessibilityAnalyzer(provider=mock_provider)

        report = analyzer.analyze_synchronized_evidence(multi_data)

        self.assertEqual(report.summary.total_violations, 2)
        self.assertEqual(len(report.violations), 2)
        self.assertEqual(report.summary.severity_summary.CRITICAL, 1)
        self.assertEqual(report.summary.severity_summary.MAJOR, 1)

    # -------------------------------------------------------------------------
    # TEST 9: Page-level violation support (scope: PAGE, element_reference: null)
    # -------------------------------------------------------------------------
    def test_09_page_level_violation_supported(self):
        custom_resp = {
            "analysis_status": "COMPLETED",
            "summary": {
                "total_elements_analyzed": 1,
                "total_violations": 1,
                "compliance_score": 95.0,
                "severity_summary": {"CRITICAL": 0, "MAJOR": 0, "MINOR": 1, "INFO": 0},
            },
            "violations": [
                {
                    "violation_id": "AI-PAGE-01",
                    "scope": "PAGE",
                    "element_reference": None,
                    "rule_id": "WCAG 2.4.1",
                    "rule_name": "Bypass Blocks",
                    "severity": "MINOR",
                    "confidence": 0.85,
                    "title": "Missing Skip to Main Content Link",
                    "description": "Page lacks a bypass mechanism to allow keyboard users to skip repetitive navigation.",
                    "ai_rationale": "No bypass landmark or skip navigation link was detected in page structure.",
                    "evidence": {},
                    "user_impact": "Keyboard users must tab through repeated header navigation on every page load.",
                    "wcag_context": "WCAG 2.4.1 Bypass Blocks Level A.",
                    "recommendation": "Implement a skip navigation link at the top of the body.",
                    "developer_guidance": '<a href="#main" class="sr-only sr-only-focusable">[Skip to Main Content]</a>',
                }
            ],
        }
        mock_provider = MockLLMProvider(custom_response=custom_resp)
        analyzer = AIAccessibilityAnalyzer(provider=mock_provider)

        report = analyzer.analyze_synchronized_evidence({
            "url": "https://example.com",
            "forward": [self.accessible_button_sync],
            "backward": [],
        })

        self.assertEqual(len(report.violations), 1)
        v = report.violations[0]
        self.assertEqual(v.scope, "PAGE")
        self.assertIsNone(v.element_reference)

    # -------------------------------------------------------------------------
    # TEST 10: Invalid AI JSON response handling
    # -------------------------------------------------------------------------
    def test_10_invalid_ai_json_handling(self):
        broken_provider = MockLLMProvider(simulate_invalid_json=True)
        analyzer = AIAccessibilityAnalyzer(provider=broken_provider)

        report = analyzer.analyze_synchronized_evidence({
            "url": "https://example.com/broken",
            "forward": [self.unlabelled_link_sync],
            "backward": [],
        })

        self.assertIsInstance(report, AIAccessibilityAnalysisReport)
        self.assertEqual(report.summary.total_violations, 0)
        self.assertEqual(report.summary.compliance_score, 0.0)
        self.assertEqual(report.analysis_status, "FAILED")

    # -------------------------------------------------------------------------
    # TEST 11: Provider network / timeout failure handling
    # -------------------------------------------------------------------------
    def test_11_provider_failure_handling(self):
        failing_provider = MockLLMProvider(simulate_error="Connection timed out after 45000ms")
        analyzer = AIAccessibilityAnalyzer(provider=failing_provider)

        report = analyzer.analyze_synchronized_evidence({
            "url": "https://example.com/timeout",
            "forward": [self.unlabelled_link_sync],
            "backward": [],
        })

        self.assertIsInstance(report, AIAccessibilityAnalysisReport)
        self.assertEqual(report.analysis_status, "FAILED")
        self.assertEqual(report.summary.total_violations, 0)
        self.assertEqual(report.summary.compliance_score, 0.0)
        self.assertIn("Connection timed out", str(report.ai_metadata.get("errors", [])))

    # -------------------------------------------------------------------------
    # TEST 12: Gemini unavailable -> explicit AI_ANALYSIS_UNAVAILABLE state
    # -------------------------------------------------------------------------
    def test_12_gemini_unavailable_semantics(self):
        fallback_provider = FallbackLLMProvider(
            reason="No GEMINI_API_KEY detected in environment; AI accessibility analysis unavailable."
        )
        analyzer = AIAccessibilityAnalyzer(provider=fallback_provider)

        report = analyzer.analyze_synchronized_evidence({
            "url": "https://example.com/offline",
            "forward": [self.unlabelled_link_sync],
            "backward": [],
        })

        self.assertEqual(report.analysis_status, "AI_ANALYSIS_UNAVAILABLE")
        self.assertEqual(report.summary.total_violations, 0)
        self.assertEqual(report.summary.compliance_score, 0.0)
        self.assertIn("No GEMINI_API_KEY", str(report.ai_metadata.get("error", "")))

    # -------------------------------------------------------------------------
    # TEST 13: Confidence validation (reject invalid floats < 0.0 or > 1.0 or None)
    # -------------------------------------------------------------------------
    def test_13_confidence_validation_rejection(self):
        step_lookup = {1: self.unlabelled_link_sync}
        analyzer = AIAccessibilityAnalyzer(provider=MockLLMProvider())

        valid_raw = {
            "violation_id": "AI-001",
            "scope": "ELEMENT",
            "element_reference": {"direction": "forward", "step": 1},
            "rule_id": "WCAG 4.1.2",
            "rule_name": "Name, Role, Value",
            "severity": "CRITICAL",
            "confidence": 0.95,
            "title": "Test Issue",
            "description": "Test Description",
            "ai_rationale": "Evidence justifies issue.",
            "user_impact": "Impact",
            "wcag_context": "Context",
            "recommendation": "Fix",
            "developer_guidance": "Code",
        }

        # Valid confidence passes
        f, err = analyzer._validate_and_sanitize_finding(valid_raw, step_lookup)
        self.assertIsNotNone(f)
        self.assertEqual(err, "")
        self.assertEqual(f.confidence, 0.95)

        # Confidence > 1.0 rejected
        raw_high = dict(valid_raw, confidence=1.5)
        f_high, err_high = analyzer._validate_and_sanitize_finding(raw_high, step_lookup)
        self.assertIsNone(f_high)
        self.assertIn("out of bounds", err_high)

        # Confidence < 0.0 rejected
        raw_low = dict(valid_raw, confidence=-0.2)
        f_low, err_low = analyzer._validate_and_sanitize_finding(raw_low, step_lookup)
        self.assertIsNone(f_low)
        self.assertIn("out of bounds", err_low)

        # Missing confidence rejected
        raw_none = dict(valid_raw, confidence=None)
        f_none, err_none = analyzer._validate_and_sanitize_finding(raw_none, step_lookup)
        self.assertIsNone(f_none)
        self.assertIn("Missing required confidence", err_none)

    # -------------------------------------------------------------------------
    # TEST 14: Severity validation (reject severities outside allowed enum)
    # -------------------------------------------------------------------------
    def test_14_severity_validation_rejection(self):
        step_lookup = {1: self.unlabelled_link_sync}
        analyzer = AIAccessibilityAnalyzer(provider=MockLLMProvider())

        valid_raw = {
            "violation_id": "AI-001",
            "scope": "ELEMENT",
            "element_reference": {"direction": "forward", "step": 1},
            "rule_id": "WCAG 4.1.2",
            "rule_name": "Name, Role, Value",
            "severity": "CRITICAL",
            "confidence": 0.9,
            "title": "Test",
            "description": "Test",
            "ai_rationale": "Evidence rationale.",
            "user_impact": "Impact",
            "wcag_context": "Context",
            "recommendation": "Fix",
            "developer_guidance": "Code",
        }

        # Valid severities pass
        for sev in ["CRITICAL", "MAJOR", "MINOR", "INFO"]:
            f, err = analyzer._validate_and_sanitize_finding(dict(valid_raw, severity=sev), step_lookup)
            self.assertIsNotNone(f)
            self.assertEqual(f.severity, sev)

        # Invalid severity rejected
        f_bad, err_bad = analyzer._validate_and_sanitize_finding(dict(valid_raw, severity="SUPER_CRITICAL"), step_lookup)
        self.assertIsNone(f_bad)
        self.assertIn("Invalid or missing severity", err_bad)

    # -------------------------------------------------------------------------
    # TEST 15: Scope validation (reject invalid scopes)
    # -------------------------------------------------------------------------
    def test_15_scope_validation_rejection(self):
        step_lookup = {1: self.unlabelled_link_sync}
        analyzer = AIAccessibilityAnalyzer(provider=MockLLMProvider())

        valid_raw = {
            "violation_id": "AI-001",
            "scope": "UNKNOWN_SCOPE",
            "element_reference": {"direction": "forward", "step": 1},
            "rule_id": "WCAG 4.1.2",
            "rule_name": "Name, Role, Value",
            "severity": "MAJOR",
            "confidence": 0.9,
            "title": "Test",
            "description": "Test",
            "ai_rationale": "Evidence rationale.",
            "user_impact": "Impact",
            "wcag_context": "Context",
            "recommendation": "Fix",
            "developer_guidance": "Code",
        }

        f, err = analyzer._validate_and_sanitize_finding(valid_raw, step_lookup)
        self.assertIsNone(f)
        self.assertIn("Invalid or missing scope", err)

    # -------------------------------------------------------------------------
    # TEST 16: Nonexistent element step rejection (e.g. step 9999)
    # -------------------------------------------------------------------------
    def test_16_nonexistent_element_step_rejection(self):
        step_lookup = {1: self.unlabelled_link_sync}  # only step 1 exists
        analyzer = AIAccessibilityAnalyzer(provider=MockLLMProvider())

        fabricated_raw = {
            "violation_id": "AI-FABRICATED",
            "scope": "ELEMENT",
            "element_reference": {"direction": "forward", "step": 9999},
            "rule_id": "WCAG 4.1.2",
            "rule_name": "Name, Role, Value",
            "severity": "CRITICAL",
            "confidence": 0.99,
            "title": "Fabricated Defect on Nonexistent Step",
            "description": "This element does not exist in captured sync data.",
            "ai_rationale": "Imaginary finding.",
            "user_impact": "None",
            "wcag_context": "WCAG 4.1.2",
            "recommendation": "None",
            "developer_guidance": "None",
        }

        finding, err = analyzer._validate_and_sanitize_finding(fabricated_raw, step_lookup)
        self.assertIsNone(finding)
        self.assertIn("Element step 9999 does not exist", err)

    # -------------------------------------------------------------------------
    # TEST 17: Ground-truth evidence immutability (AI cannot overwrite DOM/NVDA)
    # -------------------------------------------------------------------------
    def test_17_ground_truth_evidence_immutability(self):
        sample_audit_data = {
            "url": "https://example.com/test-audit",
            "forward": [self.unlabelled_link_sync],
            "backward": [],
        }
        # AI returns fabricated evidence attempt
        custom_resp = {
            "analysis_status": "COMPLETED",
            "summary": {
                "total_elements_analyzed": 1,
                "total_violations": 1,
                "compliance_score": 85.0,
                "severity_summary": {"CRITICAL": 1, "MAJOR": 0, "MINOR": 0, "INFO": 0},
            },
            "violations": [
                {
                    "violation_id": "AI-001",
                    "scope": "ELEMENT",
                    "element_reference": {"direction": "forward", "step": 1},
                    "rule_id": "WCAG 4.1.2",
                    "rule_name": "Name, Role, Value",
                    "severity": "CRITICAL",
                    "confidence": 0.95,
                    "title": "Unlabelled Link",
                    "description": "Link has no name.",
                    "ai_rationale": "DOM is empty and NVDA announced unlabeled.",
                    "evidence": {
                        "selenium": {"tag": "FABRICATED_TAG", "fake_attr": True},
                        "nvda": {"role": "FABRICATED_ROLE"},
                    },
                    "user_impact": "User barrier.",
                    "wcag_context": "WCAG 4.1.2",
                    "recommendation": "Fix label.",
                    "developer_guidance": '<a href="/" aria-label="[Descriptive accessible name]">[Name]</a>',
                }
            ],
        }
        mock_provider = MockLLMProvider(custom_response=custom_resp)
        analyzer = AIAccessibilityAnalyzer(provider=mock_provider)

        report = analyzer.analyze_synchronized_evidence(sample_audit_data)

        self.assertEqual(len(report.violations), 1)
        v = report.violations[0]

        # Authoritative ground-truth must be preserved, NOT overwritten with FABRICATED_TAG
        self.assertEqual(v.evidence["selenium"].get("tag"), "a")
        self.assertEqual(v.evidence["nvda"].get("role"), "graphic link")
        self.assertEqual(v.evidence["comparison"].get("status"), "ROLE_MATCH_NAME_UNLABELLED")

    # -------------------------------------------------------------------------
    # TEST 18: Partial batch failure -> analysis_status: "PARTIAL"
    # -------------------------------------------------------------------------
    def test_18_partial_batch_failure_status(self):
        class AlternatingMockProvider(MockLLMProvider):
            def generate_analysis(self, system_prompt, user_prompt, violation_data=None):
                self.call_count += 1
                if self.call_count == 1:
                    # Batch 1 succeeds
                    return super().generate_analysis(system_prompt, user_prompt, violation_data)
                else:
                    # Batch 2 fails
                    from tools.ai_providers import LLMResponse
                    return LLMResponse(success=False, error="Batch 2 rate limited HTTP 429", structured_data=None)

        # 2 elements with batch_size=1 -> 2 batches
        data = {
            "url": "https://example.com/multi-batch",
            "forward": [self.unlabelled_link_sync, self.mismatched_element_sync],
            "backward": [],
        }
        alt_provider = AlternatingMockProvider(mode="single_violation")
        analyzer = AIAccessibilityAnalyzer(provider=alt_provider)

        report = analyzer.analyze_synchronized_evidence(data, batch_size=1)

        # Because batch 1 succeeded and batch 2 failed, overall status must be PARTIAL
        self.assertEqual(report.analysis_status, "PARTIAL")
        self.assertEqual(report.ai_metadata.get("successful_batches"), 1)
        self.assertEqual(report.ai_metadata.get("failed_batches"), 1)
        self.assertGreater(len(report.ai_metadata.get("batch_errors", [])), 0)

    # -------------------------------------------------------------------------
    # TEST 19: Summary and score calculated authoritatively from validated findings
    # -------------------------------------------------------------------------
    def test_19_summary_and_score_calculated_from_validated_findings(self):
        # AI returns a summary claiming 99 violations and 10.0 score, but only 1 finding is valid
        custom_resp = {
            "analysis_status": "COMPLETED",
            "summary": {
                "total_elements_analyzed": 5,
                "total_violations": 99,
                "compliance_score": 10.0,
                "severity_summary": {"CRITICAL": 50, "MAJOR": 49, "MINOR": 0, "INFO": 0},
            },
            "violations": [
                {
                    "violation_id": "AI-001",
                    "scope": "ELEMENT",
                    "element_reference": {"direction": "forward", "step": 1},
                    "rule_id": "WCAG 4.1.2",
                    "rule_name": "Name, Role, Value",
                    "severity": "CRITICAL",
                    "confidence": 0.95,
                    "title": "Unlabelled Link",
                    "description": "Missing name",
                    "ai_rationale": "Missing name in DOM and NVDA.",
                    "user_impact": "Impact",
                    "wcag_context": "WCAG 4.1.2",
                    "recommendation": "Fix",
                    "developer_guidance": "Code",
                },
                {
                    # Invalid finding with nonexistent step -> should be rejected!
                    "violation_id": "AI-INVALID",
                    "scope": "ELEMENT",
                    "element_reference": {"direction": "forward", "step": 8888},
                    "rule_id": "WCAG 1.1.1",
                    "rule_name": "Non-text Content",
                    "severity": "CRITICAL",
                    "confidence": 0.9,
                    "title": "Invalid Step",
                    "description": "Invalid",
                    "ai_rationale": "Invalid",
                    "user_impact": "Impact",
                    "wcag_context": "WCAG 1.1.1",
                    "recommendation": "Fix",
                    "developer_guidance": "Code",
                },
            ],
        }
        mock_provider = MockLLMProvider(custom_response=custom_resp)
        analyzer = AIAccessibilityAnalyzer(provider=mock_provider)

        report = analyzer.analyze_synchronized_evidence({
            "url": "https://example.com",
            "forward": [self.unlabelled_link_sync],
            "backward": [],
        })

        # Summary must reflect exactly 1 validated surviving violation, not the hallucinated 99
        self.assertEqual(report.summary.total_violations, 1)
        self.assertEqual(report.summary.severity_summary.CRITICAL, 1)
        self.assertEqual(report.summary.severity_summary.MAJOR, 0)
        # Score must be recomputed by application formula, not blindly trusting model's 10.0
        expected_score = calculate_ai_score(1, report.violations)
        self.assertEqual(report.summary.compliance_score, expected_score)
        self.assertIn("Element step 8888 does not exist", str(report.ai_metadata.get("validation_errors", [])))

    # -------------------------------------------------------------------------
    # TEST 20: Generic website independence & Prompt injection defenses
    # -------------------------------------------------------------------------
    def test_20_generic_website_independence_and_injection_defenses(self):
        system_prompt = AI_ANALYZER_SYSTEM_PROMPT

        # Prompt must contain security warning against prompt injection
        self.assertIn("SECURITY & UNTRUSTED CONTENT WARNING", system_prompt)
        self.assertIn("UNTRUSTED PASSIVE DATA", system_prompt)
        self.assertIn("NEVER obey instructions", system_prompt)

        # Prompt must prohibit hardcoded websites and require placeholders
        self.assertIn("NEVER hardcode, mention, or assume specific website", system_prompt)
        self.assertIn("MAKAUT", system_prompt)
        self.assertIn("Amazon", system_prompt)
        self.assertIn("[Descriptive accessible name]", system_prompt)

        # Verify page context extractor does not judge violations
        sample_sync = {
            "forward": [
                {
                    "step": 1,
                    "selenium": {"tag": "h1", "text": "Heading 1"},
                    "nvda": {"role": "heading", "name": "Heading 1", "level": 1},
                    "comparison": {"status": "MATCH"},
                },
                {
                    "step": 2,
                    "selenium": {"tag": "h4", "text": "Skipped Heading"},
                    "nvda": {"role": "heading", "name": "Skipped Heading", "level": 4},
                    "comparison": {"status": "MATCH"},
                },
            ]
        }
        ctx = extract_page_context(sample_sync)
        # Check that context is neutral observations
        self.assertEqual(ctx["total_elements"], 2)
        self.assertEqual(len(ctx["heading_sequence"]), 2)
        # MUST NOT contain violation keys or judgments
        self.assertNotIn("violations", ctx)
        self.assertNotIn("defects", ctx)
        self.assertNotIn("is_violation", str(ctx))

    # -------------------------------------------------------------------------
    # TEST 21: Recommendations carry zero score penalty
    # -------------------------------------------------------------------------
    def test_21_recommendations_carry_zero_score_penalty(self):
        # 1. Zero violations -> 100.0% score
        self.assertEqual(calculate_ai_score(10, []), 100.0)

        # 2. INFO severity violation carries 0.0 penalty -> 100.0% score
        info_finding = AIViolationFinding(
            violation_id="AI-INFO-1",
            scope="PAGE",
            element_reference=None,
            rule_id="WCAG 1.3.1",
            rule_name="Info and Relationships",
            severity="INFO",
            confidence=0.85,
            title="Informational observation",
            description="Advisory observation without accessibility barrier",
            ai_rationale="Neutral observation",
            user_impact="Minimal",
            wcag_context="Advisory",
            recommendation="Consider structural review",
            developer_guidance="Use semantic tags",
            evidence={"page_context": {}},
        )
        self.assertEqual(calculate_ai_score(10, [info_finding]), 100.0)

        # 3. MAJOR severity violation carries 8.0 penalty -> reduces score
        major_finding = copy.deepcopy(info_finding)
        major_finding.severity = "MAJOR"
        score_with_major = calculate_ai_score(10, [major_finding])
        self.assertEqual(score_with_major, 92.0)
        self.assertLess(score_with_major, 100.0)

    # -------------------------------------------------------------------------
    # TEST 22: Advisory Main Landmark routed to recommendations
    # -------------------------------------------------------------------------
    def test_22_advisory_main_landmark_routed_to_recommendations(self):
        class MainLandmarkMockProvider(MockLLMProvider):
            def generate_analysis(self, system_prompt, user_prompt, image_data=None):
                return type("Resp", (), {
                    "success": True,
                    "error": None,
                    "structured_data": {
                        "analysis_status": "COMPLETED",
                        "summary": {
                            "total_elements_analyzed": 1,
                            "total_violations": 1,
                            "total_recommendations": 0,
                            "compliance_score": 92.0,
                            "severity_summary": {"CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0},
                        },
                        "violations": [
                            {
                                "violation_id": "AI-001",
                                "scope": "PAGE",
                                "element_reference": None,
                                "rule_id": "WCAG 1.3.1",
                                "rule_name": "Info and Relationships",
                                "severity": "MAJOR",
                                "confidence": 0.90,
                                "title": "Missing Main Landmark Region",
                                "description": "The page does not contain a <main> landmark region.",
                                "ai_rationale": "DOM inspection shows banner, nav, and form, but no <main> tag.",
                                "user_impact": "Users cannot jump directly to main content via landmark shortcuts.",
                                "wcag_context": "WCAG 1.3.1 Level A",
                                "recommendation": "Wrap primary content in a <main> element.",
                                "developer_guidance": "Add <main role='main'>[Main Content]</main>.",
                                "evidence": {"page_context": {}},
                            }
                        ],
                        "recommendations": [],
                    }
                })()

        sync_data = {
            "url": "https://example.com",
            "forward": [self.accessible_button_sync],
            "backward": [],
        }
        analyzer = AIAccessibilityAnalyzer(provider=MainLandmarkMockProvider())
        report = analyzer.analyze_synchronized_evidence(sync_data)

        # Main landmark missing must NOT be a violation
        self.assertEqual(len(report.violations), 0)
        self.assertEqual(report.summary.total_violations, 0)

        # Must be routed to recommendations
        self.assertEqual(len(report.recommendations), 1)
        self.assertEqual(report.summary.total_recommendations, 1)
        rec = report.recommendations[0]
        self.assertEqual(rec.category, "BEST_PRACTICE")
        self.assertIn("Main", rec.title)
        self.assertIsNotNone(rec.related_guidance)
        self.assertEqual(rec.related_guidance.get("technique"), "ARIA11")

        # Compliance score must remain 100.0%
        self.assertEqual(report.summary.compliance_score, 100.0)

    # -------------------------------------------------------------------------
    # TEST 23: Advisory H1 routed to recommendations
    # -------------------------------------------------------------------------
    def test_23_advisory_h1_routed_to_recommendations(self):
        class MissingH1MockProvider(MockLLMProvider):
            def generate_analysis(self, system_prompt, user_prompt, image_data=None):
                return type("Resp", (), {
                    "success": True,
                    "error": None,
                    "structured_data": {
                        "analysis_status": "COMPLETED",
                        "summary": {
                            "total_elements_analyzed": 1,
                            "total_violations": 1,
                            "total_recommendations": 0,
                            "compliance_score": 92.0,
                            "severity_summary": {"CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0},
                        },
                        "violations": [
                            {
                                "violation_id": "AI-002",
                                "scope": "PAGE",
                                "element_reference": None,
                                "rule_id": "WCAG 1.3.1",
                                "rule_name": "Info and Relationships",
                                "severity": "MAJOR",
                                "confidence": 0.85,
                                "title": "Missing Level 1 Heading (H1)",
                                "description": "The page structure begins with an H2 heading without a top-level H1.",
                                "ai_rationale": "DOM snapshot shows heading hierarchy starts at level 2.",
                                "user_impact": "Screen reader users lack a primary document title announcement.",
                                "wcag_context": "WCAG 1.3.1 Level A",
                                "recommendation": "Add a descriptive <h1> heading.",
                                "developer_guidance": "Add <h1>[Page Title]</h1>.",
                                "evidence": {"page_context": {}},
                            }
                        ],
                        "recommendations": [],
                    }
                })()

        sync_data = {
            "url": "https://example.com",
            "forward": [self.accessible_button_sync],
            "backward": [],
        }
        analyzer = AIAccessibilityAnalyzer(provider=MissingH1MockProvider())
        report = analyzer.analyze_synchronized_evidence(sync_data)

        # Missing H1 must NOT be a violation
        self.assertEqual(len(report.violations), 0)
        self.assertEqual(report.summary.total_violations, 0)

        # Must be routed to recommendations
        self.assertEqual(len(report.recommendations), 1)
        self.assertEqual(report.summary.total_recommendations, 1)
        rec = report.recommendations[0]
        self.assertEqual(rec.category, "BEST_PRACTICE")
        self.assertIn("H1", rec.title)
        self.assertIsNotNone(rec.related_guidance)
        self.assertEqual(rec.related_guidance.get("technique"), "G141")

        # Compliance score must remain 100.0%
        self.assertEqual(report.summary.compliance_score, 100.0)

    # -------------------------------------------------------------------------
    # TEST 24: Recommendation schema validation and deduplication
    # -------------------------------------------------------------------------
    def test_24_recommendation_schema_and_deduplication(self):
        rec1 = AIRecommendation(
            recommendation_id="REC-001",
            category="BEST_PRACTICE",
            scope="PAGE",
            title="Add Main Landmark",
            description="Enables landmark navigation",
            ai_rationale="Allows quick bypass to main content",
            user_impact="Users can jump directly to primary content",
            developer_guidance="Use <main> element",
        )
        self.assertEqual(rec1.category, "BEST_PRACTICE")
        self.assertEqual(rec1.scope, "PAGE")

        # Invalid scope should raise ValueError
        with self.assertRaises(ValueError):
            AIRecommendation(
                recommendation_id="REC-ERR",
                category="BEST_PRACTICE",
                scope="INVALID_SCOPE",
                title="Invalid",
                description="Invalid",
                ai_rationale="Invalid",
                user_impact="Invalid",
                developer_guidance="Invalid",
            )

        # Category defaults to BEST_PRACTICE when given unknown category
        rec_cat = AIRecommendation(
            recommendation_id="REC-CAT",
            category="UNKNOWN_CAT",
            scope="PAGE",
            title="Cat Test",
            description="Cat Test",
            ai_rationale="Cat Test",
            user_impact="Cat Test",
            developer_guidance="Cat Test",
        )
        self.assertEqual(rec_cat.category, "BEST_PRACTICE")

        # Deduplication merges identical recommendation IDs or titles
        rec2 = copy.deepcopy(rec1)
        rec3 = copy.deepcopy(rec1)
        rec3.recommendation_id = "REC-002"  # same title
        deduped = deduplicate_recommendations([rec1, rec2, rec3])
        self.assertEqual(len(deduped), 1)

    # -------------------------------------------------------------------------
    # TEST 25: Genuine WCAG violation retains violation status and reduces score
    # -------------------------------------------------------------------------
    def test_25_genuine_violation_retains_violation_status(self):
        class GenuineViolationMockProvider(MockLLMProvider):
            def generate_analysis(self, system_prompt, user_prompt, image_data=None):
                return type("Resp", (), {
                    "success": True,
                    "error": None,
                    "structured_data": {
                        "analysis_status": "COMPLETED",
                        "summary": {
                            "total_elements_analyzed": 1,
                            "total_violations": 1,
                            "total_recommendations": 0,
                            "compliance_score": 85.0,
                            "severity_summary": {"CRITICAL": 1, "MAJOR": 0, "MINOR": 0, "INFO": 0},
                        },
                        "violations": [
                            {
                                "violation_id": "AI-001",
                                "scope": "ELEMENT",
                                "element_reference": {"step": 1, "direction": "forward"},
                                "rule_id": "WCAG 4.1.2",
                                "rule_name": "Name, Role, Value",
                                "severity": "CRITICAL",
                                "confidence": 0.95,
                                "title": "Unlabelled Interactive Button",
                                "description": "Interactive button has empty text and no accessible name.",
                                "ai_rationale": "DOM button text is empty; NVDA announces role button with no label.",
                                "normative_basis": {
                                    "success_criterion": "4.1.2",
                                    "level": "A",
                                    "failure_condition": "Interactive element lacks accessible name",
                                    "evidence_basis": ["CORROBORATED [DOM+NVDA]: DOM button text is empty; NVDA announces role button with no label."],
                                },
                                "user_impact": "Blind users cannot determine the function of the button.",
                                "wcag_context": "WCAG 4.1.2 Level A",
                                "recommendation": "Provide an accessible name using aria-label or visible text.",
                                "developer_guidance": "Add aria-label='[Descriptive Action]'.",
                            }
                        ],
                        "recommendations": [],
                    }
                })()

        sync_data = {
            "url": "https://example.com",
            "forward": [self.accessible_button_sync],
            "backward": [],
        }
        analyzer = AIAccessibilityAnalyzer(provider=GenuineViolationMockProvider())
        report = analyzer.analyze_synchronized_evidence(sync_data)

        # Genuine violation must remain in violations
        self.assertEqual(len(report.violations), 1)
        self.assertEqual(report.summary.total_violations, 1)
        self.assertEqual(report.violations[0].rule_id, "WCAG 4.1.2")
        self.assertEqual(report.violations[0].severity, "CRITICAL")
        self.assertIsNotNone(report.violations[0].normative_basis)

        # Compliance score must reflect the penalized score
        expected_score = calculate_ai_score(len(sync_data["forward"]), report.violations)
        self.assertEqual(report.summary.compliance_score, expected_score)

    # -------------------------------------------------------------------------
    # TEST 26: Nested child image in named link adjudicated to recommendation
    # -------------------------------------------------------------------------
    def test_26_nested_child_image_in_named_interactive_element_adjudicated_to_recommendation(self):
        class NestedImgMockProvider(MockLLMProvider):
            def generate_analysis(self, system_prompt, user_prompt, image_data=None):
                return type("Resp", (), {
                    "success": True,
                    "error": None,
                    "structured_data": {
                        "analysis_status": "COMPLETED",
                        "summary": {
                            "total_elements_analyzed": 1,
                            "total_violations": 1,
                            "total_recommendations": 0,
                            "compliance_score": 85.0,
                            "severity_summary": {"CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0},
                        },
                        "violations": [
                            {
                                "violation_id": "AI-001",
                                "scope": "ELEMENT",
                                "element_reference": {"step": 1, "direction": "forward"},
                                "rule_id": "WCAG 1.1.1",
                                "rule_name": "Non-text Content",
                                "severity": "MAJOR",
                                "confidence": 0.90,
                                "title": "Social Media Icons Lack Accessible Text Alternatives",
                                "description": "Footer link icons lack alt attributes on child <img> elements.",
                                "ai_rationale": "Child <img> tag inside <a> element has no alt attribute.",
                                "user_impact": "Screen reader users may hear confusing icon file names.",
                                "wcag_context": "WCAG 1.1.1 Non-text Content (Level A)",
                                "recommendation": "Provide alt text for the child image.",
                                "developer_guidance": "Add alt='' to the decorative icon.",
                            }
                        ],
                        "recommendations": [],
                    }
                })()

        sync_data = {
            "url": "https://example.com",
            "forward": [
                {
                    "step": 1,
                    "selenium": {
                        "tag": "a",
                        "href": "https://example.com/social",
                        "aria_label": "Official Social Media Channel",
                        "text": "",
                    },
                    "nvda": {
                        "name": "Official Social Media Channel",
                        "role": "link",
                        "raw_text": "Official Social Media Channel link",
                    },
                    "comparison": {"name_match": True, "role_match": True, "status": "MATCH"},
                }
            ],
            "backward": [],
        }
        analyzer = AIAccessibilityAnalyzer(provider=NestedImgMockProvider())
        report = analyzer.analyze_synchronized_evidence(sync_data)

        # Violation should be safely downgraded to an advisory recommendation
        self.assertEqual(len(report.violations), 0)
        self.assertEqual(report.summary.total_violations, 0)
        self.assertEqual(len(report.recommendations), 1)
        rec = report.recommendations[0]
        self.assertEqual(rec.category, "BEST_PRACTICE")
        self.assertIn("H67", rec.related_guidance.get("technique", ""))
        self.assertIsNotNone(rec.code_example)
        # Score must be 100.0 (zero score penalty)
        self.assertEqual(report.summary.compliance_score, 100.0)

    # -------------------------------------------------------------------------
    # TEST 26b: Unlabelled image link without author name is retained as violation
    # -------------------------------------------------------------------------
    def test_26b_unlabelled_image_in_interactive_element_retained_as_violation(self):
        class UnlabelledLinkMockProvider(MockLLMProvider):
            def generate_analysis(self, system_prompt, user_prompt, image_data=None):
                return type("Resp", (), {
                    "success": True,
                    "error": None,
                    "structured_data": {
                        "analysis_status": "COMPLETED",
                        "summary": {
                            "total_elements_analyzed": 1,
                            "total_violations": 1,
                            "total_recommendations": 0,
                            "compliance_score": 85.0,
                            "severity_summary": {"CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0},
                        },
                        "violations": [
                            {
                                "violation_id": "AI-001",
                                "scope": "ELEMENT",
                                "element_reference": {"step": 1, "direction": "forward"},
                                "rule_id": "WCAG 2.4.4",
                                "rule_name": "Link Purpose (In Context)",
                                "severity": "MAJOR",
                                "confidence": 0.95,
                                "title": "Unlabelled Icon Link Lacks Accessible Name",
                                "description": "Interactive anchor containing only an unlabelled image has no accessible name.",
                                "ai_rationale": "Link element has no text or aria-label, and child image lacks alt text.",
                                "user_impact": "Screen reader users cannot determine the link purpose.",
                                "wcag_context": "WCAG 2.4.4 Link Purpose (Level A) and WCAG 4.1.2 (Level A)",
                                "recommendation": "Provide an aria-label or alt text describing the destination.",
                                "developer_guidance": "<a href='...' aria-label='Home'><img src='...' alt='' /></a>",
                            }
                        ],
                        "recommendations": [],
                    }
                })()

        sync_data = {
            "url": "https://anywebsite.com",
            "forward": [
                {
                    "step": 1,
                    "selenium": {
                        "tag": "a",
                        "href": "https://anywebsite.com/home",
                        "aria_label": None,
                        "text": "",
                        "title": "",
                    },
                    "nvda": {
                        "name": "home_logo.",
                        "role": "graphic link",
                        "raw_text": "home_logo. Unlabeled graphic same page link",
                    },
                    "comparison": {
                        "name_match": False,
                        "role_match": True,
                        "status": "ROLE_MATCH_NAME_UNLABELLED",
                    },
                }
            ],
            "backward": [],
        }
        analyzer = AIAccessibilityAnalyzer(provider=UnlabelledLinkMockProvider())
        report = analyzer.analyze_synchronized_evidence(sync_data)

        # Must be retained as a normative violation and NOT downgraded to recommendation
        self.assertEqual(len(report.violations), 1)
        self.assertEqual(report.summary.total_violations, 1)
        self.assertEqual(report.violations[0].rule_id, "WCAG 2.4.4")
        self.assertEqual(len(report.recommendations), 0)
        self.assertLess(report.summary.compliance_score, 100.0)

    # -------------------------------------------------------------------------
    # TEST 27: Standalone informative image without alt is retained as violation
    # -------------------------------------------------------------------------
    def test_27_standalone_image_without_alt_retained_as_violation(self):
        class StandaloneImgMockProvider(MockLLMProvider):
            def generate_analysis(self, system_prompt, user_prompt, image_data=None):
                return type("Resp", (), {
                    "success": True,
                    "error": None,
                    "structured_data": {
                        "analysis_status": "COMPLETED",
                        "summary": {
                            "total_elements_analyzed": 1,
                            "total_violations": 1,
                            "total_recommendations": 0,
                            "compliance_score": 92.0,
                            "severity_summary": {"CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0},
                        },
                        "violations": [
                            {
                                "violation_id": "AI-002",
                                "scope": "ELEMENT",
                                "element_reference": {"tag": "img", "src": "diagram.png"},
                                "rule_id": "WCAG 1.1.1",
                                "rule_name": "Non-text Content",
                                "severity": "MAJOR",
                                "confidence": 0.95,
                                "title": "Informative Architecture Diagram Lacks Alt Text",
                                "description": "A standalone architecture infographic is missing an alt attribute.",
                                "ai_rationale": "Standalone <img> has src='diagram.png' and lacks alt attribute.",
                                "normative_basis": {
                                    "success_criterion": "1.1.1",
                                    "level": "A",
                                    "requirement": "All non-text content that is presented to the user has a text alternative that serves the equivalent purpose.",
                                    "failure_condition": "Informative non-text content without text alternative.",
                                    "evidence_basis": ["DIRECT [DOM]: Standalone <img> has src='diagram.png' and lacks alt attribute."],
                                },
                                "user_impact": "Blind users receive no explanation of the diagram.",
                                "wcag_context": "WCAG 1.1.1 Level A",
                                "recommendation": "Add a descriptive alt attribute describing the architecture.",
                                "developer_guidance": "<img src='diagram.png' alt='[Architecture flow chart]' />",
                            }
                        ],
                        "recommendations": [],
                    }
                })()

        sync_data = {
            "url": "https://example.com",
            "forward": [self.accessible_button_sync],
            "backward": [],
        }
        analyzer = AIAccessibilityAnalyzer(provider=StandaloneImgMockProvider())
        report = analyzer.analyze_synchronized_evidence(sync_data)

        # Standalone image violation must be preserved
        self.assertEqual(len(report.violations), 1)
        self.assertEqual(report.summary.total_violations, 1)
        v = report.violations[0]
        self.assertEqual(v.rule_id, "WCAG 1.1.1")
        self.assertEqual(v.normative_basis.requirement, "All non-text content that is presented to the user has a text alternative that serves the equivalent purpose.")
        # Score must be deducted
        self.assertLess(report.summary.compliance_score, 100.0)

    # -------------------------------------------------------------------------
    # TEST 28: CAPTCHA challenge misclassified under 4.1.2 downgraded to recommendation
    # -------------------------------------------------------------------------
    def test_28_captcha_challenge_mapped_to_412_downgraded_to_recommendation(self):
        class CaptchaMockProvider(MockLLMProvider):
            def generate_analysis(self, system_prompt, user_prompt, image_data=None):
                return type("Resp", (), {
                    "success": True,
                    "error": None,
                    "structured_data": {
                        "analysis_status": "COMPLETED",
                        "summary": {
                            "total_elements_analyzed": 1,
                            "total_violations": 1,
                            "total_recommendations": 0,
                            "compliance_score": 85.0,
                            "severity_summary": {"CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0},
                        },
                        "violations": [
                            {
                                "violation_id": "AI-003",
                                "scope": "ELEMENT",
                                "element_reference": {"tag": "img", "src": "captcha.jpg"},
                                "rule_id": "WCAG 4.1.2",
                                "rule_name": "Name, Role, Value",
                                "severity": "MAJOR",
                                "confidence": 0.85,
                                "title": "Captcha Image Lacks Descriptive Text Alternative",
                                "description": "The captcha image has alt='Captcha Image here' which does not transcribe the characters.",
                                "ai_rationale": "The captcha image does not reveal the distorted security characters.",
                                "user_impact": "Users cannot read the captcha characters.",
                                "wcag_context": "WCAG 4.1.2",
                                "recommendation": "Provide audio captcha alternative.",
                                "developer_guidance": "Add audio alternative.",
                            }
                        ],
                        "recommendations": [],
                    }
                })()

        sync_data = {
            "url": "https://example.com",
            "forward": [self.accessible_button_sync],
            "backward": [],
        }
        analyzer = AIAccessibilityAnalyzer(provider=CaptchaMockProvider())
        report = analyzer.analyze_synchronized_evidence(sync_data)

        # Captcha 4.1.2 misclassification should be downgraded to G144 recommendation
        self.assertEqual(len(report.violations), 0)
        self.assertEqual(report.summary.total_violations, 0)
        self.assertEqual(len(report.recommendations), 1)
        rec = report.recommendations[0]
        self.assertEqual(rec.category, "BEST_PRACTICE")
        self.assertIn("G144", rec.related_guidance.get("technique", ""))
        self.assertEqual(report.summary.compliance_score, 100.0)

    # -------------------------------------------------------------------------
    # TEST 29: AINormativeBasis model parsing and validation
    # -------------------------------------------------------------------------
    def test_29_normative_basis_parsing_and_model(self):
        from tools.ai_agent import AINormativeBasis
        nb = AINormativeBasis(
            success_criterion="1.1.1",
            level="A",
            requirement="Provide text alternatives for non-text content.",
            failure_condition="Missing alt attribute on informative image.",
            evidence_basis=["DOM", "nvda"],
        )
        self.assertEqual(nb.success_criterion, "1.1.1")
        self.assertEqual(nb.level, "A")
        self.assertEqual(nb.requirement, "Provide text alternatives for non-text content.")
        self.assertEqual(nb.failure_condition, "Missing alt attribute on informative image.")
        self.assertEqual(nb.evidence_basis, ["DOM", "NVDA"])

    # -------------------------------------------------------------------------
    # TEST 30: Normative basis regex extraction of concatenated LLM string
    # -------------------------------------------------------------------------
    def test_30_normative_basis_regex_extraction_of_concatenated_string(self):
        finding_data = {
            "violation_id": "AI-001",
            "scope": "ELEMENT",
            "element_reference": {"direction": "forward", "step": 1},
            "rule_id": "WCAG 2.4.4",
            "rule_name": "Link Purpose (In Context)",
            "severity": "MAJOR",
            "confidence": 0.9,
            "title": "Generic link text",
            "description": "Repeated generic link text without context",
            "ai_rationale": "DOM shows generic text",
            "normative_basis": {
                "success_criterion": "2.4.4vLevel A\nFailure Condition: Multiple links have identical text pointing to different destinations without distinguishing context.\nEvidence Basis: [DOM, NVDA, INTERACTION]",
            },
            "user_impact": "Disorientation",
            "wcag_context": "WCAG 2.4.4 Level A",
            "recommendation": "Use descriptive text",
            "developer_guidance": "Add aria-label",
        }
        finding = AIViolationFinding(**finding_data)
        self.assertIsNotNone(finding.normative_basis)
        self.assertEqual(finding.normative_basis.success_criterion, "2.4.4")
        self.assertEqual(finding.normative_basis.level, "A")
        self.assertEqual(
            finding.normative_basis.failure_condition,
            "Multiple links have identical text pointing to different destinations without distinguishing context."
        )
        self.assertEqual(finding.normative_basis.evidence_basis, ["DOM", "NVDA", "INTERACTION"])

    # -------------------------------------------------------------------------
    # TEST 31: Adjudication: Link Purpose with heading/section context downgraded to recommendation
    # -------------------------------------------------------------------------
    def test_31_adjudication_link_purpose_with_context_downgraded_to_recommendation(self):
        class LinkMockProvider(MockLLMProvider):
            def generate_analysis(self, system_prompt, user_prompt, image_data=None):
                return type("Resp", (), {
                    "success": True,
                    "error": None,
                    "structured_data": {
                        "analysis_status": "COMPLETED",
                        "summary": {
                            "total_elements_analyzed": 1,
                            "total_violations": 1,
                            "total_recommendations": 0,
                            "compliance_score": 92.0,
                            "severity_summary": {"CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0},
                        },
                        "violations": [
                            {
                                "violation_id": "AI-001",
                                "scope": "ELEMENT",
                                "element_reference": {"direction": "forward", "step": 1},
                                "rule_id": "WCAG 2.4.4",
                                "rule_name": "Link Purpose (In Context)",
                                "severity": "MAJOR",
                                "confidence": 0.85,
                                "title": "Ambiguous 'Click to Visit' link text",
                                "description": "Generic link text 'Click to Visit' used for link.",
                                "ai_rationale": "Same link text pointing to destination.",
                                "normative_basis": {
                                    "success_criterion": "2.4.4",
                                    "level": "A",
                                    "requirement": "The purpose of each link can be determined from the link text alone or from the link text together with its programmatically determined link context.",
                                    "failure_condition": "Generic link text",
                                    "evidence_basis": ["DOM", "NVDA"],
                                },
                                "user_impact": "Users navigating out of context may need to check headings.",
                                "wcag_context": "WCAG 2.4.4 Level A",
                                "recommendation": "Provide standalone descriptive text.",
                                "developer_guidance": "Add aria-label.",
                            }
                        ],
                        "recommendations": [],
                    }
                })()

        sync_data = {
            "url": "https://example.org/portal",
            "forward": [
                {
                    "step": 1,
                    "selenium": {"tag": "a", "text": "Click to Visit", "href": "https://example.org/notices"},
                    "nvda": {"role": "link", "name": "Click to Visit"},
                    "comparison": {"status": "MATCH", "name_match": True, "role_match": True},
                }
            ],
            "backward": [],
        }
        unified_pkg = {
            "url": "https://example.org/portal",
            "synchronized_evidence": sync_data,
            "correlated_elements": [
                {
                    "direction": "forward",
                    "step": 1,
                    "correlation": {"status": "MATCH", "confidence": 1.0},
                    "dom_context": {
                        "nearest_heading": "Letters & Notices",
                        "nearest_heading_level": 3,
                        "parent_section": "Letters & Notices",
                    }
                }
            ],
            "dom_snapshot": {
                "headings": [{"level": 3, "text": "Letters & Notices"}],
                "context_blocks": [{"heading": "Letters & Notices"}],
            }
        }

        analyzer = AIAccessibilityAnalyzer(provider=LinkMockProvider())
        report = analyzer.analyze_synchronized_evidence(sync_data, unified_package=unified_pkg)

        # AI-001 should be adjudicated to RECOMMENDATION (H80) because nearest heading provides programmatic context
        self.assertEqual(len(report.violations), 0)
        self.assertEqual(len(report.recommendations), 1)
        rec = report.recommendations[0]
        self.assertEqual(rec.category, "BEST_PRACTICE")
        self.assertEqual(rec.related_guidance.get("success_criterion"), "2.4.4")
        self.assertEqual(rec.related_guidance.get("technique"), "H80")
        self.assertEqual(report.summary.compliance_score, 100.0)

    # -------------------------------------------------------------------------
    # TEST 32: Adjudication: Informative logo lacking alt text retained as violation
    # -------------------------------------------------------------------------
    def test_32_adjudication_informative_logo_retained_as_violation(self):
        class LogoMockProvider(MockLLMProvider):
            def generate_analysis(self, system_prompt, user_prompt, image_data=None):
                return type("Resp", (), {
                    "success": True,
                    "error": None,
                    "structured_data": {
                        "analysis_status": "COMPLETED",
                        "summary": {
                            "total_elements_analyzed": 1,
                            "total_violations": 1,
                            "total_recommendations": 0,
                            "compliance_score": 92.0,
                            "severity_summary": {"CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0},
                        },
                        "violations": [
                            {
                                "violation_id": "AI-002",
                                "scope": "ELEMENT",
                                "element_reference": {"tag": "img", "src": "images/logo.png"},
                                "rule_id": "WCAG 1.1.1",
                                "rule_name": "Non-text Content",
                                "severity": "MAJOR",
                                "confidence": 0.95,
                                "title": "University logo missing alternative text",
                                "description": "The primary university branding logo has no alt attribute.",
                                "ai_rationale": "DOM snapshot shows alt=null and image is the sole branding identifier.",
                                "normative_basis": {
                                    "success_criterion": "1.1.1",
                                    "level": "A",
                                    "requirement": "All non-text content that is presented to the user has a text alternative that serves the equivalent purpose.",
                                    "failure_condition": "Informative branding logo lacks alt text.",
                                    "evidence_basis": ["DIRECT [DOM]: DOM snapshot shows alt=null and image is the sole branding identifier."],
                                },
                                "user_impact": "Screen reader users cannot identify the organization branding.",
                                "wcag_context": "WCAG 1.1.1 Level A",
                                "recommendation": "Add descriptive alt text to the logo.",
                                "developer_guidance": "Add alt='[Organization Name] Logo'.",
                            }
                        ],
                        "recommendations": [],
                    }
                })()

        sync_data = {
            "url": "https://example.org/portal",
            "forward": [
                {
                    "step": 1,
                    "selenium": {"tag": "a", "text": "Home", "href": "/"},
                    "nvda": {"role": "link", "name": "Home"},
                    "comparison": {"status": "MATCH", "name_match": True, "role_match": True},
                }
            ],
            "backward": [],
        }
        unified_pkg = {
            "url": "https://example.org/portal",
            "dom_snapshot": {
                "images": [
                    {
                        "tag": "img",
                        "src": "images/logo.png",
                        "alt": None,
                        "parent_context": "brand",
                    }
                ]
            }
        }

        analyzer = AIAccessibilityAnalyzer(provider=LogoMockProvider())
        report = analyzer.analyze_synchronized_evidence(sync_data, unified_package=unified_pkg)

        # Informative branding logo missing alt must remain a NORMATIVE VIOLATION under WCAG 1.1.1
        self.assertEqual(len(report.violations), 1)
        v = report.violations[0]
        self.assertEqual(v.rule_id, "WCAG 1.1.1")
        self.assertEqual(v.severity, "MAJOR")
        self.assertEqual(report.summary.compliance_score, 92.0)

    # -------------------------------------------------------------------------
    # TEST 34: Unique sequential recommendation and violation IDs
    # -------------------------------------------------------------------------
    def test_34_unique_sequential_recommendation_and_violation_ids(self):
        # 1. Deduplication re-indexes duplicate recommendation IDs sequentially
        rec_a = AIRecommendation(
            recommendation_id="REC-001",
            category="BEST_PRACTICE",
            scope="PAGE",
            title="Improve Link Purpose",
            description="Descriptive text",
            ai_rationale="Benefits users",
            user_impact="High",
            developer_guidance="Use aria-label",
        )
        rec_b = AIRecommendation(
            recommendation_id="REC-002",
            category="STRUCTURAL_ENHANCEMENT",
            scope="ELEMENT",
            title="Add Decorative Alt Text",
            description="Descriptive text",
            ai_rationale="Benefits users",
            user_impact="Medium",
            developer_guidance="Add alt=''",
        )
        rec_c = AIRecommendation(
            recommendation_id="REC-002",  # Duplicate REC-002 from adjudication
            category="BEST_PRACTICE",
            scope="ELEMENT",
            title="Provide Standalone Descriptive Link Text",
            description="Descriptive text",
            ai_rationale="Benefits users",
            user_impact="High",
            developer_guidance="Make link text unique",
        )
        deduped_recs = deduplicate_recommendations([rec_a, rec_b, rec_c])
        self.assertEqual(len(deduped_recs), 3)
        rec_ids = [r.recommendation_id for r in deduped_recs]
        self.assertEqual(rec_ids, ["REC-001", "REC-002", "REC-003"])
        self.assertEqual(len(rec_ids), len(set(rec_ids)))  # All IDs strictly unique

        # 2. Deduplication re-indexes duplicate violation IDs sequentially
        v_a = AIViolationFinding(
            violation_id="AI-001",
            scope="ELEMENT",
            element_reference={"step": 1},
            rule_id="WCAG 4.1.2",
            rule_name="Name, Role, Value",
            severity="CRITICAL",
            confidence=0.9,
            title="Unlabelled Button A",
            description="Missing accessible name",
            ai_rationale="Violates 4.1.2",
            user_impact="High",
            wcag_context="Level A",
            recommendation="Add label",
            developer_guidance="Use aria-label",
        )
        v_b = AIViolationFinding(
            violation_id="AI-001",  # Overlapping ID from batch 2
            scope="ELEMENT",
            element_reference={"step": 2},
            rule_id="WCAG 1.3.1",
            rule_name="Info and Relationships",
            severity="MAJOR",
            confidence=0.85,
            title="Unlabelled Form Field B",
            description="Missing label element",
            ai_rationale="Violates 1.3.1",
            user_impact="High",
            wcag_context="Level A",
            recommendation="Associate label",
            developer_guidance="Use <label for>",
        )
        deduped_violations = deduplicate_violations([v_a, v_b])
        self.assertEqual(len(deduped_violations), 2)
        v_ids = [v.violation_id for v in deduped_violations]
        self.assertEqual(v_ids, ["AI-001", "AI-002"])
        self.assertEqual(len(v_ids), len(set(v_ids)))  # All IDs strictly unique

        # 3. Full analyzer run produces unique recommendation IDs when adjudication converts a finding
        class AdjudicationCollisionMockProvider(MockLLMProvider):
            def generate_analysis(self, system_prompt, user_prompt, image_data=None):
                return type("Resp", (), {
                    "success": True,
                    "error": None,
                    "structured_data": {
                        "analysis_status": "COMPLETED",
                        "summary": {
                            "total_elements_analyzed": 2,
                            "total_violations": 1,
                            "total_recommendations": 2,
                            "compliance_score": 100.0,
                            "severity_summary": {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "INFO": 0},
                        },
                        "violations": [
                            # Gemini returns this as AI-002, which Gate 4 converts to a recommendation
                            {
                                "violation_id": "AI-002",
                                "scope": "ELEMENT",
                                "element_reference": {"step": 1, "direction": "forward"},
                                "rule_id": "WCAG 2.4.4",
                                "rule_name": "Link Purpose (In Context)",
                                "severity": "MINOR",
                                "confidence": 0.8,
                                "title": "Ambiguous Generic Link Text",
                                "description": "Link text 'Click to Visit' is generic.",
                                "ai_rationale": "Link text should describe destination.",
                                "user_impact": "Screen reader users need clear links.",
                                "wcag_context": "WCAG 2.4.4 Level A",
                                "recommendation": "Provide unique text.",
                                "developer_guidance": "Add aria-label.",
                            }
                        ],
                        "recommendations": [
                            # Gemini ALSO returns REC-001 and REC-002
                            {
                                "recommendation_id": "REC-001",
                                "scope": "PAGE",
                                "category": "STRUCTURAL_ENHANCEMENT",
                                "title": "Add Skip Navigation Link",
                                "description": "Add skip link",
                                "ai_rationale": "Improves bypass",
                                "user_impact": "Keyboard users",
                                "developer_guidance": "<a href='#main'>Skip</a>",
                            },
                            {
                                "recommendation_id": "REC-002",
                                "scope": "ELEMENT",
                                "category": "STRUCTURAL_ENHANCEMENT",
                                "title": "Add Decorative Alt Text",
                                "description": "Decorative image",
                                "ai_rationale": "Reduces noise",
                                "user_impact": "Screen reader users",
                                "developer_guidance": "alt=''",
                            }
                        ],
                    },
                })()

        analyzer = AIAccessibilityAnalyzer(provider=AdjudicationCollisionMockProvider())
        sync_data = {
            "url": "https://example.org/test",
            "forward": [
                {
                    "step": 1,
                    "selenium": {"tag": "a", "text": "Click to Visit", "href": "/about"},
                    "nvda": {"role": "link", "name": "Click to Visit"},
                    "context": {"nearest_heading": "About Us", "parent_section": "Company Info"},
                    "comparison": {"status": "MATCH", "name_match": True, "role_match": True},
                }
            ],
            "backward": [],
        }
        report = analyzer.analyze_synchronized_evidence(sync_data)
        self.assertEqual(len(report.recommendations), 3)
        final_rec_ids = [r.recommendation_id for r in report.recommendations]
        self.assertEqual(final_rec_ids, ["REC-001", "REC-002", "REC-003"])
        self.assertEqual(len(final_rec_ids), len(set(final_rec_ids)))


if __name__ == "__main__":
    unittest.main(verbosity=2)



