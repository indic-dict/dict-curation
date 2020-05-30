import codecs
import logging
import os
from pathlib import Path

from indic_transliteration import sanscript
# Remove all handlers associated with the root logger object.
from tqdm import tqdm

from curation_utils import file_helper

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")



def transliterate_headword(file_path, source_script=sanscript.IAST, dest_script=sanscript.DEVANAGARI, dry_run=False):
    tmp_file_path = file_path + "_fixed"
    with codecs.open(file_path, "r", 'utf-8') as file_in:
        lines = file_in.readlines()
        with codecs.open(tmp_file_path, "w", 'utf-8') as file_out:
            for index, line in enumerate(lines):
                if index % 3 == 0:
                    line = sanscript.transliterate(data=line, _from=source_script, _to=dest_script)
                line = line
                file_out.write(line)
                if dry_run:
                    print(line)
    if not dry_run:
        os.remove(file_path)
        os.rename(src=tmp_file_path, dst=file_path)


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


def get_definitions(in_path):
    logging.info("Getting definitions from %s" % in_path)
    definitions = {}
    empty_headwords = 0
    empty_definitions = 0
    definition_lines = 0
    with codecs.open(in_path, "r", 'utf-8') as file_in:
        current_headwords = []
        for (index, line) in tqdm(enumerate(file_in.readlines())):
            if index % 3 == 0:
                current_headwords = line.strip().split("|")
            if index % 3 == 1:
                definition = line.strip()
                if definition == "":
                    empty_definitions = empty_definitions + 1
                    continue
                for headword in current_headwords:
                    if headword == "":
                        empty_headwords = empty_headwords + 1
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


def join_babylon_segments_in_dir(out_path_dir):
    final_babylon_dir = Path(out_path_dir).parent
    final_babylon_name = os.path.basename(final_babylon_dir) + ".babylon"
    file_helper.concatenate_files(input_path_list=Path(out_path_dir).glob("*.babylon"), output_path=os.path.join(final_babylon_dir, final_babylon_name))
    