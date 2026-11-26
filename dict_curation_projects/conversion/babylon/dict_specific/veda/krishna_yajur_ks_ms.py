"""Build ``kyv-ms-pada-svara`` and ``kyv-ks-pada-svara`` Babylon lexicons from MS/KS padapāṭha.

Extracts authentically accented US padas from ``<details><summary>पद-पाठः (यान्त्रिकः...)</summary>``
blocks in ``vedAH_yajuH/content/{maitrAyaNIyam,kAThakam/kaTha-kapiShTalAH}/saMhitA/sarva-prastutiH``,
skipping ``js_include`` blocks, ``(यन्त्र-स्वरः)`` machine-accented blocks (unaccented KS chapters),
and ``→`` correction bullets.
Writes ONLY to the main clone under ``~/gitland/indic-dict/dicts/stardict-sanskrit-kAvya/``.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import logging
import os
from pathlib import Path
import re

from doc_curation.md.content_processor.details.common import parse_top_level_details
from doc_curation.sanskrit.accent.reconciler import find_js_include_spans

from . import taittiriya, taittiriya_brahmana
from .padasvara_common import (
    assert_writable_dict_dest,
    build_compound_extra_headwords,
    dump_padasvara_babylon,
)

MS_SOURCE_DIR = (
    "/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/content/maitrAyaNIyam/saMhitA/sarva-prastutiH"
)
MS_DEFAULT_DEST_DIRS = (
    "/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-kAvya/kyv-ms-pada-svara",
)

KS_SOURCE_DIR = (
    "/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/content/kAThakam/kaTha-kapiShTalAH/saMhitA/sarva-prastutiH"
)
KS_DEFAULT_DEST_DIRS = (
    "/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-kAvya/kyv-ks-pada-svara",
)

_PP_BLOCK_RE = re.compile(
    r"<details[^>]*>\s*<summary>\s*पद-पाठः \(यान्त्रिकः[^<]*</summary>(.*?)</details>",
    re.S,
)


def _locus_for_ms_file(rel_path: Path) -> tuple[tuple[int, ...], str] | None:
  """Return ``(sort_key, locus_str)`` for an MS ``sarva-prastutiH`` file (e.g. ``1.1.1``)."""
  if rel_path.name.startswith("_") or rel_path.name == "file_list.md":
    return None
  nums: list[int] = []
  for part in rel_path.parts[:-1]:
    head = part.split("_")[0]
    if head.isdigit():
      nums.append(int(head))
  stem = rel_path.stem.split("_")[0]
  if stem.isdigit():
    nums.append(int(stem))
  if len(nums) != 3:
    return None
  return tuple(nums), ".".join(str(n) for n in nums)


def _locus_for_ks_file(rel_path: Path) -> tuple[tuple[int, ...], str] | None:
  """Return ``(sort_key, locus_str)`` for a KS ``sarva-prastutiH`` file (e.g. ``1.1`` or ``5.1.1``)."""
  if rel_path.name.startswith("_") or rel_path.name == "file_list.md":
    return None
  parts = rel_path.parts
  if len(parts) < 3:
    return None
  part_head = parts[0].split("_")[0]
  sth_head = parts[1].split("_")[0]
  anu_raw = rel_path.stem
  anu_m = re.match(r"^(\d+)", anu_raw)
  if not (part_head.isdigit() and sth_head.isdigit() and anu_m):
    return None
  p_num = int(part_head)
  s_num = int(sth_head)
  a_num = int(anu_m.group(1))
  if p_num == 5:
    # Aśvamedha: `5.1.1` .. `5.13.13`
    locus = f"5.{s_num}.{anu_raw.lstrip('0') or '0'}"
  else:
    # Sthānakas 1..40: `1.1` .. `40.14` (preserving range stems like `15.2-04` -> `15.2-4`)
    a_disp = "-".join(seg.lstrip("0") or "0" for seg in anu_raw.split("-"))
    locus = f"{s_num}.{a_disp}"
  return (p_num, s_num, a_num), locus


def collect_ks_ms_padasvara(
    source_dir: str,
    *,
    corpus: str = "ms",
    include_yantra_svara: bool = False,
) -> tuple[Counter[str], dict[str, list[str]], int]:
  """Collect authentically accented US padas from MS or KS ``sarva-prastutiH`` files."""
  root = Path(source_dir)
  locus_fn = _locus_for_ks_file if corpus == "ks" else _locus_for_ms_file
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
    top_blocks = parse_top_level_details(txt, skip_js_includes=True)
    last_vp_was_yantra = False
    for start, _end, summ, body in top_blocks:
      if any(a <= start < b for a, b in inc_spans):
        continue
      if summ.startswith("विश्वास-प्रस्तुतिः"):
        last_vp_was_yantra = "यन्त्र-स्वरः" in summ
        continue
      if summ == "सर्वा अवतारिकाः":
        continue
      if last_vp_was_yantra and not include_yantra_svara:
        continue
      for m_pp in _PP_BLOCK_RE.finditer(body):
        padas, sk = taittiriya_brahmana._extract_padas_from_block(m_pp.group(1))
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
  counts, loci, skipped = collect_ks_ms_padasvara(
      source_dir=source_dir,
      corpus=corpus,
      include_yantra_svara=False,
  )
  extra_headwords = build_compound_extra_headwords(counts.keys(), taittiriya._join_compound_sandhi)
  readme_text = (
      f"## {dict_name}\n"
      f"- {title_desc} (US accent notation; excludes machine-reconstructed `यन्त्र-स्वरः` blocks).\n"
      "- Built by `dict_curation_projects.conversion.babylon.dict_specific.veda.krishna_yajur_ks_ms` "
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


def dump_ms(
    dest_dirs: tuple[str, ...] = MS_DEFAULT_DEST_DIRS,
    source_dir: str = MS_SOURCE_DIR,
) -> tuple[Counter[str], int]:
  """Write ``kyv-ms-pada-svara`` ``.babylon`` and ``README.md`` to the main kAvya clone."""
  return _dump_corpus(
      source_dir=source_dir,
      dest_dirs=dest_dirs,
      dict_name="kyv-ms-pada-svara",
      corpus="ms",
      title_desc="Kṛṣṇa Yajurveda Maitrāyaṇī Saṁhitā padapāṭha",
  )


def dump_ks(
    dest_dirs: tuple[str, ...] = KS_DEFAULT_DEST_DIRS,
    source_dir: str = KS_SOURCE_DIR,
) -> tuple[Counter[str], int]:
  """Write ``kyv-ks-pada-svara`` ``.babylon`` and ``README.md`` to the main kAvya clone."""
  return _dump_corpus(
      source_dir=source_dir,
      dest_dirs=dest_dirs,
      dict_name="kyv-ks-pada-svara",
      corpus="ks",
      title_desc="Kṛṣṇa Yajurveda Kāṭhaka Saṁhitā (accented chapters) padapāṭha",
  )


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  ap = argparse.ArgumentParser(description="Build Maitrāyaṇī & Kāṭhaka Saṁhitā padasvara Babylon lexicons.")
  ap.add_argument("--corpus", choices=("ms", "ks", "all"), default="all")
  cli_args = ap.parse_args()
  if cli_args.corpus in ("ms", "all"):
    dump_ms()
  if cli_args.corpus in ("ks", "all"):
    dump_ks()
