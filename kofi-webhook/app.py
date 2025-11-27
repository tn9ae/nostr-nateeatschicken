import os
import json
import logging
from pathlib import Path

from flask import Flask, request

LOG_PATH = Path(__file__).with_name("kofi_events.log")

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)


@app.route("/kofi-webhook", methods=["POST"])
def kofi_webhook():
    expected_token = os.environ.get("KOFI_VERIFICATION_TOKEN")

    data_json = None
    incoming_token = None

    # Try JSON body first (for my own curl tests)
    if request.is_json:
        data_json = request.get_json(silent=True) or {}
        incoming_token = data_json.get("verification_token")

    # Ko-fi may send the token in form fields
    if incoming_token is None:
        incoming_token = request.form.get("verification_token")

    # Ko-fi also supports X-Ko-Fi-Verification-Token header
    if incoming_token is None:
        incoming_token = request.headers.get("X-Ko-Fi-Verification-Token")

    # Token check
    if expected_token and incoming_token != expected_token:
        logging.warning("Invalid Ko-fi verification token: got %r", incoming_token)
        # NOTE: Do NOT return here; we still want to log the payload for debugging
        # and return 200 so Ko-fi does not keep retrying.

    # Build payload
    payload = None

    # Use JSON if we already parsed it
    if data_json is not None:
        payload = data_json
    elif request.is_json:
        payload = request.get_json(silent=True)
    else:
        # Ko-fi real webhooks are usually form-encoded with a 'data' JSON field
        raw_data = request.form.get("data")
        if raw_data:
            try:
                payload = json.loads(raw_data)
            except Exception as e:
                logging.error("Failed to parse Ko-fi 'data' JSON: %s", e)

    if payload is None:
        # Fallback: just store the raw body so we can see what came in
        payload = {"raw_body": request.get_data(as_text=True)}

    # Extract some summary info, best-effort
    event_type = payload.get("type") or payload.get("type_of_thing") or "-"
    from_name = payload.get("from_name") or "-"
    amount = payload.get("amount") or payload.get("total") or "-"
    message = payload.get("message") or "-"
    tier_or_product = (
        payload.get("tier_name")
        or (payload.get("shop_item") or {}).get("item_name")
        or "-"
    )

    logging.info(
        "Ko-fi event=%s from=%s amount=%s message=%s tier_or_product=%s",
        event_type, from_name, amount, message, tier_or_product,
    )

    # Append full payload to log file
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
        logging.info("Wrote Ko-fi payload to %s", LOG_PATH)
    except Exception as e:
        logging.error("Failed to write Ko-fi event to %s: %s", LOG_PATH, e)

    return "", 200


if __name__ == "__main__":
    # Bind to all interfaces so Caddy can reach us
    app.run(host="0.0.0.0", port=5000)
