"""
Evidence Correlation & Unified Multimodal Evidence Package Assembler.

Phase 3A: Correlates three independent evidence streams into one unified,
machine-readable evidence package:
1. Synchronized Selenium + NVDA Interaction Evidence (temporal / screen-reader behavior)
2. Semantic DOM / Structural Snapshot (programmatic context, landmarks, headings, sections)
3. Webpage Screenshot Evidence (visual rendering, dimensions, fixed elements)

Core Principles:
- Evidence transformation only: Does NOT detect WCAG violations, assign severity,
  or perform accessibility judgments.
- Multi-signal matching: Uses tag, ID, normalized text, href, name, type, aria attributes,
  and supporting tie-breakers to correlate interactive controls conservatively.
- Explicit status: Explicitly marks elements as MATCHED, AMBIGUOUS, or UNMATCHED.
- Preserves all original evidence intact without destructive modifications.
"""

import copy
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("EvidenceCorrelator")


def normalize_text(text: Optional[str]) -> str:
    """Normalize text by lowercasing, collapsing all whitespace, and stripping."""
    if not text:
        return ""
    return " ".join(str(text).lower().split())


def normalize_href(href: Optional[str]) -> str:
    """Normalize URL/href by stripping fragments and trailing whitespace."""
    if not href:
        return ""
    clean = str(href).strip().lower()
    # Normalize common relative anchors
    if clean.endswith("#"):
        clean = clean[:-1]
    return clean.rstrip("/")


def calculate_candidate_score(
    selenium_el: Dict[str, Any],
    dom_el: Dict[str, Any],
) -> float:
    """
    Compute a conservative multi-signal similarity score between a synchronized
    Selenium element and a candidate DOM snapshot element (0.0 to 1.0).

    Signals evaluated:
    - tag: Must match; mismatch gives 0.0.
    - id: Strong positive signal if equal (+0.45), strong penalty if both exist and differ (-0.40).
    - text: Normalized visible text matching (+0.40 if exact, +0.25 if substring, -0.25 if conflicting).
    - href: For 'a' tags, exact or normalized URL match (+0.30), conflicting URL penalty (-0.25).
    - name: Form control name attribute (+0.25 if match, -0.20 if conflict).
    - type: Form input/button type (+0.15 if match, -0.15 if conflict).
    - aria_label: Explicit aria-label matching (+0.30).
    - role: Explicit ARIA role matching (+0.10).
    - class: Class overlap supporting tie-breaker (+0.10).
    - css_path: Structural tie-breaker (+0.05).
    """
    s_tag = (selenium_el.get("tag") or "").strip().lower()
    d_tag = (dom_el.get("tag") or "").strip().lower()

    if not s_tag or not d_tag or s_tag != d_tag:
        return 0.0

    score = 0.20  # Base score for compatible tag

    # 1. ID Attribute Matching
    s_id = (selenium_el.get("id") or "").strip()
    d_id = (dom_el.get("id") or "").strip()
    if s_id and d_id:
        if s_id == d_id:
            score += 0.45
        else:
            score -= 0.40  # Different non-empty IDs strongly indicate different elements

    # 2. Normalized Text Matching
    s_text = normalize_text(selenium_el.get("text"))
    d_text = normalize_text(dom_el.get("text"))
    if s_text and d_text:
        if s_text == d_text:
            score += 0.40 if len(s_text) >= 4 else 0.20
        elif s_text in d_text or d_text in s_text:
            score += 0.25
        elif len(s_text) >= 4 and len(d_text) >= 4:
            score -= 0.25
    elif not s_text and not d_text:
        # Both lack visible text (e.g. graphic links, icon buttons)
        score += 0.15
    elif (s_text and not d_text and len(s_text) >= 4) or (d_text and not s_text and len(d_text) >= 4):
        # Discrepancy: one has substantial visible label, the other has none
        score -= 0.15

    # 3. Href Matching for Links
    if s_tag == "a":
        raw_s_href = (selenium_el.get("href") or "").strip().lower()
        raw_d_href = (dom_el.get("href") or "").strip().lower()
        if raw_s_href and raw_d_href:
            if raw_d_href == "#" and (raw_s_href == "#" or raw_s_href.endswith("/#") or raw_s_href.endswith("#")):
                score += 0.25
            elif raw_s_href == raw_d_href:
                score += 0.30
            else:
                s_norm = raw_s_href.rstrip("#").rstrip("/")
                d_norm = raw_d_href.rstrip("#").rstrip("/")
                if s_norm and d_norm and (s_norm == d_norm or s_norm.endswith(d_norm) or d_norm.endswith(s_norm)):
                    score += 0.25
                elif s_norm and d_norm:
                    score -= 0.25
        elif (raw_s_href and not raw_d_href) or (raw_d_href and not raw_s_href):
            score -= 0.15

    # 4. Form Control Name
    s_name = (selenium_el.get("name") or "").strip()
    d_name = (dom_el.get("name") or "").strip()
    if s_name and d_name:
        if s_name == d_name:
            score += 0.25
        else:
            score -= 0.20

    # 5. Form Control Type
    s_type = (selenium_el.get("type") or "").strip().lower()
    d_type = (dom_el.get("type") or "").strip().lower()
    if s_type and d_type:
        if s_type == d_type:
            score += 0.15
        else:
            score -= 0.15

    # 6. Accessibility Label (aria-label / aria_label)
    s_aria = (selenium_el.get("aria-label") or selenium_el.get("aria_label") or "").strip().lower()
    d_aria = (dom_el.get("aria_label") or dom_el.get("aria-label") or "").strip().lower()
    if s_aria and d_aria:
        if s_aria == d_aria:
            score += 0.30
        else:
            score -= 0.15

    # 7. Explicit Role
    s_role = (selenium_el.get("role") or "").strip().lower()
    d_role = (dom_el.get("role") or "").strip().lower()
    if s_role and d_role:
        if s_role == d_role:
            score += 0.10

    # 8. Class Overlap (Supporting Tie-Breaker)
    s_cls = set((selenium_el.get("class") or "").strip().split())
    d_cls = set((dom_el.get("class") or "").strip().split())
    if s_cls and d_cls:
        if s_cls.intersection(d_cls):
            score += 0.10

    # 9. CSS Path (Tie-Breaker Only — Not Primary Identity)
    s_css = (selenium_el.get("css_path") or "").strip()
    d_css = (dom_el.get("css_path") or "").strip()
    if s_css and d_css and s_css == d_css:
        score += 0.05

    return max(0.0, min(1.0, score))


