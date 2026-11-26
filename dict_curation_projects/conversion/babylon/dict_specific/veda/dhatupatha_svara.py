"""Convert ``dhAtupAThaH_sasvaraH.babylon`` classical Pāṇinian svara marks to US notation."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import re

from doc_curation.sanskrit.accent import shatapatha_solver as ss
import regex

from .padasvara_common import (
    ENCLITIC_PARTICLES,
    apply_us_marks_to_hyph,
    assert_writable_dict_dest,
    strip_all_accents,
)

PRIMARY_DHATUPATHA_BABYLON = (
    "/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-vyAkaraNa/"
    "dhAtu/dhAtupAThaH_sasvaraH/dhAtupAThaH_sasvaraH.babylon"
)
DEFAULT_DHATUPATHA_MIRRORS = (
    "/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-vyAkaraNa/dhAtu/dhAtupAThaH_sasvaraH",
)

_CL_SVARITA = "\u0951"
_CL_ANUDATTA = "\u0952"
# Exclude danda/double-danda (\u0964-\u0965) and Devanagari digits (\u0966-\u096f) so
# sentence-final enclitics like `च॑।` match `ENCLITIC_PARTICLES` cleanly.
_TOK_RE = regex.compile(r"[\u0900-\u0963\u0970-\u097f\u0951\u0952\u1cd0-\u1cffऽ]+")


def _scan_syl_strings(word: str) -> list[str]:
  """Split Devanagari word into syllable strings aligned 1:1 with ``_fast_scan_deva_syllables``."""
  syls: list[str] = []
  n = len(word)
  i = 0
  start: int | None = None
  while i < n:
    ch = word[i]
    if ch in ss._DEVA_CONSONANTS:
      if start is None:
        start = i
      if i + 1 < n and word[i + 1] == "्":
        i += 2
        continue
      i += 1
      if i < n and word[i] in ss._DEVA_MATRAS:
        i += 1
      while i < n and word[i] in ss._DEVA_TAIL_MODS:
        i += 1
      syls.append(word[start:i])
      start = None
    elif ch in ss._DEVA_IND_VOWELS:
      if start is None:
        start = i
      i += 1
      while i < n and word[i] in ss._DEVA_TAIL_MODS:
        i += 1
      syls.append(word[start:i])
      start = None
    else:
      start = None
      i += 1
  return syls


def convert_dhatupatha_token_to_us(tok: str, *, prev_ended_udatta: bool = False) -> tuple[str, bool]:
  """Convert a single classical-accented Dhātupāṭha token to US notation.

  Handles Pāṇinian root anubandha/it conventions:
  - ``अनुदात्तेत्`` (``एधँ॒``, ``च॒क्षिँ॒ङ्``, ``दा॒ण्``): anudātta only (``""``).
  - ``स्वरितेत्`` (``भ॒जँ॑``, ``डुप॒चँ॑ष्``, ``तनुँ॑``): independent svarita ``᳙`` directly on the ``ँ`` syllable.
  - ``उदात्तेत्`` (``अ॒दँ``, ``ह॒नँ``): ``U`` on the unmarked final syllable after ``॒``.
  - Running gloss compounds with omitted leading ``॒`` (``परि॒भाष॑णे`` -> ``परिभा᳓षणे``,
    ``सङ्घा॒ते`` -> ``सङ्घाते᳓``, ``सत्ता॑याम्`` -> ``स᳓त्तायाम्``).
  Returns ``(us_token, ended_udatta_for_next)``.
  """
  if _CL_SVARITA not in tok and _CL_ANUDATTA not in tok:
    return tok, False

  tok_no_av = tok.replace("ऽ", "")
  clean_bare = strip_all_accents(tok_no_av)
  syls = ss._fast_scan_deva_syllables(tok_no_av)
  syl_strs = _scan_syl_strings(tok_no_av)
  n_syl = len(syls)
  if n_syl == 0:
    return tok, False

  raw = [
      "LS" if (_CL_ANUDATTA in m and _CL_SVARITA in m) else (
          "L" if _CL_ANUDATTA in m else ("S" if _CL_SVARITA in m else "")
      )
      for m, _ in syls
  ]
  marks = [""] * n_syl
  is_anubandha = "ँ" in clean_bare
  s_idxs = [i for i, r in enumerate(raw) if r in ("S", "LS")]

  # Case 1: स्वरितेत् root with ँ + ॑ on the same syllable (भ॒जँ॑, डुप॒चँ॑ष्, तनुँ॑)
  candrabindu_s = [
      i for i, (r, s_str) in enumerate(zip(raw, syl_strs))
      if r in ("S", "LS") and "ँ" in s_str
  ]
  if (
      candrabindu_s
      and len(candrabindu_s) == 1
      and len(s_idxs) == 1
      and not clean_bare.startswith("इत्येके")
  ):
    marks[candrabindu_s[0]] = "S"
    return _render_preserving_avagraha(tok, marks), False

  # Case 2: Token ends with L (अनुदात्तेत् एधँ॒, च॒क्षिँ॒ङ्, or pre-udātta अ॒व्य॑क्ते॒)
  if raw[-1] == "L" and "S" not in raw:
    return clean_bare if "ऽ" not in tok else tok.replace(_CL_ANUDATTA, "").replace(_CL_SVARITA, ""), False

  # Case 3: Multi-accent fused sūtra segment like दीप्ता॑व॒भिप्री॑तौ or दुर्ग॑ता॒वपीत्येके॑
  if len(s_idxs) >= 2:
    for si in s_idxs:
      if si == 0:
        marks[0] = "S" if syls[0][1] else "U"
      elif raw[si - 1] == "L":
        marks[si] = "S" if syls[si][1] else "U"
      elif si >= 2 and raw[si - 2] == "L":
        marks[si - 1] = "U"
      else:
        marks[si - 1] = "U"
    return _render_preserving_avagraha(tok, marks), bool(marks[-1] == "U")

  # Case 4: Trailing L after an earlier accent (अव्य॑क्ते॒, आ॒ह्वाने॒)
  if "L" in raw and raw[-1] == "L":
    l_end = len(raw) - 1
    if "S" in raw[:l_end]:
      si = raw[:l_end].index("S")
      if si == 0:
        marks[0] = "S" if syls[0][1] else "U"
      else:
        marks[si - 1] = "U"
    elif l_end >= 2 and raw[l_end - 2] == "L" and raw[l_end - 1] == "":
      marks[l_end - 1] = "U"
    return _render_preserving_avagraha(tok, marks), False

  # Case 5: Single/last L followed by unmarked U (परि॒भाष॑णे, सङ्घा॒ते, अ॒दँ, मेधाहिंस॒नयोः॑)
  if "L" in raw:
    last_l = max(i for i, r in enumerate(raw) if r == "L")
    if last_l + 1 < n_syl:
      if raw[last_l + 1] == "S" and syls[last_l + 1][1]:
        marks[last_l + 1] = "S"  # e.g. भा॒ष्य॑म्
      else:
        marks[last_l + 1] = "U"
      return _render_preserving_avagraha(tok, marks), (last_l + 1 == n_syl - 1)
    # Only anudātta before nothing (e.g. anubandha with internal L only)
    return _render_preserving_avagraha(tok, marks), False

  # Case 6: No L anywhere, single S (सत्ता॑याम्, वृद्धौ॑, इत्येके॑, व्य॑क्तायां, च॑)
  if len(s_idxs) == 1:
    si = s_idxs[0]
    if si == 0:
      if n_syl == 1 and clean_bare in ENCLITIC_PARTICLES and prev_ended_udatta:
        return _render_preserving_avagraha(tok, marks), False
      marks[0] = "S" if syls[0][1] else "U"
      return _render_preserving_avagraha(tok, marks), (n_syl == 1 and marks[0] == "U")
    if is_anubandha and si == n_syl - 1:
      # e.g. तनुँ॑ -> स्वरितेत् already caught above, keep safety guard
      marks[si] = "S"
      return _render_preserving_avagraha(tok, marks), False
    marks[si - 1] = "U"
    return _render_preserving_avagraha(tok, marks), (si - 1 == n_syl - 1)

  return _render_preserving_avagraha(tok, marks), False


def _render_preserving_avagraha(tok: str, flat_marks: list[str]) -> str:
  bare_with_av = strip_all_accents(tok)
  if "ऽ" not in bare_with_av:
    return apply_us_marks_to_hyph(bare_with_av, flat_marks)
  lead_av = "ऽ" if bare_with_av.startswith("ऽ") else ""
  trail_av = "ऽ" if len(bare_with_av) > 1 and bare_with_av.endswith("ऽ") else ""
  hyph = bare_with_av.strip("ऽ").replace("ऽ", "-")
  us_h = apply_us_marks_to_hyph(hyph, flat_marks) if hyph else ""
  return f"{lead_av}{us_h.replace('-', 'ऽ')}{trail_av}"


def convert_dhatupatha_segment_to_us(seg: str) -> str:
  """Convert one ``<br>``-delimited segment of a ``dhAtupAThaH_sasvaraH`` entry to US notation."""
  if _CL_SVARITA not in seg and _CL_ANUDATTA not in seg:
    return seg
  parts: list[str] = []
  pos = 0
  prev_u = False
  for m in _TOK_RE.finditer(seg):
    between = seg[pos:m.start()]
    parts.append(between)
    # Reset prev_u across punctuation breaks
    if any(ch in between for ch in "।(),[]"):
      prev_u = False
    us_tok, ended_u = convert_dhatupatha_token_to_us(m.group(0), prev_ended_udatta=prev_u)
    parts.append(us_tok)
    prev_u = ended_u
    pos = m.end()
  parts.append(seg[pos:])
  return "".join(parts)


def convert_dhatupatha_babylon_to_us(
    src_babylon: str = PRIMARY_DHATUPATHA_BABYLON,
    mirror_dirs: tuple[str, ...] = DEFAULT_DHATUPATHA_MIRRORS,
) -> tuple[int, list[str]]:
  """Convert ``dhAtupAThaH_sasvaraH.babylon`` to US notation and mirror to all 3 target dirs."""
  text = Path(src_babylon).read_text(encoding="utf-8")
  blocks = text.split("\n\n")
  out_blocks: list[str] = []
  converted = 0
  leftover: list[str] = []

  for blk in blocks:
    if not blk.strip() or blk.strip().startswith("#"):
      out_blocks.append(blk)
      continue
    lines = blk.splitlines()
    if len(lines) < 2:
      out_blocks.append(blk)
      continue
    hw_us = convert_dhatupatha_segment_to_us(lines[0])
    body_segs = "<br>".join(lines[1:]).split("<br>")
    new_segs = [convert_dhatupatha_segment_to_us(s) for s in body_segs]
    new_blk = f"{hw_us}\n{'<br>'.join(new_segs)}"
    if _CL_SVARITA in new_blk or _CL_ANUDATTA in new_blk:
      leftover.append(new_blk)
    converted += 1
    out_blocks.append(new_blk)

  out_text = "\n\n".join(out_blocks)
  if not out_text.endswith("\n\n"):
    out_text = out_text.rstrip("\n") + "\n\n"

  for d in mirror_dirs:
    assert_writable_dict_dest(d)
    os.makedirs(d, exist_ok=True)
    out_path = os.path.join(d, "dhAtupAThaH_sasvaraH.babylon")
    Path(out_path).write_text(out_text, encoding="utf-8")
    logging.info("Wrote US dhAtupAThaH_sasvaraH (%d entries) to %s", converted, out_path)

  return converted, leftover


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  cnt, rem = convert_dhatupatha_babylon_to_us()
  print(f"Converted {cnt} entries, leftover classical marks: {len(rem)}")
