"""
AI-Powered Screen Reader Accessibility Testing System
Unified Entry Point
"""

import sys
import os
import argparse
import unittest


def run_live_listener(url=None, enable_ai=True, screenshot_path=None, output_dir=None):
    """
    Interactive Mode: Listens to NVDA announcements live as the user navigates.
    Supports optional target URL (auto-opens browser), visual evidence capture
    (screenshot & DOM snapshot), unified evidence package assembly, and multimodal AI analysis.
    """
    import time
    import json
    from tools.nvda_tool import NVDATextExtractor
    from tools.nvda_filter import NVDAFilter
    from tools.nvda_parser import NVDAParser
    from tools.nvda_classifier import NVDAClassifier
    from tools.ai_agent import AIAccessibilityAnalyzer
    from tools.screenshot_capture import capture_webpage_screenshot, get_image_dimensions
    from tools.dom_extractor import extract_dom_snapshot
    from tools.evidence_correlator import assemble_unified_evidence_package

    READ_DELAY = 1
    POLL_DELAY = 0.2

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    log_path = os.path.join(output_dir, "nvda_log.txt") if output_dir else "nvda_log.txt"
    elements_path = os.path.join(output_dir, "website_elements.json") if output_dir else "website_elements.json"
    sync_path = os.path.join(output_dir, "synchronized_output.json") if output_dir else "synchronized_output.json"
    ai_rep_path = os.path.join(output_dir, "ai_accessibility_report.json") if output_dir else "ai_accessibility_report.json"
    screenshot_meta_path = os.path.join(output_dir, "screenshot_metadata.json") if output_dir else "screenshot_metadata.json"
    dom_snapshot_path = os.path.join(output_dir, "dom_snapshot.json") if output_dir else "dom_snapshot.json"
    unified_pkg_path = os.path.join(output_dir, "unified_evidence_package.json") if output_dir else "unified_evidence_package.json"

    resolved_screenshot_path = screenshot_path or (os.path.join(output_dir, "webpage_screenshot.png") if output_dir else "webpage_screenshot.png")

    print("\n" + "=" * 70)
    print("MODE: LIVE INTERACTIVE NVDA LISTENER")
    print("=" * 70)
    if url:
        print(f"Target URL     : {url}")
    print(f"AI Audit       : {'Enabled (Multimodal Gemini)' if enable_ai else 'Disabled'}")
    if output_dir:
        print(f"Output Dir     : {output_dir}")
    print("=" * 70)

    try:
        extractor = NVDATextExtractor()
    except Exception as e:
        print(f"Error connecting to NVDA Speech Viewer: {e}")
        print("Please ensure NVDA is running and the Speech Viewer window is open.")
        return

    filter_tool = NVDAFilter()
    parser = NVDAParser()
    classifier = NVDAClassifier()
    driver = None
    dom_snapshot = {}
    screenshot_metadata = {"status": "FAILED", "error": "Screenshot capture not attempted"}

    try:
        if url:
            from selenium import webdriver
            from tools.pre_audit_stabilizer import PreAuditStabilizer, get_safe_chrome_options
            print("\nLaunching Chrome browser for manual navigation...")
            chrome_options = get_safe_chrome_options()
            driver = webdriver.Chrome(options=chrome_options)
            driver.maximize_window()
            extractor.mark_baseline()
            print(f"[PAGE] Navigating to target URL: {url}")
            driver.get(url)

            # PRE-AUDIT STABILIZATION (Phase 3C)
            print("\n[STABILIZER] Initializing pre-audit page stabilization...")
            stabilizer = PreAuditStabilizer()
            stabilization_meta = stabilizer.stabilize(driver)
            print(
                f"[STABILIZER] Page stabilization complete: status={stabilization_meta.get('status')}, "
                f"dismissed={stabilization_meta.get('dismissed_count')}, "
                f"remaining={stabilization_meta.get('remaining_dialog_count')}, "
                f"time={stabilization_meta.get('stabilization_duration_ms')}ms"
            )

            # Clear stale NVDA speech produced during page load & popup dismissal
            print("[STABILIZER] Resetting NVDA capture baseline...")
            extractor.reset_capture_baseline()

            print("[NVDA] Draining pre-interaction page initialization speech...")
            initial_speech, is_settled = extractor.drain_initial_speech(from_baseline=True)
            print(f"[NVDA] Baseline established ({len(initial_speech)} chars drained, settled={is_settled}).")
            print("Browser is ready! You can manually navigate (Tab, Shift+Tab, Arrows, Mouse).")
            print("NVDA speech is being captured live. Press Ctrl+C when finished.\n")
        else:
            extractor.mark_baseline()
            print("Listening to NVDA Speech Viewer... (Press Ctrl+C to stop)\n")

        with open(log_path, "w", encoding="utf-8") as log:
            while True:
                text = extractor.get_new_text()

                if text:
                    cleaned = filter_tool.clean(text)
                    events = parser.parse(cleaned)

                    classifier.classify(events)
                    classifier.save(filename=elements_path)

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
        print("STOPPED LIVE LISTENING. COLLECTING VISUAL EVIDENCE & RUNNING AI AUDIT...")
        print("=" * 70)

        # Step 1: Capture or extract visual evidence & DOM snapshot
        if driver is not None:
            print("\nCapturing visual evidence from active browser session...")
            try:
                dom_snapshot = extract_dom_snapshot(driver)
            except Exception as dom_err:
                dom_snapshot = {"error": str(dom_err), "headings": [], "landmarks": [], "sections": [], "interactive_elements": []}

            try:
                screenshot_metadata = capture_webpage_screenshot(
                    driver,
                    output_path=resolved_screenshot_path,
                    output_dir=output_dir,
                )
                if screenshot_metadata.get("status") == "SUCCESS":
                    print(f"Screenshot captured: {screenshot_metadata.get('path')} ({screenshot_metadata.get('width')}x{screenshot_metadata.get('height')}, mode: {screenshot_metadata.get('capture_mode')})")
                else:
                    print(f"Screenshot capture notice: {screenshot_metadata.get('error')}")
            except Exception as ss_err:
                screenshot_metadata = {"status": "FAILED", "error": str(ss_err)}

            print("Closing browser window...")
            try:
                driver.quit()
            except Exception:
                pass
        else:
            # Standalone manual mode (no Selenium driver)
            if resolved_screenshot_path and os.path.exists(resolved_screenshot_path):
                try:
                    with open(resolved_screenshot_path, "rb") as ss_f:
                        ss_bytes = ss_f.read()
                    w, h = get_image_dimensions(ss_bytes)
                    screenshot_metadata = {
                        "status": "SUCCESS",
                        "path": resolved_screenshot_path,
                        "filename": os.path.basename(resolved_screenshot_path),
                        "width": w,
                        "height": h,
                        "capture_mode": "MANUAL_IMAGE_EVIDENCE",
                        "has_fixed_elements": False,
                    }
                    print(f"Loaded existing visual evidence: {resolved_screenshot_path} ({w}x{h})")
                except Exception as img_err:
                    screenshot_metadata = {"status": "FAILED", "error": str(img_err)}
            else:
                screenshot_metadata = {"status": "FAILED", "error": "No screenshot provided or captured for manual session."}

            if os.path.exists(dom_snapshot_path):
                try:
                    with open(dom_snapshot_path, "r", encoding="utf-8") as f:
                        dom_snapshot = json.load(f)
                except Exception:
                    dom_snapshot = {"headings": [], "landmarks": [], "sections": [], "interactive_elements": []}
            else:
                dom_snapshot = {"headings": [], "landmarks": [], "sections": [], "interactive_elements": []}

        # Step 2: Save DOM snapshot and screenshot metadata
        try:
            with open(screenshot_meta_path, "w", encoding="utf-8") as f:
                json.dump(screenshot_metadata, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: could not save screenshot metadata: {e}")

        try:
            with open(dom_snapshot_path, "w", encoding="utf-8") as f:
                json.dump(dom_snapshot, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: could not save DOM snapshot: {e}")

        # Step 3: Package live captured elements into synchronized output
        live_elements = []
        for idx, ev in enumerate(classifier.website_elements, 1):
            role = ev.get("role", "generic")
            name = ev.get("name", "")
            tag_guess = "a" if role in ("link", "graphic link") else ("button" if role in ("button", "menu button") else ("input" if role in ("edit", "checkbox", "radio button") else "div"))
            live_elements.append({
                "step": idx,
                "selenium": {
                    "tag": tag_guess,
                    "text": name,
                    "aria-label": name if name else None,
                    "id": "",
                    "name": "",
                    "class": "",
                    "role": role,
                    "type": "text" if role == "edit" else None,
                    "expected_roles": [role] if role else [],
                },
                "nvda": ev,
                "comparison": {
                    "status": "MATCH",
                    "tag": tag_guess,
                    "nvda_role": role,
                    "dom_text": name,
                    "nvda_name": name,
                },
            })

        synchronized_output = {
            "url": url or "Live Manual Interaction Session",
            "initialization": {
                "phase": "PAGE_INITIALIZATION",
                "stabilization": locals().get("stabilization_meta"),
            } if locals().get("stabilization_meta") else None,
            "forward": live_elements,
            "backward": [],
        }

        with open(sync_path, "w", encoding="utf-8") as f:
            json.dump(synchronized_output, f, indent=4, ensure_ascii=False)

        # Step 4: Assemble unified evidence package (correlating DOM, NVDA, and screenshot)
        unified_package = {}
        try:
            unified_package = assemble_unified_evidence_package(
                url=url or "Live Manual Interaction Session",
                synchronized_output=synchronized_output,
                dom_snapshot=dom_snapshot,
                screenshot_metadata=screenshot_metadata,
                pre_audit_stabilization=locals().get("stabilization_meta"),
            )
            with open(unified_pkg_path, "w", encoding="utf-8") as f:
                json.dump(unified_package, f, indent=4, ensure_ascii=False)
            corr_summary = unified_package.get("correlation_summary", {})
            print(f"Unified evidence package assembled: {corr_summary.get('matched_count', 0)}/{corr_summary.get('total_synchronized_elements', 0)} elements matched.")
        except Exception as corr_err:
            print(f"Warning: could not assemble unified evidence package: {corr_err}")

        # Step 5: Primary Accessibility Analysis (Multimodal AI Gemini)
        if enable_ai:
            print("\n" + "=" * 70)
            print("PRIMARY ACCESSIBILITY ANALYSIS: AI ACCESSIBILITY ANALYZER (GEMINI)")
            print("=" * 70)
            ai_analyzer = AIAccessibilityAnalyzer()
            valid_ss_path = resolved_screenshot_path if screenshot_metadata.get("status") == "SUCCESS" else None
            ai_report = ai_analyzer.analyze_synchronized_evidence(
                synchronized_output,
                unified_package=unified_package,
                screenshot_path=valid_ss_path,
                screenshot_metadata=screenshot_metadata,
                output_dir=output_dir,
            )
            ai_analyzer.save_ai_report(ai_report, ai_rep_path)
            ai_dict = ai_report.to_dict()
            summary = ai_dict.get("summary", {})

            print(f"\nAI Accessibility Assessment Score: {summary.get('compliance_score', 100.0)}%")
            print(f"Total Unique Elements Captured   : {summary.get('total_elements_analyzed', len(classifier.website_elements))}")
            print(f"Total AI Violations Detected     : {summary.get('total_violations', 0)}")
            print(f"Total Recommendations Provided   : {summary.get('total_recommendations', 0)}")
            sev = summary.get("severity_summary", {})
            print(f"Severity Breakdown               : Critical={sev.get('CRITICAL', 0)}, Major={sev.get('MAJOR', 0)}, Minor={sev.get('MINOR', 0)}, Info={sev.get('INFO', 0)}")
            print(f"AI Analysis Status               : {ai_report.analysis_status} (Model: {ai_report.ai_metadata.get('model')})")

            if ai_report.violations:
                print("\nTOP AI ACCESSIBILITY VIOLATIONS DETECTED:")
                for idx, v in enumerate(ai_report.violations[:5], 1):
                    print(f"  {idx}. [{v.severity}] {v.rule_id} - {v.title} (Confidence: {v.confidence})")
                    print(f"     Impact      : {v.user_impact[:100]}...")
                    print(f"     Remediation : {v.recommendation[:100]}...")

            if hasattr(ai_report, "recommendations") and ai_report.recommendations:
                print("\nACCESSIBILITY RECOMMENDATIONS & BEST PRACTICES:")
                for idx, r in enumerate(ai_report.recommendations[:5], 1):
                    print(f"  {idx}. [{r.category}] {r.title}")
                    print(f"     Impact      : {r.user_impact[:100]}...")
                    print(f"     Guidance    : {r.developer_guidance[:100]}...")
        else:
            print("\n" + "=" * 70)
            print("AI ACCESSIBILITY AUDIT DISABLED")
            print("=" * 70)
            print("AI violation analysis was not requested (enable_ai=False).")
            unavailable_report = {
                "analysis_type": "AI_ACCESSIBILITY_ANALYSIS",
                "analysis_status": "AI_ANALYSIS_UNAVAILABLE",
                "url": url or "Live Manual Interaction Session",
                "summary": {
                    "total_elements_analyzed": len(classifier.website_elements),
                    "total_violations": 0,
                    "total_recommendations": 0,
                    "compliance_score": 0.0,
                    "severity_summary": {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "INFO": 0},
                },
                "violations": [],
                "recommendations": [],
                "ai_metadata": {"reason": "AI analysis was explicitly disabled."},
            }
            with open(ai_rep_path, "w", encoding="utf-8") as f:
                json.dump(unavailable_report, f, indent=4, ensure_ascii=False)

        print("\n" + "=" * 70)
        print("Outputs saved:")
        print(f"  - {log_path} (Stream of all captured live speech events)")
        print(f"  - {elements_path} (Unique website elements captured)")
        print(f"  - {sync_path} (DOM + Screen Reader Synchronized Data)")
        print(f"  - {screenshot_meta_path} (Screenshot Metadata)")
        if screenshot_metadata.get("status") == "SUCCESS":
            print(f"  - {screenshot_metadata.get('path')} (Webpage Screenshot Evidence)")
        print(f"  - {dom_snapshot_path} (DOM Semantic/Structural Snapshot)")
        print(f"  - {unified_pkg_path} (Unified Multimodal Evidence Package)")
        print(f"  - {ai_rep_path} (AI Accessibility Violation Report)")
        print("=" * 70)


def run_automated_audit(url, tab_limit=100, enable_ai=True, output_dir=None):
    """Automated Mode: Traverses a webpage via Selenium, syncing DOM with NVDA and running AI accessibility analysis."""
    import os
    import time
    from synchronisation.sync import (
        capture_synchronized_element,
        get_element_details,
        get_traversal_element_identifier,
    )
    from tools.nvda_tool import NVDATextExtractor
    from tools.nvda_filter import NVDAFilter
    from tools.nvda_parser import NVDAParser
    from tools.ai_agent import AIAccessibilityAnalyzer
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import StaleElementReferenceException
    import json

    TRAVERSAL_DELAY = float(os.environ.get("TRAVERSAL_DELAY", 1.0))

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

    print("\nLaunching Chrome...")
    from tools.pre_audit_stabilizer import PreAuditStabilizer, get_safe_chrome_options
    chrome_options = get_safe_chrome_options()
    driver = webdriver.Chrome(options=chrome_options)
    forward_results = []
    backward_results = []
    all_raw_events = []
    screenshot_metadata = {"status": "FAILED", "error": "Screenshot capture not attempted"}

    try:
        driver.maximize_window()
        # Mark baseline before navigation so historical Windows OS/desktop speech is excluded
        extractor.mark_baseline()
        print(f"[PAGE] Navigating to target URL: {url}")
        driver.get(url)

        # PRE-AUDIT STABILIZATION (Phase 3C)
        print("\n[STABILIZER] Initializing pre-audit page stabilization...")
        stabilizer = PreAuditStabilizer()
        stabilization_meta = stabilizer.stabilize(driver)
        print(
            f"[STABILIZER] Page stabilization complete: status={stabilization_meta.get('status')}, "
            f"dismissed={stabilization_meta.get('dismissed_count')}, "
            f"remaining={stabilization_meta.get('remaining_dialog_count')}, "
            f"time={stabilization_meta.get('stabilization_duration_ms')}ms"
        )

        # Clear stale NVDA speech produced during page load & popup dismissal
        print("[STABILIZER] Resetting NVDA capture baseline...")
        extractor.reset_capture_baseline()

        # Explicit Lifecycle State: Drain pre-traversal page initialization speech
        print("[NVDA] Page loading. Draining pre-traversal speech buffer...")
        initial_speech, is_settled = extractor.drain_initial_speech(from_baseline=True)
        print(f"[NVDA] Baseline established. Initial speech length: {len(initial_speech)} chars (settled={is_settled}).")

        initial_events = []
        if initial_speech:
            cleaned_init = filter_tool.clean(initial_speech)
            if cleaned_init:
                initial_events = [ev.to_dict() for ev in parser.parse(cleaned_init)]

        # Check if an interactive control already holds initial focus upon page load
        initial_focused_element = None
        try:
            active_init = driver.switch_to.active_element
            if active_init and active_init.tag_name.lower() not in ("body", "html"):
                initial_focused_element = get_element_details(active_init)
                print(f"[PAGE] Initial autofocus element detected: <{initial_focused_element.get('tag')}> id='{initial_focused_element.get('id')}'")
        except Exception:
            pass

        initialization_data = {
            "phase": "PAGE_INITIALIZATION",
            "stabilization": stabilization_meta,
            "raw_speech": initial_speech,
            "events": initial_events,
            "initial_focused_element": initial_focused_element,
            "settled": is_settled,
        }

        actions = ActionChains(driver)

        # Forward Traversal
        visited_forward = set()
        first_focused_forward = None
        prev_forward_id = None
        forward_stagnant_count = 0

        # Reset focus to document start so traversal starts from the first focusable element
        from tools.pre_audit_stabilizer import prepare_for_keyboard_traversal, focus_first_focusable_element
        prepare_for_keyboard_traversal(driver)

        print("\nStarting Forward Tab Traversal (TRAVERSAL_READY)...")
        for step in range(1, tab_limit + 1):
            if step == 1:
                # Step 1: Focus first visible focusable element on the page and capture its announcement
                def do_first_focus():
                    el = focus_first_focusable_element(driver)
                    if not el:
                        actions.send_keys(Keys.TAB).perform()

                step_speech, capture_status = extractor.capture_action_response(do_first_focus)
            else:
                def do_tab():
                    actions.send_keys(Keys.TAB).perform()

                step_speech, capture_status = extractor.capture_action_response(do_tab)

            try:
                active = driver.switch_to.active_element
            except StaleElementReferenceException:
                continue

            elem_id = getattr(active, "id", None)
            identifier = get_traversal_element_identifier(active)
            if not identifier:
                continue

            tag = (active.tag_name or "").lower()
            if tag in ("body", "html"):
                prev_forward_id = elem_id
                forward_stagnant_count = 0
                time.sleep(TRAVERSAL_DELAY)
                continue

            # Stagnation detection (focus stayed on the exact same element)
            if elem_id and elem_id == prev_forward_id:
                forward_stagnant_count += 1
                if forward_stagnant_count == 1:
                    # An open flyout, dropdown, or modal may be intercepting keys.
                    # Send ESCAPE to dismiss popups and free focus.
                    try:
                        actions.send_keys(Keys.ESCAPE).perform()
                        time.sleep(0.3)
                    except Exception:
                        pass
                elif forward_stagnant_count >= 3:
                    print(f"Focus trapped on element <{tag}> for {forward_stagnant_count} consecutive steps. Forward traversal halted.")
                    break
            else:
                forward_stagnant_count = 0

            prev_forward_id = elem_id

            # Loop detection: only if focus returns to the first focused element after visiting >= 5 distinct elements
            if first_focused_forward and elem_id == first_focused_forward and len(visited_forward) >= 5:
                print(f"Reached loop back to initial element at step {step}. Forward traversal completed.")
                break

            if first_focused_forward is None:
                first_focused_forward = elem_id

            visited_forward.add(elem_id or identifier)

            selenium_details = get_element_details(active)
            result = capture_synchronized_element(
                extractor,
                filter_tool,
                parser,
                selenium_details,
                captured_speech=step_speech,
                capture_status=capture_status,
            )
            result["step"] = step
            forward_results.append(result)

            if result["nvda"]:
                all_raw_events.append(result["nvda"])

            nvda_info = result["nvda"]["role"] if result["nvda"] else f"None ({capture_status})"
            print(f"Step {step:02d} | DOM: <{selenium_details['tag']}> '{selenium_details['text'][:30]}' | NVDA: {nvda_info} -> {result['comparison']['status']}")
            time.sleep(TRAVERSAL_DELAY)

        # Backward Traversal
        visited_backward = set()
        first_focused_backward = None
        prev_backward_id = None
        backward_stagnant_count = 0

        # Reset focus to document root for clean backward traversal
        prepare_for_keyboard_traversal(driver)

        print("\nStarting Backward Shift+Tab Traversal...")
        for step in range(1, tab_limit + 1):
            def do_shift_tab():
                actions.key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT).perform()

            step_speech, capture_status = extractor.capture_action_response(do_shift_tab)

            try:
                active = driver.switch_to.active_element
            except StaleElementReferenceException:
                continue

            elem_id = getattr(active, "id", None)
            identifier = get_traversal_element_identifier(active)
            if not identifier:
                continue

            tag = (active.tag_name or "").lower()
            if tag in ("body", "html"):
                prev_backward_id = elem_id
                backward_stagnant_count = 0
                time.sleep(TRAVERSAL_DELAY)
                continue

            # Stagnation detection (focus stayed on the exact same element)
            if elem_id and elem_id == prev_backward_id:
                backward_stagnant_count += 1
                if backward_stagnant_count == 1:
                    # An open flyout, dropdown, or modal may be intercepting keys.
                    # Send ESCAPE to dismiss popups and free focus.
                    try:
                        actions.send_keys(Keys.ESCAPE).perform()
                        time.sleep(0.3)
                    except Exception:
                        pass
                elif backward_stagnant_count >= 3:
                    print(f"Focus trapped on element <{tag}> for {backward_stagnant_count} consecutive steps. Backward traversal halted.")
                    break
            else:
                backward_stagnant_count = 0

            prev_backward_id = elem_id

            # Loop detection: only if focus returns to the first backward element after visiting >= 5 distinct elements
            if first_focused_backward and elem_id == first_focused_backward and len(visited_backward) >= 5:
                print(f"Reached loop back to initial backward element at step {step}. Backward traversal completed.")
                break

            if first_focused_backward is None:
                first_focused_backward = elem_id

            visited_backward.add(elem_id or identifier)

            selenium_details = get_element_details(active)
            result = capture_synchronized_element(
                extractor,
                filter_tool,
                parser,
                selenium_details,
                captured_speech=step_speech,
                capture_status=capture_status,
            )
            result["step"] = step
            backward_results.append(result)

            if result["nvda"]:
                all_raw_events.append(result["nvda"])

            nvda_info = result["nvda"]["role"] if result["nvda"] else f"None ({capture_status})"
            print(f"Step {step:02d} | DOM: <{selenium_details['tag']}> '{selenium_details['text'][:30]}' | NVDA: {nvda_info} -> {result['comparison']['status']}")
            time.sleep(TRAVERSAL_DELAY)

    finally:
        print("\nTraversal finished. Extracting semantic DOM snapshot & screenshot evidence...")
        dom_snapshot = {}
        try:
            from tools.dom_extractor import extract_dom_snapshot
            dom_snapshot = extract_dom_snapshot(driver)
        except Exception as dom_err:
            dom_snapshot = {"error": str(dom_err), "headings": [], "landmarks": [], "sections": [], "interactive_elements": []}

        try:
            from tools.screenshot_capture import capture_webpage_screenshot

            screenshot_path = os.path.join(output_dir, "webpage_screenshot.png") if output_dir else "webpage_screenshot.png"
            screenshot_metadata = capture_webpage_screenshot(driver, output_path=screenshot_path, output_dir=output_dir)
            if screenshot_metadata.get("status") == "SUCCESS":
                print(f"Screenshot captured: {screenshot_metadata.get('path')} ({screenshot_metadata.get('width')}x{screenshot_metadata.get('height')}, mode: {screenshot_metadata.get('capture_mode')})")
            else:
                print(f"Screenshot capture notice: {screenshot_metadata.get('error')}")
        except Exception as ss_err:
            screenshot_metadata = {"status": "FAILED", "error": str(ss_err)}

        print("Closing browser window...")
        try:
            driver.quit()
        except Exception:
            pass

    # Destination paths for artifacts
    log_path = os.path.join(output_dir, "nvda_log.txt") if output_dir else "nvda_log.txt"
    sync_path = os.path.join(output_dir, "synchronized_output.json") if output_dir else "synchronized_output.json"
    ai_rep_path = os.path.join(output_dir, "ai_accessibility_report.json") if output_dir else "ai_accessibility_report.json"
    screenshot_meta_path = os.path.join(output_dir, "screenshot_metadata.json") if output_dir else "screenshot_metadata.json"
    dom_snapshot_path = os.path.join(output_dir, "dom_snapshot.json") if output_dir else "dom_snapshot.json"
    unified_pkg_path = os.path.join(output_dir, "unified_evidence_package.json") if output_dir else "unified_evidence_package.json"

    # Save screenshot_metadata.json
    try:
        with open(screenshot_meta_path, "w", encoding="utf-8") as f:
            json.dump(screenshot_metadata, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: could not save screenshot metadata: {e}")

    # Save dom_snapshot.json
    try:
        with open(dom_snapshot_path, "w", encoding="utf-8") as f:
            json.dump(dom_snapshot, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: could not save DOM snapshot: {e}")

    # Save nvda_log.txt
    with open(log_path, "w", encoding="utf-8") as log:
        for ev in all_raw_events:
            log.write(json.dumps(ev, ensure_ascii=False) + "\n")

    # Save synchronized_output.json
    final_output = {
        "url": url,
        "initialization": locals().get("initialization_data", None),
        "forward": forward_results,
        "backward": backward_results,
    }

    with open(sync_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)

    # Assemble and save unified_evidence_package.json (Phase 3A)
    unified_package = {}
    try:
        from tools.evidence_correlator import assemble_unified_evidence_package
        unified_package = assemble_unified_evidence_package(
            url=url,
            synchronized_output=final_output,
            dom_snapshot=dom_snapshot,
            screenshot_metadata=screenshot_metadata,
            pre_audit_stabilization=locals().get("stabilization_meta"),
        )
        with open(unified_pkg_path, "w", encoding="utf-8") as f:
            json.dump(unified_package, f, indent=4, ensure_ascii=False)
        corr_summary = unified_package.get("correlation_summary", {})
        print(f"Unified evidence package assembled: {corr_summary.get('matched_count', 0)}/{corr_summary.get('total_synchronized_elements', 0)} elements matched ({corr_summary.get('match_rate_percent', 0)}%).")
    except Exception as corr_err:
        print(f"Warning: could not assemble unified evidence package: {corr_err}")

    # -------------------------------------------------------------------------
    # ACCESSIBILITY ANALYSIS LAYER (PURE AI - GEMINI)
    # -------------------------------------------------------------------------
    if enable_ai:
        print("\n" + "=" * 70)
        print("PRIMARY ACCESSIBILITY ANALYSIS: AI ACCESSIBILITY ANALYZER (GEMINI)")
        print("=" * 70)
        ai_analyzer = AIAccessibilityAnalyzer()
        ai_report_model = ai_analyzer.analyze_synchronized_evidence(
            final_output,
            unified_package=unified_package,
            screenshot_path=screenshot_path,
            screenshot_metadata=screenshot_metadata,
            output_dir=output_dir,
        )
        ai_analyzer.save_ai_report(ai_report_model, ai_rep_path)
        ai_report_dict = ai_report_model.to_dict()

        summary = ai_report_dict.get("summary", {})
        sev = summary.get("severity_summary", {})

        print(f"\nAI Accessibility Assessment Score: {summary.get('compliance_score', 100.0)}%")
        print(f"Total Elements Audited (by AI)   : {summary.get('total_elements_analyzed', len(forward_results))}")
        print(f"Total AI Violations Discovered   : {summary.get('total_violations', 0)}")
        print(f"Total Recommendations Provided   : {summary.get('total_recommendations', 0)}")
        print(f"AI Severity Breakdown            : Critical={sev.get('CRITICAL', 0)}, Major={sev.get('MAJOR', 0)}, Minor={sev.get('MINOR', 0)}, Info={sev.get('INFO', 0)}")
        print(f"AI Analysis Status               : {ai_report_model.analysis_status} (Model: {ai_report_model.ai_metadata.get('model')})")

        if ai_report_model.violations:
            print("\nTOP AI-DETECTED ACCESSIBILITY VIOLATIONS:")
            for idx, v in enumerate(ai_report_model.violations[:5], 1):
                print(f"  {idx}. [{v.severity}] {v.rule_id} - {v.title} (Confidence: {v.confidence})")
                print(f"     User Impact : {v.user_impact[:90]}...")
                print(f"     Remediation : {v.recommendation[:90]}...")

        if hasattr(ai_report_model, "recommendations") and ai_report_model.recommendations:
            print("\nACCESSIBILITY RECOMMENDATIONS & BEST PRACTICES:")
            for idx, r in enumerate(ai_report_model.recommendations[:5], 1):
                print(f"  {idx}. [{r.category}] {r.title}")
                print(f"     User Impact : {r.user_impact[:90]}...")
                print(f"     Guidance    : {r.developer_guidance[:90]}...")

        print("\n" + "=" * 70)
        print("Outputs saved:")
        print(f"  - {log_path} (Stream of all captured NVDA speech events)")
        print(f"  - {sync_path} (DOM + Screen Reader Synchronized Data)")
        print(f"  - {ai_rep_path} (AI Accessibility Analysis Report)")
        if screenshot_metadata.get("status") == "SUCCESS":
            print(f"  - {screenshot_metadata.get('path')} (Webpage Screenshot Evidence)")
        print(f"  - {dom_snapshot_path} (DOM Semantic/Structural Snapshot)")
        print(f"  - {unified_pkg_path} (Unified Multimodal Evidence Package)")
        print("=" * 70)
        is_success = ai_report_model.analysis_status in ("COMPLETED", "NO_VIOLATIONS")
        return {
            "status": "completed" if is_success else "failed",
            "url": url,
            "analysis_type": "AI_ACCESSIBILITY_ANALYSIS",
            "total_elements_audited": summary.get("total_elements_analyzed", len(forward_results)),
            "total_violations": summary.get("total_violations", 0),
            "total_recommendations": summary.get("total_recommendations", len(ai_report_model.recommendations) if hasattr(ai_report_model, "recommendations") else 0),
            "compliance_score": summary.get("compliance_score", 100.0),
            "severity_summary": sev,
            "analysis": ai_report_dict,
            "output_dir": output_dir,
            "screenshot": screenshot_metadata,
            "dom_snapshot": dom_snapshot,
            "unified_package": unified_package,
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
                "total_recommendations": 0,
                "compliance_score": 0.0,
                "severity_summary": {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "INFO": 0},
            },
            "violations": [],
            "recommendations": [],
            "ai_metadata": {"reason": "AI analysis was explicitly disabled."},
        }
        with open(ai_rep_path, "w", encoding="utf-8") as f:
            json.dump(unavailable_report, f, indent=4, ensure_ascii=False)

        print("\n" + "=" * 70)
        print("Outputs saved:")
        print(f"  - {log_path} (Stream of all captured NVDA speech events)")
        print(f"  - {sync_path} (DOM + Screen Reader Synchronized Data)")
        print(f"  - {ai_rep_path} (AI Accessibility Analysis Report)")
        if screenshot_metadata.get("status") == "SUCCESS":
            print(f"  - {screenshot_metadata.get('path')} (Webpage Screenshot Evidence)")
        print(f"  - {dom_snapshot_path} (DOM Semantic/Structural Snapshot)")
        print(f"  - {unified_pkg_path} (Unified Multimodal Evidence Package)")
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
            "screenshot": screenshot_metadata,
            "dom_snapshot": dom_snapshot,
            "unified_package": unified_package,
        }


def run_unit_tests():
    """Run comprehensive automated test suite across all modules."""
    from tests.test_parser import TestNVDAParserGeneric
    from tests.test_ai_agent import TestAIAccessibilityAgent
    from tests.test_gemini_multimodal import TestGeminiMultimodalIntegration
    from tests.test_backend import TestBackendAPI
    from tests.test_database import TestPostgreSQLDatabase
    from tests.test_dom_extractor import TestDOMExtractorUnit
    from tests.test_screenshot_capture import TestScreenshotCapture
    from tests.test_evidence_correlator import TestEvidenceCorrelator
    from tests.test_validation_irctc import TestIRCTCValidationCase
    from tests.test_nvda_synchronization import TestNVDASynchronizationLifecycle
    from tests.test_audit_evidence_pipeline import TestAuditEvidencePipeline
    from tests.test_traversal_and_live_listener import (
        TestTraversalIdentifierAndStagnation,
        TestLiveListenerVisualEvidence,
    )

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestNVDAParserGeneric))
    suite.addTests(loader.loadTestsFromTestCase(TestAIAccessibilityAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestGeminiMultimodalIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestBackendAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestPostgreSQLDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestDOMExtractorUnit))
    suite.addTests(loader.loadTestsFromTestCase(TestScreenshotCapture))
    suite.addTests(loader.loadTestsFromTestCase(TestEvidenceCorrelator))
    suite.addTests(loader.loadTestsFromTestCase(TestIRCTCValidationCase))
    suite.addTests(loader.loadTestsFromTestCase(TestNVDASynchronizationLifecycle))
    suite.addTests(loader.loadTestsFromTestCase(TestAuditEvidencePipeline))
    suite.addTests(loader.loadTestsFromTestCase(TestTraversalIdentifierAndStagnation))
    suite.addTests(loader.loadTestsFromTestCase(TestLiveListenerVisualEvidence))

    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


def main():
    parser = argparse.ArgumentParser(
        description="AI-Powered Screen Reader (NVDA) Accessibility Testing & Extraction System"
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=None,
        help="Target website URL for automated accessibility audit (e.g. https://example.com)",
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
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Disable AI accessibility analysis (evidence collection only)",
    )
    parser.add_argument(
        "--screenshot",
        "-s",
        type=str,
        default=None,
        help="Path to webpage screenshot image for visual evidence in live/manual mode",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=None,
        help="Directory to save audit output artifacts",
    )

    args = parser.parse_args()

    if args.test:
        run_unit_tests()
    elif args.live:
        run_live_listener(
            url=args.url,
            enable_ai=not args.no_ai,
            screenshot_path=args.screenshot,
            output_dir=args.output_dir,
        )
    elif args.url:
        try:
            run_automated_audit(
                args.url,
                tab_limit=args.limit,
                enable_ai=not args.no_ai,
                output_dir=args.output_dir,
            )
        except RuntimeError:
            sys.exit(1)
    else:
        parser.print_help()
        print("\nNotice: Please specify a target URL to audit (or use --live or --test).")
        sys.exit(0)


if __name__ == "__main__":
    main()
