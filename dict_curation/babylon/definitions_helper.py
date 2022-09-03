import codecs
import itertools
import logging
import os
import subprocess

from indic_transliteration import detect
from tqdm import tqdm

from dict_curation import Definition
import logging

# Remove all handlers associated with the root logger object.

for handler in logging.root.handlers[:]:
  logging.root.removeHandler(handler)
logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")


def get_definitions_map(in_path, do_fix_newlines=False, definitions_list=None):
  logging.info("Getting definitions from %s" % in_path)
  definitions = {}
  empty_headwords = 0
  empty_definitions = 0
  definition_lines = 0
  with codecs.open(in_path, "r", 'utf-8') as file_in:
    current_headwords = []
    lines = file_in.readlines()
    lines = list(itertools.dropwhile(lambda x: x.strip() == "" or x.startswith("#"), lines))
    if do_fix_newlines:
      from dict_curation.babylon.cleaner import fix_newlines
      lines = fix_newlines(lines=lines)
      with codecs.open(in_path + "_fixed", "w", 'utf-8') as file_out:
        file_out.writelines(lines)
    for (index, line) in tqdm(enumerate(lines)):
      if index % 3 == 0:
        current_headwords = line.strip().split("|")
      elif index % 3 == 1:
        meaning = line.strip()
        if meaning == "":
          empty_definitions = empty_definitions + 1
          logging.warning("Empty definition for %s at %d", "|".join(current_headwords), index + 1)
          continue
        definition = Definition(headwords_tuple=tuple(current_headwords), meaning=meaning)
        if definitions_list is not None:
          definitions_list.append(definition)
        for headword in current_headwords:
          if headword == "":
            empty_headwords = empty_headwords + 1
            logging.warning("Empty headword for %s at %d", "|".join(current_headwords), index + 1)
          else:
            definitions[headword] = definition
        definition_lines = definition_lines + 1
      else:
        if line.strip() != "":
          logging.error("Bad line: %d is %s", index + 1, line)
          raise Exception
  if empty_headwords != 0 or empty_definitions != 0:
    logging.warning("empty_headwords: %d , empty_definitions: %d from %s", empty_headwords, empty_definitions, in_path)
  logging.info("Getting %d definitions for %d headwords from %s" % (definition_lines, len(definitions), in_path))
  return definitions


def transform_entries(file_path, transformer, dry_run=False, *args, **kwargs):
  from dict_curation.babylon import header_helper
  line_1_index = header_helper.get_non_header_line_1_index(file_path=file_path)
  tmp_file_path = file_path + "_fixed"
  with codecs.open(file_path, "r", 'utf-8') as file_in:
    lines = file_in.readlines()
    with codecs.open(tmp_file_path, "w", 'utf-8') as file_out:
      progress_bar = tqdm(total=int(subprocess.check_output(['wc', '-l', file_path]).split()[0]), desc="Lines", position=0)
      for line_number, line in enumerate(lines):
        if line_number >= line_1_index and (line_number - line_1_index) % 3 == 0:
          # line = line.replace("‍", "").replace("~", "")
          headwords = line.strip().split("|")
          (new_headwords, lines[line_number + 1]) = transformer(headwords=headwords, definition=lines[line_number + 1], *args, **kwargs)
          # As of Python 3.7 (and CPython 3.6), standard dict is guaranteed to preserve order and is more performant than OrderedDict.
          dest_line = "|".join(dict.fromkeys(headwords + new_headwords))
          if not dest_line.endswith("\n"):
            dest_line = dest_line + "\n"
        else:
          dest_line = line
        file_out.write(dest_line)
        progress_bar.update(1)
        if dry_run:
          print(dest_line)
  if not dry_run:
    os.remove(file_path)
    os.rename(src=tmp_file_path, dst=file_path)
