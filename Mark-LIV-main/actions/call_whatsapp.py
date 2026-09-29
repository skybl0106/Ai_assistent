import time

from actions.computer_control import computer_control
from actions.send_message import _PYAUTOGUI, _open_app, _search_in_app


def call_whatsapp(parameters: dict, player=None) -> str:
    receiver = str((parameters or {}).get("receiver", "")).strip()
    if not receiver:
        return "Please specify the WhatsApp contact to call."
    if not _PYAUTOGUI:
        return "PyAutoGUI is not installed; cannot control WhatsApp."
    if not _open_app("WhatsApp"):
        return "Could not open WhatsApp."

    time.sleep(1.0)
    _search_in_app(receiver)
    safe_receiver = " ".join(receiver.replace("'", "").split())
    selected = computer_control({
        "action": "screen_click",
        "description": (
            "the WhatsApp search result whose visible contact name exactly "
            f"matches {safe_receiver!r}; do not select a different contact"
        ),
    })
    if not selected.startswith("Clicked "):
        return f"Could not find the WhatsApp contact '{receiver}'. No call was placed."

    time.sleep(1.0)
    call_button = computer_control({
        "action": "screen_click",
        "description": (
            "the telephone handset voice-call button in the header of the open "
            f"WhatsApp chat with {safe_receiver!r}; do not click the video-call button"
        ),
    })
    if not call_button.startswith("Clicked "):
        return f"Could not find the voice-call button for '{receiver}'. No call was placed."

    if player:
        player.write_log(f"[call] WhatsApp voice call started for {receiver}")
    return f"Started a WhatsApp voice call to {receiver}. Check WhatsApp for the connection status."


TOOL = {
    "name": "call_whatsapp",
    "description": (
        "Starts a WhatsApp voice call to a contact. Use only when the user asks "
        "to call someone on WhatsApp. This does not place video calls or send messages."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "receiver": {
                "type": "STRING",
                "description": "Exact WhatsApp contact name to call",
            },
        },
        "required": ["receiver"],
    },
    "handler": call_whatsapp,
}
