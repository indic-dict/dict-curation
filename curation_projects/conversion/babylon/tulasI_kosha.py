import logging
import os
from pathlib import Path

from indic_transliteration import sanscript

data_dir = "/home/vvasuki/sanskrit/raw_etexts/koshaH/tulasi_shabda_kosha"
data_files = sorted(Path(data_dir).glob("*.txt"))
outfile_path = "/home/vvasuki/indic-dict/stardict-hindi/hi-head/hi-entries/tulasi_shabda_kosha/tulasi_shabda_kosha.babylon"


os.makedirs(name=os.path.dirname(outfile_path), exist_ok=True)
with open(outfile_path, "w") as outfile:
    pass

for file in data_files:
    with open(str(file)) as csvfile:
        for line in csvfile.readlines():
            entry_parts = line.split(":")
            if len(entry_parts) < 2:
                logging.debug("Skipping line in %s: %s", str(file), line)
                continue
            roots = sanscript.SCHEMES[sanscript.DEVANAGARI].fix_lazy_anusvaara(entry_parts[0].strip()).split(",")
            roots = [root.strip() for root in roots]
            meaning = entry_parts[1].strip()
            with open(outfile_path, "a") as outfile:
                outfile.write("%s\n%s\n\n" % ("|".join(roots), meaning))