def extract_dom_context(dom_el: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant semantic, structural, and surrounding context from a matched DOM element.
    Preserves null/empty values without inventing data.
    """
    return {
        "tag": dom_el.get("tag"),
        "id": dom_el.get("id") or None,
        "name": dom_el.get("name") or None,
        "type": dom_el.get("type"),
        "text": dom_el.get("text") or None,
        "role": dom_el.get("role"),
        "aria_label": dom_el.get("aria_label"),
        "aria_labelledby_text": dom_el.get("aria_labelledby_text"),
        "aria_describedby": dom_el.get("aria_describedby"),
        "aria_expanded": dom_el.get("aria_expanded"),
        "aria_hidden": dom_el.get("aria_hidden"),
        "parent_section_id": dom_el.get("parent_section_id"),
        "parent_section": dom_el.get("parent_section"),
        "parent_landmark": dom_el.get("parent_landmark"),
        "nearest_heading": dom_el.get("nearest_heading"),
        "nearest_heading_level": dom_el.get("nearest_heading_level"),
        "surrounding_text": dom_el.get("surrounding_text") or None,
        "href": dom_el.get("href"),
        "css_path": dom_el.get("css_path"),
    }


def correlate_single_element(
    selenium_el: Dict[str, Any],
    dom_elements: List[Dict[str, Any]],
    match_threshold: float = 0.55,
    ambiguity_margin: float = 0.10,
) -> Dict[str, Any]:
    """
    Correlate a single focused Selenium element against candidate DOM interactive elements.

    Returns:
        {
            "status": "MATCHED" | "AMBIGUOUS" | "UNMATCHED",
            "confidence": float,
            "dom_element_index": int | None,
            "candidate_indices": list[int] | None,
            "dom_context": dict | None,
            "dom_element": dict | None
        }
    """
    if not dom_elements or not isinstance(selenium_el, dict):
        return {
            "status": "UNMATCHED",
            "confidence": 0.0,
            "dom_element_index": None,
            "candidate_indices": [],
            "dom_context": None,
            "dom_element": None,
        }

    # Score all candidate DOM elements
    scored_candidates: List[Tuple[int, float]] = []
    for idx, d_el in enumerate(dom_elements):
        sc = calculate_candidate_score(selenium_el, d_el)
        if sc >= match_threshold:
            scored_candidates.append((idx, sc))

    # Case 1: No candidate meets the matching threshold
    if not scored_candidates:
        return {
            "status": "UNMATCHED",
            "confidence": 0.0,
            "dom_element_index": None,
            "candidate_indices": [],
            "dom_context": None,
            "dom_element": None,
        }

    # Sort descending by score
    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    top_idx, top_score = scored_candidates[0]

    # Case 2: Single viable candidate
    if len(scored_candidates) == 1:
        matched_dom = dom_elements[top_idx]
        return {
            "status": "MATCHED",
            "confidence": round(top_score, 2),
            "dom_element_index": top_idx,
            "candidate_indices": None,
            "dom_context": extract_dom_context(matched_dom),
            "dom_element": copy.deepcopy(matched_dom),
        }

    # Case 3: Multiple viable candidates
    second_idx, second_score = scored_candidates[1]
    margin = top_score - second_score

    # If top candidate is decisively stronger, declare a clear MATCH
    if margin >= ambiguity_margin:
        matched_dom = dom_elements[top_idx]
        return {
            "status": "MATCHED",
            "confidence": round(top_score, 2),
            "dom_element_index": top_idx,
            "candidate_indices": None,
            "dom_context": extract_dom_context(matched_dom),
            "dom_element": copy.deepcopy(matched_dom),
        }

    # Otherwise, multiple candidates have similar high scores -> AMBIGUOUS
    ambiguous_indices = [
        idx for idx, sc in scored_candidates if (top_score - sc) <= ambiguity_margin
    ]
    return {
        "status": "AMBIGUOUS",
        "confidence": round(top_score, 2),
        "dom_element_index": None,
        "candidate_indices": ambiguous_indices,
        "dom_context": None,
        "dom_element": None,
    }


def correlate_direction_elements(
    steps: List[Dict[str, Any]],
    direction: str,
    dom_elements: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Correlate all synchronized steps in a given navigation direction (forward or backward).
    Preserves original synchronized elements while appending correlation findings and DOM context.
    """
    correlated_list = []
    for step_item in steps:
        step_num = step_item.get("step")
        selenium_el = step_item.get("selenium") or {}

        correlation_res = correlate_single_element(selenium_el, dom_elements)

        correlated_list.append({
            "direction": direction,
            "step": step_num,
            "synchronized_element": copy.deepcopy(step_item),
            "dom_element": correlation_res["dom_element"],
            "dom_context": correlation_res["dom_context"],
            "correlation": {
                "status": correlation_res["status"],
                "confidence": correlation_res["confidence"],
                "dom_element_index": correlation_res["dom_element_index"],
                "candidate_indices": correlation_res["candidate_indices"],
            },
        })

    return correlated_list


def assemble_unified_evidence_package(
    url: str,
    synchronized_output: Dict[str, Any],
    dom_snapshot: Dict[str, Any],
    screenshot_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Assembles a complete, unified multimodal evidence package combining:
    - Synchronized interaction evidence (forward & backward steps)
    - Semantic DOM structural snapshot (landmarks, headings, sections, interactive controls)
    - Webpage screenshot visual evidence (path, dimensions, format, fixed elements flag)
    - Explicit element-level correlation results and structural context

    Evidence-only transformation. Does NOT produce WCAG violation judgments.
    """
    dom_elements = dom_snapshot.get("interactive_elements", []) if isinstance(dom_snapshot, dict) else []

    forward_steps = synchronized_output.get("forward", []) if isinstance(synchronized_output, dict) else []
    backward_steps = synchronized_output.get("backward", []) if isinstance(synchronized_output, dict) else []

    # Correlate forward and backward directions independently
    correlated_forward = correlate_direction_elements(forward_steps, "forward", dom_elements)
    correlated_backward = correlate_direction_elements(backward_steps, "backward", dom_elements)
    all_correlated = correlated_forward + correlated_backward

    # Tally correlation statistics
    matched_count = sum(1 for c in all_correlated if c["correlation"]["status"] == "MATCHED")
    ambiguous_count = sum(1 for c in all_correlated if c["correlation"]["status"] == "AMBIGUOUS")
    unmatched_count = sum(1 for c in all_correlated if c["correlation"]["status"] == "UNMATCHED")
    total_count = len(all_correlated)
    match_rate = round((matched_count / total_count * 100.0), 1) if total_count > 0 else 0.0

    visual_evidence: Dict[str, Any] = {
        "status": "UNAVAILABLE",
        "screenshot": None,
    }
    if screenshot_metadata and isinstance(screenshot_metadata, dict):
        visual_evidence["status"] = screenshot_metadata.get("status", "UNAVAILABLE")
        visual_evidence["screenshot"] = copy.deepcopy(screenshot_metadata)

    unified_package = {
        "schema_version": "1.0",
        "url": url or synchronized_output.get("url", ""),
        "synchronized_evidence": {
            "forward": copy.deepcopy(forward_steps),
            "backward": copy.deepcopy(backward_steps),
        },
        "dom_snapshot": copy.deepcopy(dom_snapshot),
        "visual_evidence": visual_evidence,
        "correlated_elements": all_correlated,
        "correlation_summary": {
            "total_synchronized_elements": total_count,
            "forward_steps_count": len(forward_steps),
            "backward_steps_count": len(backward_steps),
            "matched_count": matched_count,
            "ambiguous_count": ambiguous_count,
            "unmatched_count": unmatched_count,
            "match_rate_percent": match_rate,
        },
    }

    logger.info(
        f"Unified evidence package assembled for {url}: {matched_count}/{total_count} matched ({match_rate}%)."
    )
    return unified_package
