#!/usr/bin/env python3
import json
import logging
import os

from flask import Flask, request

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)


def verify_token() -> bool:
    expected = os.getenv("KOFI_WEBHOOK_TOKEN")
    if not expected:
        return True
    provided = request.headers.get("X-Ko-Fi-Token")
    return provided == expected


@app.post("/kofi-webhook")
def kofi_webhook():
    if not verify_token():
        return "forbidden", 403

    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
        logging.info("Ko-fi payload (raw): %s", request.get_data(as_text=True))
    else:
        logging.info("Ko-fi payload: %s", json.dumps(payload))

    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
