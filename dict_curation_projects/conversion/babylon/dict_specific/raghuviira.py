#!/bin/python

import csv, regex
import codecs
import logging
import os

for handler in logging.root.handlers[:]:
  logging.root.removeHandler(handler)
logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")

infile_path = "/home/vvasuki/gitland/indic-dict_stardict/stardict-hindi/en-head/raghuvIra_gov_ed/raghuvIra_gov_ed.tsv"
outfile_path = infile_path.replace(".tsv", ".babylon")


def make_babylon(source_file_path, dest_file_path, delimiter='\t'):
  logging.info("Importing %s to %s", source_file_path, dest_file_path)
  os.makedirs(name=os.path.dirname(dest_file_path), exist_ok=True)
  with open(source_file_path, 'r') as csvfile, codecs.open(dest_file_path, "w", "utf-8") as target_file:
    target_file.write("\n#bookname=raghuvIra_gov_ed (en-hi)\n\n")
    for items in csv.reader(csvfile, delimiter=delimiter):
      if len(items) < 3:
        logging.fatal(items)
      headword_field = items[0].replace("\n", " ")
      subject_field = items[1]
      definition_field = "<BR>".join(items[2:]).replace("\n", "<BR>")
      definition = f"{headword_field}<BR>{subject_field}<BR>{definition_field}"
      headwords = []
      paranthesized_words = [x.group(1) for x in regex.finditer("\(([^\)]+)\)", headword_field)]
      headwords.extend(paranthesized_words)
      headword_field = regex.sub("\(([^\)]+)\)", "", headword_field)
      headwords.extend(headword_field.split(","))
      headwords = [x.strip() for x in headwords]
      target_file.write("%s\n%s\n\n" % ("|".join(headwords), definition))

if __name__ == '__main__':
  make_babylon(source_file_path=infile_path, dest_file_path=outfile_path)      
