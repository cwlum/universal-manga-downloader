import json
import os
import re
import sys

try:
    from .base_parser import BaseParser
except ImportError:  # Allow running the module directly for debugging
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from base_parser import BaseParser


class BatoV3Parser(BaseParser):
    """
    Parser for the new Bato.si page structure that uses a Qwik framework
    and embeds data in a <script type="qwik/json"> tag.
    """

    _TOKEN_PATTERN = re.compile(r"^[0-9a-z]+$")

    @staticmethod
    def get_name():
        return "Bato_V3"

    @staticmethod
    def can_parse(soup, url):
        """Check for the presence of the qwik/json script tag."""
        return soup.find('script', {'type': 'qwik/json'}) is not None

    @staticmethod
    def _resolve(value, objs, cache):
        """Resolve Qwik token references into concrete Python values."""
        if isinstance(value, str):
            cached = cache.get(value)
            if cached is not None:
                return cached

            if BatoV3Parser._TOKEN_PATTERN.match(value):
                try:
                    index = int(value, 36)
                except ValueError:
                    cache[value] = value
                    return value

                if 0 <= index < len(objs):
                    resolved = objs[index]
                    if resolved == value:
                        cache[value] = resolved
                        return resolved
                    result = BatoV3Parser._resolve(resolved, objs, cache)
                    cache[value] = result
                    return result

            cache[value] = value
            return value

        if isinstance(value, list):
            return [BatoV3Parser._resolve(item, objs, cache) for item in value]

        if isinstance(value, dict):
            return {key: BatoV3Parser._resolve(val, objs, cache) for key, val in value.items()}

        return value

    @staticmethod
    def parse(soup, url):
        """Extracts data from the qwik/json script tag."""
        try:
            script_tag = soup.find('script', {'type': 'qwik/json'})
            if not script_tag:
                return None

            data = json.loads(script_tag.string)
            objs = data.get('objs', [])
            if not isinstance(objs, list):
                return None

            cache = {}
            chapter_state = next(
                (
                    obj for obj in objs
                    if isinstance(obj, dict) and obj.get('chapterData') and obj.get('comicData')
                ),
                None,
            )

            if not chapter_state:
                return None

            chapter_data = BatoV3Parser._resolve(chapter_state.get('chapterData'), objs, cache)
            comic_data = BatoV3Parser._resolve(chapter_state.get('comicData'), objs, cache)

            if not isinstance(chapter_data, dict) or not isinstance(comic_data, dict):
                return None

            image_file = BatoV3Parser._resolve(chapter_data.get('imageFile'), objs, cache)
            if isinstance(image_file, dict):
                image_urls = BatoV3Parser._resolve(image_file.get('urlList'), objs, cache)
            else:
                image_urls = BatoV3Parser._resolve(image_file, objs, cache)

            if not image_urls or not isinstance(image_urls, list):
                return None

            image_urls = [url for url in image_urls if isinstance(url, str) and url]
            if not image_urls:
                return None

            title = comic_data.get('name') or comic_data.get('title') or 'Manga'
            chapter = chapter_data.get('dname') or chapter_data.get('title') or 'Chapter'

            return {
                'title': BatoV3Parser.sanitize_filename(title),
                'chapter': BatoV3Parser.sanitize_filename(chapter),
                'image_urls': image_urls,
            }
        except (AttributeError, json.JSONDecodeError, IndexError, KeyError) as e:
            print(f"[{BatoV3Parser.get_name()}] Parsing failed: {e}")
            return None
