"""
Generic Evidence-Basis Hardening Unit & Integration Tests (Phase 3B).

CRITICAL ARCHITECTURAL CONSTRAINTS:
1. 100% GENERIC:
   - Uses synthetic URLs (e.g. https://synthetic.example.local/test)
   - Uses neutral, generic tags, synthetic IDs, and synthetic element labels.
   - Absolutely NO production domains, real website names, production element IDs,
     or hardcoded site-specific selectors.
2. PURE AI AUTHORITY:
   - Python validates structure, availability, and consistency only.
   - Modality relevance and WCAG decisions remain entirely with AI.
3. Tests requirements A through L:
   A. DOM-supported finding (DIRECT [DOM]: ...)
   B. NVDA-supported finding (DIRECT [NVDA]: ...)
   C. Visual-supported finding (DIRECT [VISUAL]: ...)
   D. Multiple supporting modalities (CORROBORATED [DOM+NVDA]: ...)
   E. Visual + another modality (CORROBORATED [DOM+VISUAL]: ...)
   F. All modalities available but only one cited (no forced modality)
   G. Visual unavailable -> visual citation rejected
   H. NVDA unavailable -> NVDA citation rejected
   I. Unsupported modality (e.g. BRAILLE) -> rejected
   J. Legacy/inadequate format (e.g. "DOM" or ["DOM", "NVDA"]) -> rejected
   K. Valid DIRECT statement passes
   L. Valid CORROBORATED statement passes
"""

import unittest
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from tools.ai_agent import (
    AIAccessibilityAnalyzer,
    AIViolationFinding,
    AINormativeBasis,
    discover_available_modalities,
    validate_finding_evidence_basis,
)
from tools.ai_providers import MockLLMProvider


class SyntheticMockProvider(MockLLMProvider):
    """Configurable synthetic mock provider returning predetermined AI findings."""

    def __init__(self, findings: List[Dict[str, Any]], success: bool = True):
        super().__init__()
        self._findings = findings
        self._success = success

    def generate_analysis(self, system_prompt: str, user_prompt: str, image_data: Optional[str] = None):
        resp_data = {
            "analysis_status": "COMPLETED",
            "summary": {
                "total_elements_analyzed": len(self._findings) or 1,
                "total_violations": len(self._findings),
                "total_recommendations": 0,
                "compliance_score": 85.0 if self._findings else 100.0,
                "severity_summary": {
                    "CRITICAL": len(self._findings),
                    "MAJOR": 0,
                    "MINOR": 0,
                    "INFO": 0,
                },
            },
            "violations": self._findings,
            "recommendations": [],
        }
        return type("MockResponse", (), {
            "success": self._success,
            "error": None,
            "structured_data": resp_data,
            "model_name": "synthetic-gemini-test",
        })()


