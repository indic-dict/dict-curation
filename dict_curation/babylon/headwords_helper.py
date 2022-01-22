import codecs
import os
import subprocess

from tqdm import tqdm

import logging

# Remove all handlers associated with the root logger object.

for handler in logging.root.handlers[:]:
  logging.root.removeHandler(handler)
logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")



def get_headwords(in_path):
  headwords = []
  with codecs.open(in_path, "r", 'utf-8') as file_in:
    current_headwords = []
    for (index, line) in tqdm(enumerate(file_in.readlines())):
      if index % 3 == 0:
        current_headwords = [hw for hw in line.strip().split("|") if hw != ""]
        headwords.extend(current_headwords)
  headwords = list(set(headwords))
  headwords.sort()
  return headwords



def add_headwords_from_definitions(file_path, headword_extractor, line_1_index=1, dry_run=False):
  tmp_file_path = file_path + "_fixed"
  with codecs.open(file_path, "r", 'utf-8') as file_in:
    lines = file_in.readlines()
    with codecs.open(tmp_file_path, "w", 'utf-8') as file_out:
      progress_bar = tqdm(total=int(subprocess.check_output(['wc', '-l', file_path]).split()[0]), desc="Lines", position=0)
      for line_number, line in enumerate(lines):
        if line_number >= line_1_index and (line_number + 1 - line_1_index) % 3 == 0:
          # line = line.replace("‍", "").replace("~", "")
          headwords = line.strip().split("|")
          new_headwords = headword_extractor(lines[line_number + 1])
          dest_line = "|".join(set(headwords + new_headwords))
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