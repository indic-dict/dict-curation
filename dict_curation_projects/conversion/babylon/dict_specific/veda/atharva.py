"""Build ``av-padasvara`` Babylon lexicon from Śaunaka Atharvaveda padapāṭha."""

from __future__ import annotations

from collections import Counter, defaultdict
import glob
import logging
import os
import regex

from dict_curation import Definition, babylon
from dict_curation.babylon import header_helper
from indic_transliteration.sanscript.schemes.brahmic import accent

from .padasvara_common import build_visvara_headwords

BASE_DIR = "/home/vvasuki/gitland/vishvAsa/vedAH/static/atharva/shaunakam/rUDha-saMhitA/sarvASh_TIkAH"
DEFAULT_DEST_DIRS = (
    "/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-kAvya/av-padasvara",
)

_PP_RE = regex.compile(r"<details><summary>पद-?पाठः</summary>\s*(.*?)\s*</details>", regex.S)
_MULA_RE = regex.compile(r"<details><summary>मूलम्[^<]*</summary>\s*(.*?)\s*</details>", regex.S)


def get_file_dict(file_path: str) -> tuple[list[str], str]:
  with open(file_path, encoding="utf-8") as f:
    content = f.read()
  m = _PP_RE.search(content)
  if not m:
    return [], ""
  detail = regex.sub(r"[\d\.०-९\u200c,]", "", m.group(1))
  words = [w.strip() for w in regex.split(r"[।॥\s]+", detail) if w.strip()]

  mula_path = file_path.replace("sarvASh_TIkAH", "mUlam")
  muula = ""
  if os.path.isfile(mula_path):
    with open(mula_path, encoding="utf-8") as mf:
      m_content = mf.read()
    mm = _MULA_RE.search(m_content)
    if mm:
      muula = regex.sub(r"\s+", " ", mm.group(1)).strip()
  return words, muula


def get_dict(dir_path: str = BASE_DIR) -> tuple[Counter, dict[str, list[str]]]:
  md_files = sorted(glob.glob(os.path.join(dir_path, "**", "[0-9][0-9]*.md"), recursive=True))
  counts: Counter = Counter()
  dict_out: dict[str, list[str]] = defaultdict(list)
  for file_path in md_files:
    words_sasvara, muula = get_file_dict(file_path=file_path)
    if not words_sasvara:
      continue
    locus_id = file_path.replace(dir_path, "").replace(".md", "")
    locus_id = regex.sub(r"_.+?(?=/|$)", "", locus_id)
    seen_in_file: set[str] = set()
    for word in words_sasvara:
      counts[word] += 1
      if word in seen_in_file:
        continue
      seen_in_file.add(word)
      dict_out[word].append(locus_id)
  return counts, dict_out


def dump_babylon(dest_dir: str, counts: Counter | None = None, sasvara_word_dict: dict[str, list[str]] | None = None) -> None:
  if counts is None or sasvara_word_dict is None:
    counts, sasvara_word_dict = get_dict(dir_path=BASE_DIR)
  visvara_to_sasvara: dict[str, list[str]] = defaultdict(list)
  for word in sasvara_word_dict:
    visvara_word = regex.sub(fr"{accent.ACCENTS_PATTERN}|ऽ", "", word).strip()
    if visvara_word:
      visvara_to_sasvara[visvara_word].append(word)

  definitions: list[Definition] = []
  for visvara_word in sorted(visvara_to_sasvara.keys()):
    variants = sorted(visvara_to_sasvara[visvara_word], key=lambda w: (-counts[w], w))
    headwords = build_visvara_headwords(visvara_word, include_optitrans=False)
    for sasvara_word in variants:
      citations = "<br>".join(sasvara_word_dict[sasvara_word])
      meaning = f"{sasvara_word} ({counts[sasvara_word]})<br><br>{citations}"
      definitions.append(Definition(headwords_tuple=headwords, meaning=meaning))

  logging.info("Got %d AV definitions.", len(definitions))
  dict_name = os.path.basename(os.path.normpath(dest_dir))
  file_path = os.path.join(dest_dir, f"{dict_name}.babylon")
  headers = {
      "bookname": f"{dict_name} (sa-sa)",
      "sametypesequence": "h",
      "stripmethod": "keep",
  }
  babylon.dump(dest_path=file_path, definitions=definitions, headers=headers)


def dump_all(dest_dirs: tuple[str, ...] = DEFAULT_DEST_DIRS, *, include_meanings: bool = True) -> None:
  import logging

  from .padasvara_common import (
      build_compound_extra_headwords,
      convert_counts_and_loci_to_us,
      dump_padasvara_babylon,
  )
  from .taittiriya import _join_compound_sandhi
  from . import vedic_meanings

  raw_counts, raw_loci = get_dict(dir_path=BASE_DIR)
  counts, loci, fallback_count = convert_counts_and_loci_to_us(raw_counts, raw_loci, already_us=False)
  extra_headwords = build_compound_extra_headwords(counts.keys(), _join_compound_sandhi)
  meanings = (
      vedic_meanings.build_meaning_lookup_map(
          "av", counts, already_us=True, source_dir=BASE_DIR, use_cache=True
      )
      if include_meanings
      else None
  )
  logging.info(
      "Converted AV padasvara to US notation (%d unique padas, %d fallbacks, %d extra headwords, %d meanings)",
      len(counts),
      fallback_count,
      len(extra_headwords),
      len(meanings or {}),
  )
  readme_text = (
      "## av-padasvara\n"
      "- Atharvaveda Śaunakīya padapāṭha (US accent notation).\n"
      "- Built by `dict_curation_projects.conversion.babylon.dict_specific.veda.atharva`.\n"
  )
  for dest_dir in dest_dirs:
    if os.path.isdir(os.path.dirname(dest_dir)):
      dump_padasvara_babylon(
          counts,
          loci,
          dest_dir=dest_dir,
          write_final=False,
          citation_sep=", ",
          extra_headwords=extra_headwords,
          meanings=meanings,
      )
      readme_path = os.path.join(dest_dir, "README.md")
      if not os.path.exists(readme_path):
        with open(readme_path, "w", encoding="utf-8") as f:
          f.write(readme_text)


if __name__ == "__main__":
  dump_all()
