import json
import logging
import os
import re
import subprocess
from pathlib import Path

from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[1]
KOFI_LOG = REPO_ROOT / "kofi-webhook" / "kofi_events.log"
PRODUCT_MAP = {
    # Ko-fi direct_link_code -> internal action key
    "2d36c00264": "nostr_handle",  # Nostr handle product (update if needed)
    # "OTHER_CODE_HERE": "relay_power",
}
HANDLE_PRODUCT_CODES = {"2d36c00264"}  # direct_link_code for the Nostr handle product


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


def has_valid_shop_order(email: str) -> bool:
    """
    Return True if kofi_events.log contains at least one Shop Order
    for this email and a shop_items[*].direct_link_code in HANDLE_PRODUCT_CODES.
    On parse errors, log and keep going. If kofi_events.log doesn't exist, return False.
    """
    if not KOFI_LOG.exists():
        return False

    email_lower = (email or "").strip().lower()
    if not email_lower:
        return False

    try:
        with KOFI_LOG.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                except Exception as e:
                    logging.warning("Failed to parse log line in %s: %s", KOFI_LOG, e)
                    continue

                kdata = evt.get("kofi_data")
                if not isinstance(kdata, dict):
                    continue
                if kdata.get("type") != "Shop Order":
                    continue
                if (kdata.get("email") or "").strip().lower() != email_lower:
                    continue
                shop_items = kdata.get("shop_items") or []
                for item in shop_items:
                    code = item.get("direct_link_code")
                    if code in HANDLE_PRODUCT_CODES:
                        return True
    except Exception as e:
        logging.error("Error while scanning %s: %s", KOFI_LOG, e)

    return False


@app.route("/claim-handle", methods=["POST"])
def claim_handle():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "Invalid JSON body."}), 400

    email = (payload.get("email") or "").strip()
    handle = (payload.get("handle") or "").strip().lower()
    hexpub = (payload.get("hexpub") or "").strip().lower()

    if not email or not handle or not hexpub:
        return jsonify({"ok": False, "error": "Missing email/handle/hexpub"}), 400
    if not re.fullmatch(r"[0-9a-f]{64}", hexpub):
        return jsonify({"ok": False, "error": "Invalid hex pubkey"}), 400
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", handle):
        return jsonify({"ok": False, "error": "Handle is required and must be alphanumeric with ._-"}), 400

    has_order = has_valid_shop_order(email)
    if not has_order:
        logging.warning("No valid Ko-fi Shop Order found for email=%s", email)
        return jsonify({"ok": False, "error": "No valid Ko-fi order found for this email."}), 403

    try:
        nip05_res = subprocess.run(
            ["python3", "../manage_nip05.py", "claim", handle, hexpub],
            cwd=APP_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
        logging.info(
            "manage_nip05.py claim success: handle=%s hexpub=%s stdout=%s stderr=%s",
            handle,
            hexpub,
            nip05_res.stdout,
            nip05_res.stderr,
        )
    except subprocess.CalledProcessError as e:
        logging.error("manage_nip05.py claim failed: %s", e, exc_info=True)
        return jsonify({"ok": False, "error": "Failed to update NIP-05 mapping."}), 500

    try:
        supporters_res = subprocess.run(
            ["python3", "../manage_supporters.py", "add", hexpub],
            cwd=APP_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
        logging.info(
            "manage_supporters.py add success: hexpub=%s stdout=%s stderr=%s",
            hexpub,
            supporters_res.stdout,
            supporters_res.stderr,
        )
    except subprocess.CalledProcessError as e:
        logging.error(
            "manage_supporters.py add failed during claim: %s", e, exc_info=True
        )

    log_entry = {"claim": True, "email": email, "handle": handle, "hexpub": hexpub}
    try:
        KOFI_LOG.parent.mkdir(parents=True, exist_ok=True)
        with KOFI_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logging.error("Failed to record claim in %s: %s", KOFI_LOG, e)

    return jsonify({"ok": True, "handle": handle, "hexpub": hexpub}), 200


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
                        cwd=REPO_ROOT,
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
                        cwd=REPO_ROOT,
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
        KOFI_LOG.parent.mkdir(parents=True, exist_ok=True)
        with KOFI_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload_to_log) + "\n")
    except Exception as e:
        logging.error("Failed to write Ko-fi event to %s: %s", KOFI_LOG, e)

    return "", status


if __name__ == "__main__":
    # Bind to all interfaces so Caddy can reach us
    app.run(host="0.0.0.0", port=5000)
