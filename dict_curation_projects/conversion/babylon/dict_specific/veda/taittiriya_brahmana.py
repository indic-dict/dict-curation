"""Build ``kyv-tb-pada-svara`` and ``kyv-tk-pada-svara`` Babylon lexicons from TB/TK padapāṭha.

Extracts US-accented padas from non-``js_include`` ``<details><summary>पद-पाठः (यान्त्रिकः)</summary>``
blocks in ``vedAH_yajuH/content/taittirIyam/sArasvata-vibhAgaH/{brAhmaNam,kAThakam}/sarva-prastutiH``.
Writes ONLY to the main clone under ``~/gitland/indic-dict/dicts/stardict-sanskrit-kAvya/``.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import logging
import os
from pathlib import Path
import re

from doc_curation.sanskrit.accent.reconciler import find_js_include_spans
from doc_curation.sanskrit.accent.shatapatha_solver import (
    _is_dual_accent_word,
    _normalize_lookup_key,
)

from . import taittiriya
from .padasvara_common import (
    US_SVARITA,
    US_UDATTA,
    assert_writable_dict_dest,
    build_compound_extra_headwords,
    dump_padasvara_babylon,
)

TB_SOURCE_DIR = (
    "/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/content/taittirIyam/"
    "sArasvata-vibhAgaH/brAhmaNam/sarva-prastutiH"
)
TB_DEFAULT_DEST_DIRS = (
    "/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-kAvya/kyv-tb-pada-svara",
)

TK_SOURCE_DIR = (
    "/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/content/taittirIyam/"
    "sArasvata-vibhAgaH/kAThakam/sarva-prastutiH"
)
TK_DEFAULT_DEST_DIRS = (
    "/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-kAvya/kyv-tk-pada-svara",
)

_PP_BLOCK_RE = re.compile(
    r"<details[^>]*>\s*<summary>\s*पद-पाठः \(यान्त्रिकः[^<]*</summary>(.*?)</details>",
    re.S,
)
_DEVA_RE = re.compile(r"[\u0905-\u0939]")


def _locus_for_tb_file(rel_path: Path) -> tuple[tuple[int, ...], str] | None:
  """Return ``(sort_key, locus_str)`` for a TB ``sarva-prastutiH`` file (e.g. ``1.1.1``)."""
  if rel_path.name.startswith("_") or rel_path.name == "file_list.md":
    return None
  nums: list[int] = []
  for part in rel_path.parts[:-1]:
    head = part.split("_")[0]
    if head.isdigit():
      nums.append(int(head))
  stem_parts = rel_path.stem.split("_")
  if stem_parts and stem_parts[0].isdigit():
    nums.append(int(stem_parts[0]))
  elif nums:
    return tuple(nums) + (999,), ".".join(str(n) for n in nums) + f".{rel_path.stem}"
  if not nums:
    return None
  return tuple(nums), ".".join(str(n) for n in nums)


def _locus_for_tk_file(rel_path: Path) -> tuple[tuple[int, ...], str] | None:
  """Return ``(sort_key, locus_str)`` for a TK ``sarva-prastutiH`` file (e.g. ``1.1.1``, ``1.2``)."""
  if rel_path.name.startswith("_") or rel_path.name == "file_list.md":
    return None
  nums: list[int] = []
  for part in rel_path.parts[:-1]:
    head = part.split("_")[0]
    if head.isdigit():
      nums.append(int(head))
  stem_parts = rel_path.stem.split("_")
  if stem_parts and stem_parts[0].isdigit():
    nums.append(int(stem_parts[0]))
    if len(stem_parts) >= 2 and stem_parts[1].isdigit():
      nums.append(int(stem_parts[1]))
  if not nums:
    return None
  return tuple(nums), ".".join(str(n) for n in nums)


def _clean_pada_token(raw_pada: str) -> str | None:
  """Validate and normalize one US pada token; drop corrections, classical marks, or spurious multi-udātta."""
  if not raw_pada or "→" in raw_pada or "[[" in raw_pada:
    return None
  if any(c in raw_pada for c in "*[]?!="):
    return None
  pada = raw_pada.replace("\u200d", "").replace("\u200c", "").replace("ᳫँ", "ँ").replace("ᳫं", "ं")
  pada = pada.strip("।॥, ;:")
  pada = re.sub(r"-{2,}", "-", pada).strip("-")
  if not pada or not _DEVA_RE.search(pada) or not ("\u0905" <= pada[0] <= "\u0939" or pada[0] in "\u0960\u0961"):
    return None
  if "\u0951" in pada or "\u0952" in pada or "\u1cd6" in pada:
    raise ValueError(f"Unexpected classical accent mark in padapāṭha token: {raw_pada!r}")
  n_acc = pada.count(US_UDATTA) + pada.count(US_SVARITA)
  if n_acc > 1 and not _is_dual_accent_word(_normalize_lookup_key(pada)):
    return None
  return pada


def _extract_padas_from_block(body: str) -> tuple[list[str], int]:
  """Extract padas from either ``।``-separated or bullet-list ``पद-पाठः (यान्त्रिकः)`` body."""
  lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
  padas: list[str] = []
  skipped = 0
  if any(ln.startswith("- ") for ln in lines):
    for ln in lines:
      if not ln.startswith("- "):
        continue
      raw = ln[2:].strip()
      if "→" in raw or "[[" in raw:
        skipped += 1
        continue
      tok = _clean_pada_token(raw.split("(", 1)[0].strip())
      if tok:
        padas.append(tok)
      else:
        skipped += 1
  else:
    for piece in re.split(r"[।॥\s]+", body):
      if not piece:
        continue
      tok = _clean_pada_token(piece)
      if tok:
        padas.append(tok)
      else:
        skipped += 1
  return padas, skipped


def collect_taittiriya_padasvara(
    source_dir: str,
    *,
    corpus: str = "tb",
) -> tuple[Counter[str], dict[str, list[str]], int]:
  """Collect clean US padas from TB or TK ``पद-पाठः (यान्त्रिकः)`` blocks (skipping ``js_include``)."""
  root = Path(source_dir)
  locus_fn = _locus_for_tk_file if corpus == "tk" else _locus_for_tb_file
  md_items: list[tuple[tuple[int, ...], str, Path]] = []
  for p in root.rglob("*.md"):
    loc = locus_fn(p.relative_to(root))
    if loc is not None:
      md_items.append((loc[0], loc[1], p))
  md_items.sort(key=lambda x: (x[0], x[1]))

  counts: Counter[str] = Counter()
  loci: dict[str, list[str]] = defaultdict(list)
  skipped = 0

  for _, locus, path in md_items:
    txt = path.read_text(encoding="utf-8")
    inc_spans = find_js_include_spans(txt)
    for m_pp in _PP_BLOCK_RE.finditer(txt):
      if any(a <= m_pp.start() < b for a, b in inc_spans):
        continue
      padas, sk = _extract_padas_from_block(m_pp.group(1))
      skipped += sk
      for pada in padas:
        counts[pada] += 1
        if not loci[pada] or loci[pada][-1] != locus:
          loci[pada].append(locus)

  logging.info(
      "Collected %d unique %s padas (%d tokens, skipped %d)",
      len(counts),
      corpus.upper(),
      sum(counts.values()),
      skipped,
  )
  return counts, loci, skipped


def _dump_corpus(
    *,
    source_dir: str,
    dest_dirs: tuple[str, ...],
    dict_name: str,
    corpus: str,
    title_desc: str,
) -> tuple[Counter[str], int]:
  counts, loci, skipped = collect_taittiriya_padasvara(source_dir=source_dir, corpus=corpus)
  extra_headwords = build_compound_extra_headwords(counts.keys(), taittiriya._join_compound_sandhi)
  readme_text = (
      f"## {dict_name}\n"
      f"- {title_desc} (US accent notation).\n"
      "- Built by `dict_curation_projects.conversion.babylon.dict_specific.veda.taittiriya_brahmana` "
      "from `पद-पाठः (यान्त्रिकः)` blocks.\n"
  )
  for dest_dir in dest_dirs:
    assert_writable_dict_dest(dest_dir)
    if os.path.isdir(os.path.dirname(dest_dir)):
      dump_padasvara_babylon(
          counts,
          loci,
          dest_dir=dest_dir,
          write_final=False,
          citation_sep=", ",
          extra_headwords=extra_headwords,
      )
      Path(os.path.join(dest_dir, "README.md")).write_text(readme_text, encoding="utf-8")
  return counts, skipped


def dump_tb(
    dest_dirs: tuple[str, ...] = TB_DEFAULT_DEST_DIRS,
    source_dir: str = TB_SOURCE_DIR,
) -> tuple[Counter[str], int]:
  """Write ``kyv-tb-pada-svara`` ``.babylon`` and ``README.md`` to the main kAvya clone."""
  return _dump_corpus(
      source_dir=source_dir,
      dest_dirs=dest_dirs,
      dict_name="kyv-tb-pada-svara",
      corpus="tb",
      title_desc="Kṛṣṇa Yajurveda Taittirīya Brāhmaṇa padapāṭha",
  )


def dump_tk(
    dest_dirs: tuple[str, ...] = TK_DEFAULT_DEST_DIRS,
    source_dir: str = TK_SOURCE_DIR,
) -> tuple[Counter[str], int]:
  """Write ``kyv-tk-pada-svara`` ``.babylon`` and ``README.md`` to the main kAvya clone."""
  return _dump_corpus(
      source_dir=source_dir,
      dest_dirs=dest_dirs,
      dict_name="kyv-tk-pada-svara",
      corpus="tk",
      title_desc="Kṛṣṇa Yajurveda Taittirīya Kāṭhaka padapāṭha",
  )


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  ap = argparse.ArgumentParser(description="Build Taittirīya Brāhmaṇa & Kāṭhaka padasvara Babylon lexicons.")
  ap.add_argument("--corpus", choices=("tb", "tk", "all"), default="all")
  cli_args = ap.parse_args()
  if cli_args.corpus in ("tb", "all"):
    dump_tb()
  if cli_args.corpus in ("tk", "all"):
    dump_tk()
