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


def remove_devanagari_headwords(source_path, line_1_index=1):
  logging.info("\nremove_devanagari_headwords %s", source_path)
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


def process_oriya_dicts():
  process_dir(source_script="Oriya", dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-oriya/or-head")


def process_sinhala_dicts():
  process_dir(source_script=GeneralMap.SINHALA, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-sinhala/si-head/en-entries", dest_dir="/home/vvasuki/indic-dict/stardict-sinhala/si-head_dev-script/en-entries")


def process_panjabi_dicts():
  process_dir(source_script=GeneralMap.GURMUKHI, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-panjabi/pa-head/en-entries", dest_dir="/home/vvasuki/indic-dict/stardict-panjabi/pa-head_dev-script/en-entries")

def process_bengali_dicts():
  process_dir(source_script=GeneralMap.BENGALI, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-bengali/bn-head/en-entries", dest_dir="/home/vvasuki/indic-dict/stardict-bengali/bn-head_dev-script/en-entries")
  process_dir(source_script=GeneralMap.BENGALI, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-bengali/bn-head/bn-entries", dest_dir="/home/vvasuki/indic-dict/stardict-bengali/bn-head_dev-script/bn-entries")


def process_as_dicts():
  process_dir(source_script=GeneralMap.ASSAMESE, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-assamese/as-head/en-entries", dest_dir="/home/vvasuki/indic-dict/stardict-assamese/as-head_dev-script/en-entries")
  # process_dir(source_script=GeneralMap.ASSAMESE, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-assamese/as-head/as-entries", dest_dir="/home/vvasuki/indic-dict/stardict-assamese/as-head_dev-script/as-entries")

def process_ml_dicts():
  process_dir(source_script=GeneralMap.MALAYALAM, dest_script=GeneralMap.ISO, source_dir="/home/vvasuki/indic-dict/stardict-malayalam/en-head")
 
  # remove_devanagari_headwords(source_path="/home/vvasuki/indic-dict/stardict-malayalam/ml-head/datuk/datuk.babylon")
  remove_devanagari_headwords(source_path="/home/vvasuki/indic-dict/stardict-malayalam/ml-head/gundert/gundert.babylon")
  # 
  source_dir = "/home/vvasuki/indic-dict/stardict-malayalam/ml-head/"
  process_dir(source_script=GeneralMap.MALAYALAM, dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir)


def process_te_dicts():
  # process_dir(source_script=GeneralMap.TELUGU, dest_script="ISO", source_dir="/home/vvasuki/indic-dict/stardict-telugu/en-head")
  # 
  # remove_devanagari_headwords(source_path="/home/vvasuki/indic-dict/stardict-telugu/te-head/janapada/janapada.babylon")
  # remove_devanagari_headwords(source_path="/home/vvasuki/indic-dict/stardict-telugu/te-head/wiktionary_telugu/wiktionary_telugu.babylon")
  # 
  source_dir = "/home/vvasuki/indic-dict/stardict-telugu/te-head/"
  process_dir(source_script=GeneralMap.TELUGU, dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir)


def process_tamil_dicts():
  pre_options = ["TamilTranscribe"]
  source_dir = "/home/vvasuki/indic-dict/stardict-tamil/ta-head/"
  process_dir(source_script="Tamil", dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir, pre_options=pre_options)
  source_dir = "/home/vvasuki/indic-dict/stardict-tamil/en-head/"
  process_dir(source_script="Tamil", dest_script="ISO", source_dir=source_dir, pre_options=pre_options)


if __name__ == '__main__':
  process_tamil_dicts()
  # process_as_dicts()