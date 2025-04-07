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
from PIL import Image
from typing import List, Optional, Dict, Union
from zoneinfo import ZoneInfo
from config import CropConfig, PdfConfig, ImageConfig, RefreshSchedulerConfig, Config


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
    image: Image.Image,
    crop_params: Optional[CropConfig],
    max_height: int,
    max_width: int,
) -> Image.Image:
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
        (int(image.width * ratio), int(image.height * ratio)), Image.LANCZOS
    )

    return image


def process_pdf(pdf_config: PdfConfig) -> None:
    newspaper = str(pdf_config.newspaper)
    img_filename = f"{newspaper}.png"
    
    # Try with current date and go backward up to max_lookback_days if needed
    current_date = datetime.now(tz=ZoneInfo('America/Los_Angeles'))
    max_lookback_days = config.source.max_lookback_days
    
    for days_ago in range(max_lookback_days):
        date = current_date - timedelta(days=days_ago)
        if fetch_newspaper_for_date(newspaper, date, img_filename, pdf_config):
            return  # Success, exit the function
    
    # If we get here, all attempts failed
    logging.error(f"Could not fetch {newspaper} front page after {max_lookback_days} attempts")


def fetch_newspaper_for_date(newspaper: str, date: datetime, img_filename: str, pdf_config: PdfConfig) -> bool:
    """
    Attempts to fetch and process newspaper front page for a specific date.
    Returns True if successful, False otherwise.
    """
    date_str = date.strftime("%Y-%m-%d")
    pdf_url = f"{config.source.base_url}/{newspaper}/{date_str}/{config.source.pdf_slug}"

    logging.info(f"Fetching {pdf_url}...")

    try:
        # Grab and convert the PDF to an image
        response = requests.get(pdf_url)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        
        PDF_BYTES = response.content
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

        logging.info(f"Successfully fetched {pdf_url}")
        return True
        
    except Exception as e:
        logging.warning(f"Failed to fetch {pdf_url}: {e}")
        return False


def fetch_newspapers() -> None:
    delay = get_delay(config.refresh_scheduler.time, config.refresh_scheduler.timezone)
    logging.info(f"Refresh scheduled {delay} seconds from now...")
    threading.Timer(delay, fetch_newspapers).start()

    for pdf_config in config.pdfs:
        process_pdf(pdf_config)


@app.route("/")
def home() -> Union[str, bytes]:
    pdf_config = next(pdfs)
    img_filename = f"{pdf_config.newspaper}.png"
    image_copy = BytesIO(cache[img_filename].getbuffer())
    return send_file(image_copy, mimetype="image/png")


if __name__ == "__main__":
    fetch_newspapers()
    app.run(host=str(config.web.host), port=config.web.port)
