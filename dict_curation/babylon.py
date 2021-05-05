import codecs
import itertools
import logging
import os
from pathlib import Path

from dict_curation import slob, Definition
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


def get_definitions(in_path, do_fix_newlines=False):
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


def fix_newlines(lines):
    for (index, line) in tqdm(enumerate(lines)):
        if index % 3 == 2:
            if line.strip() != "":
                logging.error("Bad line: %d is %s", index + 1, line)
                line = lines.pop(index)
                lines[index-1] = lines[index-1].strip() + "<br>" + line
                return fix_newlines(lines=lines)
    return lines


def join_babylon_segments_in_dir(out_path_dir):
    final_babylon_dir = Path(out_path_dir).parent
    final_babylon_name = os.path.basename(final_babylon_dir) + ".babylon"
    input_files = list(Path(out_path_dir).glob("*.babylon"))
    input_files.sort()
    file_helper.concatenate_files(input_path_list=input_files, output_path=os.path.join(final_babylon_dir, final_babylon_name))


def get_headwords(in_path):
    headwords = []
    with codecs.open(in_path, "r", 'utf-8') as file_in:
        current_headwords = []
        for (index, line) in tqdm(enumerate(file_in.readlines())):
            if index % 3 == 0:
                current_headwords = [hw for hw in line.strip().split("|") if hw != "" ]
                headwords.extend(current_headwords)
    headwords = list(set(headwords))
    headwords.sort()
    return headwords


def dump_headwords_file(in_path, out_path):
    headwords = get_headwords(in_path=in_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with codecs.open(out_path, "w", 'utf-8') as file_out:
        for headword in headwords:
            file_out.write(headword + "\n")


def dump_definitions_file(in_path, out_path):
    definitions = get_definitions(in_path=in_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with codecs.open(out_path, "w", 'utf-8') as file_out:
        for definition in definitions.values():
            file_out.write(definition + "\n")


def to_slob(in_path, out_path):
    definitions = get_definitions(in_path=in_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if os.path.exists(out_path):
        os.remove(out_path)
    with slob.create(out_path) as w:
        for definition in set(definitions.values()):
            w.add(definition.meaning.encode('utf-8'), *(definition.headwords_tuple), content_type=slob.MIME_HTML)


if __name__ == '__main__':
    to_slob("/home/vvasuki/indic-dict/stardict-sinhala/si-head/en-entries/carter/carter.babylon_final", "/home/vvasuki/indic-dict/stardict-sinhala/si-head/en-entries/slobs/carter__2018-03-22_03-14-55__unkMB.slob")