"""
AI-Powered Screen Reader Accessibility Testing System
Unified Entry Point
"""

import sys
import os
import argparse
import unittest


def run_live_listener(enable_ai=True):
    """Interactive Mode: Listens to NVDA announcements live as the user navigates."""
    import time
    import json
    from tools.nvda_tool import NVDATextExtractor
    from tools.nvda_filter import NVDAFilter
    from tools.nvda_parser import NVDAParser
    from tools.nvda_classifier import NVDAClassifier
    from tools.ai_agent import AIAccessibilityAgent

    READ_DELAY = 2
    POLL_DELAY = 0.2

    print("\n" + "=" * 60)
    print("MODE: LIVE INTERACTIVE NVDA LISTENER")
    print("=" * 60)
    print("Listening to NVDA Speech Viewer... (Press Ctrl+C to stop)\n")

    try:
        extractor = NVDATextExtractor()
    except Exception as e:
        print(f"Error connecting to NVDA Speech Viewer: {e}")
        print("Please ensure NVDA is running and the Speech Viewer window is open.")
        return

    filter_tool = NVDAFilter()
    parser = NVDAParser()
    classifier = NVDAClassifier()

    with open("nvda_log.txt", "w", encoding="utf-8") as log:
        try:
            while True:
                text = extractor.get_new_text()

                if text:
                    cleaned = filter_tool.clean(text)
                    events = parser.parse(cleaned)

                    classifier.classify(events)
                    classifier.save()

                    for event in events:
                        print("-" * 50)
                        print(event)

                        log.write(json.dumps(event.to_dict(), ensure_ascii=False))
                        log.write("\n")

                    log.flush()
                    time.sleep(READ_DELAY)
                else:
                    time.sleep(POLL_DELAY)

        except KeyboardInterrupt:
            print("\n" + "=" * 70)
            print("STOPPED LIVE LISTENING. RUNNING WCAG ACCESSIBILITY ANALYSIS...")
            print("=" * 70)

            # Package live captured elements for WCAG analysis
            live_data = {
                "url": "Live Manual Interaction Session",
                "forward": [
                    {
                        "selenium": {
                            "tag": ev.get("role", "a"),
                            "text": ev.get("name", ""),
                            "aria-label": ev.get("name", "") if ev.get("name") else None,
                        },
                        "nvda": ev,
                    }
                    for ev in classifier.website_elements
                ],
                "backward": [],
            }

            if enable_ai:
                print("\n" + "=" * 70)
                print("MODE: AI-POWERED ACCESSIBILITY VIOLATION DETECTION (GEMINI)")
                print("=" * 70)
                ai_analyzer = AIAccessibilityAgent()
                ai_report = ai_analyzer.analyze_synchronized_evidence(live_data)
                ai_analyzer.save_ai_report(ai_report, "ai_accessibility_report.json")
                ai_dict = ai_report.to_dict()
                summary = ai_dict.get("summary", {})

                print(f"\nAI Accessibility Assessment Score: {summary.get('compliance_score', 100.0)}%")
                print(f"Total Unique Elements Captured   : {summary.get('total_elements_analyzed', 0)}")
                print(f"Total AI Violations Detected     : {summary.get('total_violations', 0)}")
                sev = summary.get("severity_summary", {})
                print(f"Severity Breakdown               : Critical={sev.get('CRITICAL', 0)}, Major={sev.get('MAJOR', 0)}, Minor={sev.get('MINOR', 0)}, Info={sev.get('INFO', 0)}")
                print(f"AI Analysis Status               : {ai_report.analysis_status} (Model: {ai_report.ai_metadata.get('model')})")

                if ai_report.violations:
                    print("\nTOP AI ACCESSIBILITY VIOLATIONS DETECTED:")
                    for idx, v in enumerate(ai_report.violations[:5], 1):
                        print(f"  {idx}. [{v.severity}] {v.rule_id} - {v.title} (Confidence: {v.confidence})")
                        print(f"     Impact      : {v.user_impact[:100]}...")
                        print(f"     Remediation : {v.developer_guidance[:100]}...")
            else:
                print("\n" + "=" * 70)
                print("AI ACCESSIBILITY AUDIT DISABLED")
                print("=" * 70)
                print("AI violation analysis was not requested (enable_ai=False).")
                unavailable_report = {
                    "analysis_type": "AI_ACCESSIBILITY_ANALYSIS",
                    "analysis_status": "AI_ANALYSIS_UNAVAILABLE",
                    "url": "Live Manual Interaction Session",
                    "summary": {
                        "total_elements_analyzed": len(classifier.website_elements),
                        "total_violations": 0,
                        "compliance_score": 0.0,
                        "severity_summary": {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "INFO": 0},
                    },
                    "violations": [],
                    "ai_metadata": {"reason": "AI analysis was explicitly disabled."},
                }
                with open("ai_accessibility_report.json", "w", encoding="utf-8") as f:
                    json.dump(unavailable_report, f, indent=4, ensure_ascii=False)

            print("\n" + "=" * 70)
            print("Outputs saved:")
            print("  - nvda_log.txt (Stream of all captured live speech events)")
            print("  - website_elements.json (Unique website elements captured)")
            print("  - ai_accessibility_report.json (AI Accessibility Violation Report)")
            print("=" * 70)


