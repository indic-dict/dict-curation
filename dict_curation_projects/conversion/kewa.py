import os, regex

from curation_utils import scraping
from dict_curation.babylon import header_helper
from dict_curation import babylon
from dict_curation.scrape import dump_babylon, dump_babylon_parallel
from doc_curation.scraping.html_scraper import souper
from urllib.parse import urljoin
from dict_curation import Definition
import logging


source_dir = "/home/vvasuki/sanskrit/samskrtam.ru/backup/sanskrit-lexicon/KEWA"
dest_dir = "/home/vvasuki/indic-dict/stardict_all/stardict-sanskrit/sa-head/en-entries/mayrhofer"


def dump_babylon():
  soup = scraping.get_soup(os.path.join(source_dir, "index.html"))
  rows = soup.select("table")[-1].select("tr")
  definitions = []
  missing_texts = 0
  for row in rows:
    sa_cell = row.select_one("p.sa")
    if sa_cell is None: continue
    headwords = [sa_cell.text]
    img = row.select_one("img")
    image_url = img["src"].replace("./", "https://github.com/sanskrit/samskrtam.ru/blob/master/backup/sanskrit-lexicon/KEWA/")
    text_path = os.path.join(source_dir, img["src"].replace("./", "") + ".txt")
    if not os.path.exists(text_path):
      logging.error(f"Missing text {text_path} for {headwords[0]}")
      missing_texts = missing_texts + 1
      meaning = ""
    else:
      replacements = {"ş": "ṣ", "ț": "ṭ"}
      with open(text_path) as f:
        meaning = f.read().replace("\n", "<br>")
        meaning = regex.sub("﻿_+", "", meaning)
        for x, y in replacements.items():
          meaning = meaning.replace(x, y)
    text_url = f"{image_url}.txt"
    meaning = f"<p>{sa_cell.text} {row.select_one('p.iast').text} <a href='{image_url}'>IMG</a> <a href='{text_url}'>Edit</a> </p><p>{meaning}</p>"
    definition = Definition(headwords_tuple=tuple(headwords), meaning=meaning)
    definitions.append(definition)

  logging.info(f"Out of {len(definitions)}, {missing_texts} are missing texts.")
  file_path = os.path.join(dest_dir, os.path.basename(dest_dir) + ".babylon")
  headers = header_helper.get_default_headers(file_path)
  babylon.dump(dest_path=file_path, definitions=definitions, headers=headers)


if __name__ == '__main__':
  dump_babylon()
  pass
