import logging
import os
import requests
import threading
import time
import yaml
from datetime import datetime, timedelta
from flask import Flask, send_file
from io import BytesIO
from itertools import cycle
from pdf2image import convert_from_bytes
from PIL import Image
from zoneinfo import ZoneInfo

# Load configuration from YAML file
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)
pdfs = cycle(config["pdfs"])

cache = {}
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


def get_delay(target_time, target_timezone):
    target_time_obj = datetime.strptime(target_time, "%H:%M").time()
    now = datetime.now(tz=ZoneInfo(target_timezone))
    target = datetime.combine(
        now.date(), target_time_obj, tzinfo=ZoneInfo(target_timezone)
    )

    if now.time() > target_time_obj:
        target += timedelta(days=1)

    delay = (target - now).total_seconds()
    return delay


def crop_and_resize_image(image, crop_params, max_height, max_width):
    if crop_params:
        image = image.crop(
            (
                crop_params["left_edge"] * image.width,
                crop_params["top_edge"] * image.height,
                image.width - (crop_params["right_edge"] * image.width),
                image.height - (crop_params["bottom_edge"] * image.height),
            )
        )

    ratio = min(max_width / image.width, max_height / image.height)
    image = image.resize(
        (int(image.width * ratio), int(image.height * ratio)), Image.LANCZOS
    )

    return image


def process_pdf(pdf_config):
    pdf_url = pdf_config["url"]
    img_filename = f"{os.path.basename(pdf_url)}.png"

    logging.info(f"Fetching {pdf_url}...")

    # Grab and convert the PDF to an image
    PDF_BYTES = requests.get(pdf_url).content
    image = convert_from_bytes(
        PDF_BYTES, dpi=config["image"]["dpi"], first_page=1, last_page=1
    )[0]

    image = crop_and_resize_image(
        image,
        pdf_config.get("crop"),
        config["image"]["max_height"],
        config["image"]["max_width"],
    )

    # Save image to in-memory file
    image_file = BytesIO()
    image.save(image_file, "PNG")
    image_file.seek(0)

    # Add image to cache
    cache[img_filename] = image_file

    logging.info(f"Finished fetching {pdf_url}")


def fetch_newspapers():
    delay = get_delay(
        config["refresh_scheduler"]["time"], config["refresh_scheduler"]["timezone"]
    )
    logging.info(f"Refresh scheduled {delay} seconds from now...")
    threading.Timer(delay, fetch_newspapers).start()

    for pdf_config in config["pdfs"]:
        process_pdf(pdf_config)


@app.route("/")
def home():
    pdf_config = next(pdfs)
    img_filename = f"{os.path.basename(pdf_config['url'])}.png"
    image_copy = BytesIO(cache[img_filename].getbuffer())
    return send_file(image_copy, mimetype="image/png")


if __name__ == "__main__":
    fetch_newspapers()
    app.run(host=config["web"]["host"], port=config["web"]["port"])
