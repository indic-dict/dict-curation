import codecs
import logging
import os
from pathlib import Path

from curation_utils import file_helper
from tqdm import tqdm

from dict_curation.babylon.definitions import get_definitions


def fix_newlines(lines):
  for (index, line) in tqdm(enumerate(lines)):
    if index % 3 == 2:
      if line.strip() != "":
        logging.error("Bad line: %d is %s", index + 1, line)
        line = lines.pop(index)
        lines[index - 1] = lines[index - 1].strip() + "<br>" + line
        return fix_newlines(lines=lines)
  return lines


def join_babylon_segments_in_dir(out_path_dir, glob_pattern="**/*.babylon"):
  final_babylon_dir = Path(out_path_dir).parent
  final_babylon_name = os.path.basename(final_babylon_dir) + ".babylon"
  input_files = list(Path(out_path_dir).glob(glob_pattern))
  input_files.sort()
  logging.info("Combining %d files in %s to %s", len(input_files), )
  file_helper.concatenate_files(input_path_list=input_files,
                                output_path=os.path.join(final_babylon_dir, final_babylon_name))


def split_to_babylon_segements(file_path, out_path_dir=None):
  definitions = get_definitions(in_path=file_path)
  if out_path_dir is None:
    out_path_dir = os.path.join(os.path.dirname(file_path), os.path.basename(file_path).replace(".babylon", ""))
  for headword, definition in definitions.items():
    os.makedirs(out_path_dir, exist_ok=True)
    out_path = os.path.join(out_path_dir, file_helper.clean_file_name(headword + ".babylon"))
    with codecs.open(out_path, "w", 'utf-8') as file_out:
      file_out.writelines(["%s\n%s\n\n" % (headword, definition)])