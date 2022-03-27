import codecs
import logging
import os
from pathlib import Path

from curation_utils import file_helper
from tqdm import tqdm

from dict_curation import babylon
from dict_curation.babylon import header_helper
from dict_curation.babylon.definitions_helper import get_definitions_map


def fix_newlines(lines):
  # TODO: use line_1_index = header_helper.get_non_header_line_index(file_path=source_path)
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


def split_to_chunks(input_path, num_chunks):
  definitions_list = []
  get_definitions_map(in_path=input_path, definitions_list=definitions_list)
  chunk_size = len(definitions_list)//num_chunks + 1
  definition_chunks = [definitions_list[i * chunk_size:(i + 1) * chunk_size] for i in range((len(definitions_list) + chunk_size - 1) // chunk_size )]

  headers = header_helper.get_headers(file_path=input_path)
  header_helper.set_html_headers(headers=headers)

  dict_name_base = os.path.basename(os.path.dirname(input_path))
  for index, chunk in enumerate(definition_chunks):
    dict_name = f"{dict_name_base}_{index + 1}"
    dict_path = os.path.join(os.path.dirname(os.path.dirname(input_path)), dict_name, f"{dict_name}.babylon")
    logging.info(f"Dumping {dict_name} to {dict_path}")
    # headers.get("bookname", dict_name_base)
    from dict_curation.babylon import language
    headers["bookname"] = dict_name_base + f" p{index + 1} {language.get_language_pair_string(dict_path)}"
    
    babylon.dump(dest_path=dict_path, definitions=chunk, headers=headers)
  


def split_to_per_headword_babylon_segements(file_path, out_path_dir=None):
  definitions = get_definitions_map(in_path=file_path)
  if out_path_dir is None:
    out_path_dir = os.path.join(os.path.dirname(file_path), os.path.basename(file_path).replace(".babylon", ""))
  for headword, definition in definitions.items():
    os.makedirs(out_path_dir, exist_ok=True)
    out_path = os.path.join(out_path_dir, file_helper.clean_file_name(headword + ".babylon"))
    with codecs.open(out_path, "w", 'utf-8') as file_out:
      file_out.writelines(["%s\n%s\n\n" % (headword, definition)])


