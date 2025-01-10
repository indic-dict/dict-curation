import logging
import os

from sanskrit_data.collection_helper import OrderedSet
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


def dev(x):
  return transliterate(str(x), Scheme.Slp1, Scheme.Devanagari)


def slp(x):
  return transliterate(str(x), Scheme.Devanagari, Scheme.Slp1)


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
      headwords = [dev(dhaatu.aupadeshika)]
      sanaadyanta = dhaatu.with_sanadi(sanadi)
      sanaadi_str = ""
      for p in v.derive(sanaadyanta):
        sanaadyanta_str = dev(p.text)
        if sanaadyanta_str not in headwords:
          headwords.append(sanaadyanta_str)
      if len(sanadi) > 0 :
        sanaadi_str = f" + {'+ '.join([x.name for x in sanaadyanta.sanadi])} = {sanaadyanta_str}"
      entry = dev(f"{dhaatu_str}{sanaadi_str}") + "<BR>"
      for kRt in Krt.choices():
        anga = Pratipadika.krdanta(sanaadyanta, kRt)
        prakriyas = v.derive(anga)
        for p in prakriyas:
          headwords.append(dev(p.text))
          # logging.debug(f"{'|'.join(headwords)}\n{entry}\n")
          entry += dev(f"+{kRt} = {p.text}") + "<BR>"
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
      praatipadika_str = dev(praatipadika.pratipadika.text)
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
              pada_str = dev(prakriya.text)
              headwords.add(pada_str)
              forms.append(pada_str)
            vachana_entry = ", ".join(forms)
            vachana_entries.append(vachana_entry)
          lines.append("; ".join(vachana_entries))
        linga_str = dev(str(linga))
        defintion = Definition(headwords_tuple=tuple(headwords), meaning=f"{praatipadika_str} {linga_str[:4]}<BR>{'<BR>'.join(lines)}")
        definitions.append(defintion)
    logging.info(f"Got {len(definitions)} for {dict_name}.")
    dest_file_path = os.path.join(dest_dir, dict_name, f"{dict_name}.babylon")
    headers = header_helper.get_default_headers(dest_file_path)
    babylon.dump(dest_path=dest_file_path, definitions=definitions, headers=headers)


def dump_taddhitaantas(dest_dir="/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-vyAkaraNa/taddhitAnta/vidyut/", overwrite=False):
  dicts ={
    'a': ("", "इ"),
    'i': ("इ", "उ"),
    'uch': ("उ", "क"),
    'ku': ("क", "च"),
    'chu': ("च", "ट"),
    'Tu': ("ट", "त"),
    'tu1': ("त", "प"),
    'p': ("प", "ब"),
    'b': ("ब", "य"),
    'yr': ("य", "ल"),
    'lv': ("ल", "व"),
    'sh': ("श", "स"),
    's': ("स", "ह"),
    'hal': ("ह", "ा"),
  }
  for dict_name, border, in dicts.items():
    definitions = []
    dict_name = f"vidyut-taddhitAnta-{dict_name}"
    dest_file_path = os.path.join(dest_dir, dict_name, f"{dict_name}.babylon")
    if not overwrite and os.path.exists(dest_file_path):
      logging.info(f"Skipping {dict_name}")
      continue
    logging.info(f"Producing {dict_name}")
    for praatipadika in tqdm(kosha.pratipadikas()):
      if type(praatipadika) in [PratipadikaEntry.Krdanta]:
        continue
      praatipadika_str = dev(praatipadika.pratipadika.text)
      if not (praatipadika_str >= border[0] and praatipadika_str < border[1]):
        continue
      headwords = OrderedSet()
      headwords.add(praatipadika_str)
      lines = []
      for taddhita in Taddhita.choices():
        if str(taddhita) == "YiW":
          continue
        anga = Pratipadika.taddhitanta(praatipadika.pratipadika, taddhita)
        prakriyas = v.derive(anga)
        if len(prakriyas) > 0:
          derivatives = [dev(p.text) for p in prakriyas]
          headwords.extend(derivatives)
          lines.append(f'+ {dev(taddhita)} = {", ".join(derivatives)}')
      linga_str = dev(",".join([str(linga) for linga in praatipadika.lingas]))
      defintion = Definition(headwords_tuple=tuple(headwords), meaning=f"{praatipadika_str} {linga_str}<BR>{'<BR>'.join(lines)}")
      definitions.append(defintion)
    logging.info(f"Got {len(definitions)}.")
    headers = header_helper.get_default_headers(dest_file_path)
    babylon.dump(dest_path=dest_file_path, definitions=definitions, headers=headers)


def print_prakriyA(shabda):
  entries = kosha.get(slp(shabda))
  if len(entries) == 0:
    logging.error(f"Can't get entry for {shabda}.")
    return
  for entry in entries:
    prakriyas = v.derive(entry)
    for p in prakriyas:
      steps = []
      for step in p.history:
        url = "[A](https://ashtadhyayi.github.io/suutra/{step.code[:3]}/{step.code})"
        detail = f"{step.code} → {dev(','.join(step.result))} {url}"
        steps.append(detail)
      md_newline = '  \n'
      logging.info(f"\n{md_newline.join(steps)}\n")
  pass


if __name__ == '__main__':
  pass
  # dump_kRdantas()
  # dump_subantas()
  dump_taddhitaantas()
  # print_prakriyA("वमितवत्")