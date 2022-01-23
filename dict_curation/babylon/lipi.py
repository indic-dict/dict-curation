import codecs
import logging
import os
import shutil
import subprocess

import aksharamukha.transliterate
import regex
import tqdm
from aksharamukha import GeneralMap
from indic_transliteration import sanscript

from dict_curation.babylon import header_helper

GeneralMap.DEVANAGARI = "Devanagari"
GeneralMap.BENGALI = "Bengali"
GeneralMap.TAMIL = "Tamil"
GeneralMap.TELUGU = "Telugu"

for handler in logging.root.handlers[:]:
  logging.root.removeHandler(handler)
logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")



def convert_with_aksharamukha(source_path, dest_path, source_script, dest_script, pre_options = [], post_options = []):
  logging.info("\nTransliterating (%s > %s) %s to %s", source_script, dest_script, source_path, dest_path)
  os.makedirs(os.path.dirname(dest_path), exist_ok=True)
  with codecs.open(source_path, "r", "utf-8") as in_file, codecs.open(dest_path, "w", "utf-8") as out_file:
    progress_bar = tqdm.tqdm(total=int(subprocess.check_output(['wc', '-l', source_path]).split()[0]), desc="Lines", position=0)
    for line in in_file:
      dest_line = aksharamukha.transliterate.process(src=source_script, tgt=dest_script, txt=line, nativize = True, pre_options = pre_options, post_options = post_options)
      out_file.write(dest_line)
      progress_bar.update(1)


def remove_devanagari_headwords(source_path):
  logging.info("\nremove_devanagari_headwords %s", source_path)
  line_1_index = header_helper.get_non_header_line_1_index(file_path=source_path)
  with codecs.open(source_path, "r", "utf-8") as in_file, codecs.open(source_path + ".tmp", "w", "utf-8") as out_file:
    progress_bar = tqdm.tqdm(total=int(subprocess.check_output(['wc', '-l', source_path]).split()[0]), desc="Lines", position=0)
    line_number = 1
    for line in in_file:
      if "|" in line and line_number >= line_1_index and (line_number - line_1_index) % 3 == 0:
        # line = line.replace("‍", "").replace("~", "")
        headwords = line.split("|")
        filtered_headwords = [headword for headword in headwords if not regex.search(r"[ऀ-ॿ]", headword)]
        dest_line = "|".join(filtered_headwords)
        if not dest_line.endswith("\n"):
          dest_line = dest_line + "\n"
      else:
        dest_line = line
      out_file.write(dest_line)
      progress_bar.update(1)
      line_number = line_number + 1


def add_devanagari_headwords(source_path, source_script, pre_options=[] ):
  source_path = str(source_path)
  logging.info("\nadd_devanagari_headwords %s", source_path)
  tmp_path = source_path + ".tmp"
  line_1_index = header_helper.get_non_header_line_1_index(file_path=source_path)
  from ordered_set import OrderedSet
  with codecs.open(source_path, "r", "utf-8") as in_file, codecs.open(tmp_path, "w", "utf-8") as out_file:
    progress_bar = tqdm.tqdm(total=int(subprocess.check_output(['wc', '-l', source_path]).split()[0]), desc="Lines", position=0)
    line_number = 1
    for line in in_file:
      if line_number >= line_1_index and (line_number - line_1_index) % 3 == 0:
        # line = line.replace("‍", "").replace("~", "")
        headwords = line.strip().split("|")
        devanagari_headwords = [aksharamukha.transliterate.process(src=source_script, tgt="Devanagari", txt=headword, nativize = True, pre_options = pre_options) for headword in headwords]
        dest_line = "|".join(OrderedSet(headwords + devanagari_headwords))
        if not dest_line.endswith("\n"):
          dest_line = dest_line + "\n"
      else:
        dest_line = line
      out_file.write(dest_line)
      progress_bar.update(1)
      line_number = line_number + 1
  os.remove(source_path)
  shutil.move(tmp_path, source_path)


def add_lazy_anusvaara_headwords(source_path, source_script):
  logging.info("\nadd_lazy_anusvaara_headwords %s", source_path)
  tmp_path = source_path + ".tmp"
  line_1_index = header_helper.get_non_header_line_1_index(file_path=source_path)
  with codecs.open(source_path, "r", "utf-8") as in_file, codecs.open(tmp_path, "w", "utf-8") as out_file:
    progress_bar = tqdm.tqdm(total=int(subprocess.check_output(['wc', '-l', source_path]).split()[0]), desc="Lines", position=0)
    line_number = 1
    for line in in_file:
      if line_number >= line_1_index and (line_number - line_1_index) % 3 == 0:
        # line = line.replace("‍", "").replace("~", "")
        headwords = line.strip().split("|")
        new_headwords = [sanscript.SCHEMES[source_script].force_lazy_anusvaara(headword) for headword in headwords]
        dest_line = "|".join(set(headwords + new_headwords))
        if not dest_line.endswith("\n"):
          dest_line = dest_line + "\n"
      else:
        dest_line = line
      out_file.write(dest_line)
      progress_bar.update(1)
      line_number = line_number + 1
  os.remove(source_path)
  shutil.move(tmp_path, source_path)


def process_dir(source_script, dest_script, source_dir, dest_dir=None, pre_options=[], post_options=[], overwrite=False):
  SCRIPT_TO_SUFFIX = {GeneralMap.DEVANAGARI: "dev", "ISO": "en"}
  dest_dir_suffix = SCRIPT_TO_SUFFIX[dest_script]
  source_dir = source_dir.rstrip("/")
  if dest_dir is None:
    dest_dir_base =  "%s_%s-script" % (os.path.basename(source_dir),dest_dir_suffix)
    dest_dir = os.path.join(os.path.dirname(source_dir), dest_dir_base)
  
  for subdir in os.listdir(source_dir):
    subdir_path = os.path.join(source_dir, subdir)
    if os.path.isdir(subdir_path):
      dest_dict_name = "%s_%s" % (subdir, dest_dir_suffix)
      source_dict_path = os.path.join(subdir_path, subdir + ".babylon")
      if os.path.exists(source_dict_path):
        dest_path = os.path.join(dest_dir, dest_dict_name, dest_dict_name + ".babylon")
        if not os.path.exists(dest_path) or overwrite:
          convert_with_aksharamukha(source_path=source_dict_path, dest_path=dest_path, source_script=source_script, dest_script=dest_script, pre_options=pre_options, post_options=post_options)
        else:
          logging.info("Skipping %s as it exists", dest_path)
      else:
        logging.warning("did not find %s", source_dict_path)


def transliterate_headword_with_sanscript(file_path, source_script=sanscript.IAST, dest_script=sanscript.DEVANAGARI, dry_run=False):
  tmp_file_path = file_path + "_fixed"
  with codecs.open(file_path, "r", 'utf-8') as file_in:
    lines = file_in.readlines()
    with codecs.open(tmp_file_path, "w", 'utf-8') as file_out:
      for index, line in enumerate(lines):
        if index % 3 == 0:
          line = sanscript.transliterate(data=line, _from=source_script, _to=dest_script)
        line = line
        file_out.write(line)
        if dry_run:
          print(line)
  if not dry_run:
    os.remove(file_path)
    os.rename(src=tmp_file_path, dst=file_path)