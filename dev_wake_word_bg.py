"""
DevMind "DEV" Wake Word Listener — Background Process
Listens continuously for the wake word "DEV" (or "Hey Dev", "DevMind") from the microphone.
Sends trigger payloads to the DevMind AI IDE server (http://localhost:7860).
"""

import sys
import os
import time
import json
import urllib.request
import urllib.parse

# ── Dependency Guard ─────────────────────────────────────────────────────────
try:
    import speech_recognition as sr
except ImportError:
    print(json.dumps({
        "type": "ERROR",
        "msg": "DEPENDENCY_MISSING: 'speech_recognition' is not installed. Run: pip install SpeechRecognition"
    }))
    sys.stdout.flush()
    sys.exit(1)

try:
    import pyaudio  # noqa: F401
except ImportError:
    print(json.dumps({
        "type": "ERROR",
        "msg": "DEPENDENCY_MISSING: 'pyaudio' is not installed. Run: pip install pyaudio"
    }))
    sys.stdout.flush()
    sys.exit(1)

# ── Wake Word Matching Logic ──────────────────────────────────────────────────
WAKE_WORD_VARIANTS = {
    "dev", "hey dev", "hello dev", "hi dev", "devmind",
    "deb", "dave", "dab", "devin", "open dev", "ok dev"
}

def is_dev_wake_word(text: str) -> str | None:
    t = text.lower().strip()
    words = t.split()
    for variant in WAKE_WORD_VARIANTS:
        if variant in t or any(w == "dev" for w in words):
            return variant
    return None

def notify_devmind_server(text: str, command: str):
    url = "http://localhost:7860/api/voice/trigger"
    payload = json.dumps({"text": text, "command": command, "source": "dev_wake_word"}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            pass
    except Exception:
        pass

def listen_for_dev():
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True

    try:
        with sr.Microphone() as source:
            print(json.dumps({"type": "INFO", "msg": "Microphone initialized. Listening for wake word 'DEV'..."}))
            sys.stdout.flush()
            r.adjust_for_ambient_noise(source, duration=0.5)

            print(json.dumps({"type": "INFO", "msg": "DEV Engine Active. Speak 'Dev' or 'Hey Dev'..."}))
            sys.stdout.flush()

            last_error_time = 0

            while True:
                try:
                    audio = r.listen(source, phrase_time_limit=8)
                    text = r.recognize_google(audio).lower()
                    
                    trigger_found = is_dev_wake_word(text)
                    if trigger_found:
                        command = text.replace(trigger_found, "", 1).strip()
                        result = {
                            "type": "WAKE_WORD",
                            "wake_word": trigger_found,
                            "text": text,
                            "command": command
                        }
                        print(json.dumps(result))
                        sys.stdout.flush()
                        notify_devmind_server(text, command)

                except sr.UnknownValueError:
                    # Normal silence or unrecognized audio — skip silently
                    pass
                except sr.RequestError:
                    now = time.time()
                    if now - last_error_time > 10:
                        print(json.dumps({
                            "type": "WARN",
                            "msg": "Network connectivity check required for cloud voice recognition. Retrying in background..."
                        }))
                        sys.stdout.flush()
                        last_error_time = now
                    time.sleep(2)
                except Exception as e:
                    print(json.dumps({"type": "ERROR", "msg": str(e)}))
                    sys.stdout.flush()
                    time.sleep(1)

    except OSError as e:
        print(json.dumps({
            "type": "ERROR",
            "msg": f"MICROPHONE_ERROR: {str(e)}. Check microphone permissions/connection."
        }))
        sys.stdout.flush()
        sys.exit(1)

if __name__ == "__main__":
    try:
        listen_for_dev()
    except KeyboardInterrupt:
        sys.exit(0)
