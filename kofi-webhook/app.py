#!/usr/bin/env python3
import json
import logging
import os
from pathlib import Path

from flask import Flask, request

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
LOG_PATH = Path(__file__).with_name("kofi_events.log")


def verify_token(payload: dict) -> bool:
    expected = os.getenv("KOFI_VERIFICATION_TOKEN")
    if not expected:
        return True
    payload = payload or {}
    incoming_token = (
        request.headers.get("X-Ko-Fi-Verification-Token")
        or payload.get("verification_token")
        or request.form.get("verification_token")
    )
    if incoming_token != expected:
        logging.warning("Invalid Ko-fi verification token")
        return False
    return True


def truncate_message(message: str, limit: int = 120) -> str:
    if not message:
        return ""
    if len(message) <= limit:
        return message
    return f"{message[: limit - 3]}..."


def log_payload_summary(payload: dict) -> None:
    event_type = payload.get("type") or payload.get("event")
    from_name = payload.get("from_name")
    tier_or_product = (
        payload.get("tier_name")
        or payload.get("shop_item")
        or payload.get("product_name")
        or payload.get("product")
    )

    amount = payload.get("amount")
    currency = payload.get("currency")
    amount_summary = "-"
    if amount is not None or currency:
        parts = []
        if amount is not None:
            parts.append(str(amount))
        if currency:
            parts.append(str(currency))
        amount_summary = " ".join(parts)

    message_summary = truncate_message(payload.get("message", ""))

    logging.info(
        "Ko-fi event=%s from=%s amount=%s message=%s tier_or_product=%s",
        event_type or "-",
        from_name or "-",
        amount_summary,
        message_summary or "-",
        tier_or_product or "-",
    )


@app.route("/kofi-webhook", methods=["POST"])
def kofi_webhook():
    payload = None

    if request.is_json:
        payload = request.get_json(silent=True)
        if payload is not None:
            logging.debug("Ko-fi payload (json): %s", json.dumps(payload))
    else:
        raw_data = request.form.get("data")
        if raw_data:
            try:
                payload = json.loads(raw_data)
                logging.debug("Ko-fi payload (form): %s", raw_data)
            except Exception as exc:  # noqa: BLE001
                logging.error("Failed to parse Ko-fi form data JSON: %s", exc)

    if payload is None:
        raw_body = request.get_data(as_text=True)
        logging.debug("Ko-fi payload (raw): %s", raw_body)
        logging.error("Unable to parse Ko-fi payload, body=%s", raw_body)
        payload = {"raw_body": raw_body}

    if not verify_token(payload):
        return "", 403

    log_payload_summary(payload)

    try:
        with LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(payload))
            log_file.write("\n")
    except Exception as exc:  # noqa: BLE001
        logging.error("Failed to write Ko-fi event to log file: %s", exc)

    return "", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
