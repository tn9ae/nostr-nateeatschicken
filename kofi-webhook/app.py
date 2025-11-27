#!/usr/bin/env python3
import json
import logging
import os

from flask import Flask, request

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)


def verify_token(payload: dict) -> bool:
    expected = os.getenv("KOFI_VERIFICATION_TOKEN")
    if not expected:
        return True
    return payload.get("verification_token") == expected


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


@app.post("/kofi-webhook")
def kofi_webhook():
    payload = None

    if request.form:
        form_payload = request.form.get("data")
        if form_payload:
            try:
                payload = json.loads(form_payload)
                logging.debug("Ko-fi payload (form): %s", form_payload)
            except json.JSONDecodeError:
                logging.error("Failed to decode Ko-fi form payload: %s", form_payload)

    if payload is None:
        payload = request.get_json(silent=True)
        if payload is not None:
            logging.debug("Ko-fi payload (json): %s", json.dumps(payload))

    if not isinstance(payload, dict):
        raw_body = request.get_data(as_text=True)
        logging.error("Unable to parse Ko-fi payload, body=%s", raw_body)
        return "ok", 200

    if not verify_token(payload):
        return "forbidden", 403

    log_payload_summary(payload)

    log_path = os.path.join(os.path.dirname(__file__), "kofi_events.log")
    try:
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(payload))
            log_file.write("\n")
    except Exception:
        logging.exception("Failed to write Ko-fi payload to log file")

    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
