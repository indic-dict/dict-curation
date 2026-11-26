"""Build ``syv-vs-m-padasvara`` and ``syv-vs-k-padasvara`` Babylon lexicons from Śukla-Yajurveda padapāṭha.

Sources:
- Mādhyandina (``syv-vs-m-padasvara``): ``<summary>पदपाठः - दयानन्दादि</summary>`` across Mādhyandina ``sarva-prastutiH``.
- Kāṇva (``syv-vs-k-padasvara``): accented ``<summary>पदपाठः</summary>`` / ``<summary>पदपाठः - काण्वः</summary>`` across Kāṇva ``sarva-prastutiH`` (falling back to exact-reading shared ``पदपाठः - दयानन्दादि`` when Kāṇva padapāṭha is absent or unaccented).
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import glob
import logging
import os
from pathlib import Path
import regex

from doc_curation.sanskrit.accent.reconciler import find_js_include_spans
from doc_curation.sanskrit.accent.samhita_splitter import parse_top_level_details

from .padasvara_common import (
    build_compound_extra_headwords,
    convert_counts_and_loci_to_us,
    dump_padasvara_babylon,
)

SOURCE_DIR = "/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/content/vAjasaneyam/mAdhyandinam/saMhitA/sarva-prastutiH"
STATIC_SOURCE_DIR = "/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/static/vAjasaneyam/mAdhyandinam/saMhitA/sarvASh_TIkAH"
DEFAULT_DEST_DIRS = (
    "/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-kAvya/syv-vs-m-padasvara",
)
KANVA_SOURCE_DIR = "/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/content/vAjasaneyam/kANvam/saMhitA/sarva-prastutiH"
KANVA_DEFAULT_DEST_DIRS = (
    "/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-kAvya/syv-vs-k-padasvara",
)
VISHVASA_ROOT = "/home/vvasuki/gitland/vishvAsa"
URL_ATTR_RE = regex.compile(r"""url=["']([^"']+)["']""")

ACC = r"[\u0951-\u0954\u1cd0-\u1ce8\u1cf9\u1cfa]"
MATRA = r"[िीुूृेैोौ]"
DEVA = "\u0900-\u097f"
PADA_BLOCK_RE = regex.compile(r"<summary>पदपाठः - दयानन्दादि</summary>(.*?)</details>", regex.S)
# The padapATha glosses a pada as "pada iti resolved-pada" (e.g.
# "सोम॑राज्ञी॒रिति॒ सोम॑ऽराज्ञीः"), the "iti" being written either glued to the
# pada before it, on its own, or glued to the pada after it ("इत्यु॒पऽस्थे॑").
GLUE_NEXT_RE = regex.compile(rf"(?:इत्य|ेत्य|ीत्य|(?<=इ)त्य|(?<=म्)त्य|(?<=र्)त्य|(?<=्)त्य)(?P<acc>{ACC}*)")
# "iti" merged with the pada on *both* sides, e.g. "अ॒श्विभ्या॒मित्य॒श्विऽभ्या॑म्";
# only taken as a gloss when the two halves really are the same pada.
GLUE_BOTH_RE = regex.compile(rf"(?:{MATRA}?)त्य(?P<acc>{ACC}*)")
ITI_WORD_RE = regex.compile(rf"(?:^|(?<=\s)|(?<=ऽ)|(?<={MATRA}))(?:इति|ेति|ीति){ACC}*ऽ?")
# a pada ending in -ti followed by a pada beginning with i ("…स्पती॒इतीन्द्रा॒…"),
# the two i-sounds merging into "…ती"
ITI_VOWEL_NEXT_RE = regex.compile(rf"(?:{MATRA}|्)?ति{ACC}*ऽ?(?=[इीि])")
# "iti" whose final ि merged with a following (post-pada) इ into ी: "इ॒मेऽइती॒मे"
ITI_LONG_I_RE = regex.compile(rf"(?:इ|े|ी)?ती{ACC}*ऽ?(?=\S)")
ITI_TAIL_RE = regex.compile(rf"(?:{MATRA}|्)?ति{ACC}*ऽ?(?=\s|$)")
MATRA_TO_VOWEL = {"ा": "आ", "ि": "इ", "ी": "ई", "ु": "उ", "ू": "ऊ", "ृ": "ऋ", "े": "ए", "ै": "ऐ", "ो": "ओ", "ौ": "औ"}


def _restore_initial_vowel(fragment: str, accents: str = "") -> str:
  """Undo the sandhi of the final ``i`` of *iti* with the vowel starting the next pada.

  The accent marks written right after the merged ``ity`` belong to that vowel.
  """
  if fragment and fragment[0] in MATRA_TO_VOWEL:
    return MATRA_TO_VOWEL[fragment[0]] + accents + fragment[1:]
  return "अ" + accents + fragment


def _similar_halves(a: str, b: str) -> bool:
  """Whether two gloss halves look like the same pada (a gloss, not a genuine word)."""
  strip = lambda s: regex.sub(rf"{ACC}|[ऽ\s]", "", s)
  a, b = strip(a), strip(b)
  common = 0
  for ca, cb in zip(a, b):
    if ca != cb:
      break
    common += 1
  return common >= min(4, len(a), len(b))


def strip_gloss(token: str) -> list[str]:
  """Return the pada(s) of a padapATha token, resolving ``X iti Y`` glosses.

  The analyzed form (``Y``, e.g. ``सोमऽराज्ञीः``) is preferred, since that is the
  pada itself; the sandhi-joined ``X`` is only a by-form of it.  A token may hide
  more than one pada (the source occasionally omits a daṇḍa).
  """
  m = GLUE_NEXT_RE.search(token)
  if m and token[m.end():].strip():
    return _restore_initial_vowel(token[m.end():].strip(), m.group("acc")).split()
  for m in GLUE_BOTH_RE.finditer(token):
    post = _restore_initial_vowel(token[m.end():].strip(), m.group("acc"))
    if _similar_halves(token[:m.start()], post):
      return post.split()
  m = ITI_WORD_RE.search(token)
  if m:
    post = token[m.end():].strip()
    if post:
      return post.split()
    pre = regex.sub(rf"(?:{MATRA}|्)$", "", token[:m.start()].strip())
    if pre:
      return pre.split()
  m = ITI_VOWEL_NEXT_RE.search(token)
  if m:
    rest = token[m.end():]
    if rest[0] in "ीि":
      rest = "इ" + rest[1:]
    return rest.split()
  for m in ITI_LONG_I_RE.finditer(token):
    init_i = "ई" if token[:m.start()].lstrip().startswith("ई") else "इ"
    post = init_i + token[m.end():].strip()
    if _similar_halves(token[:m.start()], post):
      return post.split()
  m = ITI_TAIL_RE.search(token)
  if m:
    post = token[m.end():].strip()
    if post:
      return post.split()
    pre = regex.sub(rf"(?:{MATRA}|्)$", "", token[:m.start()].strip())
    if pre:
      return pre.split()
  return [token]


def _page_key(path: str) -> tuple[int, int]:
  adhyaya_str, file_name = path.split(os.sep)[-2:]
  return int(adhyaya_str), int(file_name.split("_")[0])


_DEVA_TO_ASCII_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_SECTION_HEADING_RE = regex.compile(r"(?m)^##\s+([०-९0-9]+)[^\n]*\n")


def _ingest_pp_body(
    body: str,
    adhyaya: int,
    mantra_num: int,
    counts: Counter,
    loci: dict[str, list[str]],
    *,
    allow_segment_bump: bool = False,
) -> None:
  segment = 0
  for raw_token in body.replace("\n", " ").split("।"):
    token = regex.sub(r"[\u200c\u200d\s]+", " ", raw_token).strip()
    token = regex.sub(r"[०-९0-9]+$", "", token).strip()
    if not token:
      continue
    if regex.fullmatch(r"[०-९0-9]+", token):
      if allow_segment_bump:
        segment += 1
      continue
    if not regex.search(f"[{DEVA}]", token):
      continue
    for pada in strip_gloss(token):
      pada = regex.sub(r"[\u200c\u200d\s]+", "", pada).strip("ऽ")
      if not pada or not regex.search(f"[{DEVA}]", pada):
        continue
      counts[pada] += 1
      locus = f"{adhyaya}.{mantra_num + max(segment - 1, 0)}"
      if not loci[pada] or loci[pada][-1] != locus:
        loci[pada].append(locus)


def collect_padas(source_dir: str = SOURCE_DIR) -> tuple[Counter, dict[str, list[str]]]:
  """Extract all Mādhyandina padapāṭha padas with frequencies and ``adhyāya.mantra`` citations.

  Supports both chapter-level ``sarva-prastutiH/01.md..40.md`` (default, covering all 40
  adhyāyas / 1,975 mantras including clause-split yajus) and legacy per-mantra ``static/01/01_*.md``.
  """
  counts: Counter = Counter()
  loci: dict[str, list[str]] = defaultdict(list)
  n_mantras = 0

  chapter_files = [
      p
      for p in glob.glob(os.path.join(source_dir, "*.md"))
      if os.path.splitext(os.path.basename(p))[0].isdigit()
  ]
  if chapter_files:
    for path in sorted(chapter_files, key=lambda p: int(os.path.splitext(os.path.basename(p))[0])):
      adhyaya = int(os.path.splitext(os.path.basename(path))[0])
      with open(path, encoding="utf-8") as f:
        text = f.read()
      matches = list(_SECTION_HEADING_RE.finditer(text))
      for idx, hm in enumerate(matches):
        mantra_num = int(hm.group(1).translate(_DEVA_TO_ASCII_DIGITS))
        sec_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sec_text = text[hm.end():sec_end]
        pp_blocks = PADA_BLOCK_RE.findall(sec_text)
        if not pp_blocks:
          continue
        n_mantras += 1
        for body in pp_blocks:
          _ingest_pp_body(body, adhyaya, mantra_num, counts, loci, allow_segment_bump=False)
  else:
    paths = [p for p in glob.glob(os.path.join(source_dir, "*", "*.md")) if not p.endswith("_index.md")]
    paths = [p for p in paths if p.split(os.sep)[-2].isdigit() and p.split(os.sep)[-1].split("_")[0].isdigit()]
    for path in sorted(paths, key=_page_key):
      adhyaya_str, file_name = path.split(os.sep)[-2:]
      adhyaya = int(adhyaya_str)
      file_index = int(file_name.split("_")[0])
      with open(path, encoding="utf-8") as f:
        text = f.read()
      m = PADA_BLOCK_RE.search(text)
      if not m:
        logging.warning("No padapATha block in %s", path)
        continue
      n_mantras += 1
      _ingest_pp_body(m.group(1), adhyaya, file_index, counts, loci, allow_segment_bump=True)

  logging.info(
      "Collected %d unique padas from %d mantras (%d tokens)",
      len(counts), n_mantras, sum(counts.values()),
  )
  return counts, loci


def _resolve_vishvasa_url(url: str, *, vishvasa_root: str = VISHVASA_ROOT) -> str:
  parts = url.lstrip("/").split("/", 1)
  if len(parts) != 2:
    return ""
  return os.path.join(vishvasa_root, parts[0], "static", parts[1])


def _walk_details_blocks(txt: str) -> list[tuple[str, str]]:
  out: list[tuple[str, str]] = []
  for _, _, ttl, inner in parse_top_level_details(txt):
    out.append((ttl.strip(), inner))
    out.extend(_walk_details_blocks(inner))
  return out


def _is_accented_pp_block(body: str, min_ratio: float = 0.7) -> bool:
  toks = [t.strip() for t in regex.split(r"[।॥\s]+", body) if regex.search(f"[{DEVA}]", t)]
  if not toks:
    return False
  acc_n = sum(1 for t in toks if "\u0951" in t or "\u0952" in t)
  return acc_n >= min_ratio * len(toks)


def _select_kanva_pp_bodies(sec_text: str, *, vishvasa_root: str = VISHVASA_ROOT) -> list[str]:
  """Collect Kāṇva padapāṭha bodies for one section, resolving includes safely."""
  parts: list[str] = []
  urls: list[str] = []
  cur = 0
  for a, b in find_js_include_spans(sec_text):
    parts.append(sec_text[cur:a])
    chunk = sec_text[a:b]
    m_url = URL_ATTR_RE.search(chunk)
    resolved = False
    if m_url:
      url = m_url.group(1)
      urls.append(url)
      fp = _resolve_vishvasa_url(url, vishvasa_root=vishvasa_root)
      if fp and os.path.isfile(fp):
        with open(fp, encoding="utf-8") as f:
          parts.append(f.read())
        resolved = True
    if not resolved:
      parts.append(chunk)
    cur = b
  parts.append(sec_text[cur:])
  blocks = _walk_details_blocks("\n".join(parts))

  pp_k_acc = [b for h, b in blocks if h in ("पदपाठः", "पदपाठः - काण्वः") and _is_accented_pp_block(b)]
  if pp_k_acc:
    return pp_k_acc
  is_exact_shared = any("/Rk/vishvAsa-prastutiH/" in u or "/yajuH/sarva-prastutiH/" in u for u in urls)
  if is_exact_shared:
    return [b for h, b in blocks if h == "पदपाठः - दयानन्दादि"]
  return []


def collect_kanva_padas(
    source_dir: str = KANVA_SOURCE_DIR,
    *,
    vishvasa_root: str = VISHVASA_ROOT,
) -> tuple[Counter, dict[str, list[str]]]:
  """Extract Kāṇva Saṁhitā padapāṭha padas with frequencies and ``adhyāya.mantra`` citations."""
  counts: Counter = Counter()
  loci: dict[str, list[str]] = defaultdict(list)
  n_mantras = 0
  chapter_files = [
      p
      for p in glob.glob(os.path.join(source_dir, "*.md"))
      if os.path.splitext(os.path.basename(p))[0].isdigit()
  ]
  for path in sorted(chapter_files, key=lambda p: int(os.path.splitext(os.path.basename(p))[0])):
    adhyaya = int(os.path.splitext(os.path.basename(path))[0])
    with open(path, encoding="utf-8") as f:
      text = f.read()
    matches = list(_SECTION_HEADING_RE.finditer(text))
    for idx, hm in enumerate(matches):
      mantra_num = int(hm.group(1).translate(_DEVA_TO_ASCII_DIGITS))
      sec_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
      sec_text = text[hm.end():sec_end]
      pp_bodies = _select_kanva_pp_bodies(sec_text, vishvasa_root=vishvasa_root)
      if not pp_bodies:
        continue
      n_mantras += 1
      for body in pp_bodies:
        _ingest_pp_body(body, adhyaya, mantra_num, counts, loci, allow_segment_bump=False)

  logging.info(
      "Collected %d unique Kāṇva padas from %d mantras (%d tokens)",
      len(counts), n_mantras, sum(counts.values()),
  )
  return counts, loci


def _write_readme(dest_dir: str, dict_name: str, recension_desc: str, summary_label: str) -> None:
  readme_text = (
      f"## {dict_name}\n"
      f"- Śukla-Yajurveda {recension_desc} padapāṭha (US notation).\n"
      f"- Extracted from `{summary_label}` by `dict_curation_projects.conversion.babylon.dict_specific.veda.madhyandina` (`X iti Y` glosses resolved to `Y`).\n"
      "- `adhyāya.mantra` citations refer to adhyāya and mantra numbers of that saṁhitā.\n"
  )
  Path(os.path.join(dest_dir, "README.md")).write_text(readme_text, encoding="utf-8")


def dump_all(
    dest_dirs: tuple[str, ...] = DEFAULT_DEST_DIRS,
    source_dir: str = SOURCE_DIR,
    *,
    include_meanings: bool = True,
) -> None:
  from .taittiriya import _join_compound_sandhi
  from . import vedic_meanings

  raw_counts, raw_loci = collect_padas(source_dir=source_dir)
  counts, loci, fallback_count = convert_counts_and_loci_to_us(raw_counts, raw_loci, already_us=False)
  extra_headwords = build_compound_extra_headwords(counts.keys(), _join_compound_sandhi)
  meanings = (
      vedic_meanings.build_meaning_lookup_map(
          "vs-m", counts, already_us=True, source_dir=source_dir, use_cache=True
      )
      if include_meanings
      else None
  )
  logging.info(
      "Converted VS-M padasvara to US notation (%d unique padas, %d fallbacks, %d extra headwords, %d meanings)",
      len(counts),
      fallback_count,
      len(extra_headwords),
      len(meanings or {}),
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
      _write_readme(
          dest_dir,
          os.path.basename(os.path.normpath(dest_dir)),
          "Mādhyandina Saṁhitā",
          "<summary>पदपाठः - दयानन्दादि</summary>",
      )


def dump_kanva(
    dest_dirs: tuple[str, ...] = KANVA_DEFAULT_DEST_DIRS,
    source_dir: str = KANVA_SOURCE_DIR,
    *,
    vishvasa_root: str = VISHVASA_ROOT,
    include_meanings: bool = True,
) -> None:
  """Write ``syv-vs-k-padasvara`` ``.babylon`` and ``README.md``."""
  from .taittiriya import _join_compound_sandhi
  from . import vedic_meanings

  raw_counts, raw_loci = collect_kanva_padas(source_dir=source_dir, vishvasa_root=vishvasa_root)
  counts, loci, fallback_count = convert_counts_and_loci_to_us(raw_counts, raw_loci, already_us=False)
  extra_headwords = build_compound_extra_headwords(counts.keys(), _join_compound_sandhi)
  meanings = (
      vedic_meanings.build_meaning_lookup_map(
          "vs-k", counts, already_us=True, source_dir=source_dir, use_cache=True
      )
      if include_meanings
      else None
  )
  logging.info(
      "Converted VS-K padasvara to US notation (%d unique padas, %d fallbacks, %d extra headwords, %d meanings)",
      len(counts),
      fallback_count,
      len(extra_headwords),
      len(meanings or {}),
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
      _write_readme(
          dest_dir,
          os.path.basename(os.path.normpath(dest_dir)),
          "Kāṇva Saṁhitā",
          "<summary>पदपाठः</summary>` / `<summary>पदपाठः - काण्वः</summary>",
      )


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  ap = argparse.ArgumentParser(description="Build Śukla-Yajurveda VS-M/VS-K padasvara Babylon lexicons.")
  ap.add_argument("--recension", choices=("madhyandina", "kanva", "all"), default="all")
  cli_args = ap.parse_args()
  if cli_args.recension in ("madhyandina", "all"):
    dump_all()
  if cli_args.recension in ("kanva", "all"):
    dump_kanva()
