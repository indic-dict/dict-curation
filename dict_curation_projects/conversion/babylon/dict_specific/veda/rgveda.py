"""Build ``rv-padasvara-dev`` Babylon lexicon from ``vedAH_Rk`` Śākala padapāṭha."""

from __future__ import annotations

from collections import Counter, defaultdict
import glob
import logging
import os
import regex

from indic_transliteration.sanscript.schemes.brahmic import accent

from .padasvara_common import (
    build_compound_extra_headwords,
    convert_counts_and_loci_to_us,
    dump_padasvara_babylon,
    us_to_dependent_pada,
)

BASE_DIR = "/home/vvasuki/gitland/vishvAsa/vedAH_Rk/static/shAkalam/saMhitA/sarvASh_TIkAH"
DEFAULT_DEST_DIRS = (
    "/home/vvasuki/gitland/sanskrit/raw_etexts/koshaH/indic-dict/kAvya/rv-padasvara-dev",
    "/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-kAvya/rv-padasvara-dev",
    "/home/vvasuki/gitland/indic-dict/stardict/stardict-sanskrit-kAvya/rv-padasvara-dev",
)

_PP_RE = regex.compile(r"<details><summary>पद-पाठः</summary>\s*(.*?)\s*</details>", regex.S)

# Verified single-verse encoding/OCR typos in vedAH_Rk <summary>पद-पाठः</summary>,
# cross-checked against <summary>Thomson & Solcum</summary> in the same files:
_KNOWN_PP_TOKEN_FIXES: dict[str, str] = {
    "हि॒तऽमि॑त्रः॑": "हि॒तऽमि॑त्रः",      # 1.73.3 हित᳓मित्रो
    "ति॒ग्मऽअ॑नी॑कम्": "ति॒ग्मऽअ॑नीकम्",  # 1.95.2 तिग्मा᳓नीकं
    "प्र॑ऽमु॒ञ्चन्": "प्रऽमु॒ञ्चन्",      # 1.140.8 प्रमुञ्च᳓न्
    "ग॑म्याः": "ग॒म्याः॒",               # 1.186.6 न इह᳓ गम्याः
    "श्र॑यन्ताम्": "श्र॒य॒न्ता॒म्",       # 2.3.5 वि᳓ श्रयन्ताम्
    "सु॒ऽधि॑तम्": "सुऽधि॑तम्",           # 4.2.10, 6.15.2 सु᳓धितं
    "अ॒भ॑रन्": "अभ॑रन्",                # 4.33.4 अ᳓भरन्
    "ह॒व्य॒ऽवाह॑नः॑": "ह॒व्य॒ऽवाह॑नः",    # 5.25.4 हव्यवा᳓हनो
    "पुर॑म्ऽधि॑म्": "पुर॑म्ऽधिम्",        # 6.21.9 पु᳓रंधिं
    "त्रि॑ऽपृ॒ष्ठैः": "त्रि॒ऽपृ॒ष्ठैः",    # 7.37.1 अभि᳓ त्रिपृष्ठैः᳓
    "अहेः॑े॑": "अहेः॑",                  # 8.93.14 अ᳓हेर्
    "स्पः॑": "स्पः॒",                    # 9.70.10 निद᳓ स्पः
    "माँ॒श्च॑त्वे": "माँश्च॑त्वे",        # 9.97.54 माँ᳓श्चत्वे
    "सु॒ऽम॒तीः॑": "सु॒ऽम॒तीः",           # 10.20.10 सुमती᳓र्
    "अ॒भी॑द्धात्": "अ॒भीद्धा॑त्",        # 10.190.1 चाभी᳓द्धात्
}