class TestGenericEvidenceBasisHardening(unittest.TestCase):
    """Comprehensive test suite for Phase 3B Generic Evidence-Basis Hardening."""

    def setUp(self):
        # Generic synthetic synchronized evidence
        self.synthetic_sync_data = {
            "url": "https://synthetic.example.local/test-form",
            "forward": [
                {
                    "step": 1,
                    "direction": "forward",
                    "selenium": {
                        "tag": "button",
                        "id": "synthetic_btn_submit",
                        "text": "",
                        "aria_label": "",
                        "role": "button",
                    },
                    "nvda": {
                        "name": "",
                        "role": "button",
                        "raw_text": "button",
                    },
                    "comparison": {
                        "status": "ROLE_MATCH_NAME_EMPTY",
                        "name_match": True,
                        "role_match": True,
                    },
                }
            ],
            "backward": [],
        }

        # Generic synthetic DOM snapshot
        self.synthetic_dom_snapshot = {
            "interactive_elements": [
                {
                    "tag": "button",
                    "id": "synthetic_btn_submit",
                    "text": "",
                    "aria_label": "",
                }
            ],
            "headings": [],
            "landmarks": [],
        }

    # =========================================================================
    # REQUIREMENT A: DOM-supported finding
    # =========================================================================
    def test_requirement_a_dom_supported_finding(self):
        """Verify that a finding citing only DOM evidence is accepted: DIRECT [DOM]: ..."""
        available_modalities = {"DOM", "INTERACTION"}
        evidence_basis = [
            "DIRECT [DOM]: Element <button id='synthetic_btn_submit'> has empty innerText and no aria-label attribute."
        ]

        is_valid, cleaned, err = validate_finding_evidence_basis(
            evidence_basis,
            available_modalities=available_modalities,
            strict_rich_format=True,
        )
        self.assertTrue(is_valid, f"Validation failed: {err}")
        self.assertEqual(len(cleaned), 1)
        self.assertTrue(cleaned[0].startswith("DIRECT [DOM]:"))

        # Verify through full analyzer pipeline
        finding_payload = {
            "violation_id": "AI-001",
            "scope": "ELEMENT",
            "element_reference": {"direction": "forward", "step": 1},
            "rule_id": "WCAG 4.1.2",
            "rule_name": "Name, Role, Value",
            "severity": "CRITICAL",
            "confidence": 0.95,
            "title": "Synthetic Button Missing Name",
            "description": "Button has no accessible name in DOM.",
            "ai_rationale": "DOM inspection establishes button has empty text.",
            "normative_basis": {
                "success_criterion": "4.1.2",
                "level": "A",
                "requirement": "Name, Role, Value",
                "failure_condition": "Button lacks accessible name in DOM",
                "evidence_basis": evidence_basis,
            },
            "user_impact": "Screen reader users cannot determine action.",
            "wcag_context": "WCAG 4.1.2 Level A",
            "recommendation": "Provide aria-label.",
            "developer_guidance": "Add aria-label attribute.",
        }

        provider = SyntheticMockProvider([finding_payload])
        analyzer = AIAccessibilityAnalyzer(provider=provider)
        report = analyzer.analyze_synchronized_evidence(self.synthetic_sync_data)

        self.assertEqual(len(report.violations), 1)
        v = report.violations[0]
        self.assertIn("DIRECT [DOM]:", v.evidence_basis[0])
        self.assertEqual(v.normative_basis.evidence_basis, v.evidence_basis)

    # =========================================================================
    # REQUIREMENT B: NVDA-supported finding
    # =========================================================================
    def test_requirement_b_nvda_supported_finding(self):
        """Verify that a finding citing only NVDA speech is accepted: DIRECT [NVDA]: ..."""
        available_modalities = {"NVDA", "INTERACTION"}
        evidence_basis = [
            "DIRECT [NVDA]: NVDA speech viewer output vocalized 'button' with no accompanying accessible name."
        ]

        is_valid, cleaned, err = validate_finding_evidence_basis(
            evidence_basis,
            available_modalities=available_modalities,
            strict_rich_format=True,
        )
        self.assertTrue(is_valid, f"Validation failed: {err}")
        self.assertEqual(len(cleaned), 1)
        self.assertTrue(cleaned[0].startswith("DIRECT [NVDA]:"))

        finding_payload = {
            "violation_id": "AI-001",
            "scope": "ELEMENT",
            "element_reference": {"direction": "forward", "step": 1},
            "rule_id": "WCAG 4.1.2",
            "rule_name": "Name, Role, Value",
            "severity": "CRITICAL",
            "confidence": 0.95,
            "title": "Unannounced Button Name in NVDA",
            "description": "NVDA output announces role button without label.",
            "ai_rationale": "Speech stream announces role button with empty name.",
            "normative_basis": {
                "success_criterion": "4.1.2",
                "level": "A",
                "requirement": "Name, Role, Value",
                "failure_condition": "NVDA announces only button",
                "evidence_basis": evidence_basis,
            },
            "user_impact": "Users hear only role with no label.",
            "wcag_context": "WCAG 4.1.2 Level A",
            "recommendation": "Add accessible name.",
            "developer_guidance": "Add aria-label.",
        }

        provider = SyntheticMockProvider([finding_payload])
        analyzer = AIAccessibilityAnalyzer(provider=provider)
        report = analyzer.analyze_synchronized_evidence(self.synthetic_sync_data)

        self.assertEqual(len(report.violations), 1)
        self.assertIn("DIRECT [NVDA]:", report.violations[0].evidence_basis[0])

    # =========================================================================
    # REQUIREMENT C: Visual-supported finding
    # =========================================================================
    def test_requirement_c_visual_supported_finding(self):
        """Verify that a finding citing only visual evidence is accepted when screenshot was supplied: DIRECT [VISUAL]: ..."""
        available_modalities = {"DOM", "NVDA", "VISUAL", "INTERACTION"}
        evidence_basis = [
            "DIRECT [VISUAL]: Screenshot confirms icon within button has no rendered adjacent visible text."
        ]

        is_valid, cleaned, err = validate_finding_evidence_basis(
            evidence_basis,
            available_modalities=available_modalities,
            strict_rich_format=True,
        )
        self.assertTrue(is_valid, f"Validation failed: {err}")
        self.assertEqual(len(cleaned), 1)
        self.assertTrue(cleaned[0].startswith("DIRECT [VISUAL]:"))

    # =========================================================================
    # REQUIREMENT D: Multiple supporting modalities
    # =========================================================================
    def test_requirement_d_multiple_supporting_modalities(self):
        """Verify corroborated finding across DOM and NVDA: CORROBORATED [DOM+NVDA]: ..."""
        available_modalities = {"DOM", "NVDA", "INTERACTION"}
        evidence_basis = [
            "CORROBORATED [DOM+NVDA]: DOM button text is empty and NVDA speech reader announced role button with no label."
        ]

        is_valid, cleaned, err = validate_finding_evidence_basis(
            evidence_basis,
            available_modalities=available_modalities,
            strict_rich_format=True,
        )
        self.assertTrue(is_valid, f"Validation failed: {err}")
        self.assertEqual(len(cleaned), 1)
        self.assertTrue(cleaned[0].startswith("CORROBORATED [DOM+NVDA]:"))

    # =========================================================================
    # REQUIREMENT E: Visual + another modality
    # =========================================================================
    def test_requirement_e_visual_corroborated_with_another_modality(self):
        """Verify that a corroborated visual claim can be represented when supplied evidence supports it."""
        available_modalities = {"DOM", "NVDA", "VISUAL", "INTERACTION"}
        evidence_basis = [
            "CORROBORATED [DOM+VISUAL]: DOM has empty alt attribute and rendered screenshot shows informative diagram icon without visible text."
        ]

        is_valid, cleaned, err = validate_finding_evidence_basis(
            evidence_basis,
            available_modalities=available_modalities,
            strict_rich_format=True,
        )
        self.assertTrue(is_valid, f"Validation failed: {err}")
        self.assertEqual(len(cleaned), 1)
        self.assertTrue(cleaned[0].startswith("CORROBORATED [DOM+VISUAL]:"))

        # Also verify 3-way corroboration: DOM+NVDA+VISUAL
        multi_basis = [
            "CORROBORATED [DOM+NVDA+VISUAL]: DOM text empty, NVDA unannounced, visual icon standalone."
        ]
        is_valid3, cleaned3, _ = validate_finding_evidence_basis(
            multi_basis,
            available_modalities=available_modalities,
            strict_rich_format=True,
        )
        self.assertTrue(is_valid3)
        self.assertEqual(cleaned3[0], "CORROBORATED [DOM+NVDA+VISUAL]: DOM text empty, NVDA unannounced, visual icon standalone.")

    # =========================================================================
    # REQUIREMENT F: All modalities available but only one cited (no forced modality)
    # =========================================================================
    def test_requirement_f_all_modalities_available_only_one_cited(self):
        """Verify that when DOM, NVDA, and VISUAL are all available, the system does NOT force all modalities to be cited."""
        available_modalities = {"DOM", "NVDA", "VISUAL", "INTERACTION"}
        
        # Finding only relies on DOM
        dom_only_basis = [
            "DIRECT [DOM]: HTML element lacks required aria-expanded state attribute."
        ]
        is_valid, cleaned, err = validate_finding_evidence_basis(
            dom_only_basis,
            available_modalities=available_modalities,
            strict_rich_format=True,
        )
        self.assertTrue(is_valid)
        self.assertNotIn("VISUAL", cleaned[0])
        self.assertNotIn("NVDA", cleaned[0])

        # Finding only relies on NVDA
        nvda_only_basis = [
            "DIRECT [NVDA]: Live speech stream vocalized unexpected pronunciation."
        ]
        is_valid2, cleaned2, _ = validate_finding_evidence_basis(
            nvda_only_basis,
            available_modalities=available_modalities,
            strict_rich_format=True,
        )
        self.assertTrue(is_valid2)
        self.assertNotIn("VISUAL", cleaned2[0])
        self.assertNotIn("DOM", cleaned2[0])

    # =========================================================================
    # REQUIREMENT G: Visual unavailable -> visual citation rejected
    # =========================================================================
    def test_requirement_g_visual_unavailable_rejected(self):
        """Verify that an AI response claiming visual evidence is rejected when screenshot was not supplied."""
        # Visual is NOT in available modalities
        available_modalities = {"DOM", "NVDA", "INTERACTION"}

        # 1. DIRECT visual claim must be rejected
        direct_visual = [
            "DIRECT [VISUAL]: Visual rendering in screenshot shows red outline around field."
        ]
        is_valid, _, err = validate_finding_evidence_basis(
            direct_visual,
            available_modalities=available_modalities,
            strict_rich_format=True,
        )
        self.assertFalse(is_valid)
        self.assertIn("VISUAL", err)
        self.assertIn("not supplied in available evidence modalities", err)

        # 2. CORROBORATED visual claim must also be rejected
        corrob_visual = [
            "CORROBORATED [DOM+VISUAL]: DOM has aria-invalid and visual screenshot shows red border."
        ]
        is_valid2, _, err2 = validate_finding_evidence_basis(
            corrob_visual,
            available_modalities=available_modalities,
            strict_rich_format=True,
        )
        self.assertFalse(is_valid2)
        self.assertIn("VISUAL", err2)
        self.assertIn("not supplied in available evidence modalities", err2)

        # 3. Verify in full analyzer execution: finding claiming visual evidence is rejected
        finding_payload = {
            "violation_id": "AI-001",
            "scope": "ELEMENT",
            "element_reference": {"direction": "forward", "step": 1},
            "rule_id": "WCAG 1.4.3",
            "rule_name": "Contrast (Minimum)",
            "severity": "CRITICAL",
            "confidence": 0.9,
            "title": "Low Contrast Visual Text",
            "description": "Text has low contrast visually.",
            "ai_rationale": "Visual inspection indicates light gray on white.",
            "normative_basis": {
                "success_criterion": "1.4.3",
                "level": "AA",
                "requirement": "Contrast (Minimum)",
                "failure_condition": "Visual text contrast is below 4.5:1",
                "evidence_basis": direct_visual,
            },
            "user_impact": "Low vision users cannot read text.",
            "wcag_context": "WCAG 1.4.3 Level AA",
            "recommendation": "Increase contrast.",
            "developer_guidance": "Use darker color.",
        }

        # Run analyzer WITHOUT screenshot (visual unavailable)
        provider = SyntheticMockProvider([finding_payload])
        analyzer = AIAccessibilityAnalyzer(provider=provider)
        report = analyzer.analyze_synchronized_evidence(self.synthetic_sync_data, screenshot_path=None)

        self.assertEqual(len(report.violations), 0)
        self.assertIn("validation_errors", report.ai_metadata)
        self.assertTrue(any("VISUAL" in str(e) for e in report.ai_metadata["validation_errors"]))

    # =========================================================================
    # REQUIREMENT H: NVDA unavailable -> NVDA citation rejected
    # =========================================================================
    def test_requirement_h_nvda_unavailable_rejected(self):
        """Verify that an AI response claiming NVDA evidence is rejected when NVDA was not supplied."""
        available_modalities = {"DOM", "VISUAL"}

        # 1. DIRECT NVDA claim must be rejected
        direct_nvda = [
            "DIRECT [NVDA]: NVDA speech viewer output vocalized unlabelled button."
        ]
        is_valid, _, err = validate_finding_evidence_basis(
            direct_nvda,
            available_modalities=available_modalities,
            strict_rich_format=True,
        )
        self.assertFalse(is_valid)
        self.assertIn("NVDA", err)
        self.assertIn("not supplied in available evidence modalities", err)

        # 2. CORROBORATED NVDA claim must also be rejected
        corrob_nvda = [
            "CORROBORATED [DOM+NVDA]: DOM and NVDA mismatch."
        ]
        is_valid2, _, err2 = validate_finding_evidence_basis(
            corrob_nvda,
            available_modalities=available_modalities,
            strict_rich_format=True,
        )
        self.assertFalse(is_valid2)
        self.assertIn("NVDA", err2)

    # =========================================================================
    # REQUIREMENT I: Unsupported modality
    # =========================================================================
    def test_requirement_i_unsupported_modality_rejected(self):
        """Verify that an AI response cannot claim a modality that was not supplied (e.g. BRAILLE, HAPTIC)."""
        available_modalities = {"DOM", "NVDA", "VISUAL", "INTERACTION"}

        unsupported_claims = [
            "DIRECT [BRAILLE]: Refreshable braille display produced 8-dot uncontracted output.",
            "DIRECT [HAPTIC]: Vibration feedback was not triggered on activation.",
            "CORROBORATED [DOM+AUDIO]: Audio tone did not accompany focus change.",
        ]

        for claim in unsupported_claims:
            is_valid, _, err = validate_finding_evidence_basis(
                [claim],
                available_modalities=available_modalities,
                strict_rich_format=True,
            )
            self.assertFalse(is_valid, f"Expected claim '{claim}' to be rejected, but it was accepted.")
            self.assertIn("not supplied in available evidence modalities", err)

    # =========================================================================
    # REQUIREMENT J: Legacy / Inadequate format rejected
    # =========================================================================
    def test_requirement_j_legacy_inadequate_format_rejected(self):
        """Verify that plain strings like 'DOM' or ['DOM', 'NVDA'] are rejected when rich format is required."""
        available_modalities = {"DOM", "NVDA", "VISUAL", "INTERACTION"}

        inadequate_cases = [
            ["DOM"],
            ["NVDA"],
            ["DOM", "NVDA"],
            ["VISUAL"],
            ["INTERACTION"],
            ["random unstructured text without directive prefix"],
            ["DIRECT: missing modality brackets"],
            ["CORROBORATED: missing modality brackets"],
        ]

        for case in inadequate_cases:
            is_valid, _, err = validate_finding_evidence_basis(
                case,
                available_modalities=available_modalities,
                strict_rich_format=True,
            )
            self.assertFalse(is_valid, f"Expected legacy format {case} to be rejected in strict rich format.")
            self.assertTrue(
                "Legacy/inadequate evidence format" in err or "evidence statements must follow structured format" in err,
                f"Unexpected error message for {case}: {err}"
            )

    # =========================================================================
    # REQUIREMENT K: Valid DIRECT statement passes
    # =========================================================================
    def test_requirement_k_valid_direct_statement_passes(self):
        """Verify that well-formed DIRECT statements pass schema and availability validation."""
        available_modalities = {"DOM", "NVDA", "VISUAL", "INTERACTION"}

        valid_direct_cases = [
            ("DIRECT [DOM]: <input type='text'> element has no associated <label> or aria-label.", "DOM"),
            ("DIRECT [NVDA]: NVDA speech viewer output vocalized 'edit blank' with no label announcement.", "NVDA"),
            ("DIRECT [VISUAL]: Full-page screenshot shows error text rendered in red with exclamation icon.", "VISUAL"),
            ("DIRECT [INTERACTION]: Tab traversal skips the interactive widget entirely.", "INTERACTION"),
        ]

        for statement, expected_mod in valid_direct_cases:
            is_valid, cleaned, err = validate_finding_evidence_basis(
                [statement],
                available_modalities=available_modalities,
                strict_rich_format=True,
            )
            self.assertTrue(is_valid, f"Statement '{statement}' failed validation: {err}")
            self.assertEqual(len(cleaned), 1)
            self.assertTrue(cleaned[0].startswith(f"DIRECT [{expected_mod}]:"))

    # =========================================================================
    # REQUIREMENT L: Valid CORROBORATED statement passes
    # =========================================================================
    def test_requirement_l_valid_corroborated_statement_passes(self):
        """Verify that well-formed CORROBORATED statements pass schema and availability validation."""
        available_modalities = {"DOM", "NVDA", "VISUAL", "INTERACTION"}

        valid_corrob_cases = [
            ("CORROBORATED [DOM+NVDA]: DOM shows missing name attribute and NVDA announces only 'button'.", "DOM+NVDA"),
            ("CORROBORATED [DOM+VISUAL]: DOM contains no alt text and screenshot shows diagram image.", "DOM+VISUAL"),
            ("CORROBORATED [NVDA+INTERACTION]: Focus moves to element but NVDA announces nothing.", "NVDA+INTERACTION"),
            ("CORROBORATED [DOM+NVDA+VISUAL]: All three modalities confirm complete lack of accessible information.", "DOM+NVDA+VISUAL"),
        ]

        for statement, expected_mods in valid_corrob_cases:
            is_valid, cleaned, err = validate_finding_evidence_basis(
                [statement],
                available_modalities=available_modalities,
                strict_rich_format=True,
            )
            self.assertTrue(is_valid, f"Statement '{statement}' failed validation: {err}")
            self.assertEqual(len(cleaned), 1)
            self.assertTrue(cleaned[0].startswith(f"CORROBORATED [{expected_mods}]:"))

    # =========================================================================
    # ADDITIONAL TESTS: Dynamic Modality Discovery & Model Synchronization
    # =========================================================================
    def test_dynamic_modality_discovery_generic(self):
        """Verify discover_available_modalities dynamically derives modalities from packages."""
        # 1. Package with DOM and visual
        pkg_dom_visual = {
            "dom_snapshot": {"landmarks": ["main"]},
            "visual_evidence": {"status": "SUCCESS", "screenshot": {"path": "shot.png"}},
        }
        mods1 = discover_available_modalities(unified_package=pkg_dom_visual, has_visual=True)
        self.assertIn("DOM", mods1)
        self.assertIn("VISUAL", mods1)
        self.assertNotIn("NVDA", mods1)

        # 2. Package with custom evidence modality
        pkg_custom = {
            "dom_snapshot": {"landmarks": ["main"]},
            "custom_evidence": {"status": "SUCCESS"},
        }
        mods2 = discover_available_modalities(unified_package=pkg_custom)
        self.assertIn("DOM", mods2)
        self.assertIn("CUSTOM", mods2)

    def test_pydantic_model_evidence_basis_synchronization(self):
        """Verify AIViolationFinding synchronizes finding.evidence_basis with normative_basis.evidence_basis."""
        finding = AIViolationFinding(
            violation_id="AI-001",
            scope="PAGE",
            element_reference=None,
            rule_id="WCAG 2.4.1",
            rule_name="Bypass Blocks",
            severity="MINOR",
            confidence=0.9,
            title="Synthetic Bypass Issue",
            description="Page lacks bypass link.",
            ai_rationale="No skip link detected.",
            normative_basis={
                "success_criterion": "2.4.1",
                "level": "A",
                "requirement": "Bypass Blocks",
                "failure_condition": "No skip navigation link",
                "evidence_basis": ["DIRECT [DOM]: No skip link found in DOM."],
            },
            user_impact="Keyboard users cannot skip navigation.",
            wcag_context="WCAG 2.4.1 Level A",
            recommendation="Add skip link.",
            developer_guidance="Add <a href='#main'>Skip</a>.",
        )
        self.assertEqual(finding.evidence_basis, ["DIRECT [DOM]: No skip link found in DOM."])
        self.assertEqual(finding.normative_basis.evidence_basis, finding.evidence_basis)

    def test_empty_evidence_basis_rejected(self):
        """Verify that empty evidence_basis is strictly rejected."""
        is_valid, _, err = validate_finding_evidence_basis([], available_modalities={"DOM"})
        self.assertFalse(is_valid)
        self.assertIn("empty", err.lower())

    def test_none_evidence_basis_rejected(self):
        """Verify that None evidence_basis is strictly rejected."""
        is_valid, _, err = validate_finding_evidence_basis(None, available_modalities={"DOM"})
        self.assertFalse(is_valid)
        self.assertIn("missing", err.lower())


if __name__ == "__main__":
    unittest.main()
