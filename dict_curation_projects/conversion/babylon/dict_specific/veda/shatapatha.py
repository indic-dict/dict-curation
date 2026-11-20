"""Build ``syv-sb-m-pada-svara`` Babylon lexicon from Śatapatha Brāhmaṇa (Mādhyandina) padapāṭha.

Extracts US-accented padas from ``<details><summary>पद-पाठः (यान्त्रिकः)</summary>`` blocks in
``sarva-prastutiH``, keeping only padas with no suggested correction (excluding ``→`` lines).
"""

from __future__ import annotations

from collections import Counter, defaultdict
import logging
import os
from pathlib import Path
import re

from . import taittiriya
from .padasvara_common import (
    US_SVARITA,
    US_UDATTA,
    build_compound_extra_headwords,
    dump_padasvara_babylon,
    strip_all_accents,
)

SOURCE_DIR = (
    "/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/content/vAjasaneyam/"
    "mAdhyandinam/shatapatha-brAhmaNam/sarva-prastutiH"
)
DEFAULT_DEST_DIRS = (
    "/home/vvasuki/gitland/sanskrit/raw_etexts/koshaH/indic-dict/kAvya/syv-sb-m-pada-svara",
    "/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-kAvya/syv-sb-m-pada-svara",
    "/home/vvasuki/gitland/indic-dict/stardict/stardict-sanskrit-kAvya/syv-sb-m-pada-svara",
)

_SECTION_SPLIT_RE = re.compile(r"(?m)^##\s+([^\n]+)\n")
_PP_BLOCK_RE = re.compile(r"<details[^>]*>\s*<summary>\s*पद-पाठः[^<]*</summary>(.*?)</details>", re.S)
_KANDIKA_NUM_RE = re.compile(r"^([०-९0-9]+)")


def _devanagari_int(num_str: str) -> int:
  trans = str.maketrans("०१२३४५६७८९", "0123456789")
  return int(num_str.translate(trans))


def _locus_prefix_for_file(rel_path: Path) -> tuple[int, int, int] | None:
  """Return ``(kanda, adhyaya, brahmana)`` from relative path inside ``sarva-prastutiH``."""
  if rel_path.name.startswith("_") or rel_path.name == "file_list.md":
    return None
  parts = rel_path.parts
  if len(parts) < 3 or not parts[0].isdigit() or not rel_path.parent.name.isdigit():
    return None
  b_stem = rel_path.stem.split("_")[0]
  if not b_stem.isdigit():
    return None
  return int(parts[0]), int(rel_path.parent.name), int(b_stem)


def _clean_sb_bullet_pada(bullet_line: str) -> str | None:
  """Extract clean US pada from an uncorrected bullet line; return ``None`` if correction suggested."""
  s = bullet_line.strip()
  if not s.startswith("- "):
    return None
  body = s[2:].strip()
  # Exclude any bullet suggesting a correction (→) or uncertain/annotated flags on the pada token itself
  if "→" in body or "[[" in body:
    return None
  raw_pada = body.split("(", 1)[0].strip()
  if not raw_pada or any(c in raw_pada for c in "*[]?!="):
    return None
  pada = raw_pada.replace("\u200d", "").replace("\u200c", "").replace("ᳫँ", "ँ").replace("ᳫं", "ं")
  pada = pada.strip("।॥, ;:")
  pada = re.sub(r"-{2,}", "-", pada).strip("-")
  if not pada or not any("\u0900" <= c <= "\u097f" for c in pada):
    return None
  if "\u0951" in pada or "\u0952" in pada or "\u1cd6" in pada:
    raise ValueError(f"Unexpected classical accent mark in SB padapāṭha pada: {raw_pada!r}")
  return pada


def collect_sb_padasvara(source_dir: str = SOURCE_DIR) -> tuple[Counter[str], dict[str, list[str]], int]:
  """Collect uncorrected US padas from Śatapatha Brāhmaṇa ``पद-पाठः (यान्त्रिकः)`` blocks."""
  root = Path(source_dir)
  md_items: list[tuple[tuple[int, int, int], Path]] = []
  for p in root.rglob("*.md"):
    prefix = _locus_prefix_for_file(p.relative_to(root))
    if prefix is not None:
      md_items.append((prefix, p))
  md_items.sort(key=lambda x: x[0])

  counts: Counter[str] = Counter()
  loci: dict[str, list[str]] = defaultdict(list)
  skipped_corrections = 0

  for (kanda, adhyaya, brahmana), path in md_items:
    txt = path.read_text(encoding="utf-8")
    segs = _SECTION_SPLIT_RE.split(txt)
    pairs = [(None, segs[0])] + [(segs[i].strip(), segs[i + 1]) for i in range(1, len(segs), 2)]
    for heading, chunk in pairs:
      m_pp = _PP_BLOCK_RE.search(chunk)
      if not m_pp:
        continue
      if heading:
        mk = _KANDIKA_NUM_RE.match(heading)
        kandika = _devanagari_int(mk.group(1)) if mk else 0
        locus = f"{kanda}.{adhyaya}.{brahmana}.{kandika}" if kandika else f"{kanda}.{adhyaya}.{brahmana}"
      else:
        locus = f"{kanda}.{adhyaya}.{brahmana}"

      for line in m_pp.group(1).splitlines():
        s = line.strip()
        if not s.startswith("- "):
          continue
        if "→" in s or "[[" in s:
          skipped_corrections += 1
          continue
        pada = _clean_sb_bullet_pada(s)
        if not pada:
          continue
        counts[pada] += 1
        if not loci[pada] or loci[pada][-1] != locus:
          loci[pada].append(locus)

  logging.info(
      "Collected %d unique SB padas (%d tokens, skipped %d suggested corrections)",
      len(counts), sum(counts.values()), skipped_corrections,
  )
  return counts, loci, skipped_corrections


def dump_all(dest_dirs: tuple[str, ...] = DEFAULT_DEST_DIRS, source_dir: str = SOURCE_DIR) -> tuple[Counter[str], int]:
  """Write ``syv-sb-m-pada-svara`` ``.babylon``, ``.babylon_final``, and ``README.md`` to all mirrors."""
  counts, loci, skipped = collect_sb_padasvara(source_dir=source_dir)
  extra_headwords = build_compound_extra_headwords(counts.keys(), taittiriya._join_compound_sandhi)
  readme_text = (
      "## syv-sb-m-pada-svara\n"
      "- Śukla Yajurveda Mādhyandina Śatapatha Brāhmaṇa padapāṭha (US notation).\n"
      "- Built by `dict_curation_projects.conversion.babylon.dict_specific.veda.shatapatha` "
      "from `पद-पाठः (यान्त्रिकः)` excluding entries with suggested corrections (`→`).\n"
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
      Path(os.path.join(dest_dir, "README.md")).write_text(readme_text, encoding="utf-8")
  return counts, skipped


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  dump_all()
