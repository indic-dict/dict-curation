import codecs
import csv
import logging
import os

import pandas

from dict_curation import babylon
# Remove all handlers associated with the root logger object.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")


def from_combined_source(dict_id, out_path):
    def process_file(csv_in):
        with open(csv_in, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if row[0] == dict_id:
                    logging.info(row)
                    file_out.write(row[1] + "\n")
                    file_out.write(row[2] + "\n\n")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with codecs.open(out_path, "w", 'utf-8') as file_out:
        process_file(csv_in="/home/vvasuki/paali-bhaasaa/raw_etexts/kosha/dict_words_1.csv")
        process_file(csv_in="/home/vvasuki/paali-bhaasaa/raw_etexts/kosha/dict_words_2.csv")
    babylon.transliterate_headword(file_path=out_path, dry_run=False)


if __name__ == '__main__':
    # babylon.transliterate_headword(file_path="/home/vvasuki/indic-dict/stardict-pali/pali-head/pts_pali/pts_pali.babylon", dry_run=False)
    from_combined_source(dict_id="C", out_path="/home/vvasuki/indic-dict/stardict-pali/pali-head/en-entries/concise-buddhadatta/concise-buddhadatta.babylon")