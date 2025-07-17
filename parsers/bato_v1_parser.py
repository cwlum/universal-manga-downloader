import re
import json
from .base_parser import BaseParser

class BatoV1Parser(BaseParser):
    """
    Parser for the older Bato.to page structure that uses 'astro-island'
    to store image information.
    """

    @staticmethod
    def get_name():
        return "Bato_V1"

    @staticmethod
    def can_parse(soup, url):
        """Check for the presence of the astro-island component."""
        return soup.find('astro-island', {'component-url': re.compile(r'ImageList')}) is not None

    @staticmethod
    def parse(soup, url):
        """Extracts data from the astro-island component."""
        try:
            # --- Title and Chapter ---
            title_tag = soup.find('a', href=re.compile(r'/title/\d+'))
            chapter_info = soup.find('h6', class_='text-lg')

            if not title_tag or not chapter_info:
                return None

            title = BatoV1Parser.sanitize_filename(title_tag.text.strip())
            chapter = BatoV1Parser.sanitize_filename(chapter_info.text.strip())

            # --- Image URLs ---
            astro_island = soup.find('astro-island', {'component-url': re.compile(r'ImageList')})
            props_str = astro_island.get('props', '{}')
            props_json = json.loads(props_str.replace('"', '"'))
            image_files_str = props_json.get('imageFiles', [0, '[]'])[1]
            image_urls = [img[1] for img in json.loads(image_files_str)]

            if not image_urls:
                return None

            return {
                'title': title,
                'chapter': chapter,
                'image_urls': image_urls
            }
        except (AttributeError, json.JSONDecodeError, IndexError) as e:
            print(f"[{BatoV1Parser.get_name()}] Parsing failed: {e}")
            return None
