"""
Webpage Screenshot Evidence Capture Tool.

Captures a visual representation of the audited webpage near the end of the
audit lifecycle (immediately before driver.quit()), providing objective
visual evidence for downstream multimodal analysis.

Key Characteristics:
- Evidence-only: Does NOT perform WCAG assessment or inject accessibility judgments.
- Non-intrusive: Does NOT move focus, reload the page, or manipulate DOM content.
- Full-page capture: Utilizes Chrome DevTools Protocol (CDP) `Page.captureScreenshot`
  with `captureBeyondViewport=True` to capture the entire document height without
  scrolling or altering viewport scroll state.
- Graceful degradation: Safely falls back to viewport capture (`get_screenshot_as_png`)
  if CDP is unavailable, explicitly reporting `capture_mode="VIEWPORT"`.
- Resilient: Never raises unhandled exceptions or crashes the audit runner if capture fails.
"""

import base64
import io
import logging
import os
import struct
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("ScreenshotCapture")

DEFAULT_SCREENSHOT_FILENAME = "webpage_screenshot.png"
MAX_TEXTURE_DIMENSION = 16384


def get_image_dimensions(image_bytes: bytes) -> Tuple[Optional[int], Optional[int]]:
    """
    Extract width and height from PNG bytes.
    First tries Pillow if installed, with a binary PNG IHDR header parsing fallback.
    """
    if not image_bytes:
        return None, None

    try:
        from PIL import Image

        with Image.open(io.BytesIO(image_bytes)) as img:
            return int(img.width), int(img.height)
    except Exception:
        pass

    # Standard PNG header binary parsing:
    # 8 bytes signature + 4 bytes length + 4 bytes chunk type ("IHDR") + 4 bytes width + 4 bytes height
    try:
        if len(image_bytes) >= 24 and image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            width, height = struct.unpack(">II", image_bytes[16:24])
            return width, height
    except Exception as e:
        logger.debug(f"Failed to parse PNG dimensions from binary header: {e}")

    return None, None


def get_relative_artifact_path(target_path: str, output_dir: Optional[str] = None) -> str:
    """
    Derive a portable, audit-relative or project-relative artifact path
    to avoid exposing machine-specific absolute filesystem paths in metadata.
    """
    if not target_path:
        return ""
    try:
        base_dir = os.path.abspath(output_dir) if output_dir else os.getcwd()
        rel = os.path.relpath(target_path, base_dir)
        if rel.startswith(".."):
            return os.path.basename(target_path)
        return rel.replace("\\", "/")
    except Exception:
        return os.path.basename(target_path)


def detect_fixed_position_elements(driver: Any) -> bool:
    """
    Generic DOM inspection to determine whether rendered fixed or sticky positioned
    elements are present on the webpage. Returns True if any rendered element has
    computed position 'fixed' or 'sticky' with non-zero dimensions.
    """
    if not driver or not hasattr(driver, "execute_script"):
        return False
    try:
        script = """
        try {
            var els = document.querySelectorAll('*');
            for (var i = 0; i < els.length; i++) {
                var s = window.getComputedStyle(els[i]);
                if (s && (s.position === 'fixed' || s.position === 'sticky')) {
                    var r = els[i].getBoundingClientRect();
                    if (r && r.width > 0 && r.height > 0) {
                        return true;
                    }
                }
            }
        } catch (e) {}
        return false;
        """
        return bool(driver.execute_script(script))
    except Exception as e:
        logger.debug(f"Failed to check for fixed position elements: {e}")
        return False


