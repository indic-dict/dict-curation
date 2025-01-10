import logging
import os

from chandas.svat.identify.identifier import OrderedSet
from tqdm import tqdm
from vidyut.kosha import Kosha, PratipadikaEntry
from vidyut.lipi import transliterate, Scheme
from vidyut.prakriya import Data, Vyakarana, Sanadi, Krt, Pratipadika, Vibhakti, Vacana, Linga, Pada, Taddhita

from dict_curation import Definition
from dict_curation import babylon
from dict_curation.babylon import header_helper

v = Vyakarana()
data = Data("/home/vvasuki/gitland/ambuda-org/vidyut-latest/prakriya")
kosha = Kosha("/home/vvasuki/gitland/ambuda-org/vidyut-latest/kosha")

def dump_kRdantas(dest_dir="/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-vyAkaraNa/kRdanta/vidyut/"):
  dhatus = [e.dhatu for e in data.load_dhatu_entries()]
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
      dhaatu_str = f"{dhaatu.aupadeshika} ({dhaatu.gana})"
      if dhaatu.antargana is not None:
        dhaatu_str = f"{dhaatu_str} ({dhaatu.antargana})"
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


def dump_subantas(dest_dir="/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-vyAkaraNa/subanta/vidyut/"):
  dicts ={
    'a': ("", "इ"),
    'i': ("इ", "उ"),
    'uch': ("उ", "क"),
    'ku': ("क", "च"),
    'chu': ("च", "ट"),
    'Tu': ("ट", "त"),
    'tu1': ("त", "प"),
    'pu': ("प", "य"),
    'yrlv': ("य", "श"),
    'shal': ("श", "ा"),
  }
  for dict_name, border, in dicts.items():
    definitions = []
    dict_name = f"vidyut-subanta-{dict_name}"
    for praatipadika in tqdm(kosha.pratipadikas()):
      if type(praatipadika) in [PratipadikaEntry.Krdanta]:
        continue
      praatipadika_str = transliterate(praatipadika.pratipadika.text, Scheme.Slp1, Scheme.Devanagari)
      if not (praatipadika_str >= border[0] and praatipadika_str < border[1]):
        continue
      for linga in praatipadika.lingas:
        headwords = OrderedSet()
        headwords.add(praatipadika_str)
        lines = []
        for vibhakti in Vibhakti.choices():
          vachana_entries = []
          for vacana in Vacana.choices():
            prakriyas = v.derive(Pada.Subanta(
              pratipadika=praatipadika.pratipadika,
              linga=linga,
              vibhakti=vibhakti,
              vacana=vacana,
            ))
            forms = []
            for prakriya in prakriyas:
              pada_str = transliterate(prakriya.text, Scheme.Slp1, Scheme.Devanagari)
              headwords.add(pada_str)
              forms.append(pada_str)
            vachana_entry = ", ".join(forms)
            vachana_entries.append(vachana_entry)
          lines.append("; ".join(vachana_entries))
        linga_str = transliterate(str(linga), Scheme.Slp1, Scheme.Devanagari)
        defintion = Definition(headwords_tuple=tuple(headwords), meaning=f"{praatipadika_str} {linga_str[:4]}<BR>{'<BR>'.join(lines)}")
        definitions.append(defintion)
    logging.info(f"Got {len(definitions)} for {dict_name}.")
    dest_file_path = os.path.join(dest_dir, dict_name, f"{dict_name}.babylon")
    headers = header_helper.get_default_headers(dest_file_path)
    babylon.dump(dest_path=dest_file_path, definitions=definitions, headers=headers)


def dump_taddhitaantas(dest_dir="/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-vyAkaraNa/taddhitAnta/vidyut/"):
  definitions = []
  dict_name = "vidyut-taddhitAnta"
  for praatipadika in tqdm(kosha.pratipadikas()):
    if type(praatipadika) in [PratipadikaEntry.Krdanta]:
      continue
    praatipadika_str = transliterate(praatipadika.pratipadika.text, Scheme.Slp1, Scheme.Devanagari)
    for taddhita in Taddhita.choices():
      anga = Pratipadika.taddhitanta(praatipadika, taddhita)
      prakriyas = v.derive(anga)
      for p in prakriyas:
        print(taddhita, p.text)
        # lines.append("; ".join(vachana_entries))
      defintion = Definition(headwords_tuple=tuple(headwords), meaning=f"{praatipadika_str} {linga}<BR>{'<BR>'.join(lines)}")
      definitions.append(defintion)
  logging.info(f"Got {len(definitions)}.")
  dest_file_path = os.path.join(dest_dir, dict_name, f"{dict_name}.babylon")
  headers = header_helper.get_default_headers(dest_file_path)
  babylon.dump(dest_path=dest_file_path, definitions=definitions, headers=headers)


if __name__ == '__main__':
  pass
  # dump_kRdantas()
  dump_subantas()