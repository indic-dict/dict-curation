import logging
import os

import langcodes
import regex


language_code_map = {"ayurveda": "sa", "prakrit": "pi", "test": "en"}


def get_main_language(file_path):
  matches = regex.findall("stardict[-_][^/]+", str(file_path))
  main_langage = matches[-1][len("stardict-"):]
  if main_langage in language_code_map:
    main_langage = language_code_map[main_langage]
  return main_langage


def set_languages(file_path, src_language=None, dest_language=None):
  file_path = str(file_path)
  short_file_path = file_path.replace("/home/vvasuki/indic-dict/stardict_all/", "")
  lang_pair = get_language_pair_string(file_path=file_path, dest_language=dest_language, src_language=src_language)

  from dict_curation.babylon import header_helper
  headers = header_helper.get_headers(file_path=file_path)
  headers["bookname"] = headers.get("bookname", os.path.basename(file_path).replace(".babylon_final", "").replace(".babylon", ""))
  
  preset_lang_pairs = regex.findall(r"\(..-..\)", headers["bookname"])
  if len(preset_lang_pairs) > 0:
    preset_lang_pair = preset_lang_pairs[0]
    if preset_lang_pair != lang_pair:
      logging.info("Retaining %s (deduced %s) in %s", preset_lang_pair, lang_pair, short_file_path)
    else:
      logging.info("Already fine: %s", short_file_path)
    return
  else:
    logging.info("Setting %s in %s", lang_pair, short_file_path)
    headers["bookname"] = "%s (%s-%s)" % (headers["bookname"], src_language, dest_language)

  header_helper.set_headers(file_path=file_path, headers=headers)


def get_language_pair_string(file_path, dest_language=None, src_language=None):
  if src_language is None:
    src_language = deduce_source_language(file_path)
  if len(src_language) > 2:
    try:
      src_language = langcodes.standardize_tag(langcodes.find(src_language))
    except LookupError:
      logging.fatal("%s", file_path)
  if dest_language is None:
    dest_language = deduce_entry_language(file_path=file_path)
  if len(dest_language) > 2:
    try:
      dest_language = langcodes.standardize_tag(langcodes.find(dest_language))
    except LookupError:
      logging.fatal("%s", file_path)
  return "(%s-%s)" % (src_language, dest_language)


def deduce_entry_language(file_path):
  main_language = get_main_language(file_path=file_path)
  entries_matches = regex.findall("[^/-_]+[_-]entries", str(file_path))
  if len(entries_matches) > 0:
    dest_language = entries_matches[0][:-len("-entries")]
    if dest_language.startswith("other"):
      dest_language = main_language
  else:
    dest_language = main_language
  return dest_language


def deduce_source_language(file_path):
  main_language = get_main_language(file_path=file_path)
  matches = regex.findall("[^/-_]+[-_]head", str(file_path))
  if len(matches) > 0:
    src_language = matches[0][:-len("-head")]
  else:
    src_language = main_language
  if src_language in language_code_map:
    src_language = language_code_map[src_language]
  return src_language