def capture_webpage_screenshot(
    driver: Any,
    output_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    filename: str = DEFAULT_SCREENSHOT_FILENAME,
    max_dimension: int = MAX_TEXTURE_DIMENSION,
) -> Dict[str, Any]:
    """
    Capture a full-page (or fallback viewport) screenshot of the current page state.

    Args:
        driver: Active Selenium WebDriver instance.
        output_path: Exact destination path for the screenshot file. If provided, overrides output_dir and filename.
        output_dir: Directory to save the screenshot into. Used if output_path is not specified.
        filename: Filename when output_dir is specified (default: 'webpage_screenshot.png').
        max_dimension: Maximum allowed dimension in pixels (default: 16384).

    Returns:
        Dict with screenshot metadata:
        {
            "status": "SUCCESS" | "FAILED",
            "path": str | None,
            "format": "png",
            "width": int | None,
            "height": int | None,
            "file_size_bytes": int,
            "capture_mode": "FULL_PAGE" | "VIEWPORT" | None,
            "fixed_position_elements_possible": bool,
            "error": str (only if status is "FAILED")
        }
    """
    # Resolve target filesystem path (always absolute internally for I/O)
    if output_path:
        target_path = os.path.abspath(output_path)
    elif output_dir:
        target_path = os.path.abspath(os.path.join(output_dir, filename))
    else:
        target_path = os.path.abspath(filename)

    # Derive portable relative artifact path for metadata
    reported_path = get_relative_artifact_path(target_path, output_dir=output_dir)

    result_meta: Dict[str, Any] = {
        "status": "FAILED",
        "path": reported_path,
        "format": "png",
        "width": None,
        "height": None,
        "file_size_bytes": 0,
        "capture_mode": None,
        "fixed_position_elements_possible": False,
    }

    if driver is None:
        logger.warning("WebDriver is None; cannot capture webpage screenshot.")
        result_meta["error"] = "WebDriver instance is None"
        return result_meta

    # Check for fixed-position elements generically (does NOT alter DOM or screenshot)
    fixed_elements_present = detect_fixed_position_elements(driver)
    result_meta["fixed_position_elements_possible"] = fixed_elements_present

    png_bytes: Optional[bytes] = None
    capture_mode: Optional[str] = None
    error_msg: Optional[str] = None

    # Step 1: Attempt true full-page capture via Chrome DevTools Protocol (CDP)
    if hasattr(driver, "execute_cdp_cmd"):
        try:
            cdp_params: Dict[str, Any] = {
                "captureBeyondViewport": True,
                "fromSurface": True,
            }

            raw_cdp = driver.execute_cdp_cmd("Page.captureScreenshot", cdp_params)
            if isinstance(raw_cdp, dict) and "data" in raw_cdp:
                png_bytes = base64.b64decode(raw_cdp["data"])
                capture_mode = "FULL_PAGE"
                logger.info("Captured full-page screenshot via Chrome DevTools Protocol.")
            else:
                logger.warning(f"Unexpected CDP Page.captureScreenshot response: {type(raw_cdp)}")
        except Exception as cdp_err:
            logger.warning(
                f"CDP Page.captureScreenshot full-page capture failed: {cdp_err}. Falling back to viewport capture."
            )
            error_msg = f"CDP error: {cdp_err}"

    # Step 2: Fallback to standard Selenium viewport screenshot if CDP failed or not supported
    if png_bytes is None:
        try:
            if hasattr(driver, "get_screenshot_as_png"):
                png_bytes = driver.get_screenshot_as_png()
                capture_mode = "VIEWPORT"
                logger.info("Captured standard viewport screenshot (fallback).")
            else:
                raise AttributeError("Driver does not support get_screenshot_as_png")
        except Exception as vp_err:
            logger.error(f"Viewport screenshot fallback failed: {vp_err}")
            combined_err = f"{error_msg}; Viewport fallback failed: {vp_err}" if error_msg else str(vp_err)
            result_meta["error"] = combined_err
            return result_meta

    if not png_bytes:
        result_meta["error"] = "Captured screenshot data is empty."
        return result_meta

    # Step 3: Parse image dimensions
    width, height = get_image_dimensions(png_bytes)

    # Step 4: Write screenshot file to disk
    try:
        target_dir = os.path.dirname(target_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)

        with open(target_path, "wb") as f:
            f.write(png_bytes)

        result_meta["status"] = "SUCCESS"
        result_meta["path"] = reported_path
        result_meta["width"] = width
        result_meta["height"] = height
        result_meta["file_size_bytes"] = len(png_bytes)
        result_meta["capture_mode"] = capture_mode
        logger.info(
            f"Saved {capture_mode} screenshot to {target_path} ({width}x{height}, {len(png_bytes)} bytes)"
        )
        return result_meta
    except Exception as io_err:
        logger.error(f"Failed to write screenshot file to {target_path}: {io_err}", exc_info=True)
        result_meta["error"] = f"File write error: {io_err}"
        return result_meta
