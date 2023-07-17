import logging
import os
import requests
import threading
import yaml
from datetime import datetime, timedelta
from flask import Flask, send_file
from io import BytesIO
from itertools import cycle
from pdf2image import convert_from_bytes
from PIL import Image as PILImage
from typing import List, Optional, Dict, Union
from zoneinfo import ZoneInfo
from pydantic import BaseModel, Field
from typing import List


class Crop(BaseModel):
    left_edge: float
    right_edge: float
    top_edge: float
    bottom_edge: float


class Pdf(BaseModel):
    url: str
    crop: Crop


class Web(BaseModel):
    host: str
    port: int


class Image(BaseModel):
    dpi: int
    max_width: int
    max_height: int


class RefreshScheduler(BaseModel):
    time: str
    timezone: str


class Config(BaseModel):
    pdfs: List[Pdf]
    web: Web
    image: Image
    refresh_scheduler: RefreshScheduler


# Load configuration from YAML file
with open("config.yaml", "r") as f:
    data = yaml.safe_load(f)
    config = Config(**data)

pdfs = cycle(config.pdfs)
cache: Dict[str, BytesIO] = {}
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


def get_delay(target_time: str, target_timezone: str) -> float:
    target_time_obj = datetime.strptime(target_time, "%H:%M").time()
    now = datetime.now(tz=ZoneInfo(target_timezone))
    target = datetime.combine(
        now.date(), target_time_obj, tzinfo=ZoneInfo(target_timezone)
    )

    if now.time() > target_time_obj:
        target += timedelta(days=1)

    delay = (target - now).total_seconds()
    return delay


def crop_and_resize_image(
    image: PILImage.Image,
    crop_params: Optional[Crop],
    max_height: int,
    max_width: int,
) -> PILImage.Image:
    if crop_params:
        image = image.crop(
            (
                crop_params.left_edge * image.width,
                crop_params.top_edge * image.height,
                image.width - (crop_params.right_edge * image.width),
                image.height - (crop_params.bottom_edge * image.height),
            )
        )

    ratio = min(max_width / image.width, max_height / image.height)
    image = image.resize(
        (int(image.width * ratio), int(image.height * ratio)), PILImage.LANCZOS
    )

    return image


def process_pdf(pdf_config: Pdf) -> None:
    pdf_url = pdf_config.url
    img_filename = f"{os.path.basename(pdf_url)}.png"

    logging.info(f"Fetching {pdf_url}...")

    # Grab and convert the PDF to an image
    PDF_BYTES = requests.get(pdf_url).content
    image = convert_from_bytes(
        PDF_BYTES, dpi=config.image.dpi, first_page=1, last_page=1
    )[0]

    image = crop_and_resize_image(
        image,
        pdf_config.crop,
        config.image.max_height,
        config.image.max_width,
    )

    # Save image to in-memory file
    image_file = BytesIO()
    image.save(image_file, "PNG")
    image_file.seek(0)

    # Add image to cache
    cache[img_filename] = image_file

    logging.info(f"Finished fetching {pdf_url}")


def fetch_newspapers() -> None:
    delay = get_delay(config.refresh_scheduler.time, config.refresh_scheduler.timezone)
    logging.info(f"Refresh scheduled {delay} seconds from now...")
    threading.Timer(delay, fetch_newspapers).start()

    for pdf_config in config.pdfs:
        process_pdf(pdf_config)


@app.route("/")
def home() -> Union[str, bytes]:
    pdf_config = next(pdfs)
    img_filename = f"{os.path.basename(pdf_config.url)}.png"
    image_copy = BytesIO(cache[img_filename].getbuffer())
    return send_file(image_copy, mimetype="image/png")


if __name__ == "__main__":
    fetch_newspapers()
    app.run(host=config.web.host, port=config.web.port)
