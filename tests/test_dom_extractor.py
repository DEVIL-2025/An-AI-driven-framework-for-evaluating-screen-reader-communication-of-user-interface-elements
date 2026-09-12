"""
Unit Tests for DOM / Structural Snapshot Extractor Module (Phase 1 Refined).
Tests structural extraction across all 10 Phase 1 Refinement criteria:
1. Generic <div>-based meaningful grouping (panels, navbars, card-groups).
2. Correct heading/context association (associating headings when inside same section/container).
3. Returning null rather than an unrelated heading (e.g. controls preceding headings or in unrelated containers).
4. Useful bounded surrounding text (verifying substantive text is returned, and null rather than "[...]").
5. Header/logo contextual evidence (checking parent_context="brand", nearby_text, dimensions).
6. Distinct interactive elements with identical CSS paths (duplicate ID disambiguation).
7. Image alt/context extraction (decorative vs non-decorative, dimensions, nearby card text).
8. Existing bounds still work.
9. Minimal HTML still works.
10. Existing Phase 1 behavior is not unnecessarily broken.
"""

import unittest
import sys
import os
import urllib.parse

# Ensure root directory is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.dom_extractor import extract_dom_snapshot, sanitize_dom_snapshot, _fallback_snapshot


class MockWebDriver:
    """Mock WebDriver to simulate browser script execution and error conditions."""

    def __init__(self, return_value=None, raise_exception=None):
        self.return_value = return_value
        self.raise_exception = raise_exception
        self.last_script = None
        self.last_args = None

    def execute_script(self, script, *args):
        self.last_script = script
        self.last_args = args
        if self.raise_exception:
            raise self.raise_exception
        return self.return_value


class TestDOMExtractorUnit(unittest.TestCase):
    """Offline unit tests using MockWebDriver for resilience and edge cases."""

    def test_1_driver_none_returns_fallback(self):
        """extract_dom_snapshot handles driver=None gracefully without raising exceptions."""
        result = extract_dom_snapshot(None)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "EXTRACTION_FAILED")
        self.assertIn("error", result)
        self.assertEqual(result["counts"]["total_headings"], 0)
        self.assertEqual(result["counts"]["total_interactive"], 0)

    def test_2_script_exception_returns_fallback(self):
        """extract_dom_snapshot catches script execution errors safely."""
        mock_driver = MockWebDriver(raise_exception=RuntimeError("Simulated browser crash"))
        result = extract_dom_snapshot(mock_driver)
        self.assertEqual(result["status"], "EXTRACTION_FAILED")
        self.assertIn("Simulated browser crash", result.get("error", ""))

    def test_3_non_dict_return_handled_gracefully(self):
        """If script returns invalid non-dict payload, fallback is returned."""
        mock_driver = MockWebDriver(return_value="not a dict")
        result = extract_dom_snapshot(mock_driver)
        self.assertEqual(result["status"], "EXTRACTION_FAILED")
        self.assertIn("did not return a valid dictionary", result.get("error", ""))

    def test_4_sanitize_dom_snapshot_enforces_schema(self):
        """sanitize_dom_snapshot guarantees all required top-level keys exist."""
        incomplete_payload = {
            "status": "SUCCESS",
            "page_metadata": {"title": "Sample"},
        }
        sanitized = sanitize_dom_snapshot(incomplete_payload)
        self.assertEqual(sanitized["status"], "SUCCESS")
        self.assertEqual(sanitized["page_metadata"]["title"], "Sample")
        self.assertEqual(sanitized["page_metadata"]["lang"], "")
        self.assertEqual(sanitized["headings"], [])
        self.assertEqual(sanitized["landmarks"], [])
        self.assertEqual(sanitized["sections"], [])
        self.assertEqual(sanitized["interactive_elements"], [])
        self.assertEqual(sanitized["forms"], [])
        self.assertEqual(sanitized["images"], [])
        self.assertIn("counts", sanitized)


