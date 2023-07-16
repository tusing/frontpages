# Frontpages

![frontpages](https://github.com/tusing/frontpages/assets/1077203/0605d3c5-9fdd-4acf-8d51-0e1ba8e014da)

Frontpages is a web server designed to fetch the front pages of various newspapers, convert them into images suitable for e-ink displays, and serve them through a Flask application. This is ideal for use with displays like the Visionect 32" e-ink display.

The server retrieves PDF versions of the newspaper front pages from specified URLs, crops them based on provided parameters, resizes them to fit the display, and then serves them in a round-robin fashion.

## Configuration

The server is configured through a YAML file, `config.yaml`, with the following structure:

```yaml
pdfs:
  - url: 'https://cdn.freedomforum.org/dfp/pdf15/NY_NYT.pdf'  # The URL to the newspaper's front page in PDF format
    crop:  # [optional] Parameters to crop the PDF
      left_edge: 0.02  # Crop the left edge by 2% of the total width
      right_edge: 0.02  # Crop the right edge by 2% of the total width
      top_edge: 0.022  # Crop the top edge by 2.2% of the total height
      bottom_edge: 0.03  # Crop the bottom edge by 3% of the total height
  # More newspapers...

host: "0.0.0.0" # Run on all addresses, set to 127.0.0.1 for localhost-only
port: 5001 # The port to run the web-server on
cache_enabled: True  # Enable in-memory caching of images (~3MB/newspaper)
cache_timeout: 14400  # Cache timeout in seconds - here, images are cached for 4 hours
dpi: 300  # Resolution for the PDF to image conversion
max_width: 1440  # The maximum width of the image
max_height: 2560  # The maximum height of the image
```

## Running the server

### With Nix

If you have [Nix](https://nixos.org) installed, you can use the following command to run the server:

```bash
nix run
```

### Without Nix

If you don't have Nix installed, you will need to install the required dependencies manually. These can be installed using pip with the requirements.txt file.

```bash
pip install -r requirements.txt
```

Once the dependencies are installed, you can run the server with the following command:

```bash
python3 frontpages.py
```

## Accessing the front pages

Once the server is running, you can access the front pages by opening a web browser and navigating to `http://localhost:5000/`.
