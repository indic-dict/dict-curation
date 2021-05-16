import codecs
import os
import subprocess

import aksharamukha.transliterate
import regex
import tqdm
import logging

from aksharamukha import GeneralMap

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
  with codecs.open(source_path, "r", "utf-8") as in_file, codecs.open(source_path + ".tmp", "w", "utf-8") as out_file:
    progress_bar = tqdm.tqdm(total=int(subprocess.check_output(['wc', '-l', source_path]).split()[0]), desc="Lines", position=0)
    for line in in_file:
      if "|" in line:
        # line = line.replace("‍", "").replace("~", "")
        headwords = line.split("|")
        filtered_headwords = [headword for headword in headwords if not regex.search(r"[ऀ-ॿ]", headword)]
        dest_line = "|".join(filtered_headwords)
      else:
        dest_line = line
      out_file.write(dest_line)
      progress_bar.update(1)


def process_dir(source_script, dest_script, source_dir, dest_dir=None, pre_options=[], post_options=[]):
  SCRIPT_TO_SUFFIX = {GeneralMap.DEVANAGARI: "dev", "ISO": "en"}
  dest_dir_suffix = SCRIPT_TO_SUFFIX[dest_script]
  
  if dest_dir is None:
    dest_dir_base =  "%s_%s-script" % (os.path.basename(source_dir),dest_dir_suffix)
    dest_dir = os.path.join(os.path.dirname(source_dir), dest_dir_base)
  
  for subdir in os.listdir(source_dir):
    subdir_path = os.path.join(source_dir, subdir)
    if os.path.isdir(subdir_path):
      dest_dict_name = "%s_%s" % (subdir, dest_dir_suffix)
      convert_with_aksharamukha(source_path=os.path.join(subdir_path, subdir + ".babylon"), dest_path=os.path.join(dest_dir, dest_dict_name, dest_dict_name + ".babylon"), source_script=source_script, dest_script=dest_script, pre_options=pre_options, post_options=post_options)


def process_oriya_dicts():
  process_dir(source_script="Oriya", dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-oriya/or-head")


def process_sinhala_dicts():
  process_dir(source_script=GeneralMap.SINHALA, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-sinhala/si-head/en-entries", dest_dir="/home/vvasuki/indic-dict/stardict-sinhala/si-head_dev-script/en-entries")


def process_panjabi_dicts():
  process_dir(source_script=GeneralMap.GURMUKHI, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-panjabi/pa-head/en-entries", dest_dir="/home/vvasuki/indic-dict/stardict-panjabi/pa-head_dev-script/en-entries")

def process_bengali_dicts():
  process_dir(source_script=GeneralMap.BENGALI, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-bengali/bn-head/en-entries", dest_dir="/home/vvasuki/indic-dict/stardict-panjabi/bn-head_dev-script/en-entries")
  process_dir(source_script=GeneralMap.BENGALI, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-bengali/bn-head/bn-entries", dest_dir="/home/vvasuki/indic-dict/stardict-panjabi/bn-head_dev-script/bn-entries")


def process_ml_dicts():
  process_dir(source_script="Malayalam", dest_script="ISO", source_dir="/home/vvasuki/indic-dict/stardict-malayalam/en-head")
 
  # remove_devanagari_headwords(source_path="/home/vvasuki/indic-dict/stardict-malayalam/ml-head/datuk/datuk.babylon")
  # remove_devanagari_headwords(source_path="/home/vvasuki/indic-dict/stardict-malayalam/ml-head/gundert/gundert.babylon")
  # 
  source_dir = "/home/vvasuki/indic-dict/stardict-malayalam/ml-head/"
  process_dir(source_script="Malayalam", dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir)


def process_tamil_dicts():
  pre_options = ["TamilTranscribe"]
  source_dir = "/home/vvasuki/indic-dict/stardict-tamil/ta-head/"
  process_dir(source_script="Tamil", dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir, pre_options=pre_options)
  source_dir = "/home/vvasuki/indic-dict/stardict-tamil/en-head/"
  process_dir(source_script="Tamil", dest_script="ISO", source_dir=source_dir, pre_options=pre_options)


if __name__ == '__main__':
  process_panjabi_dicts()