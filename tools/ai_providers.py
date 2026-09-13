"""
AI Provider Abstraction Layer (Gemini-Powered)
Provides a modular interface for Large Language Model integrations (Google Gemini, Mock, Fallback)
with robust error handling, rate limiting tolerance, and zero hardcoded credentials.
"""

import os
import json
import base64
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("AIAccessibilityAgent.Providers")


def load_screenshot_image(
    image_path: Optional[str],
    max_bytes: int = 20 * 1024 * 1024,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Safely load a screenshot image from disk and encode it as base64 for Gemini multimodal input.
    Validates:
    - Non-empty path string
    - File exists and is a regular file
    - File size is within safe bounds (default 20MB)
    - Supported extension/MIME type (png, jpg, jpeg, webp)

    Returns:
        (image_part_dict, error_string)
        Where image_part_dict is:
        {
            "inline_data": {
                "mime_type": "<MIME_TYPE>",
                "data": "<BASE64_STRING>"
            }
        }
        Or (None, error_string) if loading failed or path unavailable.
    """
    if not image_path or not isinstance(image_path, str) or not image_path.strip():
        return None, "Screenshot path is empty or not a string."

    clean_path = image_path.strip()
    if not os.path.exists(clean_path):
        return None, f"Screenshot file does not exist: {clean_path}"

    if not os.path.isfile(clean_path):
        return None, f"Screenshot path is not a regular file: {clean_path}"

    ext = os.path.splitext(clean_path)[1].lower().lstrip(".")
    mime_map = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }
    mime_type = mime_map.get(ext, "image/png")

    try:
        file_size = os.path.getsize(clean_path)
        if file_size == 0:
            return None, f"Screenshot file is empty (0 bytes): {clean_path}"
        if file_size > max_bytes:
            return None, f"Screenshot file exceeds maximum allowed size ({file_size} > {max_bytes} bytes): {clean_path}"

        with open(clean_path, "rb") as img_file:
            raw_bytes = img_file.read()

        b64_data = base64.b64encode(raw_bytes).decode("ascii")
        logger.info(f"Loaded screenshot evidence ({len(raw_bytes)} bytes, {mime_type}) for multimodal analysis.")
        return {
            "inline_data": {
                "mime_type": mime_type,
                "data": b64_data,
            }
        }, None

    except Exception as e:
        logger.warning(f"Failed to read screenshot file from {clean_path}: {e}")
        return None, f"Failed to read screenshot file: {str(e)}"


def _load_env_file():
    """Lightweight loader for .env file in workspace root if present."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_file = os.path.join(root_dir, ".env")
    if os.path.isfile(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


_load_env_file()


class LLMResponse:
    """Standardized response from an LLM provider."""

    def __init__(
        self,
        raw_text: str = "",
        structured_data: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error: Optional[str] = None,
        provider_name: str = "unknown",
        model_name: str = "unknown",
    ):
        self.raw_text = raw_text
        self.structured_data = structured_data or {}
        self.success = success
        self.error = error
        self.provider_name = provider_name
        self.model_name = model_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "structured_data": self.structured_data,
            "error": self.error,
            "provider_name": self.provider_name,
            "model_name": self.model_name,
        }


class BaseLLMProvider(ABC):
    """Abstract Base Class for LLM providers."""

    def __init__(self, provider_name: str, model_name: str):
        self.provider_name = provider_name
        self.model_name = model_name

    @abstractmethod
    def generate_analysis(
        self,
        system_prompt: str,
        user_prompt: str,
        violation_data: Optional[Dict[str, Any]] = None,
        image_data: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        """
        Generate structured analysis.
        Works for full synchronized accessibility audits, multimodal audits, and enrichment.
        Optionally accepts image_data (e.g. inline base64 screenshot) for multimodal reasoning.
        """
        pass


ACCESSIBILITY_ANALYSIS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "analysis_status": {
            "type": "STRING",
            "enum": ["COMPLETED", "NO_VIOLATIONS", "PARTIAL", "FAILED", "AI_ANALYSIS_UNAVAILABLE"],
        },
        "summary": {
            "type": "OBJECT",
            "properties": {
                "total_elements_analyzed": {"type": "INTEGER"},
                "total_violations": {"type": "INTEGER"},
                "total_recommendations": {"type": "INTEGER"},
                "compliance_score": {"type": "NUMBER"},
                "severity_summary": {
                    "type": "OBJECT",
                    "properties": {
                        "CRITICAL": {"type": "INTEGER"},
                        "MAJOR": {"type": "INTEGER"},
                        "MINOR": {"type": "INTEGER"},
                        "INFO": {"type": "INTEGER"},
                    },
                    "required": ["CRITICAL", "MAJOR", "MINOR", "INFO"],
                },
            },
            "required": [
                "total_elements_analyzed",
                "total_violations",
                "total_recommendations",
                "compliance_score",
                "severity_summary",
            ],
        },
        "violations": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "violation_id": {"type": "STRING"},
                    "scope": {"type": "STRING", "enum": ["ELEMENT", "PAGE"]},
                    "element_reference": {
                        "type": "OBJECT",
                        "properties": {
                            "direction": {"type": "STRING"},
                            "step": {"type": "INTEGER"},
                            "tag": {"type": "STRING"},
                            "src": {"type": "STRING"},
                            "id": {"type": "STRING"},
                            "selector": {"type": "STRING"},
                        },
                    },
                    "rule_id": {"type": "STRING"},
                    "rule_name": {"type": "STRING"},
                    "severity": {
                        "type": "STRING",
                        "enum": ["CRITICAL", "MAJOR", "MINOR", "INFO"],
                    },
                    "confidence": {"type": "NUMBER"},
                    "title": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "ai_rationale": {"type": "STRING"},
                    "normative_basis": {
                        "type": "OBJECT",
                        "properties": {
                            "success_criterion": {
                                "type": "STRING",
                                "description": "Strictly the WCAG Success Criterion number only e.g. '2.4.4', '1.1.1', '4.1.2'",
                            },
                            "level": {
                                "type": "STRING",
                                "enum": ["A", "AA", "AAA"],
                                "description": "WCAG Conformance level: 'A', 'AA', or 'AAA'",
                            },
                            "requirement": {
                                "type": "STRING",
                                "description": "The exact normative requirement sentence from the WCAG specification",
                            },
                            "failure_condition": {
                                "type": "STRING",
                                "description": "The specific observed failure condition established by multimodal evidence",
                            },
                            "evidence_basis": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "STRING",
                                    "enum": ["DOM", "NVDA", "VISUAL", "INTERACTION"],
                                },
                                "description": "Evidence modalities actually evaluated: DOM, NVDA, VISUAL, INTERACTION",
                            },
                        },
                        "required": [
                            "success_criterion",
                            "level",
                            "requirement",
                            "failure_condition",
                            "evidence_basis",
                        ],
                    },
                    "user_impact": {"type": "STRING"},
                    "wcag_context": {"type": "STRING"},
                    "recommendation": {"type": "STRING"},
                    "developer_guidance": {"type": "STRING"},
                },
                "required": [
                    "violation_id",
                    "scope",
                    "rule_id",
                    "rule_name",
                    "severity",
                    "confidence",
                    "title",
                    "description",
                    "ai_rationale",
                    "user_impact",
                    "wcag_context",
                    "recommendation",
                    "developer_guidance",
                ],
            },
        },
        "recommendations": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "recommendation_id": {"type": "STRING"},
                    "scope": {"type": "STRING", "enum": ["ELEMENT", "PAGE"]},
                    "element_reference": {
                        "type": "OBJECT",
                        "properties": {
                            "direction": {"type": "STRING"},
                            "step": {"type": "INTEGER"},
                            "tag": {"type": "STRING"},
                            "src": {"type": "STRING"},
                            "id": {"type": "STRING"},
                            "selector": {"type": "STRING"},
                        },
                    },
                    "category": {
                        "type": "STRING",
                        "enum": ["BEST_PRACTICE", "STRUCTURAL_ENHANCEMENT", "ADVISORY"],
                    },
                    "title": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "ai_rationale": {"type": "STRING"},
                    "user_impact": {"type": "STRING"},
                    "related_guidance": {
                        "type": "OBJECT",
                        "properties": {
                            "success_criterion": {"type": "STRING"},
                            "relationship": {"type": "STRING"},
                            "technique": {"type": "STRING"},
                        },
                    },
                    "developer_guidance": {"type": "STRING"},
                    "code_example": {"type": "STRING"},
                },
                "required": [
                    "recommendation_id",
                    "scope",
                    "category",
                    "title",
                    "description",
                    "ai_rationale",
                    "user_impact",
                    "developer_guidance",
                ],
            },
        },
    },
    "required": ["analysis_status", "summary", "violations", "recommendations"],
}


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic mock provider for unit testing and offline verification.
    Simulates:
    1. Zero violations (fully accessible page)
    2. Single violation
    3. Multiple violations
    4. Invalid structured JSON output
    5. Provider failure / network exception
    """

    def __init__(
        self,
        model_name: str = "mock-gemini-v1",
        custom_response: Optional[Dict[str, Any]] = None,
        simulate_error: Optional[str] = None,
        simulate_invalid_json: bool = False,
        mode: str = "default",
    ):
        super().__init__(provider_name="MockProvider", model_name=model_name)
        self.custom_response = custom_response
        self.simulate_error = simulate_error
        self.simulate_invalid_json = simulate_invalid_json
        self.mode = mode
        self.call_count = 0
        self.last_violation_data = None
        self.last_user_prompt = None
        self.last_system_prompt = None
        self.last_image_data = None

    def generate_analysis(
        self,
        system_prompt: str,
        user_prompt: str,
        violation_data: Optional[Dict[str, Any]] = None,
        image_data: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        self.call_count += 1
        self.last_violation_data = violation_data
        self.last_user_prompt = user_prompt
        self.last_system_prompt = system_prompt
        self.last_image_data = image_data

        if self.simulate_error:
            return LLMResponse(
                raw_text="",
                structured_data=None,
                success=False,
                error=self.simulate_error,
                provider_name=self.provider_name,
                model_name=self.model_name,
            )

        if self.simulate_invalid_json:
            return LLMResponse(
                raw_text="NOT A VALID JSON RESPONSE {{{",
                structured_data=None,
                success=True,  # HTTP/raw call succeeded but body is invalid JSON
                error="Invalid JSON payload returned",
                provider_name=self.provider_name,
                model_name=self.model_name,
            )

        if self.custom_response is not None:
            return LLMResponse(
                raw_text=json.dumps(self.custom_response),
                structured_data=self.custom_response,
                success=True,
                provider_name=self.provider_name,
                model_name=self.model_name,
            )

        # Mode: zero_violations
        if self.mode == "zero_violations":
            zero_resp = {
                "analysis_status": "COMPLETED",
                "summary": {
                    "total_elements_analyzed": 10,
                    "total_violations": 0,
                    "total_recommendations": 0,
                    "compliance_score": 100.0,
                    "severity_summary": {
                        "CRITICAL": 0,
                        "MAJOR": 0,
                        "MINOR": 0,
                        "INFO": 0,
                    },
                },
                "violations": [],
                "recommendations": [],
            }
            return LLMResponse(
                raw_text=json.dumps(zero_resp),
                structured_data=zero_resp,
                success=True,
                provider_name=self.provider_name,
                model_name=self.model_name,
            )

        # Mode: single_violation
        if self.mode == "single_violation":
            single_resp = {
                "analysis_status": "COMPLETED",
                "summary": {
                    "total_elements_analyzed": 5,
                    "total_violations": 1,
                    "total_recommendations": 0,
                    "compliance_score": 85.0,
                    "severity_summary": {
                        "CRITICAL": 1,
                        "MAJOR": 0,
                        "MINOR": 0,
                        "INFO": 0,
                    },
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
                        "title": "Unlabelled Interactive Link",
                        "description": "The interactive link contains no accessible name or text alternative.",
                        "ai_rationale": "DOM <a> element has empty text and no aria-label, confirmed by NVDA announcing 'graphic link' with empty name.",
                        "user_impact": "Screen reader users cannot identify the target or purpose of this interactive link.",
                        "wcag_context": "WCAG 2.1 Success Criterion 4.1.2 Name, Role, Value (Level A).",
                        "recommendation": "Provide an explicit, descriptive accessible name using aria-label or inner text.",
                        "developer_guidance": '<a href="/login" aria-label="[Descriptive accessible name]">\n  <svg ...></svg>\n</a>',
                    }
                ],
                "recommendations": [],
            }
            return LLMResponse(
                raw_text=json.dumps(single_resp),
                structured_data=single_resp,
                success=True,
                provider_name=self.provider_name,
                model_name=self.model_name,
            )

        # Mode: multiple_violations
        if self.mode == "multiple_violations":
            multi_resp = {
                "analysis_status": "COMPLETED",
                "summary": {
                    "total_elements_analyzed": 12,
                    "total_violations": 2,
                    "total_recommendations": 0,
                    "compliance_score": 77.0,
                    "severity_summary": {
                        "CRITICAL": 1,
                        "MAJOR": 1,
                        "MINOR": 0,
                        "INFO": 0,
                    },
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
                        "title": "Unlabelled Interactive Link",
                        "description": "The interactive link lacks an accessible name in DOM and NVDA.",
                        "ai_rationale": "Interactive anchor has no accessible text or aria-label; NVDA announced an unlabelled graphic link.",
                        "user_impact": "Blind users cannot determine the link target.",
                        "wcag_context": "WCAG 4.1.2 Name, Role, Value (Level A).",
                        "recommendation": "Add a descriptive accessible name via aria-label.",
                        "developer_guidance": '<a href="/portal" aria-label="[Descriptive accessible name]">Portal</a>',
                    },
                    {
                        "violation_id": "AI-002",
                        "scope": "ELEMENT",
                        "element_reference": {"direction": "forward", "step": 3},
                        "rule_id": "WCAG 2.4.4",
                        "rule_name": "Link Purpose (In Context)",
                        "severity": "MAJOR",
                        "confidence": 0.88,
                        "title": "Ambiguous Link Text ('Click here')",
                        "description": "Link text 'Click here' is non-descriptive out of context.",
                        "ai_rationale": "Link text 'Click here' provides zero contextual indication of destination when read by screen reader.",
                        "user_impact": "Screen reader users navigating links list will encounter uninformative purpose.",
                        "wcag_context": "WCAG 2.4.4 Link Purpose (In Context) (Level A).",
                        "recommendation": "Replace generic link text with a descriptive target description.",
                        "developer_guidance": '<a href="/details">[Descriptive destination name]</a>',
                    },
                ],
                "recommendations": [],
            }
            return LLMResponse(
                raw_text=json.dumps(multi_resp),
                structured_data=multi_resp,
                success=True,
                provider_name=self.provider_name,
                model_name=self.model_name,
            )

        # Legacy enrichment support when violation_data is passed
        if violation_data is not None:
            rule_id = violation_data.get("rule_id", "WCAG Unknown")
            rule_name = violation_data.get("rule_name", "Accessibility Guideline")
            severity = violation_data.get("severity", "MAJOR")
            title = violation_data.get("title", "Accessibility Issue")
            element_info = violation_data.get("element_info", {})
            tag = element_info.get("tag", "element")

            mock_data = {
                "explanation": f"The <{tag}> element fails {rule_id} ({rule_name}) because it lacks an accessible name or required state in the accessibility tree.",
                "user_impact": "Screen reader users will hear an unlabelled or ambiguous announcement, preventing them from understanding or interacting with the control.",
                "severity_reasoning": f"Classified as {severity} because it directly hinders primary assistive navigation.",
                "wcag_context": f"Violates {rule_id} ({rule_name}). Level A / AA requirement for assistive technology compatibility.",
                "recommendation": f"Provide an explicit accessible name using text content, aria-label, or associated label for the <{tag}> element.",
                "developer_guidance": f"Add an aria-label attribute (e.g. <{tag} aria-label=\"[Descriptive accessible name]\">) or visible label to the <{tag}> element.",
            }

            return LLMResponse(
                raw_text=json.dumps(mock_data),
                structured_data=mock_data,
                success=True,
                provider_name=self.provider_name,
                model_name=self.model_name,
            )

        # Default synchronized analysis mock response
        default_resp = {
            "analysis_status": "COMPLETED",
            "summary": {
                "total_elements_analyzed": 1,
                "total_violations": 1,
                "total_recommendations": 0,
                "compliance_score": 85.0,
                "severity_summary": {
                    "CRITICAL": 1,
                    "MAJOR": 0,
                    "MINOR": 0,
                    "INFO": 0,
                },
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
                    "title": "Unlabelled Interactive Control",
                    "description": "Interactive element has no accessible name or text alternative.",
                    "ai_rationale": "Captured DOM link and NVDA announcement lack any accessible name.",
                    "user_impact": "Screen reader users cannot identify control purpose.",
                    "wcag_context": "WCAG 4.1.2 Name, Role, Value (Level A).",
                    "recommendation": "Provide an explicit accessible name using aria-label or visible text.",
                    "developer_guidance": '<a href="/" aria-label="[Descriptive accessible name]">[Descriptive accessible name]</a>',
                }
            ],
            "recommendations": [],
        }

        return LLMResponse(
            raw_text=json.dumps(default_resp),
            structured_data=default_resp,
            success=True,
            provider_name=self.provider_name,
            model_name=self.model_name,
        )


class FallbackLLMProvider(BaseLLMProvider):
    """
    Fallback provider invoked when Gemini credentials are missing or external AI service is unavailable.
    IMPORTANT ARCHITECTURAL RULE:
    Does NOT silently pretend deterministic analysis is AI findings.
    Explicitly reports that the AI analysis is unavailable or failed.
    """

    def __init__(self, reason: str = "AI service not configured or offline"):
        super().__init__(provider_name="FallbackProvider", model_name="ai-unavailable")
        self.reason = reason
        self.call_count = 0

    def generate_analysis(
        self,
        system_prompt: str,
        user_prompt: str,
        violation_data: Optional[Dict[str, Any]] = None,
        image_data: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        self.call_count += 1
        self.last_image_data = image_data
        unavailable_data = {
            "analysis_status": "AI_ANALYSIS_UNAVAILABLE",
            "error": self.reason,
            "summary": {
                "total_elements_analyzed": 0,
                "total_violations": 0,
                "total_recommendations": 0,
                "compliance_score": 0.0,
                "severity_summary": {
                    "CRITICAL": 0,
                    "MAJOR": 0,
                    "MINOR": 0,
                    "INFO": 0,
                },
            },
            "violations": [],
            "recommendations": [],
        }

        return LLMResponse(
            raw_text=json.dumps(unavailable_data),
            structured_data=unavailable_data,
            success=False,
            error=self.reason,
            provider_name=self.provider_name,
            model_name=self.model_name,
        )


class GeminiLLMProvider(BaseLLMProvider):
    """
    Google Gemini LLM provider.
    Reads API key from GEMINI_API_KEY environment variable.
    Defaults to gemini-2.5-flash (or GEMINI_MODEL if specified).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: int = 90,
    ):
        resolved_model = model_name or os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
        super().__init__(provider_name="GeminiProvider", model_name=resolved_model)
        self.api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY")
        self.timeout = int(os.environ.get("GEMINI_TIMEOUT", timeout))

    def generate_analysis(
        self,
        system_prompt: str,
        user_prompt: str,
        violation_data: Optional[Dict[str, Any]] = None,
        image_data: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(
                success=False,
                error="GEMINI_API_KEY is not configured.",
                provider_name=self.provider_name,
                model_name=self.model_name,
            )

        try:
            import requests
            import re

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}

            # Build multimodal content parts
            content_parts = [{"text": user_prompt}]
            if image_data and isinstance(image_data, dict):
                content_parts.append(image_data)

            payload = {
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": content_parts}],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "response_schema": ACCESSIBILITY_ANALYSIS_SCHEMA,
                    "temperature": 0.1,
                },
            }

            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)

            if response.status_code != 200:
                return LLMResponse(
                    raw_text=response.text,
                    success=False,
                    error=f"Gemini API returned HTTP {response.status_code}: {response.text[:200]}",
                    provider_name=self.provider_name,
                    model_name=self.model_name,
                )

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return LLMResponse(
                    raw_text=response.text,
                    success=False,
                    error="Gemini returned no response candidates.",
                    provider_name=self.provider_name,
                    model_name=self.model_name,
                )

            content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            # Clean markdown JSON fences if model wraps response
            if content_text.startswith("```"):
                content_text = re.sub(r"^```(?:json)?\s*", "", content_text)
                content_text = re.sub(r"\s*```$", "", content_text).strip()

            parsed_json = json.loads(content_text)

            return LLMResponse(
                raw_text=content_text,
                structured_data=parsed_json,
                success=True,
                provider_name=self.provider_name,
                model_name=self.model_name,
            )

        except json.JSONDecodeError as jde:
            return LLMResponse(
                raw_text=str(jde),
                success=False,
                error=f"Model response was not valid JSON: {str(jde)}",
                provider_name=self.provider_name,
                model_name=self.model_name,
            )
        except Exception as e:
            return LLMResponse(
                raw_text="",
                success=False,
                error=f"Gemini request failed: {str(e)}",
                provider_name=self.provider_name,
                model_name=self.model_name,
            )


def get_default_provider(provider_type: Optional[str] = None, **kwargs) -> BaseLLMProvider:
    """
    Factory function to initialize the configured LLM provider.
    Checks environment variables if no explicit provider is requested:
    1. Explicit type passed
    2. GEMINI_API_KEY present -> GeminiLLMProvider
    3. Fallback -> FallbackLLMProvider
    """
    pt = (provider_type or os.environ.get("LLM_PROVIDER", "")).strip().lower()

    if pt == "mock":
        return MockLLMProvider(**kwargs)
    elif pt in ("gemini", "google"):
        return GeminiLLMProvider(**kwargs)
    elif pt == "fallback":
        return FallbackLLMProvider(**kwargs)

    # Auto-detection for Gemini
    if os.environ.get("GEMINI_API_KEY"):
        return GeminiLLMProvider(**kwargs)

    return FallbackLLMProvider(
        reason="No GEMINI_API_KEY detected in environment; AI accessibility analysis unavailable."
    )

