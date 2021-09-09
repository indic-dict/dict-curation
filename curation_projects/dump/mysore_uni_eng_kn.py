import argparse
import codecs
import logging
import os
from functools import partial
from multiprocessing import Pool

import regex
import requests
import tqdm
from doc_curation import md
from indic_transliteration import sanscript

from curation_utils import scraping, file_helper
from dict_curation import babylon
from dict_curation.scrape.letter_based import dump_definitions


def get_headword_defs(letter):
  url = "https://uni-mysore.ac.in/mlrccdictionary/listing/alphabet/%s" % letter.upper()
  soup = scraping.get_soup(url=url)
  word_anchors = soup.select(selector="a")
  word_anchors = [a for a in word_anchors if "describe/word" in a.get("href", "")]
  logging.info("%s has %d words", letter, len(word_anchors))
  words = ["%s\t%s" % (anchor.text, anchor["href"]) for anchor in word_anchors]
  return word_anchors, words


def get_definition(headword, url, log):
  if url is None:
    url = "https://uni-mysore.ac.in/mlrccdictionary/describe/word/%s" % headword
  soup = scraping.get_soup(url=url)
  def_containers = soup.select("div.container")
  if len(def_containers) == 0:
    definition_md = "NO DEFINITION DETECTED. Check %s at %s" % (headword, url)
    if log is not None:
      log.set_description_str(definition_md)
  else:
    try:
      definition_md = md.get_md_with_pandoc(content_in=str(def_containers[-1]))
    except Exception:
      definition_md = "PARSE ERROR. Check %s at %s" % (headword, url)
  definition_body = definition_md.replace("\n", "<br>")
  return ("%s<br>%s" % (headword, definition_body))


if __name__ == '__main__':
  letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
  finished_letters = ""
  # get_headwords(letters=letters, out_path="/home/vvasuki/indic-dict/stardict-kannada/en-head/mysore_uni_eng_kn/headwords/")
  dump_definitions(letters=letters, in_path_dir="/home/vvasuki/indic-dict/stardict-kannada/en-head/mysore_uni_eng_kn/headwords/", out_path_dir="/home/vvasuki/indic-dict/stardict-kannada/en-head/mysore_uni_eng_kn/definitions/", get_definition=get_definition)