class TestDOMExtractorHeadlessBrowser(unittest.TestCase):
    """
    In-depth structural tests running against local in-memory HTML pages
    using headless Chrome (zero network requests, runs 100% offline).
    """

    driver = None

    @classmethod
    def setUpClass(cls):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,800")
        cls.driver = webdriver.Chrome(options=options)

    @classmethod
    def tearDownClass(cls):
        if cls.driver:
            try:
                cls.driver.quit()
            except Exception:
                pass

    def load_html(self, html_content: str):
        """Load an in-memory HTML string via data URI."""
        encoded = urllib.parse.quote(html_content)
        self.driver.get(f"data:text/html;charset=utf-8,{encoded}")

    def test_5_page_title_and_lang_extraction(self):
        """Page title and HTML lang attributes are extracted accurately."""
        html = """
        <!DOCTYPE html>
        <html lang="en-US">
        <head><title>Accessibility Test Portal</title></head>
        <body><main><h1>Hello World</h1></main></body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        self.assertEqual(snapshot["status"], "SUCCESS")
        self.assertEqual(snapshot["page_metadata"]["title"], "Accessibility Test Portal")
        self.assertEqual(snapshot["page_metadata"]["lang"], "en-US")

    def test_6_heading_hierarchy_extraction(self):
        """H1-H6 tags and ARIA heading roles are extracted with level, text, and landmark."""
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Headings Test</title></head>
        <body>
            <header>
                <h1>Site Masthead</h1>
            </header>
            <main>
                <h2>Primary Section</h2>
                <h3>Subsection Alpha</h3>
                <div role="heading" aria-level="4" id="custom-h4">ARIA Level 4 Heading</div>
            </main>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        headings = snapshot["headings"]
        self.assertEqual(len(headings), 4)

        self.assertEqual(headings[0]["tag"], "h1")
        self.assertEqual(headings[0]["level"], 1)
        self.assertEqual(headings[0]["text"], "Site Masthead")
        self.assertEqual(headings[0]["landmark"], "banner")

        self.assertEqual(headings[1]["tag"], "h2")
        self.assertEqual(headings[1]["level"], 2)
        self.assertEqual(headings[1]["text"], "Primary Section")
        self.assertEqual(headings[1]["landmark"], "main")

        self.assertEqual(headings[3]["level"], 4)
        self.assertEqual(headings[3]["text"], "ARIA Level 4 Heading")
        self.assertEqual(headings[3]["id"], "custom-h4")

    def test_7_landmarks_semantic_and_aria_roles(self):
        """Semantic tags and explicit ARIA landmark roles are identified with labels."""
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Landmarks Test</title></head>
        <body>
            <header>Header content</header>
            <nav aria-label="Main Navigation">
                <a href="#home">Home</a>
            </nav>
            <main>
                <section aria-labelledby="sec-label">
                    <h2 id="sec-label">Services</h2>
                </section>
                <div role="region" aria-label="Featured News">News feed</div>
            </main>
            <aside>Related articles</aside>
            <footer>Copyright 2026</footer>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        landmarks = snapshot["landmarks"]
        roles = [lm["role"] for lm in landmarks]

        self.assertIn("banner", roles)
        self.assertIn("navigation", roles)
        self.assertIn("main", roles)
        self.assertIn("complementary", roles)
        self.assertIn("contentinfo", roles)
        self.assertIn("region", roles)

        nav_lm = next(l for l in landmarks if l["role"] == "navigation")
        self.assertEqual(nav_lm["label"], "Main Navigation")

        sec_lm = next(l for l in landmarks if l["label"] == "Services")
        self.assertEqual(sec_lm["tag"], "section")

    def test_8_generic_div_based_meaningful_grouping(self):
        """Generic <div>-based components (navbar, panels, card groups) are identified as sections."""
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Div Components Test</title></head>
        <body>
            <div class="navbar">
                <a href="#" class="brand">University Portal</a>
            </div>
            <div class="row card-grid">
                <div class="col"><a href="#1" class="databox">Card 1</a></div>
                <div class="col"><a href="#2" class="databox">Card 2</a></div>
            </div>
            <div class="panel panel-default">
                <div class="panel-heading">Notice Board</div>
                <div class="panel-body"><p>Important news announcement.</p></div>
            </div>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        sections = snapshot["sections"]
        block_types = [s["block_type"] for s in sections]

        self.assertIn("header", block_types)
        self.assertIn("card-group", block_types)
        self.assertIn("panel", block_types)

        panel = next(s for s in sections if s["block_type"] == "panel")
        self.assertEqual(panel["heading"], "Notice Board")

    def test_9_correct_heading_and_section_association_motivating_example(self):
        """
        Motivating Example: Verifies that 'Click to Visit' links under distinct sections
        correctly associate with their respective section headings ('MEMBER'S AREA' vs 'LETTERS & NOTICES').
        """
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Context Correlation Test</title></head>
        <body>
            <main>
                <section id="sec-members">
                    <h2>MEMBER'S AREA</h2>
                    <p>Dashboard: <a href="/members" id="link-member">Click to Visit</a></p>
                </section>
                <section id="sec-notices">
                    <h2>LETTERS & NOTICES</h2>
                    <p>Bulletins: <a href="/notices" id="link-notices">Click to Visit</a></p>
                </section>
            </main>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        interactive = snapshot["interactive_elements"]
        self.assertEqual(len(interactive), 2)

        link1 = interactive[0]
        self.assertEqual(link1["id"], "link-member")
        self.assertEqual(link1["text"], "Click to Visit")
        self.assertEqual(link1["href"], "/members")
        self.assertEqual(link1["parent_section"], "MEMBER'S AREA")
        self.assertEqual(link1["nearest_heading"], "MEMBER'S AREA")
        self.assertIn("Dashboard", link1["surrounding_text"])

        link2 = interactive[1]
        self.assertEqual(link2["id"], "link-notices")
        self.assertEqual(link2["text"], "Click to Visit")
        self.assertEqual(link2["href"], "/notices")
        self.assertEqual(link2["parent_section"], "LETTERS & NOTICES")
        self.assertEqual(link2["nearest_heading"], "LETTERS & NOTICES")
        self.assertIn("Bulletins", link2["surrounding_text"])

    def test_10_returns_null_rather_than_unrelated_heading(self):
        """
        MAKAUT Real-Page Scenario: Top controls preceding all headings must receive
        nearest_heading=null, not an unrelated subsequent footer/helpdesk heading.
        """
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Unrelated Heading Test</title></head>
        <body>
            <div class="main-container">
                <div class="page-body">
                    <div class="row">
                        <a href="#login" id="link-student">STUDENT Click to Login</a>
                    </div>
                    <div class="panel">
                        <h3>Helpdesk Issues:</h3>
                        <p>Call support at 1800-000-000</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        interactive = snapshot["interactive_elements"]
        link = next(el for el in interactive if el["id"] == "link-student")

        # Must be None, NOT "Helpdesk Issues:"
        self.assertIsNone(link["nearest_heading"])
        self.assertIsNone(link["nearest_heading_level"])

    def test_11_useful_bounded_surrounding_text_no_bracket_noise(self):
        """Surrounding text contains substantive context and returns null rather than '[...]'."""
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Surrounding Text Test</title></head>
        <body>
            <div>
                <p>Important instructions for users: <a href="#start" id="link-start">Get Started</a></p>
            </div>
            <div>
                <a href="#solo" id="link-solo"><span>Click Solo</span></a>
            </div>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        interactive = snapshot["interactive_elements"]
        link_start = next(el for el in interactive if el["id"] == "link-start")
        self.assertIn("Important instructions for users", link_start["surrounding_text"])
        self.assertNotIn("[...]", link_start["surrounding_text"])

        link_solo = next(el for el in interactive if el["id"] == "link-solo")
        # Solo link with no other text returns None, never "[...]"
        self.assertIsNone(link_solo["surrounding_text"])

    def test_12_header_logo_context_and_image_evidence(self):
        """Logo images preserve brand context, dimensions, and nearby university title."""
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Logo Context Test</title></head>
        <body>
            <header class="navbar">
                <a class="navbar-brand" href="#">
                    <img id="img-logo" src="/makaut-logo.png" alt="University Logo" width="600" height="90" />
                </a>
                <span class="sublogo">STATE UNIVERSITY PORTAL</span>
            </header>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        images = snapshot["images"]
        self.assertEqual(len(images), 1)

        logo = images[0]
        self.assertEqual(logo["id"], "img-logo")
        self.assertEqual(logo["alt"], "University Logo")
        self.assertEqual(logo["parent_context"], "brand")
        self.assertEqual(logo["width"], "600")
        self.assertEqual(logo["height"], "90")
        self.assertIn("STATE UNIVERSITY PORTAL", logo["nearby_text"])
        self.assertFalse(logo["is_decorative"])

    def test_13_distinct_elements_with_identical_css_paths(self):
        """Multiple elements with duplicate IDs or identical CSS selectors remain distinct and disambiguated."""
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Duplicate ID Test</title></head>
        <body>
            <div class="row">
                <div id="resultD"><a href="/result-details">RESULT Click here</a></div>
                <div id="resultD"><a href="/helpdesk">HelpDesk Click here</a></div>
            </div>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        interactive = snapshot["interactive_elements"]
        self.assertEqual(len(interactive), 2)

        link_res = interactive[0]
        link_help = interactive[1]

        self.assertIn("RESULT", link_res["text"])
        self.assertEqual(link_res["href"], "/result-details")

        self.assertIn("HelpDesk", link_help["text"])
        self.assertEqual(link_help["href"], "/helpdesk")

        # Distinct CSS paths via nth-of-type
        self.assertNotEqual(link_res["css_path"], link_help["css_path"])

    def test_14_accessibility_attributes_captured(self):
        """ARIA attributes, labels, expanded states, and decorative images are properly extracted."""
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Accessibility Attributes Test</title></head>
        <body>
            <main>
                <label id="lbl-search" for="inp-search">Search Documents</label>
                <input type="text" id="inp-search" aria-describedby="desc-help" aria-expanded="true" />
                <span id="desc-help">Type at least 3 characters.</span>

                <button id="btn-toggle" aria-label="Toggle Navigation Menu" aria-expanded="false">
                    <span>Menu</span>
                </button>

                <img id="img-decor" src="/divider.png" alt="" role="presentation" />
            </main>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        interactive = snapshot["interactive_elements"]
        inp = next(el for el in interactive if el["id"] == "inp-search")
        self.assertEqual(inp["type"], "text")
        self.assertEqual(inp["aria_describedby"], "desc-help")
        self.assertEqual(inp["aria_expanded"], "true")

        btn = next(el for el in interactive if el["id"] == "btn-toggle")
        self.assertEqual(btn["aria_label"], "Toggle Navigation Menu")
        self.assertEqual(btn["aria_expanded"], "false")

        images = snapshot["images"]
        img_decor = next(im for im in images if im["id"] == "img-decor")
        self.assertEqual(img_decor["alt"], "")
        self.assertTrue(img_decor["is_decorative"])

    def test_15_noise_exclusion_scripts_styles_omitted(self):
        """Scripts, styles, and noscript tags do not bleed into extracted text."""
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Clean Text Test</title>
            <style>body { color: red; } .hidden { display: none; }</style>
        </head>
        <body>
            <main>
                <h2>Legitimate Heading</h2>
                <p>
                    Clean visible content.
                    <script>var x = "MALICIOUS_SCRIPT_NOISE";</script>
                    <noscript>Noscript fallback text</noscript>
                </p>
                <button id="btn-clean">
                    Accept Terms
                    <script>console.log("noisy");</script>
                </button>
            </main>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        h = snapshot["headings"][0]
        self.assertEqual(h["text"], "Legitimate Heading")
        self.assertNotIn("color: red", h["text"])

        btn = snapshot["interactive_elements"][0]
        self.assertEqual(btn["text"], "Accept Terms")
        self.assertNotIn("noisy", btn["text"])

    def test_16_bounded_output_limits(self):
        """String truncation and element count bounds are respected."""
        headings_html = "".join([f"<h3>Heading Number {i} with very long descriptive heading content exceeding standard size</h3>" for i in range(15)])
        long_paragraph = "<p>" + ("Lorem ipsum dolor sit amet " * 20) + "</p>"
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Bounded Limits Test</title></head>
        <body><main>{headings_html}{long_paragraph}</main></body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver, max_headings=5, max_text_len=30)

        self.assertEqual(len(snapshot["headings"]), 5)
        self.assertTrue(snapshot["headings"][0]["text"].endswith("..."))
        self.assertLessEqual(len(snapshot["headings"][0]["text"]), 35)

    def test_17_graceful_minimal_html(self):
        """Handles completely empty or minimal HTML without error."""
        html = "<!DOCTYPE html><html><head></head><body></body></html>"
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        self.assertEqual(snapshot["status"], "SUCCESS")
        self.assertEqual(snapshot["headings"], [])
        self.assertEqual(snapshot["landmarks"], [])
        self.assertEqual(snapshot["interactive_elements"], [])
        self.assertEqual(snapshot["counts"]["total_headings"], 0)
        self.assertEqual(snapshot["counts"]["total_interactive"], 0)

    def test_18_generic_non_semantic_grouping_test_a(self):
        """
        TEST A — Generic non-semantic grouping:
        Arbitrary class names ('random-wrapper', 'random-item') without standard names
        capture useful grouping, headings, and parent block IDs.
        """
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Generic Non-Semantic Test</title></head>
        <body>
            <div class="random-wrapper">
                <h2>Products</h2>
                <div class="random-item">
                    <a href="/product/1" id="prod-1">View product</a>
                </div>
                <div class="random-item">
                    <a href="/product/2" id="prod-2">View product</a>
                </div>
            </div>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        sections = snapshot["sections"]
        self.assertGreaterEqual(len(sections), 1)

        # Container is captured as a heading-anchored or repeated section
        prod_sec = next(s for s in sections if s["heading"] == "Products")
        self.assertIsNotNone(prod_sec["block_id"])
        self.assertTrue(prod_sec["block_id"].startswith("context-"))
        self.assertEqual(prod_sec["heading"], "Products")
        self.assertEqual(prod_sec["heading_level"], 2)

        # Interactive elements are associated with the heading and the section block ID
        interactive = snapshot["interactive_elements"]
        self.assertEqual(len(interactive), 2)
        p1 = next(el for el in interactive if el["id"] == "prod-1")
        self.assertEqual(p1["nearest_heading"], "Products")
        self.assertEqual(p1["nearest_heading_level"], 2)
        self.assertEqual(p1["parent_section_id"], prod_sec["block_id"])

    def test_19_generic_header_and_logo_test_b(self):
        """
        TEST B — Generic header + logo:
        Minimal semantic header with logo and company name captures image alt,
        parent_context='header', and nearby text without generating violations.
        """
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Header Logo Test</title></head>
        <body>
            <header>
                <img id="comp-logo" src="logo.png" alt="Company logo">
                <span>Company Name</span>
            </header>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        images = snapshot["images"]
        self.assertEqual(len(images), 1)
        img = images[0]
        self.assertEqual(img["id"], "comp-logo")
        self.assertEqual(img["src"], "logo.png")
        self.assertEqual(img["alt"], "Company logo")
        self.assertIn(img["parent_context"], ["header", "brand"])
        self.assertEqual(img["parent_landmark"], "banner")
        self.assertIn("Company Name", img["nearby_text"])
        self.assertFalse(img["is_decorative"])

        # Extractor is purely evidence-only and contains NO violation flags
        self.assertNotIn("violations", snapshot)
        self.assertNotIn("wcag_violations", snapshot)

    def test_20_poor_non_semantic_html_test_c(self):
        """
        TEST C — Poor/non-semantic HTML:
        Deeply nested <div> tags without headings or semantic roles do NOT force a heading,
        while capturing contextual surrounding text and element properties.
        """
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Non-Semantic HTML Test</title></head>
        <body>
            <div>
                <div>
                    <div>Account Services</div>
                    <div>
                        <a href="/login" id="link-login">Click here</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        # No real headings exist; extractor must NOT force a synthetic heading
        self.assertEqual(len(snapshot["headings"]), 0)

        interactive = snapshot["interactive_elements"]
        self.assertEqual(len(interactive), 1)
        link = interactive[0]
        self.assertEqual(link["id"], "link-login")
        self.assertEqual(link["text"], "Click here")
        self.assertEqual(link["href"], "/login")

        # Must not force a heading
        self.assertIsNone(link["nearest_heading"])
        self.assertIsNone(link["nearest_heading_level"])

        # Surrounding context captures "Account Services"
        self.assertIsNotNone(link["surrounding_text"])
        self.assertIn("Account Services", link["surrounding_text"])

    def test_21_identical_css_paths_disambiguation_test_d(self):
        """
        TEST D — Multiple elements with identical CSS paths:
        Multiple elements sharing identical tag/class hierarchies are preserved,
        retaining distinct texts, hrefs, and disambiguated paths.
        """
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Identical Paths Test</title></head>
        <body>
            <div class="card-list">
                <div class="card-item"><a href="/item/1" class="btn">View Alpha</a></div>
                <div class="card-item"><a href="/item/2" class="btn">View Beta</a></div>
            </div>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        interactive = snapshot["interactive_elements"]
        self.assertEqual(len(interactive), 2)

        el1, el2 = interactive[0], interactive[1]
        self.assertEqual(el1["text"], "View Alpha")
        self.assertEqual(el1["href"], "/item/1")
        self.assertEqual(el2["text"], "View Beta")
        self.assertEqual(el2["href"], "/item/2")

        # Disambiguated structural selectors
        self.assertNotEqual(el1["css_path"], el2["css_path"])

    def test_22_real_heading_association_test_e(self):
        """
        TEST E — Real heading association:
        When strong DOM containment exists (e.g. within same <section>),
        the control correctly associates with the heading.
        """
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Real Heading Association Test</title></head>
        <body>
            <section id="sec-account">
                <h2>Account</h2>
                <a href="/login" id="link-acc-login">Login</a>
            </section>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        interactive = snapshot["interactive_elements"]
        link = next(el for el in interactive if el["id"] == "link-acc-login")
        self.assertEqual(link["nearest_heading"], "Account")
        self.assertEqual(link["nearest_heading_level"], 2)
        self.assertEqual(link["parent_section"], "Account")
        self.assertIsNotNone(link["parent_section_id"])

    def test_23_unrelated_heading_not_associated_test_f(self):
        """
        TEST F — Unrelated heading must NOT be associated:
        A heading in a distinct or previous section must not bleed into an
        unrelated container.
        """
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Unrelated Heading Test</title></head>
        <body>
            <h2>Payment Information</h2>
            <div class="unrelated-area">
                <a href="/login" id="link-unrelated-login">Login</a>
            </div>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        interactive = snapshot["interactive_elements"]
        link = next(el for el in interactive if el["id"] == "link-unrelated-login")

        # Must NOT inherit "Payment Information"
        self.assertIsNone(link["nearest_heading"])
        self.assertIsNone(link["nearest_heading_level"])

    def test_24_no_synthetic_heading_in_sections(self):
        """
        Ensures that section blocks never invent synthetic labels (e.g. 'Portal Cards Group').
        Actual DOM text is used or heading is null.
        """
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>No Synthetic Heading Test</title></head>
        <body>
            <div class="row card-grid">
                <div class="col"><a href="#1">Card 1</a></div>
                <div class="col"><a href="#2">Card 2</a></div>
                <div class="col"><a href="#3">Card 3</a></div>
            </div>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)

        sections = snapshot["sections"]
        for sec in sections:
            # Heading must be None or an exact string from the HTML
            if sec["heading"] is not None:
                self.assertIn(sec["heading"], html)
            # Must have machine-level block_id
            self.assertTrue(sec["block_id"].startswith("context-"))

    def test_25_redundant_nested_layout_wrappers_suppressed(self):
        """
        Ensures that genuinely redundant nested layout wrappers (e.g. inner divs duplicating parent text
        with zero non-interactive contextual text or empty content) are suppressed, and empty headings do not
        create phantom heading groups.
        """
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Redundancy Test</title></head>
        <body>
            <div class="navbar">
                <div class="navbar-inner">
                    <div class="navbar-container">
                        <div class="navbar-header">
                            <a href="/">Brand Logo</a>
                        </div>
                    </div>
                </div>
            </div>
            <div class="panel panel-default">
                <div class="panel-heading"><b>Panel Title</b></div>
                <div class="panel-body">
                </div>
            </div>
            <div class="modal">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h4 id="empty-modal-title"></h4>
                            <button class="close">X</button>
                        </div>
                        <div class="modal-body"><p>Dialog body text</p></div>
                        <div class="modal-footer"><button>OK</button></div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)
        sections = snapshot["sections"]

        # Exactly 3 meaningful components should be detected: navbar, panel, and modal
        self.assertEqual(len(sections), 3)
        self.assertEqual(sections[0]["block_type"], "header")
        self.assertEqual(sections[1]["block_type"], "panel")
        self.assertEqual(sections[1]["heading"], "Panel Title")
        # Empty h4 must not create a phantom heading group with null heading
        for sec in sections:
            if sec["block_type"] == "heading-group":
                self.assertIsNotNone(sec["heading"])
                self.assertNotEqual(sec["heading"].strip(), "")

    def test_26_same_interactive_count_with_meaningful_context_retained(self):
        """
        Regression Test: Distinguish Duplicate vs Additional Context.
        A. Duplicate contextual evidence -> SUPPRESS:
            Nested wrapper contributing identical non-interactive text and interactive elements
            as its parent must be suppressed.
        B. Additional contextual evidence -> RETAIN:
            Nested container contributing genuinely additional contextual text not provided
            by parent must be retained.
        C. Pure control wrapper -> SUPPRESS:
            Nested wrapper with zero non-interactive text must be suppressed.
        """
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Duplicate vs Additional Context Test</title></head>
        <body>
            <!-- A. Duplicate contextual evidence: inner wrapper has identical text & button as parent -> SUPPRESSED -->
            <div class="outer-duplicate card">
                <div class="wrapper-duplicate card">
                    <span>Company Name</span>
                    <button>Continue</button>
                </div>
            </div>

            <!-- B. Additional contextual evidence: inner container contributes additional text -> RETAINED -->
            <div class="outer-additional card">
                <button>Continue</button>
                <div class="meaningful-context card">
                    <span>Important information about this action</span>
                    <button>Continue</button>
                </div>
            </div>

            <!-- C. Pure control wrapper with NO contextual text -> SUPPRESSED -->
            <div class="outer-control card">
                <div class="redundant-btn-wrapper card">
                    <button>Submit</button>
                </div>
            </div>
        </body>
        </html>
        """
        self.load_html(html)
        snapshot = extract_dom_snapshot(self.driver)
        sections = snapshot["sections"]

        # A. Verify duplicate wrapper is SUPPRESSED (does not survive merely because it repeats parent text)
        duplicate_blocks = [s for s in sections if "wrapper-duplicate" in s.get("class", "")]
        self.assertEqual(len(duplicate_blocks), 0, "The wrapper-duplicate block must be suppressed as duplicate evidence")

        # B. Verify meaningful-context is RETAINED (contributes genuinely additional contextual evidence)
        meaningful_blocks = [s for s in sections if "meaningful-context" in s.get("class", "")]
        self.assertEqual(len(meaningful_blocks), 1, "The meaningful-context block must be retained")
        self.assertIn("Important information about this action", meaningful_blocks[0]["contextual_text"])

        # C. Verify redundant-btn-wrapper (zero contextual text) is SUPPRESSED
        redundant_blocks = [s for s in sections if "redundant-btn-wrapper" in s.get("class", "")]
        self.assertEqual(len(redundant_blocks), 0, "The redundant-btn-wrapper block must be suppressed")


if __name__ == "__main__":
    unittest.main()

