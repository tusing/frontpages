import yaml
from flask import Flask, send_file
import requests
import os
import datetime
from pdf2image import convert_from_path
from itertools import cycle
from PIL import Image

app = Flask(__name__)
app.run(host='0.0.0.0')

# Load configuration from YAML file
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

pdfs = cycle(config['pdfs'])
PDF_PATH = 'tmp.pdf'

MAX_WIDTH = config['max_width']
MAX_HEIGHT = config['max_height']

def get_cache_folder():
    date_str = datetime.datetime.now().strftime('%Y%m%d')
    folder_path = os.path.join('cache', date_str)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

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
    crop_params = pdf_config.get('crop')  # Use .get() to allow None if 'crop' key does not exist
    img_filename = f'{os.path.basename(pdf_url)}.png'
    cache_folder = get_cache_folder()
    img_path = os.path.join(cache_folder, img_filename)

    # if image doesn't exist in cache, download and convert pdf
    if not os.path.exists(img_path):
        response = requests.get(pdf_url)
        with open(PDF_PATH, 'wb') as f:
            f.write(response.content)

        image = convert_from_path(PDF_PATH, dpi=config['dpi'], first_page=1, last_page=1)[0]

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

        # Save the final image to disk
        image.save(img_path, 'PNG')

    return send_file(img_path, mimetype='image/png')
