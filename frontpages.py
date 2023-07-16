import os
import yaml
from flask import Flask, send_file
from flask_caching import Cache
import requests
from pdf2image import convert_from_bytes
from itertools import cycle
from PIL import Image
from io import BytesIO

# Load configuration from YAML file
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

app = Flask(__name__)
pdfs = cycle(config['pdfs'])
MAX_WIDTH = config['max_width']
MAX_HEIGHT = config['max_height']

if config['cache_enabled'] == True:
    cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': config['cache_timeout']})


def resize_image(image, max_height, max_width):
    # Calculate the ratio to maintain aspect ratio
    ratio = min(max_width/image.width, max_height/image.height)
    
    # Calculate the new width and height
    new_width = int(image.width * ratio)
    new_height = int(image.height * ratio)
    
    # Resize the image
    image = image.resize((new_width, new_height), Image.ANTIALIAS)

    return image

@app.route('/')
def home():
    pdf_config = next(pdfs)
    pdf_url = pdf_config['url']
    crop_params = pdf_config.get('crop') 
    img_filename = f'{os.path.basename(pdf_url)}.png'

    # Get the image if it exists in cache
    if config['cache_enabled'] == True:
        cached_image_data = cache.get(img_filename)
    else:
        cached_image_data = None

    # if image doesn't exist in cache, download and convert pdf
    if cached_image_data is None:
        response = requests.get(pdf_url)
        PDF_BYTES = response.content

        image = convert_from_bytes(PDF_BYTES, dpi=config['dpi'], first_page=1, last_page=1)[0]

        # Apply cropping if crop parameters are specified
        if crop_params is not None:
            image = image.crop((
                crop_params['left_edge'], 
                crop_params['top_edge'], 
                image.width - crop_params['right_edge'],
                image.height - crop_params['bottom_edge']
            ))

        # Resize the image
        image = resize_image(image, MAX_HEIGHT, MAX_WIDTH)

        # Save the final image to in-memory file
        image_file = BytesIO()
        image.save(image_file, 'PNG')
        image_file.seek(0)  # Move cursor back to beginning of file

        # Add the image to cache
        if config['cache_enabled'] == True:
            cache.set(img_filename, image_file)

    else:
        image_file = cached_image_data

    return send_file(image_file, mimetype='image/png')

if __name__ == '__main__':
    app.run(host='0.0.0.0')
