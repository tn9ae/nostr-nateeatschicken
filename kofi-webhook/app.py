import json
import logging
from pathlib import Path

from flask import Flask, request

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

LOG_PATH = Path(__file__).with_name("kofi_events.log")


@app.route("/kofi-webhook", methods=["POST"])
def kofi_webhook():
    # Capture as much info as possible about the incoming request
    json_body = request.get_json(silent=True)
    form_data = request.form.to_dict(flat=False)
    raw_body = request.get_data(as_text=True)
    headers = {k: v for k, v in request.headers.items()}

    payload = {
        "remote_addr": request.remote_addr,
        "method": request.method,
        "path": request.path,
        "content_type": request.content_type,
        "headers": headers,
        "form": form_data,
        "json": json_body,
        "raw_body": raw_body,
    }

    logging.info("Ko-fi webhook received: content_type=%s", request.content_type)

    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
        logging.info("Appended webhook payload to %s", LOG_PATH)
    except Exception as e:
        logging.error("Failed to write webhook payload to %s: %s", LOG_PATH, e)

    # Always return 200 for now so Ko-fi doesn't keep retrying
    return "", 200


if __name__ == "__main__":
    # Bind to all interfaces so Caddy can reach us
    app.run(host="0.0.0.0", port=5000)
