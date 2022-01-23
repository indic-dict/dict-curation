import logging

# Remove all handlers associated with the root logger object.
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