def strip_rk_iti(raw_tok: str) -> str:
  """Normalize a single ``।``-delimited Śākala padapāṭha token, stripping ``इति`` pragṛhya/r-stem markers."""
  tok = regex.sub(r"\[[^\]]*\]", "", raw_tok)
  tok = regex.sub(r"\s+", " ", tok).strip()
  if not tok:
    return ""
  tok = _KNOWN_PP_TOKEN_FIXES.get(tok, tok)
  if tok in ("इति॑", "इ॒ति॒", "इति"):
    return tok

  # Case 1: "<surface> इति॑ <gloss>" (e.g. "श॒त॒क्र॒तो॒ इति॑ शतऽक्रतो", "स्व१॒॑रिति॑ स्वः॑")
  m_sp = regex.match(r"^(\S+)\s+इति[॒॑]*\s+(\S+)$", tok)
  if m_sp:
    left, right = m_sp.group(1), m_sp.group(2)
    right = _KNOWN_PP_TOKEN_FIXES.get(right, right)
    if regex.search(accent.ACCENTS_PATTERN, right):
      return right
    left_us = accent.to_US_accents(left)
    if "\u1cd3" not in left_us and "\u1cd9" not in left_us:
      return us_to_dependent_pada(right)
    return right

  # Case 2: fused "<surface>रिति॑ <gloss>" / "<surface>तीति/ेति <gloss>" or "<surface>इत्य/इती<gloss>"
  # (never touch lyaBanta gerunds like "अ॒भि॒ऽइत्य॑" where nothing follows "इत्य॑"!)
  m_fus = regex.match(
      r"^(\S+?)(?:रिति[॒॑]*\s+|(?:तीति|ेति)[॒॑]*\s+|इ[॒॑]?त्य[॒॑]?|इ[॒॑]?ती[॒॑]?)(\S+)$",
      tok,
  )
  if m_fus and "ऽइत्य" not in tok:
    left_full = tok
    right = _KNOWN_PP_TOKEN_FIXES.get(m_fus.group(2), m_fus.group(2))
    # Verify right bare consonant/vowel stem resembles left prefix (guards against false splits)
    l_bare = regex.sub(fr"{accent.ACCENTS_PATTERN}|[ऽ१२३123]", "", m_fus.group(1))
    r_bare = regex.sub(fr"{accent.ACCENTS_PATTERN}|[ऽ१२३123]", "", right)
    if l_bare and r_bare and (r_bare[0] == l_bare[0] or (l_bare[0] in "अआइईउऊऋएओ" and r_bare[0] in "अआइईउऊऋएओ")):
      if regex.search(accent.ACCENTS_PATTERN, right):
        return right
      full_us = accent.to_US_accents(left_full)
      left_us = regex.split(r"रि\u1cd3?ति|ती\u1cd3?ति|इ\u1cd3?त्य|इ\u1cd3?ती", full_us)[0]
      if "\u1cd3" not in left_us and "\u1cd9" not in left_us:
        return us_to_dependent_pada(right)
      return right

  # Case 3: pure pragṛhya "<pada> इति॑" (e.g. "रोद॑सी॒ इति॑", "द॒धा॒थे॒ इति॒॑")
  if regex.search(r"\s+इति[॒॑]*$", tok):
    us = accent.to_US_accents(tok)
    us_pada = regex.sub(r"\s+इ[\u1cd3\u1cd9]?ति[\u1cd3\u1cd9]?$", "", us).strip()
    # Normalize "ऊं" pragṛhya -> "ऊँ" / keep original nasal
    return us_to_dependent_pada(us_pada)

  # Case 4: standalone r-stem "<stem>रिति॑" without gloss (e.g. "पुन॒रिति॑" -> "पुनः॑", "प्रात॒रिति॑" -> "प्रातः")
  if regex.search(r"रिति[॒॑]?$", tok) and " " not in tok:
    us = accent.to_US_accents(tok)
    us_pada = regex.sub(r"रि[\u1cd3\u1cd9]?ति$", "ः", us)
    return us_to_dependent_pada(us_pada)

  # Strip pluta digits like स्व१॒॑ः if any remain
  tok = regex.sub(r"[१२३123]", "", tok)
  tok = _KNOWN_PP_TOKEN_FIXES.get(tok, tok)
  return tok


