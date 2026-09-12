"""
Unit and integration tests for tools/screenshot_capture.py.
"""

import base64
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from tools.screenshot_capture import (
    capture_webpage_screenshot,
    get_image_dimensions,
    DEFAULT_SCREENSHOT_FILENAME,
)

# 1x1 valid PNG bytes (68 bytes)
TINY_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

# 100x50 valid PNG bytes
SAMPLE_100x50_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x64"  # width: 100
    b"\x00\x00\x00\x32"  # height: 50
    b"\x08\x02\x00\x00\x00"
    b"\x00\x00\x00\x00"  # mock crc/trailing
)


class TestScreenshotCapture(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="screenshot_test_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_image_dimensions_tiny_png(self):
        """Test parsing dimensions from tiny 1x1 PNG."""
        width, height = get_image_dimensions(TINY_PNG_BYTES)
        self.assertEqual(width, 1)
        self.assertEqual(height, 1)

    def test_get_image_dimensions_binary_header_fallback(self):
        """Test fallback parsing of dimensions from raw IHDR chunk."""
        width, height = get_image_dimensions(SAMPLE_100x50_PNG)
        self.assertEqual(width, 100)
        self.assertEqual(height, 50)

    def test_get_image_dimensions_empty_or_corrupt(self):
        """Test get_image_dimensions on empty or non-PNG bytes."""
        self.assertEqual(get_image_dimensions(b""), (None, None))
        self.assertEqual(get_image_dimensions(b"NOT_A_PNG"), (None, None))

    def test_successful_fullpage_capture_cdp(self):
        """CDP captureScreenshot succeeds -> FULL_PAGE capture_mode, file written, metadata complete."""
        mock_driver = MagicMock()
        mock_driver.execute_cdp_cmd.return_value = {
            "data": base64.b64encode(TINY_PNG_BYTES).decode("utf-8")
        }
        mock_driver.execute_script.return_value = False

        out_path = os.path.join(self.temp_dir, "test_shot.png")
        meta = capture_webpage_screenshot(mock_driver, output_path=out_path)

        self.assertEqual(meta["status"], "SUCCESS")
        self.assertEqual(meta["capture_mode"], "FULL_PAGE")
        self.assertEqual(meta["format"], "png")
        self.assertEqual(meta["width"], 1)
        self.assertEqual(meta["height"], 1)
        self.assertEqual(meta["file_size_bytes"], len(TINY_PNG_BYTES))
        # Portable relative artifact path
        self.assertEqual(meta["path"], "test_shot.png")
        self.assertFalse(meta["fixed_position_elements_possible"])
        self.assertTrue(os.path.isfile(out_path))

        with open(out_path, "rb") as f:
            saved_content = f.read()
        self.assertEqual(saved_content, TINY_PNG_BYTES)

    def test_output_dir_parameter_handling(self):
        """Specifying output_dir places default filename inside target directory and reports relative name."""
        mock_driver = MagicMock()
        mock_driver.execute_cdp_cmd.return_value = {
            "data": base64.b64encode(TINY_PNG_BYTES).decode("utf-8")
        }

        meta = capture_webpage_screenshot(mock_driver, output_dir=self.temp_dir)
        expected_path = os.path.abspath(os.path.join(self.temp_dir, DEFAULT_SCREENSHOT_FILENAME))

        self.assertEqual(meta["status"], "SUCCESS")
        # Reported path is portable and relative to output_dir
        self.assertEqual(meta["path"], DEFAULT_SCREENSHOT_FILENAME)
        self.assertTrue(os.path.isfile(expected_path))

    def test_fallback_to_viewport_when_cdp_fails(self):
        """When CDP raises exception, falls back to get_screenshot_as_png with VIEWPORT mode."""
        mock_driver = MagicMock()
        mock_driver.execute_cdp_cmd.side_effect = RuntimeError("CDP command failed")
        mock_driver.get_screenshot_as_png.return_value = TINY_PNG_BYTES

        out_path = os.path.join(self.temp_dir, "fallback_viewport.png")
        meta = capture_webpage_screenshot(mock_driver, output_path=out_path)

        self.assertEqual(meta["status"], "SUCCESS")
        self.assertEqual(meta["capture_mode"], "VIEWPORT")
        self.assertEqual(meta["path"], "fallback_viewport.png")
        self.assertTrue(os.path.isfile(out_path))

    def test_fallback_when_cdp_not_supported(self):
        """When driver lacks execute_cdp_cmd attribute, uses get_screenshot_as_png directly."""
        class ViewportOnlyDriver:
            def get_screenshot_as_png(self):
                return TINY_PNG_BYTES

        driver = ViewportOnlyDriver()
        out_path = os.path.join(self.temp_dir, "viewport_only.png")
        meta = capture_webpage_screenshot(driver, output_path=out_path)

        self.assertEqual(meta["status"], "SUCCESS")
        self.assertEqual(meta["capture_mode"], "VIEWPORT")
        self.assertEqual(meta["path"], "viewport_only.png")
        self.assertTrue(os.path.isfile(out_path))

    def test_capture_failure_reported_explicitly_when_both_fail(self):
        """When both CDP and viewport capture fail, returns FAILED status and does not fabricate file."""
        mock_driver = MagicMock()
        mock_driver.execute_cdp_cmd.side_effect = RuntimeError("CDP crash")
        mock_driver.get_screenshot_as_png.side_effect = RuntimeError("Viewport crash")

        out_path = os.path.join(self.temp_dir, "failed_capture.png")
        meta = capture_webpage_screenshot(mock_driver, output_path=out_path)

        self.assertEqual(meta["status"], "FAILED")
        self.assertIn("error", meta)
        self.assertIsNone(meta["capture_mode"])
        self.assertEqual(meta["path"], "failed_capture.png")
        self.assertFalse(os.path.exists(out_path))

    def test_capture_with_none_driver(self):
        """Passing driver=None reports explicit failure without raising an exception."""
        out_path = os.path.join(self.temp_dir, "none_driver.png")
        meta = capture_webpage_screenshot(None, output_path=out_path)

        self.assertEqual(meta["status"], "FAILED")
        self.assertEqual(meta["error"], "WebDriver instance is None")
        self.assertEqual(meta["path"], "none_driver.png")
        self.assertFalse(os.path.exists(out_path))

    def test_fixed_position_elements_detection_mock(self):
        """detect_fixed_position_elements reports True when driver script finds fixed/sticky elements."""
        mock_driver = MagicMock()
        mock_driver.execute_cdp_cmd.return_value = {
            "data": base64.b64encode(TINY_PNG_BYTES).decode("utf-8")
        }
        mock_driver.execute_script.return_value = True

        out_path = os.path.join(self.temp_dir, "fixed_test.png")
        meta = capture_webpage_screenshot(mock_driver, output_path=out_path)

        self.assertEqual(meta["status"], "SUCCESS")
        self.assertTrue(meta["fixed_position_elements_possible"])

    def test_capture_file_io_error(self):
        """File write errors are caught safely and reported in metadata."""
        mock_driver = MagicMock()
        mock_driver.execute_cdp_cmd.return_value = {
            "data": base64.b64encode(TINY_PNG_BYTES).decode("utf-8")
        }

        # Target an invalid path (e.g. existing directory as target file name)
        invalid_file_path = self.temp_dir  # Writing directly to directory path will raise IsADirectoryError / PermissionError
        meta = capture_webpage_screenshot(mock_driver, output_path=invalid_file_path)

        self.assertEqual(meta["status"], "FAILED")
        self.assertIn("error", meta)


class TestRealBrowserScreenshotCapture(unittest.TestCase):
    """Integration tests using real headless Chrome."""

    @classmethod
    def setUpClass(cls):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--window-size=1024,768")
        cls.driver = webdriver.Chrome(options=opts)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "driver") and cls.driver:
            cls.driver.quit()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="real_screenshot_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fullpage_capture_covers_entire_tall_document(self):
        """
        Verify that a tall document (2500px tall) in a 768px viewport
        is captured in its entirety by CDP without altering scroll position.
        """
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Tall Page Test</title></head>
        <body style="margin:0; padding:0; background: #fff;">
            <header style="height: 200px; background: #333; color: white;">
                <h1>Header at Top</h1>
            </header>
            <div style="height: 2000px; background: #eee;">
                <p>Middle Content</p>
            </div>
            <footer style="height: 300px; background: #222; color: white;">
                <p>Footer at Bottom</p>
            </footer>
        </body>
        </html>
        """
        import base64
        data_url = "data:text/html;base64," + base64.b64encode(html.encode("utf-8")).decode("utf-8")
        self.driver.get(data_url)

        # Scroll page down midway to simulate traversal having scrolled the page
        self.driver.execute_script("window.scrollTo(0, 1200);")
        scroll_before = self.driver.execute_script("return window.scrollY;")
        self.assertGreater(scroll_before, 0)

        out_path = os.path.join(self.temp_dir, "tall_page_full.png")
        meta = capture_webpage_screenshot(self.driver, output_path=out_path)

        # 1. Capture succeeded and is full page
        self.assertEqual(meta["status"], "SUCCESS")
        self.assertEqual(meta["capture_mode"], "FULL_PAGE")
        self.assertTrue(os.path.isfile(out_path))

        # 2. Captured height covers the document (> 2000px), not merely the 768px viewport
        self.assertGreater(meta["height"], 2000)
        self.assertGreater(meta["file_size_bytes"], 1000)

        # 3. Scroll position was NOT altered by capture
        scroll_after = self.driver.execute_script("return window.scrollY;")
        self.assertEqual(scroll_before, scroll_after)

    def test_real_browser_fixed_elements_detection(self):
        """
        Verify that real Chrome detects fixed-position elements generically
        and reports fixed_position_elements_possible=True.
        """
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Fixed Element Test</title></head>
        <body style="margin:0; padding:0; height: 1500px;">
            <div style="position: fixed; bottom: 0; width: 100%; height: 50px; background: red;">
                Sticky Footer
            </div>
            <div>Content</div>
        </body>
        </html>
        """
        import base64
        data_url = "data:text/html;base64," + base64.b64encode(html.encode("utf-8")).decode("utf-8")
        self.driver.get(data_url)

        out_path = os.path.join(self.temp_dir, "fixed_page.png")
        meta = capture_webpage_screenshot(self.driver, output_path=out_path)

        self.assertEqual(meta["status"], "SUCCESS")
        self.assertTrue(meta["fixed_position_elements_possible"])
        self.assertEqual(meta["path"], "fixed_page.png")


if __name__ == "__main__":
    unittest.main()
