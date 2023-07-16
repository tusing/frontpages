import os
import yaml
from flask import Flask, send_file
from flask_caching import Cache
import requests
from pdf2image import convert_from_bytes
from itertools import cycle
from PIL import Image
from io import BytesIO

app = Flask(__name__)

# Load configuration from YAML file
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

pdfs = cycle(config['pdfs'])
MAX_WIDTH, MAX_HEIGHT = config['max_width'], config['max_height']

cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': config['cache_timeout']}) if config.get('cache_enabled') else None

def resize_image(image, max_height, max_width):
    ratio = min(max_width/image.width, max_height/image.height)
    new_width, new_height = int(image.width * ratio), int(image.height * ratio)
    return image.resize((new_width, new_height), Image.ANTIALIAS)

@app.route('/')
def home():
    pdf_config = next(pdfs)
    pdf_url = pdf_config['url']
    img_filename = f'{os.path.basename(pdf_url)}.png'

    # Check if image exists in cache
    image_file = cache.get(img_filename) if cache else None

    if image_file is None:
        PDF_BYTES = requests.get(pdf_url).content
        image = convert_from_bytes(PDF_BYTES, dpi=config['dpi'], first_page=1, last_page=1)[0]

        # Apply cropping if parameters specified
        if crop_params := pdf_config.get('crop'):
            image = image.crop((
                crop_params['left_edge'], 
                crop_params['top_edge'], 
                image.width - crop_params['right_edge'],
                image.height - crop_params['bottom_edge']
            ))

        # Resize the image
        image = resize_image(image, MAX_HEIGHT, MAX_WIDTH)

        # Save image to in-memory file
        image_file = BytesIO()
        image.save(image_file, 'PNG')
        image_file.seek(0)  # Move cursor back to start of file

        # Add image to cache
        if cache:
            cache.set(img_filename, image_file)

    return send_file(image_file, mimetype='image/png')

if __name__ == '__main__':
    app.run(host='0.0.0.0')
