import json
import os.path

from dict_curation import Definition, babylon
from dict_curation.babylon import header_helper


def dump_entries():
  output = []
  source_file_path = "/home/vvasuki/gitland/indic-dict/dicts/stardict-prakrit/prakrit-head/hi-entries/dhanapAla/pAia-lacchI-nAmamAlA_cleaned.json"
  definitions = []
  with open(source_file_path, 'r') as source_file:
    data = json.load(source_file)
    for entry_in in data:
      # Extracting values from the dictionary
      headword = entry_in.get("headword", "")
      sanskrit = entry_in.get("sanskrit", "")
      hindi = entry_in.get("hindi", "")
      english = entry_in.get("english", "")
      index = entry_in.get("index", "")
  
      # Formatting Line 1: PRAKRIT_HEADWORD|SANSKRIT|HINDI|ENGLISH
      headwords = [headword]
      potential_headwords = [sanskrit, hindi, english]
      for x in potential_headwords:
        for headword in x.split(","):
          headwords.append(headword)
  
      meaning = f"सं - {sanskrit}<BR>हि - {hindi}<BR>{english}<BR>({index})"
  
      defintion = Definition(headwords_tuple=tuple(headwords), meaning=meaning)
      definitions.append(defintion)
  
  dict_name = os.path.basename(os.path.dirname(source_file_path))
  dest_path = os.path.join(os.path.dirname(source_file_path), dict_name + ".babylon")
  headers = header_helper.get_default_headers(dest_path)
  babylon.dump(dest_path=dest_path, definitions=definitions, headers=headers)


if __name__ == '__main__':
  dump_entries()