import codecs
import itertools
import logging
import os

from tqdm import tqdm

from dict_curation import Definition
import logging

# Remove all handlers associated with the root logger object.

for handler in logging.root.handlers[:]:
  logging.root.removeHandler(handler)
logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")


def fix_definitions(f, file_path, dry_run=False):
  tmp_file_path = file_path + "_fixed"
  with codecs.open(file_path, "r", 'utf-8') as file_in:
    lines = file_in.readlines()
    with codecs.open(tmp_file_path, "w", 'utf-8') as file_out:
      for index, line in enumerate(lines):
        if index % 3 == 1:
          line = f(line)
        line = line
        file_out.write(line)
        if dry_run:
          print(line)
  if not dry_run:
    os.remove(file_path)
    os.rename(src=tmp_file_path, dst=file_path)


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
