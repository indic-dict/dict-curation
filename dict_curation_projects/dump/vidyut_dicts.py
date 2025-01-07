import logging
import os

from tqdm import tqdm
from vidyut.lipi import transliterate, Scheme
from vidyut.prakriya import Data, Vyakarana, Sanadi, Krt, Pratipadika

from dict_curation import Definition
from dict_curation import babylon
from dict_curation.babylon import header_helper

v = Vyakarana()
data = Data("/home/vvasuki/gitland/ambuda-org/vidyut-latest/prakriya")
dhatus = [e.dhatu for e in data.load_dhatu_entries()]

def dump_kRdantas(dest_dir="/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-vyAkaraNa/kRdanta/vidyut/"):
  sanaadi_dict ={
    'vidyut-kRdanta': (),
    'vidyut-Nic-kRdanta': (Sanadi.Ric,),
    'vidyut-san-kRdanta': (Sanadi.san,),
    'vidyut-yaN-kRdanta': (Sanadi.yaN,),
    'vidyut-yaNluk-kRdanta': (Sanadi.yaNluk,),
    'vidyut-san-Nic-kRdanta': (Sanadi.san, Sanadi.Ric),
    'vidyut-Nic-san-kRdanta': (Sanadi.Ric, Sanadi.san)
  }


  v = Vyakarana()

  for dict_name, sanadi, in sanaadi_dict.items():
    definitions = []
    for dhaatu in tqdm(dhatus, desc=f"Dhaatus {dict_name}", position=0, leave=True):
      dhaatu_str = f"{dhaatu.aupadeshika} ({dhaatu.gana.name})"
      if dhaatu.antargana is not None:
        dhaatu_str = f"{dhaatu_str} ({dhaatu.antargana.name})"
      headwords = [transliterate(dhaatu.aupadeshika, Scheme.Slp1, Scheme.Devanagari)]
      sanaadyanta = dhaatu.with_sanadi(sanadi)
      sanaadi_str = ""
      for p in v.derive(sanaadyanta):
        sanaadyanta_str = transliterate(p.text, Scheme.Slp1, Scheme.Devanagari)
        if sanaadyanta_str not in headwords:
          headwords.append(sanaadyanta_str)
      if len(sanadi) > 0 :
        sanaadi_str = f" + {'+ '.join([x.name for x in sanaadyanta.sanadi])} = {sanaadyanta_str}"
      entry = transliterate(f"{dhaatu_str}{sanaadi_str}", Scheme.Slp1, Scheme.Devanagari) + "<BR>"
      for kRt in Krt.choices():
        anga = Pratipadika.krdanta(sanaadyanta, kRt)
        prakriyas = v.derive(anga)
        for p in prakriyas:
          headwords.append(transliterate(p.text, Scheme.Slp1, Scheme.Devanagari))
          # logging.debug(f"{'|'.join(headwords)}\n{entry}\n")
          entry += transliterate(f"+{kRt} = {p.text}", Scheme.Slp1, Scheme.Devanagari) + "<BR>"
      defintion = Definition(headwords_tuple=tuple(headwords), meaning=entry)
      definitions.append(defintion)
    logging.info(f"Got {len(definitions)}.")
    dest_file_path = os.path.join(dest_dir, dict_name, f"{dict_name}.babylon")
    headers = header_helper.get_default_headers(dest_file_path)
    babylon.dump(dest_path=dest_file_path, definitions=definitions, headers=headers)


if __name__ == '__main__':
  dump_kRdantas()