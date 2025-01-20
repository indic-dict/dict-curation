import logging
import os
from copy import copy
from indic_transliteration.vidyut_helper import dev, slp

import regex
from click.utils import make_default_short_help
from sanskrit_data.collection_helper import OrderedSet
from tqdm import tqdm
from vidyut.kosha import Kosha, PratipadikaEntry
from vidyut.prakriya import Data, Vyakarana, Sanadi, Krt, Pratipadika, Vibhakti, Vacana, Linga, Pada, Taddhita, \
  DhatuPada, Lakara, Purusha, Prayoga, Gana, Dhatu

from dict_curation import Definition
from dict_curation import babylon
from dict_curation.babylon import header_helper

v = Vyakarana()
data = Data("/home/vvasuki/gitland/ambuda-org/vidyut-latest/prakriya")
code_to_sutra = {(s.source, s.code): s.text for s in data.load_sutras()}
kosha = Kosha("/home/vvasuki/gitland/ambuda-org/vidyut-latest/kosha")


sanaadi_dict_kRdanta ={
  'vidyut-kRdanta': (),
  'vidyut-Nic-kRdanta': (Sanadi.Ric,),
  'vidyut-san-kRdanta': (Sanadi.san,),
  'vidyut-yaN-kRdanta': (Sanadi.yaN,),
  'vidyut-yaNluk-kRdanta': (Sanadi.yaNluk,),
  'vidyut-san-Nic-kRdanta': (Sanadi.san, Sanadi.Ric),
  'vidyut-Nic-san-kRdanta': (Sanadi.Ric, Sanadi.san)
}


sanaadi_dict_tiNanta ={
  'vidyut-tiN': (),
  'vidyut-Nic-tiN': (Sanadi.Ric,),
  'vidyut-san-tiN': (Sanadi.san,),
  'vidyut-yaN-tiN': (Sanadi.yaN,),
  'vidyut-yaN-luk-tiN': (Sanadi.yaNluk,),
  'vidyut-san-Nic-tiN': (Sanadi.san, Sanadi.Ric),
  'vidyut-Nic-san-tiN': (Sanadi.Ric, Sanadi.san)
}



def _get_kRdanta_entry(entry_head, headwords_in, sanaadyanta, *args, **kwargs):
  entry = f"{entry_head}<BR>"
  for kRt in Krt.choices():
    anga = Pratipadika.krdanta(sanaadyanta, kRt)
    prakriyas = v.derive(anga)
    for p in prakriyas:
      headwords_in.add(dev(p.text))
      # logging.debug(f"{'|'.join(headwords)}\n{entry}\n")
      entry += dev(f"+{kRt} = {p.text}") + "<BR>"

  defintion = Definition(headwords_tuple=tuple(headwords_in), meaning=entry)
  return [defintion]


def _get_tiNanta_entry(entry_head, headwords_in, sanaadyanta, prayoga):
  definitions = []
  for lakara in Lakara.choices():
    headwords = []
    table_lines = []
    for parasmai_mode in [DhatuPada.Parasmaipada, DhatuPada.Atmanepada]:
      lines = []
      pada_headwords = []
      for purusha in Purusha.choices():
        vacana_forms = []
        for vacana in Vacana.choices():
          prakriyas = v.derive(Pada.Tinanta(
            dhatu=sanaadyanta,
            prayoga=prayoga,
            dhatu_pada=parasmai_mode,
            lakara=lakara,
            purusha=purusha,
            vacana=vacana,
          ))
          forms = [dev(p.text) for p in prakriyas]
          pada_headwords.extend(forms)
          vacana_forms.append('/ '.join(forms))
        puruSha_line = f"{'<BR>'.join(vacana_forms)}"
        lines.append(puruSha_line)
      if len(pada_headwords) > 0:
        table_head = f"{entry_head} {dev(lakara)}"
        if prayoga == Prayoga.Karmani:
          table_head = f"{table_head} अकर्तरि<BR><BR>"
        else:
          table_head = f"{table_head} {dev(parasmai_mode)}"
        table_lines.append(table_head)
        table_lines.append("<BR>--<BR>".join(lines))
        headwords.extend(pada_headwords)
    if len(headwords) > 0:
      headwords = OrderedSet(list(headwords_in) + headwords)
      entry = f"<BR><BR>".join(table_lines)
      entry = entry.replace("लृँत्", "लृँट्")
      definition = Definition(headwords_tuple=tuple(headwords), meaning=entry)
      definitions.append(definition)
  return definitions


def dump_sanaadi_dicts(dest_dir="/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-vyAkaraNa/kRdanta/vidyut/", sanaadi_dict=sanaadi_dict_kRdanta, make_entry=_get_kRdanta_entry):
  dhaatu_entries = data.load_dhatu_entries()

  for dict_name, sanadi, in sanaadi_dict.items():
    if sanaadi_dict == sanaadi_dict_kRdanta:
      prayogas = [Prayoga.Kartari]
    else:
      prayogas = [Prayoga.Kartari, Prayoga.Karmani]
    for prayoga in prayogas:
      if prayoga == Prayoga.Kartari:
        prayoga_suffix = ""
      else:
        prayoga_suffix = "-akartari"
      dict_name = f"{dict_name}{prayoga_suffix}"
      definitions = []
      for dhaatu_entry in tqdm(dhaatu_entries, desc=f"Dhaatus {dict_name}", position=0, leave=True):
        dhaatu = dhaatu_entry.dhatu
        headwords_in = OrderedSet()
        aupadeshika = dev(dhaatu.aupadeshika)
        headwords_in.extend([aupadeshika, regex.sub("[॒॑]", "", aupadeshika), regex.sub("[॒॑ँ]", "", aupadeshika)])
        dhaatu_str = f"{dhaatu.aupadeshika} {dhaatu_entry.artha} ({dhaatu.gana})"
        for p in v.derive(dhaatu):
          dhaatu_form = dev(p.text)
          if dev(dhaatu.aupadeshika) != dhaatu_form:
            dhaatu_str += f" {dhaatu_form}"
            headwords_in.add(dhaatu_form)
        if dhaatu.antargana is not None:
          dhaatu_str = f"{dhaatu_str} ({dhaatu.antargana})"
        sanaadyanta = dhaatu.with_sanadi(sanadi)
        sanaadi_str = ""
        for p in v.derive(sanaadyanta):
          sanaadyanta_str = dev(p.text)
          headwords_in.add(sanaadyanta_str)
        if len(sanadi) > 0 :
          sanaadi_str = f" + {'+ '.join([x.name for x in sanaadyanta.sanadi])} = {sanaadyanta_str}"
        entry_head = dev(f"{dhaatu_str}{sanaadi_str}")
        definitions_d = make_entry(entry_head, headwords_in, sanaadyanta, prayoga)
        definitions.extend(definitions_d)
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


if __name__ == '__main__':
  pass
  # dump_sanaadi_dicts(dest_dir="/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-vyAkaraNa/kRdanta/vidyut/", sanaadi_dict=sanaadi_dict_kRdanta, make_entry=_get_kRdanta_entry)
  # dump_sanaadi_dicts(dest_dir="/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-vyAkaraNa/tiNanta/vidyut/", sanaadi_dict=sanaadi_dict_tiNanta, make_entry=_get_tiNanta_entry)
  # dump_subantas()
  # dump_taddhitaantas(overwrite=True)
  # print_prakriyA("उच्चैश्रवाः")
  # derive_and_print_kRdanta()