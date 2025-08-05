import re
import json
from .base_parser import BaseParser

class ComickParser(BaseParser):
    """
    Parser for comick.fun.
    """

    @staticmethod
    def get_name():
        return "Comick"

    @staticmethod
    def can_parse(soup, url):
        """Check if the URL is from comick.fun."""
        return "comick.fun" in url

    @staticmethod
    def parse(soup, url):
        """Extracts data from the page."""
        try:
            script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
            if not script_tag:
                return None

            json_data = json.loads(script_tag.string)
            chapter_data = json_data.get('props', {}).get('pageProps', {}).get('chapter', {})
            
            if not chapter_data:
                return None

            title = ComickParser.sanitize_filename(chapter_data.get('md_comics', {}).get('title', ''))
            chapter = ComickParser.sanitize_filename(chapter_data.get('chap', ''))
            
            image_urls = []
            for image in chapter_data.get('md_images', []):
                image_urls.append(f"https://meo.comick.pictures/{image.get('b2key')}")

            if not title or not chapter or not image_urls:
                return None

            return {
                'title': title,
                'chapter': chapter,
                'image_urls': image_urls
            }
        except (AttributeError, json.JSONDecodeError, IndexError) as e:
            print(f"[{ComickParser.get_name()}] Parsing failed: {e}")
            return None
