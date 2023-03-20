import logging
import os
from collections import defaultdict

import regex
from tqdm import tqdm

from dict_curation import Definition, babylon
from dict_curation.babylon import header_helper
from doc_curation.md.content_processor import details_helper
from doc_curation.md.file import MdFile
from indic_transliteration.sanscript.schemes.brahmic import accent

from doc_curation.md.library import arrangement

BASE_DIR = "/home/vvasuki/gitland/vishvAsa/vedAH/static/atharva/shaunakam/rUDha-saMhitA/sarvASh_TIkAH"


def get_file_dict(md_file):
  (metadata, content) = md_file.read()
  detail = details_helper.get_detail_content(content=content, metadata=metadata, titles=["पदपाठः"])
  detail = regex.sub("[\d\.०-९‌‌,]", "", detail)
  words = set(regex.split("[।॥\s]+", detail))
  words = [w.strip() for w in words if w != ""]
  
  (metadata, content) = MdFile(file_path=md_file.file_path.replace("sarvASh_TIkAH", "mUlam")).read()
  muula = details_helper.get_detail_content(content=content, metadata=metadata, titles=["मूलम् (VS)"])
  muula = regex.sub("\s+", " ", muula).strip()
  return (words, muula)


def get_dict(dir_path=BASE_DIR):
  md_files = arrangement.get_md_files_from_path(dir_path=dir_path, file_pattern="**/[0-9][0-9]*.md")
  dict_out = defaultdict(list)
  for md_file in tqdm(md_files, desc="Reading files"):
    (words_sasvara, muula) = get_file_dict(md_file=md_file)
    id = md_file.file_path.replace(dir_path, "").replace(".md", "")
    id = regex.sub("_.+?(?=/|$)", "", id)
    for word in words_sasvara:
      if regex.search(accent.ACCENTS_PATTERN, word):
        dict_out[word].append(f"{id}")
      else:
        dict_out[word].append(f"{id}: {muula}")
  return dict_out


def dump_babylon(dest_dir):
  sasvara_word_dict = get_dict(dir_path=BASE_DIR)
  visvara_to_sasvara = defaultdict(list)
  for word in tqdm(sasvara_word_dict, desc="sasvara_words"):
    visvara_word = regex.sub(fr"{accent.ACCENTS_PATTERN}|ऽ", "", word)
    visvara_to_sasvara[visvara_word].append(word)
  definitions = []
  for visvara_word in tqdm(sorted(sasvara_word_dict.keys()), desc="visvara_words"):
    for sasvara_word in visvara_to_sasvara[visvara_word]:
      citations = "<br>".join(sasvara_word_dict[sasvara_word])
      meaning = f"{sasvara_word}<br><br>{citations}"
      headwords = [visvara_word]
      if visvara_word.endswith("ः"):
        headwords.append(visvara_word[:-1])
      elif visvara_word.endswith("म्"):
        headwords.append(visvara_word[:-2])
      defintion = Definition(headwords_tuple=tuple(headwords), meaning=meaning)
      definitions.append(defintion)

  logging.info(f"Got {len(definitions)}.")
  file_path = os.path.join(dest_dir, os.path.basename(dest_dir) + ".babylon")
  headers = header_helper.get_default_headers(file_path)
  babylon.dump(dest_path=file_path, definitions=definitions, headers=headers)


if __name__ == '__main__':
  dump_babylon(dest_dir="/home/vvasuki/gitland/indic-dict_stardict/stardict-sanskrit-kAvya/av-padasvara")    