def run_automated_audit(url, tab_limit=100, enable_ai=True, output_dir=None):
    """Automated Mode: Traverses a webpage via Selenium, syncing DOM with NVDA and running AI accessibility analysis."""
    import os
    import sys
    from synchronisation.sync import (
        capture_synchronized_element,
        get_element_details,
    )
    from tools.nvda_tool import NVDATextExtractor
    from tools.nvda_filter import NVDAFilter
    from tools.nvda_parser import NVDAParser
    from tools.nvda_classifier import NVDAClassifier
    from tools.ai_agent import AIAccessibilityAgent, AIAccessibilityAnalyzer
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import StaleElementReferenceException
    import time
    import json

    print("\n" + "=" * 70)
    print("MODE: AUTOMATED BROWSER + NVDA SYNCHRONIZED AUDIT")
    print("=" * 70)
    print(f"Target URL : {url}")
    print(f"Tab Limit  : {tab_limit}")
    print(f"AI Audit   : {'Enabled (Primary Authority)' if enable_ai else 'Disabled'}")
    if output_dir:
        print(f"Output Dir : {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
    print("=" * 70)

    try:
        extractor = NVDATextExtractor()
    except Exception as e:
        print(f"Error connecting to NVDA Speech Viewer: {e}")
        print("Please ensure NVDA is running and the Speech Viewer window is open.")
        raise RuntimeError(f"NVDA Speech Viewer is not available: {e}") from e

    filter_tool = NVDAFilter()
    parser = NVDAParser()
    classifier = NVDAClassifier()

    print("\nLaunching Chrome...")
    driver = webdriver.Chrome()
    forward_results = []
    backward_results = []
    all_raw_events = []

    try:
        driver.maximize_window()
        driver.get(url)
        time.sleep(2)

        try:
            driver.find_element(By.TAG_NAME, "body").click()
        except Exception:
            pass

        actions = ActionChains(driver)

        # Forward Traversal
        visited_forward = set()

        print("\nStarting Forward Tab Traversal...")
        for step in range(1, tab_limit + 1):
            actions.send_keys(Keys.TAB).perform()
            time.sleep(0.2)

            try:
                active = driver.switch_to.active_element
                identifier = (
                    active.tag_name,
                    active.get_attribute("id"),
                    active.get_attribute("name"),
                    active.get_attribute("href"),
                    active.get_attribute("class"),
                    (active.text or "").strip(),
                )
            except StaleElementReferenceException:
                continue

            if identifier in visited_forward:
                print(f"Reached loop/end of focusable elements at step {step}.")
                break

            visited_forward.add(identifier)
            if active.tag_name.lower() == "body":
                continue

            selenium_details = get_element_details(active)
            result = capture_synchronized_element(extractor, filter_tool, parser, selenium_details)
            result["step"] = step
            forward_results.append(result)

            if result["nvda"]:
                all_raw_events.append(result["nvda"])

            nvda_info = result["nvda"]["role"] if result["nvda"] else "None"
            print(f"Step {step:02d} | DOM: <{selenium_details['tag']}> '{selenium_details['text'][:30]}' | NVDA: {nvda_info} -> {result['comparison']['status']}")

        # Backward Traversal
        visited_backward = set()

        print("\nStarting Backward Shift+Tab Traversal...")
        for step in range(1, tab_limit + 1):
            actions.key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT).perform()
            time.sleep(0.2)

            try:
                active = driver.switch_to.active_element
                identifier = (
                    active.tag_name,
                    active.get_attribute("id"),
                    active.get_attribute("name"),
                    active.get_attribute("href"),
                    active.get_attribute("class"),
                    (active.text or "").strip(),
                )
            except StaleElementReferenceException:
                continue

            if identifier in visited_backward:
                print(f"Reached loop/end of backward elements at step {step}.")
                break

            visited_backward.add(identifier)
            if active.tag_name.lower() == "body":
                continue

            selenium_details = get_element_details(active)
            result = capture_synchronized_element(extractor, filter_tool, parser, selenium_details)
            result["step"] = step
            backward_results.append(result)

            if result["nvda"]:
                all_raw_events.append(result["nvda"])

            nvda_info = result["nvda"]["role"] if result["nvda"] else "None"
            print(f"Step {step:02d} | DOM: <{selenium_details['tag']}> '{selenium_details['text'][:30]}' | NVDA: {nvda_info} -> {result['comparison']['status']}")

    finally:
        print("\nTraversal finished. Closing browser window...")
        try:
            driver.quit()
        except Exception:
            pass

    # Destination paths for artifacts
    log_path = os.path.join(output_dir, "nvda_log.txt") if output_dir else "nvda_log.txt"
    sync_path = os.path.join(output_dir, "synchronized_output.json") if output_dir else "synchronized_output.json"
    ai_rep_path = os.path.join(output_dir, "ai_accessibility_report.json") if output_dir else "ai_accessibility_report.json"

    # Save nvda_log.txt
    with open(log_path, "w", encoding="utf-8") as log:
        for ev in all_raw_events:
            log.write(json.dumps(ev, ensure_ascii=False) + "\n")

    # Save synchronized_output.json
    final_output = {
        "url": url,
        "forward": forward_results,
        "backward": backward_results,
    }

    with open(sync_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)

    # -------------------------------------------------------------------------
    # ACCESSIBILITY ANALYSIS LAYER (PURE AI - GEMINI)
    # -------------------------------------------------------------------------
    if enable_ai:
        print("\n" + "=" * 70)
        print("PRIMARY ACCESSIBILITY ANALYSIS: AI ACCESSIBILITY ANALYZER (GEMINI)")
        print("=" * 70)
        ai_analyzer = AIAccessibilityAnalyzer()
        ai_report_model = ai_analyzer.analyze_synchronized_evidence(final_output)
        ai_analyzer.save_ai_report(ai_report_model, ai_rep_path)
        ai_report_dict = ai_report_model.to_dict()

        summary = ai_report_dict.get("summary", {})
        sev = summary.get("severity_summary", {})

        print(f"\nAI Accessibility Assessment Score: {summary.get('compliance_score', 100.0)}%")
        print(f"Total Elements Audited (by AI)   : {summary.get('total_elements_analyzed', len(forward_results))}")
        print(f"Total AI Violations Discovered   : {summary.get('total_violations', 0)}")
        print(f"AI Severity Breakdown            : Critical={sev.get('CRITICAL', 0)}, Major={sev.get('MAJOR', 0)}, Minor={sev.get('MINOR', 0)}, Info={sev.get('INFO', 0)}")
        print(f"AI Analysis Status               : {ai_report_model.analysis_status} (Model: {ai_report_model.ai_metadata.get('model')})")

        if ai_report_model.violations:
            print("\nTOP AI-DETECTED ACCESSIBILITY VIOLATIONS:")
            for idx, v in enumerate(ai_report_model.violations[:5], 1):
                print(f"  {idx}. [{v.severity}] {v.rule_id} - {v.title} (Confidence: {v.confidence})")
                print(f"     User Impact : {v.user_impact[:90]}...")
                print(f"     Remediation : {v.recommendation[:90]}...")

        print("\n" + "=" * 70)
        print("Outputs saved:")
        print(f"  - {log_path} (Stream of all captured NVDA speech events)")
        print(f"  - {sync_path} (DOM + Screen Reader Synchronized Data)")
        print(f"  - {ai_rep_path} (AI Accessibility Analysis Report)")
        is_success = ai_report_model.analysis_status in ("COMPLETED", "NO_VIOLATIONS")
        return {
            "status": "completed" if is_success else "failed",
            "url": url,
            "analysis_type": "AI_ACCESSIBILITY_ANALYSIS",
            "total_elements_audited": summary.get("total_elements_analyzed", len(forward_results)),
            "total_violations": summary.get("total_violations", 0),
            "compliance_score": summary.get("compliance_score", 100.0),
            "severity_summary": sev,
            "analysis": ai_report_dict,
            "output_dir": output_dir,
        }

    else:
        # Explicit non-AI mode (enable_ai=False)
        print("\n" + "=" * 70)
        print("AI ACCESSIBILITY AUDIT DISABLED")
        print("=" * 70)
        print("AI violation analysis was not requested (enable_ai=False).")
        unavailable_report = {
            "analysis_type": "AI_ACCESSIBILITY_ANALYSIS",
            "analysis_status": "AI_ANALYSIS_UNAVAILABLE",
            "url": url,
            "summary": {
                "total_elements_analyzed": len(forward_results),
                "total_violations": 0,
                "compliance_score": 0.0,
                "severity_summary": {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "INFO": 0},
            },
            "violations": [],
            "ai_metadata": {"reason": "AI analysis was explicitly disabled."},
        }
        with open(ai_rep_path, "w", encoding="utf-8") as f:
            json.dump(unavailable_report, f, indent=4, ensure_ascii=False)

        print("\n" + "=" * 70)
        print("Outputs saved:")
        print(f"  - {log_path} (Stream of all captured NVDA speech events)")
        print(f"  - {sync_path} (DOM + Screen Reader Synchronized Data)")
        print(f"  - {ai_rep_path} (AI Accessibility Analysis Report)")
        print("=" * 70)

        return {
            "status": "completed",
            "url": url,
            "analysis_type": "AI_ACCESSIBILITY_ANALYSIS",
            "total_elements_audited": len(forward_results),
            "total_violations": 0,
            "compliance_score": 0.0,
            "severity_summary": {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "INFO": 0},
            "analysis": unavailable_report,
            "output_dir": output_dir,
        }


