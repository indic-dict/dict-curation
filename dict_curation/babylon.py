import codecs
import logging
import os

from indic_transliteration import sanscript
# Remove all handlers associated with the root logger object.
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

