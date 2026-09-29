"""Local, offline recognition of the Geni wake phrases."""
from __future__ import annotations

import importlib.util
import json
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import zipfile
from pathlib import Path
from typing import Callable
from urllib.request import urlopen

WAKE_PHRASES = ("hi geni", "hi genie", "hey geni", "hey genie")
WAKE_PHRASE = WAKE_PHRASES[0]
SAMPLE_RATE = 16000
MODEL_NAME = "vosk-model-small-en-us-0.15"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"
MODEL_DIR = Path.home() / ".buddy" / "models" / MODEL_NAME


def is_installed() -> bool:
    """True if the Vosk speech-recognition package is importable."""
    try:
        return importlib.util.find_spec("vosk") is not None
    except Exception:
        return False


def is_ready() -> bool:
    """Cheap check for the installed package and downloaded acoustic model."""
    return is_installed() and (MODEL_DIR / "am" / "final.mdl").is_file()


def install_and_download(logger: Callable[[str], None] = print,
                         notify: Callable[[str], None] | None = None) -> tuple[bool, str]:
    """Install Vosk and download its small English model for local recognition."""
    tell = notify or (lambda _msg: None)
    try:
        if not is_installed():
            logger("Wake word: installing Vosk (one-time)…")
            tell("Wake word: installing Vosk (one-time)…")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "vosk"],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                tail = (result.stderr or result.stdout or "").strip().splitlines()[-1:] or [""]
                return False, f"Vosk install failed: {tail[0][:160]}"

        if not is_ready():
            logger("Wake word: downloading the English speech model (one-time)…")
            tell("Wake word: downloading the English speech model (one-time)…")
            model_parent = MODEL_DIR.parent
            model_parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(
                    prefix="buddy-vosk-", dir=model_parent) as temp_dir:
                archive = Path(temp_dir) / f"{MODEL_NAME}.zip"
                with urlopen(MODEL_URL, timeout=60) as response, archive.open("wb") as output:
                    shutil.copyfileobj(response, output)
                with zipfile.ZipFile(archive) as bundle:
                    root = Path(temp_dir).resolve()
                    for entry in bundle.infolist():
                        target = (root / entry.filename).resolve()
                        if not target.is_relative_to(root):
                            raise ValueError("model archive contains an invalid path")
                    bundle.extractall(root)
                extracted = Path(temp_dir) / MODEL_NAME
                if not (extracted / "am" / "final.mdl").is_file():
                    return False, "downloaded model is incomplete."
                if MODEL_DIR.exists():
                    shutil.rmtree(MODEL_DIR)
                shutil.move(str(extracted), str(MODEL_DIR))

        if not is_ready():
            return False, "Vosk installed, but the English model is not ready."
        logger("Wake word: ready for 'Hi Geni'.")
        return True, "Offline 'Hi Geni' recognition is ready."
    except Exception as exc:
        return False, f"wake-word setup failed: {exc}"


def _matches_wake_result(result_json: str) -> bool:
    try:
        result = json.loads(result_json)
    except (TypeError, json.JSONDecodeError):
        return False
    if not isinstance(result, dict):
        return False

    recognized = " ".join(re.findall(r"[a-z]+", str(result.get("text", "")).lower()))
    return recognized in WAKE_PHRASES


class WakeWordDetector:
    """Run constrained phrase recognition off the real-time microphone thread."""

    def __init__(self, on_detect: Callable[[], None],
                 logger: Callable[[str], None] = print,
                 notify: Callable[[str], None] | None = None):
        self._on_detect = on_detect
        self._logger = logger
        self._notify = notify or (lambda _msg: None)
        self._queue: queue.Queue = queue.Queue(maxsize=50)
        self._thread: threading.Thread | None = None
        self._running = False
        self._model = None
        self._recognizer = None
        self._ready = False

    def start(self) -> bool:
        """Load the local model and start recognition. Safe to call repeatedly."""
        if self._running:
            return True
        try:
            import vosk
            vosk.SetLogLevel(-1)
            self._model = vosk.Model(str(MODEL_DIR))
            self._recognizer = vosk.KaldiRecognizer(
                self._model, SAMPLE_RATE, json.dumps([*WAKE_PHRASES, "[unk]"])
            )
        except Exception as exc:
            self._logger(f"Wake word: could not load model — {exc}")
            self._notify("Wake word unavailable — use the WAKE NOW button.")
            self._model = None
            self._recognizer = None
            return False
        self._running = True
        self._ready = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="WakeWordThread")
        self._thread.start()
        self._logger("Wake word: listening locally for 'Hi Geni'.")
        return True

    def stop(self) -> None:
        self._running = False
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass
        self._model = None
        self._recognizer = None
        self._ready = False

    @property
    def ready(self) -> bool:
        return self._ready

    def feed(self, frame_int16) -> None:
        """Copy and enqueue microphone audio without blocking its callback."""
        if not self._running:
            return
        try:
            data = (frame_int16[:, 0].copy() if getattr(frame_int16, "ndim", 1) > 1
                    else frame_int16.copy())
            self._queue.put_nowait(data)
        except Exception:
            pass

    def _loop(self) -> None:
        import numpy as np
        while self._running:
            try:
                frame = self._queue.get()
                if frame is None or not self._running:
                    break
                audio = np.asarray(frame, dtype=np.int16).reshape(-1).tobytes()
                if not self._recognizer.AcceptWaveform(audio):
                    continue
                if _matches_wake_result(self._recognizer.Result()):
                    self._recognizer.Reset()
                    self._drain()
                    try:
                        self._on_detect()
                    except Exception as exc:
                        self._logger(f"Wake word: on_detect error — {exc}")
            except Exception as exc:
                self._logger(f"Wake word: inference error — {exc}")

    def _drain(self) -> None:
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass
