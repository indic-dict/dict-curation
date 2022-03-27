import codecs
import logging
import os
from functools import partial
from multiprocessing import Pool

from curation_utils import file_helper, scraping

import dict_curation.babylon.cleaner
from dict_curation import babylon

for handler in logging.root.handlers[:]:
  logging.root.removeHandler(handler)
logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")


def get_letter_headwords(letter, out_path_dir, get_headword_defs, overwrite=True):
  out_path = os.path.join(out_path_dir, letter + ".csv")
  if os.path.exists(out_path) and not overwrite:
    logging.warning("Skipping %s as %s exists", letter, out_path)
    return 0
  os.makedirs(os.path.dirname(out_path), exist_ok=True)
  with codecs.open(out_path, "w", 'utf-8') as file_out:
    word_anchors, words = get_headword_defs(letter)

    file_out.write("\n".join(words) + "\n")
    return len(word_anchors)


def get_headwords(letters, out_path):
  pool = Pool(4)
  f = partial(get_letter_headwords, out_path_dir=out_path)
  counts = pool.map(f, letters)
  logging.info(list(zip(letters, counts)))



def dump_headword_definition(headword_detail, out_path_dir, get_definition, log):
  (headword, url) = headword_detail.split("\t")
  out_path = os.path.join(out_path_dir,  file_helper.clean_file_name(headword + ".babylon"))
  if os.path.exists(out_path):
    return "SKIPPED"
  if log is not None:
    log.set_description_str(headword_detail)
  definition = get_definition(headword=headword.strip(), url=url.strip(), log=log)
  if definition == "" or "NO DEFINITION" in definition or "PARSE ERROR" in definition:
    return None
  os.makedirs(os.path.dirname(out_path), exist_ok=True)
  with codecs.open(out_path, "w", 'utf-8') as file_out:
    file_out.writelines(["%s\n%s\n\n" % (headword, definition)])
  return "DONE"


def dump_letter_definitions(letter, in_path_dir, out_path_dir, get_definition):
  in_path = os.path.join(in_path_dir, letter + ".csv")
  count = 0
  empty_count = 0
  skipped_count = 0
  out_path_dir = os.path.join(out_path_dir, letter)
  dict_curation.babylon.cleaner.split_to_per_headword_babylon_segements(file_path=out_path_dir + ".babylon")
  with codecs.open(in_path, "r", 'utf-8') as file_in:
    headword_details = file_in.readlines()
    from tqdm.contrib.concurrent import process_map  # or thread_map
    f = partial(dump_headword_definition, out_path_dir=out_path_dir, get_definition=get_definition, log=None)
    results = process_map(f, headword_details, max_workers=8)
    for result in results:
      count += 1
      if result == None:
        empty_count += 1
      elif result == "SKIPPED":
        skipped_count += 1

  dict_curation.babylon.cleaner.join_babylon_segments_in_dir(out_path_dir=out_path_dir, glob_pattern="*.babylon")
  return (count, empty_count)


def dump_definitions(letters, in_path_dir, out_path_dir, get_definition):
  from tqdm.contrib.concurrent import process_map  # or thread_map
  # dump_letter_definitions("A", in_path_dir, out_path_dir)
  for letter in letters:
    dump_letter_definitions(letter=letter, in_path_dir=in_path_dir, out_path_dir=out_path_dir, get_definition=get_definition)
  dict_curation.babylon.cleaner.join_babylon_segments_in_dir(out_path_dir=out_path_dir, glob_pattern="*.babylon")
