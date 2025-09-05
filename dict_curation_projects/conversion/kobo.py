import logging
import subprocess
import sys
import os

import regex

for handler in logging.root.handlers[:]:
  logging.root.removeHandler(handler)
logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")


lang_to = "en"    # 'en' for English


def make_kobo(input_file):
  """Builds and executes the PyGlossary command."""
  details = regex.match(r"^.*/stardict(?:/[^/]+)*/stardict-(.+?)/(.{2})-head/.*/(.+?).ifo", input_file)
  lang_src = details.group(2)
  input_file = os.path.abspath(input_file)
  output_file = regex.sub("/[^/]+?.ifo", f"/dicthtml-{lang_src}-{lang_to}.zip", input_file)
  # Check if the input file exists before trying to run the command
  if not os.path.exists(input_file):
    logging.info(f"ERROR: Input file not found at '{input_file}'")
    sys.exit(1)

  # Build the command as a list of strings.
  # This is the safest way to pass arguments to subprocess.
  command = [
    '/home/vvasuki/gitland/python_venv/bin/pyglossary',
    input_file,
    output_file,
    '--read-format', "Stardict",
    '--write-format', "Kobo",
  ]
  logging.info("Starting dictionary conversion with PyGlossary...")
  # This is a user-friendly way to show the command that will be run
  logging.info(f"  Command: {' '.join(command)}")

  # subprocess.run() is the modern and recommended way to run commands.
  # - check=True: Raises an exception if the command returns a non-zero exit code (i.e., fails).
  # - capture_output=True: Captures stdout and stderr.
  # - text=True: Decodes stdout and stderr as text using the default encoding.
  result = subprocess.run(
    command,
    check=True,
    capture_output=True,
    text=True,
      encoding='utf-8'
  )

  logging.info("\n--- PyGlossary Success Output (stdout) ---")
  logging.info(result.stdout)
  logging.info("----------------------------------------")
  logging.info(f"\nSuccessfully created dictionary: '{output_file}'")
  
  # Copy to kobo
  os.system(f"cp {output_file} /media/vvasuki/KOBOeReader/.kobo/dict")


if __name__ == "__main__":
  # make_kobo(input_file="/media/vvasuki/vData/dicts/stardict/indic-dict/stardict-sanskrit/sa-head/en-entries/apte-1890/apte-1890.ifo")
  make_kobo(input_file="/media/vvasuki/vData/dicts/stardict/indic-dict/stardict-tamil/ta-head/en-entries_dev-script/fabricius_dev/fabricius_dev.ifo")