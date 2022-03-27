import logging
import os
from pathlib import Path

import regex
from indic_transliteration import sanscript


for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")

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
                if len(regex.findall("[ऀ-ॿ]", line)) > 0 and not line.startswith("#"):
                    logging.warning("Skipping line in %s:\n%s", str(file), line)
                continue
            roots = entry_parts[0].strip().split(",")
            roots = [root.strip() for root in roots]
            roots.extend([sanscript.SCHEMES[sanscript.DEVANAGARI].fix_lazy_anusvaara(root) for root in roots])
            from  more_itertools import unique_everseen
            roots = list(unique_everseen(roots))
            for root in roots:
                if " " in root and not root.endswith("यो") and not root.endswith("यौ") and not root.endswith("उ") and not root.endswith("टा"):
                    # logging.warning("%s contains space", root)
                    print(root)
            meaning = entry_parts[1].strip()
            with open(outfile_path, "a") as outfile:
                outfile.write("%s\n%s\n\n" % ("|".join(roots), meaning))

