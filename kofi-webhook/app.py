import os
import json
import logging
from pathlib import Path

from flask import Flask, request

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

LOG_PATH = Path(__file__).with_name("kofi_events.log")


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
