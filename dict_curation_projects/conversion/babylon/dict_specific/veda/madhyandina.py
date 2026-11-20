"""Build ``syv-ms-padasvara`` Babylon lexicon from the Mādhyandina Śukla-Yajurveda padapāṭha.

Source: the ``सर्वाष् टीकाः`` Markdown files of the Mādhyandina Saṁhitā, which carry
the accented padapāṭha in the ``<details><summary>पदपाठः - दयानन्दादि</summary>``
block of every mantra page (one page per mantra, ``<adhyāya>/<mantra>_title.md``).
"""

from __future__ import annotations

from collections import Counter, defaultdict
import glob
import logging
import os
import regex

from .padasvara_common import (
    build_compound_extra_headwords,
    convert_counts_and_loci_to_us,
    dump_padasvara_babylon,
)

SOURCE_DIR = "/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/static/vAjasaneyam/mAdhyandinam/saMhitA/sarvASh_TIkAH"
DEFAULT_DEST_DIRS = (
    "/home/vvasuki/gitland/sanskrit/raw_etexts/koshaH/indic-dict/kAvya/syv-ms-padasvara",
    "/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-kAvya/syv-ms-padasvara",
    "/home/vvasuki/gitland/indic-dict/stardict/stardict-sanskrit-kAvya/syv-ms-padasvara",
)

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


def collect_padas(source_dir: str = SOURCE_DIR) -> tuple[Counter, dict[str, list[str]]]:
  """Extract all Mādhyandina padapāṭha padas with frequencies and ``adhyāya.mantra`` citations."""
  counts: Counter = Counter()
  loci: dict[str, list[str]] = defaultdict(list)
  n_mantras = 0
  paths = [p for p in glob.glob(os.path.join(source_dir, "*", "*.md")) if not p.endswith("_index.md")]
  paths = [p for p in paths if p.split(os.sep)[-2].isdigit() and p.split(os.sep)[-1].split("_")[0].isdigit()]
  for path in sorted(paths, key=_page_key):
    adhyaya_str, file_name = path.split(os.sep)[-2:]
    adhyaya = int(adhyaya_str)
    file_index = int(file_name.split("_")[0])
    with open(path) as f:
      text = f.read()
    m = PADA_BLOCK_RE.search(text)
    if not m:
      logging.warning("No padapATha block in %s", path)
      continue
    n_mantras += 1
    segment = 0  # mantra offset inside the page (a page occasionally holds two)
    for raw_token in m.group(1).replace("\n", " ").split("।"):
      token = regex.sub(r"[\u200c\u200d\s]+", " ", raw_token).strip()
      # a daNDa-less mantra number sometimes sticks to the last pada ("ऊ॒तिभिः॑६")
      token = regex.sub(r"[०-९0-9]+$", "", token).strip()
      if not token:
        continue
      if regex.fullmatch(r"[०-९0-9]+", token):
        segment += 1
        continue
      if not regex.search(f"[{DEVA}]", token):
        continue
      for pada in strip_gloss(token):
        pada = regex.sub(r"[\u200c\u200d\s]+", "", pada).strip("ऽ")
        if not pada or not regex.search(f"[{DEVA}]", pada):
          continue
        counts[pada] += 1
        locus = f"{adhyaya}.{file_index + max(segment - 1, 0)}"
        if not loci[pada] or loci[pada][-1] != locus:
          loci[pada].append(locus)
  logging.info(
      "Collected %d unique padas from %d mantra pages (%d tokens)",
      len(counts), n_mantras, sum(counts.values()),
  )
  return counts, loci


def dump_all(dest_dirs: tuple[str, ...] = DEFAULT_DEST_DIRS) -> None:
  from .taittiriya import _join_compound_sandhi

  raw_counts, raw_loci = collect_padas()
  counts, loci, fallback_count = convert_counts_and_loci_to_us(raw_counts, raw_loci, already_us=False)
  extra_headwords = build_compound_extra_headwords(counts.keys(), _join_compound_sandhi)
  logging.info(
      "Converted MS padasvara to US notation (%d unique padas, %d fallbacks, %d extra headwords)",
      len(counts),
      fallback_count,
      len(extra_headwords),
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
      )


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  dump_all()