def run_unit_tests():
    """Run automated parser, AI agent, backend, and database tests."""
    from tests.test_parser import TestNVDAParserGeneric
    from tests.test_ai_agent import TestAIAccessibilityAgent
    from tests.test_backend import TestBackendAPI
    from tests.test_database import TestPostgreSQLDatabase

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestNVDAParserGeneric))
    suite.addTests(loader.loadTestsFromTestCase(TestAIAccessibilityAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestBackendAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestPostgreSQLDatabase))

    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


def main():
    parser = argparse.ArgumentParser(
        description="AI-Powered Screen Reader (NVDA) Accessibility Testing & Extraction System"
    )
    parser.add_argument(
        "url",
        nargs="?",
        default="https://makaut1.ucanapply.com/smartexam/public/student/dashboard",
        help="Target website URL for automated accessibility audit",
    )
    parser.add_argument(
        "--live",
        "-l",
        action="store_true",
        help="Run live interactive NVDA listener (manual navigation mode)",
    )
    parser.add_argument(
        "--test",
        "-t",
        action="store_true",
        help="Run automated generic unit test suite",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum tab steps during automated traversal (default: 100)",
    )

    args = parser.parse_args()

    if args.test:
        run_unit_tests()
    elif args.live:
        run_live_listener(enable_ai=True)
    else:
        try:
            run_automated_audit(args.url, tab_limit=args.limit, enable_ai=True)
        except RuntimeError:
            sys.exit(1)


if __name__ == "__main__":
    main()
