import codecs
import logging

# Remove all handlers associated with the root logger object.
import os
import subprocess
from pathlib import Path

from tqdm import tqdm

for handler in logging.root.handlers[:]:
  logging.root.removeHandler(handler)
logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")


def process_all(dir_path, transformer, *args, **kwargs):
  babylon_files = list(Path(dir_path).glob("**/*.babylon_final"))
  babylon_files += Path(dir_path).glob("**/*.babylon")
  for babylon_file in babylon_files:
    logging.info("Processing %s", babylon_file)
    transformer(babylon_file, *args, **kwargs)
    

def dump(dest_path, definitions, headers=None):
  os.makedirs(os.path.dirname(dest_path), exist_ok=True)
  with codecs.open(dest_path, "w") as f:
    if headers is not None:
      f.write("\n")
      for key, value in headers.items():
        f.write("#%s=%s\n" % (key, value))
      f.write("\n")
    for definition in definitions:
      f.write(f"{'|'.join(definition.headwords_tuple)}\n{definition.meaning.strip()}\n\n")


def transform(file_path, transformer, dry_run=False, *args, **kwargs):
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
          dest_line = "|".join(new_headwords)
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
