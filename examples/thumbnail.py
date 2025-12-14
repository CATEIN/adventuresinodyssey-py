import sys
import requests
import os
from urllib.parse import urlparse
from adventuresinodyssey import AIOClient

def download_aio_thumbnail():
    """Fetches AIO content data and downloads the large thumbnail, using the original filename."""
    if len(sys.argv) < 2:
        print("Usage: python download.py <URL>")
        sys.exit(1)

    url = sys.argv[1]
    content_id = os.path.basename(urlparse(url).path)

    if not content_id:
        print("Error: Could not extract content ID from URL.")
        sys.exit(1)

    try:
        client = AIOClient()
        data = client.fetch_content(content_id)
        thumbnail_url = data.get("thumbnail_large")

        if not thumbnail_url:
            print(f"Error: Thumbnail URL not found for ID: {content_id}")
            return

        parsed_url = urlparse(thumbnail_url)
        filename = os.path.basename(parsed_url.path)
        
        if not filename or '.' not in filename:
            filename = f"aio_thumbnail_{content_id}.jpg"
        
        img_response = requests.get(thumbnail_url, timeout=15)
        img_response.raise_for_status() 

        with open(filename, 'wb') as f:
            f.write(img_response.content)

        print(f"Thumbnail saved as {filename}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    try:
        download_aio_thumbnail()
    except ImportError:
        print("\n--- Setup Error ---")
        print("Make sure you have 'requests' and 'adventuresinodyssey' installed.")