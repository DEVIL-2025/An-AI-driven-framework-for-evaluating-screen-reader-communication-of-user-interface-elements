"""
Generic Regression Test Suite for Accessibility Audit Evidence Pipeline
Verifies the 10 core regression test cases defined in Requirement 16:
- TEST 1: Captured text field with visible unannounced validation error
- TEST 2: Captured field with correct accessible name and no error
- TEST 3: Captured field with correct accessible name but unannounced validation error (independent analysis)
- TEST 4: Captured link with aria-label matching NVDA announcement
- TEST 5: Captured link with no meaningful name ("link")
- TEST 6: Forward and backward traversal deduplication into 1 unique element
- TEST 7: Configurable N-element dynamic traversal population
- TEST 8: Full DOM snapshot elements not traversed are excluded from audit population
- TEST 9: Initialization speech events excluded from interactive element count
- TEST 10: Validation error in nearby DOM container captured without surrounding_text

All tests are completely generic with NO website-specific or sample-specific hardcoding.
"""

import copy
import json
import unittest
from typing import Dict, Any, List

from tools.evidence_correlator import (
    assemble_unified_evidence_package,
    build_audit_population,
    compute_stable_element_identity,
    correlate_direction_elements,
    extract_dom_context,
)
from tools.ai_agent import (
    AIAccessibilityAnalyzer,
    prepare_compact_evidence,
    format_multimodal_user_prompt,
    extract_page_context,
)
from tools.ai_providers import MockLLMProvider


