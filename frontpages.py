import os
import yaml
import logging
import requests
from pdf2image import convert_from_bytes
from itertools import cycle
from PIL import Image
from io import BytesIO
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time
import threading
from flask import Flask, send_file

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


def crop_image(image, crop_params):
    if crop_params is not None:
        left_edge = crop_params["left_edge"] * image.width
        top_edge = crop_params["top_edge"] * image.height
        right_edge = image.width - (crop_params["right_edge"] * image.width)
        bottom_edge = image.height - \
            (crop_params["bottom_edge"] * image.height)
        image = image.crop((left_edge, top_edge, right_edge, bottom_edge))
    return image


def resize_image(image, max_height, max_width):
    ratio = min(max_width / image.width, max_height / image.height)
    new_width, new_height = int(image.width * ratio), int(image.height * ratio)
    return image.resize((new_width, new_height), Image.LANCZOS)


def fetch_newspapers():
    delay = get_delay(config["refresh_scheduler"]["time"],
                      config["refresh_scheduler"]["timezone"])
    threading.Timer(delay, fetch_newspapers).start()

    for pdf_config in config["pdfs"]:
        pdf_url = pdf_config["url"]
        img_filename = f"{os.path.basename(pdf_url)}.png"

        logging.info(f"Fetching {pdf_url}...")

        # Grab and convert the PDF to an image
        PDF_BYTES = requests.get(pdf_url).content
        image = convert_from_bytes(
            PDF_BYTES, dpi=config["image"]["dpi"], first_page=1, last_page=1
        )[0]

        image = crop_image(image, pdf_config.get("crop"))
        image = resize_image(
            image, config["image"]["max_height"], config["image"]["max_width"])

        # Save image to in-memory file
        image_file = BytesIO()
        image.save(image_file, "PNG")
        image_file.seek(0)

        # Add image to cache
        cache[img_filename] = image_file

        logging.info(f"Finished fetching {pdf_url}")


@app.route("/")
def home():
    pdf_config = next(pdfs)
    pdf_url = pdf_config["url"]
    img_filename = f"{os.path.basename(pdf_url)}.png"
    image_file = cache[img_filename]
    image_copy = BytesIO(image_file.getbuffer())
    return send_file(image_copy, mimetype="image/png")


if __name__ == "__main__":
    fetch_newspapers()
    app.run(host=config["web"]["host"], port=config["web"]["port"])
