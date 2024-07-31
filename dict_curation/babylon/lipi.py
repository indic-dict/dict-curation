import codecs
import logging
import os
import shutil
import subprocess

import aksharamukha.transliterate
import regex
import tqdm
from aksharamukha import GeneralMap
from indic_transliteration import sanscript, aksharamukha_helper, detect

import dict_curation.babylon
from dict_curation.babylon import lipi, definitions_helper

GeneralMap.DEVANAGARI = "Devanagari"
GeneralMap.BENGALI = "Bengali"
GeneralMap.TAMIL = "Tamil"
GeneralMap.TELUGU = "Telugu"

for handler in logging.root.handlers[:]:
  logging.root.removeHandler(handler)
logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")




def transliterate_headword_with_sanscript(headwords, definition, source_script=sanscript.IAST, dest_script=sanscript.DEVANAGARI, dry_run=False):
  new_headwords = []
  for headword in headwords:
    new_headwords.append(sanscript.transliterate(data=headword, _from=source_script, _to=dest_script))
  return (list(dict.fromkeys(new_headwords)), definition)


def remove_devanagari_headwords(headwords, definition):
  filtered_headwords = [headword for headword in headwords if not regex.search(r"[ऀ-ॿ]", headword)]
  return (filtered_headwords, definition)


def add_devanagari_headwords(headwords, definition, source_script, language=None, pre_options=[] ):
  if "urdu" == language.lowercase() and source_script == sanscript.ISO:
    optitrans_headwords = [sanscript.SCHEMES[sanscript.OPTITRANS].approximate_from_iso_urdu(x) for x in headwords]
    optitrans_headwords += [x.replace("E", "e") for x in optitrans_headwords]
    devanagari_headwords = [sanscript.transliterate(x, _from=sanscript.OPTITRANS, _to=sanscript.DEVANAGARI) for x in optitrans_headwords]
    devanagari_headwords += [x.replace("-", "").replace("\u200d", "") for x in devanagari_headwords]
    optitrans_headwords = [x.replace("{}", "") for x in optitrans_headwords]
    devanagari_headwords = devanagari_headwords + optitrans_headwords
  else:
    devanagari_headwords = [aksharamukha.transliterate.process(src=source_script, tgt="Devanagari", txt=headword, nativize = True, pre_options = pre_options) for headword in headwords]
  return (list(dict.fromkeys(headwords + devanagari_headwords)), definition)


def add_lazy_anusvaara_headwords(headwords, definition, source_script):
  new_headwords = [sanscript.SCHEMES[source_script].force_lazy_anusvaara(headword) for headword in headwords]
  return (list(dict.fromkeys(headwords + new_headwords)), definition)




def transliterate_tamil(headwords, definition, dest_script="Devanagari"):
  new_headwords = []
  transcribed_headwords =[]
  for headword in headwords:
    headword_script = detect.detect(headword).lower()
    if headword_script == dest_script.lower():
      continue
    else:
      new_headwords.append(headword)
      if headword_script == "tamil":
        new_headword = aksharamukha.transliterate.process(src="Tamil", tgt=dest_script, txt=headword, nativize = True, pre_options = [], post_options = [])
        transcribed_headwords.append(new_headword)
        new_headword = aksharamukha.transliterate.process(src="Tamil", tgt=dest_script, txt=headword, nativize = True, pre_options = ["TamilTranscribe"], post_options = [])
        transcribed_headwords.append(new_headword)
        new_headword = aksharamukha.transliterate.process(src="Tamil", tgt=dest_script, txt=headword, nativize = True, pre_options = ["TamilTranscribeDialect"], post_options = [])
        transcribed_headwords.append(new_headword)
  new_headwords.extend(transcribed_headwords)
  new_headwords = list(dict.fromkeys(new_headwords))
  definition = aksharamukha.transliterate.process(src="Tamil", tgt=dest_script, txt=definition, nativize = True, pre_options = ["TamilTranscribe"], post_options = [])
  definition = f"{'|'.join(new_headwords)}<br>{definition}"
  return (new_headwords, definition)


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
          if source_script == "Tamil" and "en-head" not in source_dir:
            os.makedirs(os.path.dirname(source_dict_path), exist_ok=True)
            shutil.copy(source_dict_path, dest_path)
            dict_curation.babylon.transform(file_path=dest_path, transformer=lipi.transliterate_tamil, dry_run=False, dest_script=dest_script)
          else:
            aksharamukha_helper.convert_file(source_path=source_dict_path, dest_path=dest_path, source_script=source_script, dest_script=dest_script, pre_options=pre_options, post_options=post_options)
        else:
          logging.info("Skipping %s as it exists", dest_path)
      else:
        logging.warning("did not find %s", source_dict_path)
