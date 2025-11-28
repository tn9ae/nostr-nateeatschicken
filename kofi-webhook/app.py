import json
import logging
import os
import re
import subprocess
from pathlib import Path

from flask import Flask, request

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

LOG_PATH = Path(__file__).with_name("kofi_events.log")
PRODUCT_MAP = {
    # Ko-fi direct_link_code -> internal action key
    "2d36c00264": "nostr_handle",  # Nostr handle product (update if needed)
    # "OTHER_CODE_HERE": "relay_power",
}


def parse_handle_and_pubkey_from_message(message: str):
    """
    Parse 'handle' and a 64-char hex pubkey from Ko-fi message text.

    Expected patterns, in any order:
      handle: myname
      hexpub: 64_hex_characters

    Returns (handle, hex_pubkey) or (None, None) if not found.
    """
    if not message:
        return None, None

    handle = None
    pubkey = None

    # case-insensitive 'handle: something'
    m = re.search(r"handle\s*:\s*([a-zA-Z0-9_.-]+)", message, re.IGNORECASE)
    if m:
        handle = m.group(1).lower()

    # 64-char hex pubkey
    m2 = re.search(r"\b([0-9a-fA-F]{64})\b", message)
    if m2:
        pubkey = m2.group(1).lower()

    return handle, pubkey


def extract_kofi_payload():
    """
    Returns (kofi_data, json_body, form_dict).

    - kofi_data: dict parsed from Ko-fi's JSON (either form["data"][0] or JSON body)
    - json_body: raw request JSON (if any)
    - form_dict: full form as dict(list)
    """
    json_body = request.get_json(silent=True) if request.is_json else None
    form_dict = request.form.to_dict(flat=False)

    kofi_data = None

    # Ko-fi's real webhooks: application/x-www-form-urlencoded with a 'data' field containing JSON
    if "data" in form_dict and form_dict["data"]:
        raw_data = form_dict["data"][0]
        try:
            kofi_data = json.loads(raw_data)
        except Exception as e:
            logging.error("Failed to parse Ko-fi form 'data' JSON: %s", e)

    # Fallback: for my local application/json tests
    if kofi_data is None and isinstance(json_body, dict):
        kofi_data = json_body

    return kofi_data, json_body, form_dict


@app.route("/kofi-webhook", methods=["POST"])
def kofi_webhook():
    kofi_data, json_body, form_dict = extract_kofi_payload()

    expected_token = os.environ.get("KOFI_VERIFICATION_TOKEN")
    incoming_token = None

    # Prefer token from parsed Ko-fi JSON
    if isinstance(kofi_data, dict):
        incoming_token = kofi_data.get("verification_token")

    # Fallbacks (for tests or other clients)
    if incoming_token is None:
        incoming_token = request.headers.get("X-Ko-Fi-Verification-Token")
    if incoming_token is None:
        incoming_token = request.form.get("verification_token")

    # Token check
    status = 200
    if expected_token and incoming_token != expected_token:
        logging.warning("Invalid Ko-fi verification token: got %r", incoming_token)
        status = 403

    # Extract some summary fields (best-effort)
    event_type = "-"
    from_name = "-"
    amount = "-"
    message = "-"
    tier_or_product = "-"

    if isinstance(kofi_data, dict):
        event_type = kofi_data.get("type") or "-"
        from_name = kofi_data.get("from_name") or "-"
        amount = kofi_data.get("amount") or "-"
        message = kofi_data.get("message") or "-"
        # Shop/tier info if present
        tier_or_product = (
            kofi_data.get("tier_name")
            or (
                (kofi_data.get("shop_items") or [{}])[0].get("item_name")
                if kofi_data.get("shop_items")
                else "-"
            )
        )

    logging.info(
        "Ko-fi event=%s from=%s amount=%s message=%s tier_or_product=%s status=%s",
        event_type,
        from_name,
        amount,
        message,
        tier_or_product,
        status,
    )

    actions_taken = []

    # Only act on valid, parsed Shop Orders
    if status == 200 and isinstance(kofi_data, dict) and kofi_data.get("type") == "Shop Order":
        shop_items = kofi_data.get("shop_items") or []
        message_text = kofi_data.get("message") or ""

        handle, pubkey = parse_handle_and_pubkey_from_message(message_text)

        for item in shop_items:
            code = item.get("direct_link_code")
            action = PRODUCT_MAP.get(code)

            if not action:
                logging.info("Ko-fi Shop item with unknown code %r, skipping", code)
                continue

            if action == "nostr_handle":
                if not handle or not pubkey:
                    logging.warning("Missing handle/pubkey in message for nostr_handle product; message=%r", message_text)
                    continue

                try:
                    result = subprocess.run(
                        ["python3", "manage_nip05.py", "add", "--name", handle, "--pubkey", pubkey],
                        cwd=Path(__file__).resolve().parents[1],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    logging.info(
                        "manage_nip05.py add success: handle=%s pubkey=%s stdout=%s",
                        handle,
                        pubkey,
                        result.stdout.strip(),
                    )
                    actions_taken.append(f"nip05:{handle}")
                except subprocess.CalledProcessError as e:
                    logging.error("manage_nip05.py failed: %s %s", e, e.stderr)

            elif action == "relay_power":
                # Placeholder for relay power user behaviour (e.g. manage_supporters.py add)
                if not pubkey:
                    logging.warning("Missing pubkey in message for relay_power product; message=%r", message_text)
                    continue

                try:
                    result = subprocess.run(
                        ["python3", "manage_supporters.py", "add", "--pubkey", pubkey],
                        cwd=Path(__file__).resolve().parents[1],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    logging.info(
                        "manage_supporters.py add success: pubkey=%s stdout=%s",
                        pubkey,
                        result.stdout.strip(),
                    )
                    actions_taken.append(f"relay:{pubkey}")
                except subprocess.CalledProcessError as e:
                    logging.error("manage_supporters.py failed: %s %s", e, e.stderr)

    # Log full structured info for debugging
    payload_to_log = {
        "remote_addr": request.remote_addr,
        "method": request.method,
        "path": request.path,
        "content_type": request.content_type,
        "headers": {k: v for k, v in request.headers.items()},
        "kofi_data": kofi_data,
        "json": json_body,
        "form": form_dict,
        "status": status,
        "actions_taken": actions_taken,
    }

    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload_to_log) + "\n")
    except Exception as e:
        logging.error("Failed to write Ko-fi event to %s: %s", LOG_PATH, e)

    return "", status


if __name__ == "__main__":
    # Bind to all interfaces so Caddy can reach us
    app.run(host="0.0.0.0", port=5000)
