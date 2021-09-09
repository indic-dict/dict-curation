#!/bin/python

import csv
import codecs
import logging
import os

import indic_transliteration
from indic_transliteration import sanscript
from indic_transliteration.detect import detect


def decomment(csvfile):
  for row in csvfile:
    raw = row.split('#')[0].strip()
    if raw and row != "": yield row


def import_dict(source_file_path, dest_file_path, delimiter=','):
  logging.info("Importing %s to %s", source_file_path, dest_file_path)
  os.makedirs(name=os.path.dirname(dest_file_path), exist_ok=True)
  with open(source_file_path, 'rU') as csvfile, codecs.open(dest_file_path, "w", "utf-8") as targetFile:
    for items in csv.reader(decomment(csvfile), delimiter=delimiter):
      headwords = [items[0]]
      source_script = detect(text=headwords[0])
      if source_script != sanscript.DEVANAGARI:
        headword_dev = sanscript.transliterate(data=headwords[0], _from=source_script, _to=sanscript.DEVANAGARI)
        headwords.append(headword_dev)
      else:
        headword_dev = headwords[0]
      headword_dev_non_lazy = sanscript.SCHEMES[sanscript.DEVANAGARI].fix_lazy_anusvaara(headword_dev, omit_sam=False, omit_yrl=True, ignore_padaanta=True)
      if headword_dev_non_lazy != headword_dev:
        headwords.append(headword_dev_non_lazy)
      meaning = items[1].replace("\n", "<br>")
      targetFile.write("%s\n%s\n\n" % ("|".join(headwords), meaning))