class TestAuditEvidencePipeline(unittest.TestCase):
    """Generic regression tests for the synchronized evidence and AI audit pipeline."""

    def test_01_visible_unannounced_validation_error(self):
        """
        TEST 1: A captured text field has a visible validation error and NVDA does not announce the error.
        Expected: The evidence package contains enough structured information for the AI to detect the discrepancy.
        """
        sync_data = {
            "url": "https://generic-test.org/form",
            "forward": [
                {
                    "step": 1,
                    "selenium": {
                        "tag": "input",
                        "id": "field_user_account",
                        "name": "user_account",
                        "type": "text",
                    },
                    "nvda": {
                        "role": "edit",
                        "name": "User Account",
                        "raw_text": "User Account edit blank",
                    },
                    "comparison": {
                        "status": "MATCH",
                        "name_match": True,
                        "role_match": True,
                    },
                }
            ],
            "backward": [],
            "initialization": {"events": []},
        }

        dom_snapshot = {
            "interactive_elements": [
                {
                    "tag": "input",
                    "id": "field_user_account",
                    "name": "user_account",
                    "type": "text",
                    "label_text": "User Account",
                    "validation_context": {
                        "has_error": True,
                        "error_text": "User Account is required",
                        "error_nodes": [
                            {
                                "selector": ".validation-msg",
                                "text": "User Account is required",
                                "role": "alert",
                                "id": "err_user_account",
                                "relationship": "sibling",
                            }
                        ],
                        "programmatic_association": {
                            "aria_describedby": None,
                            "aria_errormessage": None,
                            "resolved": False,
                            "is_associated": False,
                        },
                    },
                    "surrounding_text": None,
                }
            ]
        }

        package = assemble_unified_evidence_package(
            "https://generic-test.org/form", sync_data, dom_snapshot
        )
        audit_pop = package["synchronized_evidence"]["audit_population"]
        self.assertEqual(audit_pop["unique_element_count"], 1)

        elem = audit_pop["elements"][0]
        self.assertIsNotNone(elem.get("validation_context"))
        self.assertTrue(elem["validation_context"]["has_error"])
        self.assertEqual(elem["validation_context"]["error_text"], "User Account is required")

        # Prepare compact evidence and format prompt
        compact_elements, step_lookup = prepare_compact_evidence(package["synchronized_evidence"], dom_snapshot)
        page_ctx = extract_page_context(package["synchronized_evidence"])
        prompt = format_multimodal_user_prompt(
            "https://generic-test.org/form", 1, 1, compact_elements, page_ctx, dom_snapshot
        )

        # Discrepancy is explicitly visible in the AI prompt: error exists but not in NVDA speech
        self.assertIn("User Account is required", prompt)
        self.assertIn("User Account edit blank", prompt)
        self.assertNotIn("User Account is required", elem["nvda"]["raw_text"])

    def test_02_correct_accessible_name_and_no_error(self):
        """
        TEST 2: A captured field has correct accessible name and no error.
        Expected: No false validation violation.
        """
        sync_data = {
            "url": "https://generic-test.org/search",
            "forward": [
                {
                    "step": 1,
                    "selenium": {
                        "tag": "input",
                        "id": "query_input",
                        "name": "q",
                        "type": "search",
                    },
                    "nvda": {
                        "role": "edit",
                        "name": "Search Catalog",
                        "raw_text": "Search Catalog edit blank",
                    },
                    "comparison": {
                        "status": "MATCH",
                        "name_match": True,
                        "role_match": True,
                    },
                }
            ],
            "backward": [],
            "initialization": {"events": []},
        }

        dom_snapshot = {
            "interactive_elements": [
                {
                    "tag": "input",
                    "id": "query_input",
                    "name": "q",
                    "type": "search",
                    "label_text": "Search Catalog",
                    "validation_context": {
                        "has_error": False,
                        "error_text": None,
                        "error_nodes": [],
                        "programmatic_association": {
                            "aria_describedby": None,
                            "aria_errormessage": None,
                            "resolved": False,
                            "is_associated": False,
                        },
                    },
                }
            ]
        }

        package = assemble_unified_evidence_package(
            "https://generic-test.org/search", sync_data, dom_snapshot
        )
        elem = package["synchronized_evidence"]["audit_population"]["elements"][0]
        self.assertFalse(elem["validation_context"]["has_error"])

        # Run analyzer with zero-violation mock
        analyzer = AIAccessibilityAnalyzer(provider=MockLLMProvider(mode="zero_violations"))
        report = analyzer.analyze_synchronized_evidence(
            package["synchronized_evidence"],
            unified_package=package,
        )

        self.assertEqual(report.summary.total_violations, 0)
        self.assertEqual(len(report.violations), 0)
        self.assertEqual(report.summary.compliance_score, 100.0)

    def test_03_accessible_name_passes_while_error_analysis_fails(self):
        """
        TEST 3: A captured field has correct accessible name but an unannounced validation error.
        Expected: Name analysis can PASS while error analysis can FAIL independently.
        """
        sync_data = {
            "url": "https://generic-test.org/account",
            "forward": [
                {
                    "step": 1,
                    "selenium": {
                        "tag": "input",
                        "id": "email_input",
                        "name": "user_email",
                        "type": "email",
                    },
                    "nvda": {
                        "role": "edit",
                        "name": "Email Address",
                        "raw_text": "Email Address edit blank",
                    },
                    "comparison": {
                        "status": "MATCH",
                        "name_match": True,
                        "role_match": True,
                    },
                }
            ],
            "backward": [],
            "initialization": {"events": []},
        }

        dom_snapshot = {
            "interactive_elements": [
                {
                    "tag": "input",
                    "id": "email_input",
                    "name": "user_email",
                    "type": "email",
                    "label_text": "Email Address",
                    "validation_context": {
                        "has_error": True,
                        "error_text": "Valid email address is required",
                        "error_nodes": [
                            {
                                "selector": ".err-txt",
                                "text": "Valid email address is required",
                                "role": "alert",
                            }
                        ],
                        "programmatic_association": {
                            "aria_describedby": None,
                            "aria_errormessage": None,
                            "resolved": False,
                            "is_associated": False,
                        },
                    },
                }
            ]
        }

        package = assemble_unified_evidence_package(
            "https://generic-test.org/account", sync_data, dom_snapshot
        )
        elem = package["synchronized_evidence"]["audit_population"]["elements"][0]

        # Name analysis check: Accessible name is fully resolved and matches NVDA speech
        self.assertEqual(elem["selenium"].get("label_text") or elem["dom_context"].get("label_text"), "Email Address")
        self.assertEqual(elem["nvda"]["name"], "Email Address")
        self.assertTrue(elem["comparison"]["name_match"])

        # Error analysis check: Visible error exists but is unannounced
        val_ctx = elem["validation_context"]
        self.assertTrue(val_ctx["has_error"])
        self.assertNotIn("Valid email address is required", elem["nvda"]["raw_text"])

        # Adjudicate simulated finding: An error identification finding is valid and retains both contexts
        custom_finding = {
            "analysis_status": "COMPLETED",
            "summary": {
                "total_elements_analyzed": 1,
                "total_violations": 1,
                "total_recommendations": 0,
                "compliance_score": 75.0,
                "severity_summary": {"CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0},
            },
            "violations": [
                {
                    "violation_id": "AI-001",
                    "scope": "ELEMENT",
                    "element_reference": {"direction": "forward", "step": 1},
                    "rule_id": "WCAG 3.3.1",
                    "rule_name": "Error Identification",
                    "severity": "MAJOR",
                    "confidence": 0.95,
                    "title": "Visible form validation error is not programmatically announced",
                    "description": "The field 'Email Address' has visible error 'Valid email address is required' but lacks programmatic association.",
                    "ai_rationale": "DOM validation_context indicates has_error=True with visible message, but NVDA announced only 'Email Address edit blank'.",
                    "normative_basis": {
                        "success_criterion": "3.3.1",
                        "level": "A",
                        "requirement": "Error Identification",
                        "failure_condition": "Input error is detected and displayed visually but not announced to assistive technology",
                        "evidence_basis": ["DOM", "NVDA"],
                    },
                    "user_impact": "Screen reader users cannot determine why form submission failed.",
                    "wcag_context": "WCAG 2.1 Success Criterion 3.3.1 Level A",
                    "recommendation": "Associate error text using aria-describedby or expose aria-invalid.",
                    "developer_guidance": "Add aria-describedby pointing to the error message container.",
                }
            ],
            "recommendations": [],
        }

        mock = MockLLMProvider(custom_response=custom_finding)
        analyzer = AIAccessibilityAnalyzer(provider=mock)
        report = analyzer.analyze_synchronized_evidence(
            package["synchronized_evidence"],
            unified_package=package,
        )

        self.assertEqual(report.summary.total_violations, 1)
        v = report.violations[0]
        self.assertEqual(v.rule_id, "WCAG 3.3.1")
        # Authoritative ground truth preserves both the correct accessible name and the error context
        self.assertEqual(v.evidence["nvda"]["name"], "Email Address")
        self.assertTrue(v.evidence["validation_context"]["has_error"])

    def test_04_link_with_aria_label_matching_nvda(self):
        """
        TEST 4: A captured link has aria-label and NVDA announces the same name.
        Expected: No false accessible-name violation.
        """
        sync_data = {
            "url": "https://generic-test.org/nav",
            "forward": [
                {
                    "step": 1,
                    "selenium": {
                        "tag": "a",
                        "id": "nav_link_privacy",
                        "href": "/privacy-policy",
                        "aria_label": "Privacy Policy Statement",
                        "text": "",
                    },
                    "nvda": {
                        "role": "link",
                        "name": "Privacy Policy Statement",
                        "raw_text": "Privacy Policy Statement link",
                    },
                    "comparison": {
                        "status": "MATCH",
                        "name_match": True,
                        "role_match": True,
                    },
                }
            ],
            "backward": [],
            "initialization": {"events": []},
        }

        dom_snapshot = {
            "interactive_elements": [
                {
                    "tag": "a",
                    "id": "nav_link_privacy",
                    "href": "/privacy-policy",
                    "aria_label": "Privacy Policy Statement",
                }
            ]
        }

        package = assemble_unified_evidence_package(
            "https://generic-test.org/nav", sync_data, dom_snapshot
        )
        elem = package["synchronized_evidence"]["audit_population"]["elements"][0]

        self.assertEqual(elem["selenium"].get("aria_label"), "Privacy Policy Statement")
        self.assertEqual(elem["nvda"].get("name"), "Privacy Policy Statement")
        self.assertEqual(elem["comparison"].get("status"), "MATCH")

        # Zero violations expected for well-labelled link
        analyzer = AIAccessibilityAnalyzer(provider=MockLLMProvider(mode="zero_violations"))
        report = analyzer.analyze_synchronized_evidence(
            package["synchronized_evidence"],
            unified_package=package,
        )
        self.assertEqual(report.summary.total_violations, 0)

    def test_05_link_with_vague_name_supports_finding(self):
        """
        TEST 5: A captured link has no meaningful name and NVDA announces only 'link'.
        Expected: The evidence supports a potential accessible-name finding.
        """
        sync_data = {
            "url": "https://generic-test.org/article",
            "forward": [
                {
                    "step": 1,
                    "selenium": {
                        "tag": "a",
                        "id": "empty_action_link",
                        "href": "/next-item",
                        "text": "",
                        "aria_label": None,
                    },
                    "nvda": {
                        "role": "link",
                        "name": "",
                        "raw_text": "link",
                    },
                    "comparison": {
                        "status": "ROLE_MATCH_NAME_EMPTY",
                        "name_match": False,
                        "role_match": True,
                    },
                }
            ],
            "backward": [],
            "initialization": {"events": []},
        }

        dom_snapshot = {
            "interactive_elements": [
                {
                    "tag": "a",
                    "id": "empty_action_link",
                    "href": "/next-item",
                    "text": "",
                    "aria_label": None,
                }
            ]
        }

        package = assemble_unified_evidence_package(
            "https://generic-test.org/article", sync_data, dom_snapshot
        )
        elem = package["synchronized_evidence"]["audit_population"]["elements"][0]

        # Ground truth explicitly documents unlabelled status
        self.assertEqual(elem["comparison"]["status"], "ROLE_MATCH_NAME_EMPTY")
        self.assertIn("link", elem["nvda"]["raw_text"].lower())

        finding_payload = {
            "analysis_status": "COMPLETED",
            "summary": {
                "total_elements_analyzed": 1,
                "total_violations": 1,
                "total_recommendations": 0,
                "compliance_score": 75.0,
                "severity_summary": {"CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0},
            },
            "violations": [
                {
                    "violation_id": "AI-001",
                    "scope": "ELEMENT",
                    "element_reference": {"direction": "forward", "step": 1},
                    "rule_id": "WCAG 4.1.2",
                    "rule_name": "Name, Role, Value",
                    "severity": "MAJOR",
                    "confidence": 0.95,
                    "title": "Link lacks accessible name",
                    "description": "Link element has no inner text or aria-label; NVDA announces only 'link'.",
                    "ai_rationale": "DOM text and aria_label are empty, NVDA name is empty with comparison status ROLE_MATCH_NAME_EMPTY.",
                    "normative_basis": {
                        "success_criterion": "4.1.2",
                        "level": "A",
                        "requirement": "Name, Role, Value",
                        "failure_condition": "Interactive element has no discernible accessible name",
                        "evidence_basis": ["DOM", "NVDA"],
                    },
                    "user_impact": "Users cannot know the purpose or destination of the link.",
                    "wcag_context": "WCAG 2.1 Success Criterion 4.1.2 Level A",
                    "recommendation": "Provide descriptive link text or an aria-label.",
                    "developer_guidance": "Add aria-label='[Descriptive destination name]'.",
                }
            ],
            "recommendations": [],
        }

        analyzer = AIAccessibilityAnalyzer(provider=MockLLMProvider(custom_response=finding_payload))
        report = analyzer.analyze_synchronized_evidence(
            package["synchronized_evidence"],
            unified_package=package,
        )

        self.assertEqual(report.summary.total_violations, 1)
        self.assertEqual(report.violations[0].rule_id, "WCAG 4.1.2")

    def test_06_forward_and_backward_deduplication(self):
        """
        TEST 6: The same element appears in forward and backward traversal.
        Expected: One unique element in audit_population, not two.
        """
        sync_data = {
            "url": "https://generic-test.org/checkout",
            "forward": [
                {
                    "step": 1,
                    "selenium": {"tag": "input", "id": "billing_first_name", "name": "first_name", "type": "text"},
                    "nvda": {"role": "edit", "name": "First Name", "raw_text": "First Name edit"},
                    "comparison": {"status": "MATCH"},
                }
            ],
            "backward": [
                {
                    "step": 8,
                    "selenium": {"tag": "input", "id": "billing_first_name", "name": "first_name", "type": "text"},
                    "nvda": {"role": "edit", "name": "First Name", "raw_text": "First Name edit focused"},
                    "comparison": {"status": "MATCH"},
                }
            ],
            "initialization": {"events": []},
        }

        dom_snapshot = {
            "interactive_elements": [
                {"tag": "input", "id": "billing_first_name", "name": "first_name", "type": "text"}
            ]
        }

        package = assemble_unified_evidence_package(
            "https://generic-test.org/checkout", sync_data, dom_snapshot
        )
        audit_pop = package["synchronized_evidence"]["audit_population"]

        # MUST be exactly 1 unique element
        self.assertEqual(audit_pop["unique_element_count"], 1)
        self.assertEqual(len(audit_pop["elements"]), 1)

        elem = audit_pop["elements"][0]
        self.assertEqual(set(elem["directions_observed"]), {"forward", "backward"})
        self.assertEqual(len(elem["traversal_steps"]), 2)
        self.assertEqual(len(elem["observations"]), 2)

    def test_07_configurable_n_element_traversal(self):
        """
        TEST 7: Traversal captures N elements where N is configurable.
        Expected: The evidence package and analyzer process all N elements dynamically.
        """
        for n in [1, 5, 14, 25]:
            forward_steps = [
                {
                    "step": i,
                    "selenium": {"tag": "button", "id": f"ctrl_action_{i}", "text": f"Action {i}"},
                    "nvda": {"role": "button", "name": f"Action {i}", "raw_text": f"Action {i} button"},
                    "comparison": {"status": "MATCH"},
                }
                for i in range(1, n + 1)
            ]
            sync_data = {
                "url": f"https://generic-test.org/page-n-{n}",
                "forward": forward_steps,
                "backward": [],
                "initialization": {"events": []},
            }
            dom_snapshot = {
                "interactive_elements": [
                    {"tag": "button", "id": f"ctrl_action_{i}", "text": f"Action {i}"}
                    for i in range(1, n + 1)
                ]
            }

            package = assemble_unified_evidence_package(
                f"https://generic-test.org/page-n-{n}", sync_data, dom_snapshot
            )
            audit_pop = package["synchronized_evidence"]["audit_population"]

            # Dynamic N count verified
            self.assertEqual(audit_pop["unique_element_count"], n)
            self.assertEqual(len(audit_pop["elements"]), n)

            compact_elements, _ = prepare_compact_evidence(package["synchronized_evidence"], dom_snapshot)
            self.assertEqual(len(compact_elements), n)

            # Analyze with zero violations mock to inspect summary metrics
            analyzer = AIAccessibilityAnalyzer(provider=MockLLMProvider(mode="zero_violations"))
            report = analyzer.analyze_synchronized_evidence(
                package["synchronized_evidence"],
                unified_package=package,
            )
            self.assertEqual(report.summary.total_elements_analyzed, n)

    def test_08_snapshot_elements_not_traversed_excluded_from_population(self):
        """
        TEST 8: A DOM element exists in the full snapshot but was never traversed.
        Expected: It must not become part of the synchronized audit population.
        """
        # Traversal only visited 2 elements
        sync_data = {
            "url": "https://generic-test.org/dashboard",
            "forward": [
                {
                    "step": 1,
                    "selenium": {"tag": "button", "id": "btn_active_1", "text": "Save"},
                    "nvda": {"role": "button", "name": "Save"},
                    "comparison": {"status": "MATCH"},
                },
                {
                    "step": 2,
                    "selenium": {"tag": "button", "id": "btn_active_2", "text": "Cancel"},
                    "nvda": {"role": "button", "name": "Cancel"},
                    "comparison": {"status": "MATCH"},
                },
            ],
            "backward": [],
            "initialization": {"events": []},
        }

        # Snapshot contains 40 interactive elements (e.g. footer links, sidebar buttons never reached)
        dom_elements = [
            {"tag": "button", "id": f"btn_unvisited_{i}", "text": f"Unvisited {i}"}
            for i in range(1, 39)
        ]
        dom_elements.append({"tag": "button", "id": "btn_active_1", "text": "Save"})
        dom_elements.append({"tag": "button", "id": "btn_active_2", "text": "Cancel"})

        dom_snapshot = {
            "interactive_elements": dom_elements,
            "landmarks": [{"role": "main"}],
        }

        package = assemble_unified_evidence_package(
            "https://generic-test.org/dashboard", sync_data, dom_snapshot
        )
        audit_pop = package["synchronized_evidence"]["audit_population"]

        # Exactly 2 elements traversed -> population must be 2, NOT 40
        self.assertEqual(audit_pop["unique_element_count"], 2)
        self.assertEqual(len(audit_pop["elements"]), 2)

        # Full DOM snapshot remains intact as supporting evidence
        self.assertEqual(len(package["dom_snapshot"]["interactive_elements"]), 40)

        # Analyzer audits only the 2 captured elements
        analyzer = AIAccessibilityAnalyzer(provider=MockLLMProvider(mode="zero_violations"))
        report = analyzer.analyze_synchronized_evidence(
            package["synchronized_evidence"],
            unified_package=package,
        )
        self.assertEqual(report.summary.total_elements_analyzed, 2)

    def test_09_initialization_events_excluded_from_element_count(self):
        """
        TEST 9: Initialization contains 'document', 'form landmark', 'alert', etc.
        Expected: These are not automatically counted as interactive audit elements.
        """
        sync_data = {
            "url": "https://generic-test.org/portal",
            "forward": [
                {
                    "step": 1,
                    "selenium": {"tag": "input", "id": "ctrl_code", "name": "code", "type": "text"},
                    "nvda": {"role": "edit", "name": "Code", "raw_text": "Code edit"},
                    "comparison": {"status": "MATCH"},
                }
            ],
            "backward": [],
            "initialization": {
                "raw_text": "Document\nMain landmark\nAlert: Welcome to portal\nForm landmark",
                "events": [
                    {"speech": "Document", "category": "document"},
                    {"speech": "Main landmark", "category": "landmark"},
                    {"speech": "Alert: Welcome to portal", "category": "alert"},
                    {"speech": "Form landmark", "category": "landmark"},
                ],
            },
        }

        dom_snapshot = {
            "interactive_elements": [
                {"tag": "input", "id": "ctrl_code", "name": "code", "type": "text"}
            ]
        }

        package = assemble_unified_evidence_package(
            "https://generic-test.org/portal", sync_data, dom_snapshot
        )
        audit_pop = package["synchronized_evidence"]["audit_population"]

        # Only the 1 interactive input control is in the audit population
        self.assertEqual(audit_pop["unique_element_count"], 1)
        self.assertEqual(len(audit_pop["elements"]), 1)

        # Initialization events are preserved separately
        init_events = package["synchronized_evidence"]["initialization_events"]
        self.assertEqual(len(init_events), 4)

        analyzer = AIAccessibilityAnalyzer(provider=MockLLMProvider(mode="zero_violations"))
        report = analyzer.analyze_synchronized_evidence(
            package["synchronized_evidence"],
            unified_package=package,
        )
        self.assertEqual(report.summary.total_elements_analyzed, 1)

    def test_10_validation_error_in_nearby_container_without_surrounding_text(self):
        """
        TEST 10: A field has no surrounding_text but has a validation error in a nearby DOM node.
        Expected: The structured validation context captures the error.
        """
        sync_data = {
            "url": "https://generic-test.org/register",
            "forward": [
                {
                    "step": 1,
                    "selenium": {
                        "tag": "input",
                        "id": "password_input",
                        "name": "password",
                        "type": "password",
                    },
                    "nvda": {
                        "role": "password edit",
                        "name": "Password",
                        "raw_text": "Password edit protected blank",
                    },
                    "comparison": {"status": "MATCH"},
                }
            ],
            "backward": [],
            "initialization": {"events": []},
        }

        # Sibling/parent container validation error with surrounding_text explicitly None
        dom_snapshot = {
            "interactive_elements": [
                {
                    "tag": "input",
                    "id": "password_input",
                    "name": "password",
                    "type": "password",
                    "label_text": "Password",
                    "surrounding_text": None,  # Simulating nested input wrapped in icon divs
                    "validation_context": {
                        "has_error": True,
                        "aria_invalid": True,
                        "error_text": "Password must be at least 8 characters with a number",
                        "error_nodes": [
                            {
                                "selector": ".password-group .error-bubble",
                                "text": "Password must be at least 8 characters with a number",
                                "role": "alert",
                                "id": "pwd_err",
                                "relationship": "container_descendant",
                            }
                        ],
                        "programmatic_association": {
                            "aria_describedby": "pwd_err",
                            "aria_errormessage": None,
                            "resolved": True,
                            "is_associated": True,
                        },
                    },
                }
            ]
        }

        package = assemble_unified_evidence_package(
            "https://generic-test.org/register", sync_data, dom_snapshot
        )
        elem = package["synchronized_evidence"]["audit_population"]["elements"][0]

        # surrounding_text is None
        self.assertIsNone(elem["dom_context"].get("surrounding_text"))

        # But structured validation context captured the error
        val_ctx = elem.get("validation_context")
        self.assertIsNotNone(val_ctx)
        self.assertTrue(val_ctx["has_error"])
        self.assertEqual(val_ctx["error_text"], "Password must be at least 8 characters with a number")
        self.assertEqual(len(val_ctx["error_nodes"]), 1)
        self.assertTrue(val_ctx["programmatic_association"]["is_associated"])

        # Also preserved in compact evidence
        compact_elements, _ = prepare_compact_evidence(package["synchronized_evidence"], dom_snapshot)
        compact_elem = compact_elements[0]
        self.assertEqual(
            compact_elem["validation_context"]["error_text"],
            "Password must be at least 8 characters with a number",
        )


if __name__ == "__main__":
    unittest.main()
