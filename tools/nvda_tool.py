import os
import time
import logging
from enum import Enum
from typing import Tuple, Optional, Callable, Any

try:
    from pywinauto import Desktop
except ImportError:
    Desktop = None

logger = logging.getLogger("NVDATextExtractor")


class NVDAEvidencePhase(str, Enum):
    """Explicit lifecycle state phases for NVDA accessibility evidence collection."""
    INITIALIZING = "INITIALIZING"
    PAGE_LOADING = "PAGE_LOADING"
    PAGE_LOAD_SPEECH = "PAGE_LOAD_SPEECH"
    NVDA_CAPTURE_READY = "NVDA_CAPTURE_READY"
    BASELINE_ESTABLISHED = "BASELINE_ESTABLISHED"
    TRAVERSAL_READY = "TRAVERSAL_READY"
    TRAVERSING = "TRAVERSING"
    TRAVERSAL_COMPLETE = "TRAVERSAL_COMPLETE"


class NVDATextExtractor:
    """
    Connects to the running NVDA Speech Viewer window and captures
    spoken text output with explicit lifecycle state management,
    pre-traversal speech isolation, and causal action-response boundaries.
    """

    def __init__(self, window=None, rich_edit=None):
        self.phase: NVDAEvidencePhase = NVDAEvidencePhase.INITIALIZING
        self.sequence_number: int = 0
        self.window = window
        self.rich_edit = rich_edit

        if self.rich_edit is None and Desktop is not None:
            # Attempt 1: Standard win32 exact title
            try:
                self.window = Desktop(backend="win32").window(title_re=".*Speech Viewer.*")
                self.rich_edit = self.window.child_window(class_name="RICHEDIT50W")
            except Exception:
                pass

            # Attempt 2: Search all top-level windows for Speech Viewer
            if self.rich_edit is None:
                try:
                    desktop = Desktop(backend="win32")
                    for win in desktop.windows():
                        title = win.window_text()
                        if "speech viewer" in title.lower():
                            self.window = win
                            self.rich_edit = win.child_window(class_name="RICHEDIT50W")
                            break
                except Exception:
                    pass

            # Attempt 3: Direct fallback
            if self.rich_edit is None:
                try:
                    self.window = Desktop(backend="win32").window(title="NVDA Speech Viewer")
                    self.rich_edit = self.window.child_window(class_name="RICHEDIT50W")
                except Exception as e:
                    logger.debug(f"Speech Viewer connection fallback failed: {e}")

        self.previous_text: str = self.get_text()
        self.baseline_text: str = self.previous_text
        self.phase = NVDAEvidencePhase.NVDA_CAPTURE_READY
        logger.info(f"[NVDA] Capture initialized (initial Speech Viewer buffer length={len(self.previous_text)} chars).")

    def get_text(self) -> str:
        """Return the current complete raw contents of the Speech Viewer."""
        try:
            if self.rich_edit is not None:
                return self.rich_edit.window_text()
        except Exception as e:
            logger.debug(f"Error reading Speech Viewer text: {e}")
        return ""

    def get_new_text(self) -> str:
        """
        Return newly added Speech Viewer text since the previous read.
        Maintained for backward compatibility.
        """
        current = self.get_text()
        if current.startswith(self.previous_text):
            new = current[len(self.previous_text):]
        else:
            # Speech Viewer was cleared or updated externally
            new = current

        self.previous_text = current
        return new.strip()

    def mark_baseline(self) -> str:
        """
        Record the current Speech Viewer position as the authoritative baseline boundary.
        Speech produced prior to this boundary will NEVER be attributed to subsequent actions.
        """
        current = self.get_text()
        self.baseline_text = current
        self.previous_text = current
        self.phase = NVDAEvidencePhase.BASELINE_ESTABLISHED
        logger.info(f"[NVDA] Baseline established at buffer offset {len(current)} chars.")
        return current

    @property
    def last_mark(self) -> str:
        """Alias for the baseline boundary mark."""
        return self.baseline_text

    def drain_initial_speech(
        self,
        max_timeout: float = 6.0,
        settle_interval: float = 0.6,
        poll_interval: float = 0.1,
        from_baseline: bool = False,
    ) -> Tuple[str, bool]:
        """
        Monitor Speech Viewer during page load, classify all accumulated speech as
        page initialization speech, wait for it to settle adaptively, and establish
        a clean traversal baseline boundary.

        If from_baseline is True, only speech produced strictly after baseline_text
        is captured (preventing historical OS/desktop speech from leaking into the audit).

        Returns:
            (initial_speech_text, is_settled)
        """
        self.phase = NVDAEvidencePhase.PAGE_LOAD_SPEECH
        logger.info("[NVDA] Monitoring and draining page initialization speech...")

        start_time = time.time()
        last_change_time = start_time
        prev_len = len(self.get_text())

        while time.time() - start_time < max_timeout:
            time.sleep(poll_interval)
            current_text = self.get_text()
            curr_len = len(current_text)

            if curr_len != prev_len:
                last_change_time = time.time()
                prev_len = curr_len
            elif time.time() - last_change_time >= settle_interval:
                # Speech has settled (no new speech for settle_interval)
                break

        current_full = self.get_text()
        is_settled = (time.time() - last_change_time >= settle_interval)

        # Compute initial speech produced during this session.
        if from_baseline and self.baseline_text and current_full.startswith(self.baseline_text):
            initial_speech = current_full[len(self.baseline_text):].strip()
        else:
            initial_speech = current_full.strip()

        # Establish clean baseline for traversal
        self.mark_baseline()
        self.phase = NVDAEvidencePhase.TRAVERSAL_READY

        logger.info(
            f"[NVDA] Initialization speech isolated: length={len(initial_speech)} chars, "
            f"settled={is_settled}, elapsed={round(time.time() - start_time, 2)}s."
        )
        return initial_speech, is_settled

    def capture_action_response(
        self,
        action_fn: Optional[Callable[[], Any]] = None,
        timeout: float = float(os.environ.get("TRAVERSAL_TIMEOUT", 1.0)),
        poll_interval: float = 0.05,
        settle_interval: float = 0.25,
    ) -> Tuple[str, str]:
        """
        Causal Action-Response Traversal Synchronization:
        1. Records pre-action buffer boundary mark.
        2. Executes the traversal action (e.g. Tab keystroke).
        3. Waits adaptively for fresh NVDA speech appearing strictly after the pre-action mark.
        4. Waits settle_interval for speech completion so multi-word announcements are not truncated.
        5. Updates the baseline boundary so this step's speech does not leak into future steps.

        Returns:
            (captured_speech, status) where status is "OK" or "NVDA_CAPTURE_TIMEOUT"
        """
        self.phase = NVDAEvidencePhase.TRAVERSING
        self.sequence_number += 1
        seq = self.sequence_number

        # 1. Record pre-action boundary mark
        pre_action_text = self.get_text()
        logger.debug(f"[TRAVERSAL] Sequence {seq}: Pre-action boundary recorded (len={len(pre_action_text)}).")

        # 2. Trigger traversal action
        if action_fn is not None:
            try:
                action_fn()
            except Exception as e:
                logger.error(f"[TRAVERSAL] Sequence {seq}: Traversal action failed: {e}", exc_info=True)
                return "", "ACTION_FAILED"

        logger.debug(f"[NVDA] Sequence {seq}: Waiting for traversal speech response (timeout={timeout}s)...")

        # 3. Adaptive polling for speech appearing strictly after pre_action_text
        start_time = time.time()
        new_speech_detected = False
        last_change_time = None
        current_text = pre_action_text

        while time.time() - start_time < timeout:
            time.sleep(poll_interval)
            current_text = self.get_text()

            # Check if text has advanced past pre_action_text
            if current_text != pre_action_text and len(current_text) > len(pre_action_text):
                if not new_speech_detected:
                    new_speech_detected = True
                    last_change_time = time.time()
                    logger.debug(f"[NVDA] Sequence {seq}: Fresh speech detected, waiting {settle_interval}s to settle...")
                else:
                    last_change_time = time.time()

            if new_speech_detected and last_change_time is not None:
                if time.time() - last_change_time >= settle_interval:
                    # Speech output has stabilized for this action
                    break

        # 4. Extract only the newly produced speech
        if current_text.startswith(pre_action_text):
            step_speech = current_text[len(pre_action_text):].strip()
        else:
            # Buffer was cleared or scrolled externally
            step_speech = current_text.strip()

        # 5. Advance previous_text so this step is committed
        self.previous_text = current_text

        if step_speech:
            elapsed = round(time.time() - start_time, 2)
            logger.info(f"[NVDA] Sequence {seq}: Response received in {elapsed}s: {repr(step_speech[:60])}")
            return step_speech, "OK"
        else:
            logger.warning(f"[NVDA] Sequence {seq}: NVDA_CAPTURE_TIMEOUT (no speech within {timeout}s).")
            return "", "NVDA_CAPTURE_TIMEOUT"