import os, regex
from indic_transliteration import sanscript

from dict_curation import Definition
from dict_curation.babylon import header_helper
from dict_curation import babylon
from dict_curation.scrape import dump_babylon, dump_babylon_parallel
import logging


dest_dir = "/home/vvasuki/indic-dict/stardict_all/stardict-sanskrit/sa-head/en-entries/pract"


def devanaagarify(x):
  return sanscript.transliterate(data=x, _from='slp1_accented', _to=sanscript.DEVANAGARI)
  

def dump():
  definitions = []
  with open(os.path.join(dest_dir, "local/ap.txt")) as pd:
    headword = None
    meaning = None
    for line in pd.readlines():
      line = line.strip()
      if line.startswith("<L>"):
        keyword_match = regex.search("<k1>(.+?)<", line)
        headword = keyword_match.group(1)
        headword = devanaagarify(headword)
        meaning = ""
      elif line.startswith("<LEND>"):
        defintion = Definition(headwords_tuple=tuple([headword]), meaning=meaning)
        definitions.append(defintion)
        headword = None
      elif headword is not None:
        line = line.replace("{**}", ".. ").replace("{^}", "^").replace("{sic}", "(??)")
        line = regex.sub(r"^\.", r"<BR>", line)
        line = regex.sub(r"[⁰-⁹]", lambda x: "_" * (ord(x.group(0))-ord("⁰")), line)
        line = regex.sub(r"[²-³]", lambda x: "__" + "_" * (ord(x.group(0))-ord("²")), line)
        line = regex.sub(r"<ls>(.+?)</ls>", r"[[\1]]", line)
        line = regex.sub(r"<ab>(.+?)</ab>", r"\1", line)
        # Once all tags are eliminated, we do the below.
        line = line.replace(" M£", "M£").replace("/", "̭") 
        line = regex.sub(r"{#(.+?)#}", lambda x: devanaagarify(x.group(1)), line)
        line = regex.sub(r"¦ *", "<BR>", line)
        line = regex.sub(r"{%(.+?)%}", r"<i>\1</i>", line)
        line = regex.sub(r"{@(.+?)@}", r"<b>\1</b>", line)
        line = regex.sub(r"।(?=[^ ])", r"। ", line)
        meaning = f"{meaning} {line}"

  logging.info(f"Got {len(definitions)}.")
  file_path = os.path.join(dest_dir, os.path.basename(dest_dir) + ".babylon")
  headers = header_helper.get_default_headers(file_path)
  babylon.dump(dest_path=file_path, definitions=definitions, headers=headers)


if __name__ == '__main__':
  dump()