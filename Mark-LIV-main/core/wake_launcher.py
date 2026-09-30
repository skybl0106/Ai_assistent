"""Background Windows sign-in listener that opens Geni by voice."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import subprocess
import sys
import threading

_FROZEN = getattr(sys, "frozen", False)
APP_DIR = (Path(sys.executable).resolve().parent if _FROZEN
           else Path(__file__).resolve().parent.parent)
MAIN_SCRIPT = None if _FROZEN else APP_DIR / "main.py"
LOG_PATH = Path.home() / ".buddy" / "wake_launcher.log"


def _logger() -> logging.Logger:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("buddy.wake_launcher")
    if not logger.handlers:
        handler = RotatingFileHandler(LOG_PATH, maxBytes=256_000, backupCount=2,
                                      encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def _find_buddy_process():
    try:
        import psutil
        target = Path(sys.executable).resolve() if _FROZEN else MAIN_SCRIPT.resolve()
        for process in psutil.process_iter(["cmdline", "cwd", "exe"]):
            try:
                arguments = process.info.get("cmdline") or []
                if process.pid == os.getpid() or "--wake-listener" in arguments:
                    continue
                if _FROZEN:
                    executable = process.info.get("exe")
                    if executable and Path(executable).resolve() == target:
                        return process
                    continue
                cwd = Path(process.info.get("cwd") or APP_DIR)
                for argument in arguments:
                    path = Path(argument)
                    if path.name.lower() != "main.py":
                        continue
                    if not path.is_absolute():
                        path = cwd / path
                    if path.resolve() == target:
                        return process
            except (OSError, RuntimeError):
                continue
    except Exception:
        return None
    return None


def _listen_for_wake(logger: logging.Logger) -> bool:
    import sounddevice as sd

    from core import audio_devices
    from core.wake_word import SAMPLE_RATE, WakeWordDetector
    from memory.config_manager import get_input_device

    detected = threading.Event()
    detector = WakeWordDetector(
        on_detect=detected.set,
        logger=lambda message: logger.info("%s", message),
    )
    if not detector.start():
        return False

    def _wait_on_device(device, label: str) -> None:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=1024,
            device=device,
            callback=lambda audio, _frames, _time, _status: detector.feed(audio),
        ):
            logger.info("Listening locally for Geni on %s", label)
            detected.wait()

    try:
        input_name = get_input_device()
        input_device = audio_devices.resolve(input_name, "input")
        try:
            _wait_on_device(input_device, input_name or "system default")
        except Exception:
            if input_device is None:
                raise
            logger.exception("Selected microphone '%s' failed; trying system default", input_name)
            _wait_on_device(None, "system default")
        return True
    except Exception:
        logger.exception("Could not open the wake microphone")
        return False
    finally:
        detector.stop()


def main() -> int:
    from memory.config_manager import get_wake_word_enabled

    logger = _logger()
    while get_wake_word_enabled():
        existing = _find_buddy_process()
        if existing is not None:
            logger.info("Geni is already open; waiting for it to close")
            try:
                existing.wait()
            except Exception:
                threading.Event().wait(2)
            continue

        if not _listen_for_wake(logger):
            threading.Event().wait(5)
            continue
        if not get_wake_word_enabled():
            break

        existing = _find_buddy_process()
        if existing is not None:
            continue

        environment = os.environ.copy()
        environment["BUDDY_WAKE_LAUNCH"] = "1"
        try:
            command = [sys.executable] if _FROZEN else [sys.executable, str(MAIN_SCRIPT)]
            process = subprocess.Popen(
                command,
                cwd=APP_DIR,
                env=environment,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            logger.info("Opened Geni after wake phrase (pid %d)", process.pid)
            process.wait()
        except Exception:
            logger.exception("Could not open Geni")

    logger.info("Wake listener stopped because wake word is disabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())