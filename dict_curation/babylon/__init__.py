import codecs
import logging

# Remove all handlers associated with the root logger object.
import os
from pathlib import Path

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
      f.write(f"{'|'.join(definition.headwords_tuple)}\n{definition.meaning}\n\n")