def collect_rv_padasvara(base_dir: str = BASE_DIR) -> tuple[Counter, dict[str, list[str]]]:
  """Extract all Śākala padapāṭha padas with exact frequencies and citations."""
  counts: Counter = Counter()
  loci: dict[str, list[str]] = defaultdict(list)
  md_files = sorted(glob.glob(os.path.join(base_dir, "[0-9][0-9]", "*", "[0-9][0-9]*.md")))
  for path in md_files:
    with open(path, encoding="utf-8") as f:
      txt = f.read()
    m = _PP_RE.search(txt)
    if not m:
      continue
    rel = path.split("/sarvASh_TIkAH/")[1].replace(".md", "")
    mandala, sukta, rch = rel.split("/")
    loc = f"{int(mandala)}.{int(sukta)}.{int(rch.split('_')[0])}"
    for raw_tok in regex.split(r"[।॥]+", m.group(1)):
      pada = strip_rk_iti(raw_tok)
      if not pada:
        continue
      counts[pada] += 1
      if not loci[pada] or loci[pada][-1] != loc:
        loci[pada].append(loc)

  # Verify zero fake non-jātya svaritas
  bad_svaritas = []
  for pada, cnt in counts.items():
    us = accent.to_US_accents(pada)
    if "\u1cd9" in us:
      for sm in regex.finditer(r"([\u0900-\u0963\u0971-\u097f]+?)\u1cd9", us):
        syl = sm.group(1)
        if "य" not in syl and "व" not in syl:
          bad_svaritas.append((pada, us, cnt, loci[pada][:3]))
  if bad_svaritas:
    raise ValueError(f"Fake non-jātya svaritas remain in RV padasvara: {bad_svaritas[:10]}")

  logging.info("Collected %d unique RV padas (%d total tokens)", len(counts), sum(counts.values()))
  return counts, loci


def dump_all(dest_dirs: tuple[str, ...] = DEFAULT_DEST_DIRS) -> None:
  from .taittiriya import _join_compound_sandhi

  raw_counts, raw_loci = collect_rv_padasvara()
  counts, loci, fallback_count = convert_counts_and_loci_to_us(raw_counts, raw_loci, already_us=False)
  bad_us_svaritas = []
  for pada, cnt in counts.items():
    if "\u1cd9" in pada:
      for sm in regex.finditer(r"([\u0900-\u0963\u0971-\u097f]+?)\u1cd9", pada):
        syl = sm.group(1)
        if "य" not in syl and "व" not in syl:
          bad_us_svaritas.append((pada, cnt, loci[pada][:3]))
  if bad_us_svaritas:
    raise ValueError(f"Fake non-jātya svaritas remain in US RV padasvara: {bad_us_svaritas[:10]}")
  extra_headwords = build_compound_extra_headwords(counts.keys(), _join_compound_sandhi)
  logging.info(
      "Converted RV padasvara to US notation (%d unique padas, %d fallbacks, %d extra headwords)",
      len(counts),
      fallback_count,
      len(extra_headwords),
  )
  readme_text = (
      "## rv-padasvara-dev\n"
      "- Ṛgveda Śākala padapāṭha (US accent notation).\n"
      "- Built by `dict_curation_projects.conversion.babylon.dict_specific.veda.rgveda`.\n"
  )
  for dest_dir in dest_dirs:
    if os.path.isdir(os.path.dirname(dest_dir)):
      dump_padasvara_babylon(
          counts,
          loci,
          dest_dir=dest_dir,
          write_final=True,
          citation_sep=", ",
          extra_headwords=extra_headwords,
      )
      readme_path = os.path.join(dest_dir, "README.md")
      if not os.path.exists(readme_path):
        with open(readme_path, "w", encoding="utf-8") as f:
          f.write(readme_text)


if __name__ == "__main__":
  dump_all()
