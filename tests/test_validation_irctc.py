"""
Validation Test Case: IRCTC User Signup Page
Verifies that:
1. Missing <main> landmark region is NOT classified as a WCAG 1.3.1 violation.
2. Missing <h1> heading is NOT classified as a WCAG 1.3.1 violation.
3. Both conditions are routed to 'recommendations' with 0 score penalty.
4. Total violations = 0, compliance_score = 100.0%.
5. The logic remains completely generic and website-independent.
"""

import unittest
import json
import os
import sys

# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.ai_providers import MockLLMProvider
from tools.ai_agent import AIAccessibilityAnalyzer, AIAccessibilityAnalysisReport


class TestIRCTCValidationCase(unittest.TestCase):

    def setUp(self):
        # Load unified evidence package if present, or create equivalent structural evidence
        evidence_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "unified_evidence_package.json"
        )
        if os.path.exists(evidence_path):
            with open(evidence_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.sync_data = data.get("synchronized_evidence", {})
                self.dom_snapshot = data.get("dom_snapshot", {})
        else:
            self.sync_data = {"forward": [], "backward": []}
            self.dom_snapshot = {}

    def test_irctc_advisory_findings_routed_to_recommendations(self):
        """
        Simulate the exact previous AI output on the IRCTC signup page:
        AI previously returned 2 MAJOR WCAG 1.3.1 violations for missing main and missing h1.
        The refactored architecture must intercept and route these to recommendations,
        yielding 0 violations and exactly 100.0% score.
        """
        class PreviousIRCTCResponseMock(MockLLMProvider):
            def generate_analysis(self, system_prompt, user_prompt, image_data=None):
                return type("Resp", (), {
                    "success": True,
                    "error": None,
                    "structured_data": {
                        "analysis_status": "COMPLETED",
                        "summary": {
                            "total_elements_analyzed": 15,
                            "total_violations": 2,
                            "total_recommendations": 0,
                            "compliance_score": 92.9,
                            "severity_summary": {
                                "CRITICAL": 0,
                                "MAJOR": 2,
                                "MINOR": 0,
                                "INFO": 0,
                            },
                        },
                        "violations": [
                            {
                                "violation_id": "AI-001",
                                "scope": "PAGE",
                                "element_reference": None,
                                "rule_id": "WCAG 1.3.1",
                                "rule_name": "Info and Relationships",
                                "severity": "MAJOR",
                                "confidence": 0.95,
                                "title": "Missing Main Landmark Region",
                                "description": "The webpage lacks a primary <main> landmark region or role='main', preventing screen reader users from rapidly bypassing repeated navigation and directly accessing the primary content area.",
                                "ai_rationale": "Analysis of the DOM semantic landmarks reveals banner, navigation, form, and contentinfo landmarks present, but no <main> landmark or element with role='main' exists in the observed page distribution.",
                                "user_impact": "Screen reader users cannot use landmark navigation shortcuts to quickly skip repetitive header and navigation blocks and jump straight to the primary registration form.",
                                "wcag_context": "WCAG 2.1 Success Criterion 1.3.1 Info and Relationships requires that information, structure, and relationships conveyed through presentation can be programmatically determined or are available in text.",
                                "recommendation": "Enclose the primary page content and registration form within a <main> element or add role='main' to the primary content container.",
                                "developer_guidance": "Wrap the main content area in a <main> tag or add role='main' to the container element holding the registration form and accordion sections.",
                                "evidence": {"page_context": {}},
                            },
                            {
                                "violation_id": "AI-002",
                                "scope": "PAGE",
                                "element_reference": None,
                                "rule_id": "WCAG 1.3.1",
                                "rule_name": "Info and Relationships",
                                "severity": "MAJOR",
                                "confidence": 0.90,
                                "title": "Missing Level 1 Heading (H1)",
                                "description": "The page outline lacks an <h1> heading, starting directly with an <h2> heading ('Have Questions About Registering...').",
                                "ai_rationale": "Inspection of the DOM heading hierarchy shows that the highest heading present is an <h2>, with no preceding <h1> element found on the page.",
                                "user_impact": "Screen reader users relying on heading navigation to understand the primary topic of the page are met with an out-of-order outline starting at level 2.",
                                "wcag_context": "WCAG 2.1 Success Criterion 1.3.1 Info and Relationships mandates a logical document structure and heading hierarchy.",
                                "recommendation": "Ensure the primary page title or top-level banner is marked up as an <h1> heading before subordinate <h2> headings.",
                                "developer_guidance": "Add an <h1> heading representing the main title of the page (e.g., 'User Registration') at the top of the content structure.",
                                "evidence": {"page_context": {}},
                            }
                        ],
                        "recommendations": [],
                    }
                })()

        analyzer = AIAccessibilityAnalyzer(provider=PreviousIRCTCResponseMock())
        report = analyzer.analyze_synchronized_evidence(
            self.sync_data,
            unified_package={"dom_snapshot": self.dom_snapshot},
        )

        # 1. Violations list must be completely empty
        self.assertEqual(len(report.violations), 0)
        self.assertEqual(report.summary.total_violations, 0)
        self.assertEqual(report.summary.severity_summary.MAJOR, 0)

        # 2. Recommendations list must have both advisory findings
        self.assertEqual(len(report.recommendations), 2)
        self.assertEqual(report.summary.total_recommendations, 2)

        titles = [r.title for r in report.recommendations]
        self.assertTrue(any("Main Landmark" in t for t in titles))
        self.assertTrue(any("Heading" in t for t in titles))

        # Check related guidance
        main_rec = next(r for r in report.recommendations if "Main" in r.title)
        self.assertIsNotNone(main_rec.related_guidance)
        self.assertEqual(main_rec.related_guidance.get("technique"), "ARIA11")

        h1_rec = next(r for r in report.recommendations if "Heading" in r.title)
        self.assertIsNotNone(h1_rec.related_guidance)
        self.assertEqual(h1_rec.related_guidance.get("technique"), "G141")

        # 3. Compliance score must be strictly 100.0%
        self.assertEqual(report.summary.compliance_score, 100.0)

    def test_irctc_social_media_and_captcha_adjudication(self):
        """
        Simulate the AI output flagging social media footer icons and CAPTCHA image:
        1. Social media footer icons (Img #6, Img #7) flagged under WCAG 1.1.1 -> parent <a> has aria-label.
        2. CAPTCHA image (Img #4) flagged under WCAG 4.1.2 -> static challenge graphic with purpose alt.
        The refactored architecture must adjudicate both to recommendations with zero score penalty.
        """
        class SocialAndCaptchaMock(MockLLMProvider):
            def generate_analysis(self, system_prompt, user_prompt, image_data=None):
                return type("Resp", (), {
                    "success": True,
                    "error": None,
                    "structured_data": {
                        "analysis_status": "COMPLETED",
                        "summary": {
                            "total_elements_analyzed": 15,
                            "total_violations": 2,
                            "total_recommendations": 0,
                            "compliance_score": 85.0,
                            "severity_summary": {
                                "CRITICAL": 0,
                                "MAJOR": 2,
                                "MINOR": 0,
                                "INFO": 0,
                            },
                        },
                        "violations": [
                            {
                                "violation_id": "AI-001",
                                "scope": "ELEMENT",
                                "element_reference": {"src": "whatsapp.png", "tag": "img"},
                                "rule_id": "WCAG 1.1.1",
                                "rule_name": "Non-text Content",
                                "severity": "MAJOR",
                                "confidence": 0.90,
                                "title": "Social Media Icons Lack Accessible Text Alternatives",
                                "description": "Footer link icons lack alt attributes on child <img> elements inside parent links.",
                                "ai_rationale": "The social media icons lack alt attributes on the <img> tags, though the parent link elements have descriptive aria-label attributes.",
                                "user_impact": "Screen reader users may hear redundant announcements if icons lack null alt.",
                                "wcag_context": "WCAG 1.1.1 Non-text Content",
                                "recommendation": "Add alt='' to the child image elements.",
                                "developer_guidance": "<a href='...' aria-label='Social'><img src='...' alt='' /></a>",
                            },
                            {
                                "violation_id": "AI-002",
                                "scope": "ELEMENT",
                                "element_reference": {"src": "captcha.jpg", "tag": "img"},
                                "rule_id": "WCAG 4.1.2",
                                "rule_name": "Name, Role, Value",
                                "severity": "MAJOR",
                                "confidence": 0.88,
                                "title": "Captcha Image Lacks Descriptive Text Alternative",
                                "description": "The captcha image has alt='Captcha Image here' which does not describe the distorted characters.",
                                "ai_rationale": "Static captcha image does not transcribe the distorted security characters into alt text.",
                                "user_impact": "Blind users cannot read the visual captcha code.",
                                "wcag_context": "WCAG 4.1.2 Name, Role, Value",
                                "recommendation": "Provide an audio captcha alternative.",
                                "developer_guidance": "Implement audio verification alongside visual captcha.",
                            },
                        ],
                        "recommendations": [],
                    }
                })()

        analyzer = AIAccessibilityAnalyzer(provider=SocialAndCaptchaMock())
        report = analyzer.analyze_synchronized_evidence(
            self.sync_data,
            unified_package={"dom_snapshot": self.dom_snapshot},
        )

        # Both false violations must be downgraded to recommendations
        self.assertEqual(len(report.violations), 0)
        self.assertEqual(report.summary.total_violations, 0)
        self.assertEqual(len(report.recommendations), 2)
        self.assertEqual(report.summary.total_recommendations, 2)
        self.assertEqual(report.summary.compliance_score, 100.0)

        techs = [r.related_guidance.get("technique") for r in report.recommendations if r.related_guidance]
        self.assertIn("H67", techs)
        self.assertIn("G144", techs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
