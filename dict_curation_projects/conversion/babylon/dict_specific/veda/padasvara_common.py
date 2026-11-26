"""Shared Babylon dictionary writer and US accent normalizers for Vedic padasvara lexicons."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import logging
import os
import re
from typing import Callable, Iterable, Sequence

from dict_curation import Definition, babylon
from doc_curation.sanskrit.accent import shatapatha_solver as ss
from indic_transliteration import sanscript
from indic_transliteration.sanscript.schemes.brahmic import accent
import regex

US_UDATTA = "\u1cd3"  # ᳓
US_SVARITA = "\u1cd9"  # ᳙
_CL_SVARITA = "\u0951"  # ॑
_CL_ANUDATTA = "\u0952"  # ॒
ALL_ACCENTS_RE = regex.compile(r"[\u0951\u0952\u1cd0-\u1cff]")

ENCLITIC_PARTICLES: frozenset[str] = frozenset({
    "च", "वा", "इव", "मे", "नः", "वः", "स्म", "घ", "ह", "सीम्", "ईम्", "अह", "त्व", "स्व",
})

DEVATA_DVANDVA_PREFIXES: tuple[str, ...] = (
    "इन्द्रावरुण", "इंद्रावरुण", "इन्द्राविष्णु", "इन्द्रवायु", "इन्द्राग्नी", "इंद्राग्नी",
    "इन्द्रासोम", "इन्द्राबृहस्पती", "इन्द्रापूषन्", "इन्द्रापूष", "इन्द्रापूषा", "इन्द्रापर्जन्य",
    "मित्रावरुण", "मित्रवरुण", "द्यावापृथिवी", "द्यावाक्षामा", "द्यावाभूमी", "दिवःपृथि", "दिवापृथि",
    "उषसानक्ता", "उषासानक्ता", "सोमारुद्र", "सोमापूष", "अग्नीषोम", "अग्नीवरुण",
    "सूर्याचन्द्रमस", "वातापर्य्य", "शण्डामर्क", "शुक्रामन्थिन",
    "होतापोतार", "मातापितर", "मातरापितर", "अर्णाचित्ररथ", "पर्जन्यवात", "नक्तोषासा",
)


@dataclass(frozen=True)
class NormalizedPada:
  """One normalized US-accented padapāṭha word."""

  us_form: str
  hyph_bare: str
  clean_bare: str
  marks: tuple[str, ...]
  is_unaccented: bool


def _is_devanagari(s: str) -> bool:
  return any("\u0900" <= c <= "\u097f" for c in s)


def strip_all_accents(s: str) -> str:
  return ALL_ACCENTS_RE.sub("", s)


def apply_us_marks_to_hyph(hyph_bare: str, flat_marks: Sequence[str]) -> str:
  """Render flat syllable US marks back onto a hyphenated Devanagari word cleanly."""
  if not flat_marks or all(m == "" for m in flat_marks):
    return hyph_bare
  parts = hyph_bare.split("-")
  rendered: list[str] = []
  idx = 0
  for p in parts:
    if not p:
      continue
    k = ss._fast_syllable_count(p)
    sub_marks = flat_marks[idx:idx + k]
    idx += k
    rendered.append(ss._fast_apply_us_marks(p, sub_marks))
  return "-".join(rendered)


_ITI_MATRA_TO_VOWEL: dict[str, str] = {
    "ा": "आ", "ि": "इ", "ी": "ई", "ु": "उ", "ू": "ऊ",
    "ृ": "ऋ", "ॄ": "ॠ", "े": "ए", "ै": "ऐ", "ो": "ओ", "ौ": "औ",
}
_ITI_INIT_VOWELS = ("अ", "आ", "इ", "ई", "उ", "ऊ", "ऋ", "ॠ", "ए", "ऐ", "ओ", "औ")


def _restore_iti_merged_vowel(conn: str, right: str, acc: str) -> str:
  """Restore initial vowel merged into ``इत्य``/``इती``/``इत्यु`` without vowel+mātrā glitches."""
  right_bare = strip_all_accents(right)
  if conn == "इत्य" and right_bare.startswith(("आ", "ा")):
    return ("आ" + acc + right[1:]) if right.startswith("ा") else right
  if conn in ("इत्य", "इती", "इत्यु") and not right_bare.startswith(_ITI_INIT_VOWELS):
    if right_bare and right_bare[0] in _ITI_MATRA_TO_VOWEL:
      v = ("आ" if conn == "इत्य" else "इ") if right_bare[0] == "ा" else _ITI_MATRA_TO_VOWEL[right_bare[0]]
      return v + acc + right[1:]
    init_v = {"इति": "", "इत्य": "अ", "इती": "इ", "इत्यु": "उ"}[conn]
    return init_v + acc + right
  return right


def _strip_leftover_iti_gloss(raw: str) -> str:
  """Strip unremoved ``XइतिY`` / ``Xऽइति`` padapāṭha glosses while preserving real ``इति`` compounds."""
  s = raw.strip()
  bare = strip_all_accents(s)

  if re.search(r"ऽ(?:इति|इत्य|इती)$", bare):
    left_part = regex.split(r"ऽइत[\u093f\u0940\u092f\u0951\u0952\u1cd0-\u1cff]*$", s)[0]
    if _is_devanagari(left_part):
      return left_part.rstrip("ऽ-")

  # "X इ॒वेत्य॒क्षीऽइ॑व" / "X इ॒वेति दम्पतीऽइव" / "उ॒प॒धी इ॒वेत्यु॑प॒धीऽइ॑व"
  m_iva = regex.search(
      r"\s+इ[\u0951\u0952\u1cd0-\u1cff]*वे[\u0951\u0952\u1cd0-\u1cff]*(ति|त्यु|त्य)([\u0951\u0952\u1cd0-\u1cff]*)(.+)$",
      s,
  )
  if m_iva and "ऽ" in m_iva.group(3):
    conn_iva = {"ति": "इति", "त्य": "इत्य", "त्यु": "इत्यु"}[m_iva.group(1)]
    return _restore_iti_merged_vowel(conn_iva, m_iva.group(3).strip(), m_iva.group(2))

  # "X इत्य॑द्रिऽसानो" / "Xइती॑न्द्रा॒ग्नी" / "अक॒रित्यकः॑" / "प्रणी॒तीति॒ प्र-नी॒ती॒"
  conn_re = regex.compile(
      r"(?:(इति|इत्यु|इत्य|इती)|([\u093f\u0940])([\u0951\u0952\u1cd0-\u1cff]*)(ति|त्यु|त्य|ती))([\u0902\u0901\u0903\u0951\u0952\u1cd0-\u1cff]*)"
  )
  for m in conn_re.finditer(s):
    left = s[:m.start()]
    right = s[m.end():].strip()
    if not left.strip() or not right:
      continue
    if left.rstrip(" \t\r\n").endswith(("ऽ", "-")):
      continue
    is_explicit_iti = bool(m.group(1))
    if not is_explicit_iti and strip_all_accents(right).startswith(("ऽ", "-", "ःऽ")):
      continue
    if is_explicit_iti:
      conn = m.group(1)
    else:
      left = left + ("\u094d" if m.group(2) in ("\u093f", "\u0940") else "")
      conn = {"ति": "इति", "त्य": "इत्य", "ती": "इती", "त्यु": "इत्यु"}[m.group(4)]
    conn_acc = m.group(5)
    left_bare = strip_all_accents(left.replace(" ", ""))
    if "ऽ" in left_bare:
      continue
    cand = _restore_iti_merged_vowel(conn, right, conn_acc)

    cand = regex.sub(r"^[ंँःऽ\u094d]+", "", cand.strip())
    if not cand:
      continue
    cand_bare = (
        strip_all_accents(cand.replace("ऽ", "").replace("-", ""))
        .replace("\u094d", "")
        .replace("ण", "न")
        .replace("ष", "स")
    )
    lclean = left_bare.replace("ऽ", "").replace("-", "").replace("\u094d", "").replace("ण", "न").replace("ष", "स")
    if not lclean or not cand_bare:
      continue
    has_prefix_match = (
        (len(lclean) >= 2 and len(cand_bare) >= 2 and (lclean[:2] == cand_bare[:2] or lclean.endswith(cand_bare[-2:])))
        or (len(lclean) >= 4 and len(cand_bare) >= 2 and cand_bare[:2] in lclean and lclean[0] == cand_bare[0])
    )
    if (" " in left and lclean[0] == cand_bare[0]) or has_prefix_match:
      return cand

  if bare == "अन्विति":
    return re.sub(r"न्विति.*$", "नु", s)

  return s


def _normalize_clean_token_chars(raw: str) -> str:
  """Normalize glyphs, pluta numerals, and Vedic accent marks before parsing syllables."""
  s = raw.strip()
  s = s.replace("\u200d", "").replace("\u200c", "")
  s = s.replace("᳡", _CL_SVARITA)
  s = s.replace("\u1cd6", _CL_SVARITA)  # Mādhyandina aggr. svarita
  s = s.replace("ᳫँ", "ँ").replace("ᳫं", "ं")
  s = re.sub(r"\([०-९0-9]+\)", "", s)
  s = re.sub(r"[१२३123\[\]:]", "", s)
  s = s.replace("।", "").replace("॥", "").strip()
  s = s.replace("ऽ", "-")
  s = re.sub(r"-{2,}", "-", s).strip("-")
  return s


def is_dual_accent_candidate(hyph_bare: str, clean_bare: str, marks: Sequence[str]) -> bool:
  """Check if multiple U/S accents are valid dual-accent Vedic compounds or ``-तवै`` infinitives."""
  if sum(1 for m in marks if m) != 2:
    return False
  norm_clean = clean_bare.replace("ँ", "ं")
  if ss._is_dual_accent_word(ss._normalize_lookup_key(norm_clean)):
    return True
  for pref in DEVATA_DVANDVA_PREFIXES:
    if norm_clean.startswith(pref):
      return True
  if norm_clean.endswith(("तवै", "तवा")) and marks[0] and marks[-1]:
    return True
  if "-" in hyph_bare:
    parts = [p for p in hyph_bare.split("-") if p]
    if len(parts) >= 2:
      n_pre = ss._fast_syllable_count(parts[0])
      idx_list = [i for i, m in enumerate(marks) if m]
      if len(idx_list) == 2 and idx_list[0] < n_pre <= idx_list[1]:
        return True
  return False


def _classical_syls_to_marks(
    syls: list[tuple[str, bool]],
    hyph_bare: str,
    clean_bare: str,
) -> tuple[tuple[str, ...] | None, bool]:
  """Convert scanned classical syllables to US marks ``('U'|'S'|'', ...)`` + ``is_unaccented`` flag."""
  n_syl = len(syls)
  if n_syl == 0:
    return None, False

  raw_marks: list[str] = []
  for mks, _ in syls:
    has_l = _CL_ANUDATTA in mks
    has_s = _CL_SVARITA in mks
    raw_marks.append("LS" if (has_l and has_s) else ("L" if has_l else ("S" if has_s else "")))

  if all(m == "" for m in raw_marks):
    if n_syl == 1:
      if clean_bare in ENCLITIC_PARTICLES:
        return ("",), False
      return ("U",), False
    return tuple("" for _ in range(n_syl)), True

  if all(m == "L" for m in raw_marks):
    return tuple("" for _ in range(n_syl)), False

  if n_syl == 1:
    m0 = raw_marks[0]
    if m0 in ("S", "LS"):
      return (("S",) if syls[0][1] else ("U",)), False
    return ("U",), False

  def _decode_standard(rms: list[str]) -> list[str] | None:
    us: list[str] = []
    in_pracaya = False
    for idx, mk in enumerate(rms):
      if mk == "L":
        us.append("")
        in_pracaya = False
      elif mk in ("S", "LS"):
        if idx > 0 and us[idx - 1] == "U":
          us.append("")
        elif syls[idx][1]:
          us.append("S")
        else:
          return None
        in_pracaya = True
      else:
        us.append("" if in_pracaya else "U")
    return us

  std = _decode_standard(raw_marks)
  if std is not None:
    n_acc = sum(1 for m in std if m)
    if n_acc == 1:
      return tuple(std), False
    if n_acc == 2:
      # Guard against Mādhyandina-style missing leading `॒` before `L` on non-dual compounds
      # (`सुऽप्र॒जाः`, `पुष्टि॒ऽवर्ध॑नः`, `वसुऽधे॑यस्य`): when `raw_marks[0] == ""` and no `S`/`LS`
      # precedes the first `L`, only canonical dual-accent compounds / `-तवै` infinitives keep 2 accents;
      # all other compounds fall through to Pattern 1 to repair the missing leading `॒`.
      has_unmarked_before_first_l = (
          raw_marks[0] == ""
          and "L" in raw_marks
          and not any(m in ("S", "LS") for m in raw_marks[:raw_marks.index("L")])
      )
      norm_c = clean_bare.replace("ँ", "ं")
      is_known_dual = (
          ss._is_dual_accent_word(ss._normalize_lookup_key(norm_c))
          or any(norm_c.startswith(p) for p in DEVATA_DVANDVA_PREFIXES)
          or (norm_c.endswith(("तवै", "तवा")) and bool(std[0]) and bool(std[-1]))
      )
      if is_known_dual or (
          not has_unmarked_before_first_l and is_dual_accent_candidate(hyph_bare, clean_bare, std)
      ):
        return tuple(std), False

  # Pattern 1: Leading unmarked syllable(s) missing ॒ before L (अच॒क्रे, अनू॒ची, एत॒वै, सु॒ऽउक्तस्य॑)
  if "" in raw_marks and raw_marks[0] == "" and "L" in raw_marks:
    if clean_bare.endswith(("तवै", "तवा")) and raw_marks[-1] == "":
      return tuple(["U"] + ["" for _ in range(n_syl - 2)] + ["U"]), False
    first_l = raw_marks.index("L")
    if first_l >= 1 and all(m == "" for m in raw_marks[:first_l]):
      repaired = ["L"] * first_l + raw_marks[first_l:]
      std2 = _decode_standard(repaired)
      if std2 is not None and sum(1 for m in std2 if m) == 1:
        return tuple(std2), False
      last_l = max(i for i, m in enumerate(repaired) if m == "L")
      if "S" not in repaired[last_l + 1:] and last_l + 1 < n_syl and all(m == "" for m in repaired[last_l + 1:]):
        out = [""] * n_syl
        out[last_l + 1] = "U"
        return tuple(out), False

  # Pattern 2: Initial non-jātya ॑ (AV Book 20 & MS iti-residual 'इत्य॑...')
  if raw_marks[0] in ("S", "LS") and not syls[0][1]:
    rest = raw_marks[1:]
    has_later_s = any(m in ("S", "LS") for m in rest)
    last_l_rest = max((i for i, m in enumerate(rest) if m == "L"), default=-1)
    has_l_then_final_u = (last_l_rest >= 0 and last_l_rest == len(rest) - 2 and rest[-1] == "")
    if has_later_s or has_l_then_final_u:
      repaired = ["L" if "L" in rest else ""] + rest
      if "L" in rest:
        first_l = rest.index("L") + 1
        repaired[:first_l] = ["L"] * first_l
      std2 = _decode_standard(repaired)
      if std2 is not None and sum(1 for m in std2 if m) == 1:
        return tuple(std2), False
      if "L" in repaired and "S" not in repaired:
        last_l = max(i for i, m in enumerate(repaired) if m == "L")
        if last_l + 1 < n_syl:
          out = [""] * n_syl
          out[last_l + 1] = "U"
          return tuple(out), False
    else:
      return tuple(["U"] + [""] * (n_syl - 1)), False

  # Pattern 3: L+ run followed by unmarked syllables (अ॒स्माकम्, उ॒क्थेभिः)
  if raw_marks[0] == "L" and "S" not in raw_marks:
    last_l = max(i for i, m in enumerate(raw_marks) if m == "L")
    if last_l + 1 < n_syl and all(m == "" for m in raw_marks[last_l + 1:]):
      out = [""] * n_syl
      out[last_l + 1] = "U"
      return tuple(out), False

  # Pattern 3b: Single L immediately followed by non-jātya S (अ॒मृ॑ताः, आ॒ऽवृ॑तः, वा॒जि॑ना, सु॒ऽउक्तस्य॑)
  s_only_idx = [i for i, m in enumerate(raw_marks) if m == "S"]
  if len(s_only_idx) == 1 and "LS" not in raw_marks and "L" in raw_marks:
    si = s_only_idx[0]
    last_l = max(i for i, m in enumerate(raw_marks) if m == "L")
    if last_l == si - 1 and all(m in ("", "L") for m in raw_marks[:last_l]) and all(m == "" for m in raw_marks[si + 1:]):
      out = [""] * n_syl
      out[si] = "S" if syls[si][1] else "U"
      return tuple(out), False
    if last_l < si - 1 and all(m in ("", "L") for m in raw_marks[:si]) and all(m == "" for m in raw_marks[si + 1:]):
      out = [""] * n_syl
      if syls[si][1]:
        out[si] = "S"
      else:
        out[si - 1] = "U"
      return tuple(out), False

  # Pattern 3c: Single non-jātya S at >= 1 with NO L anywhere (ग्नाःपत्नी॑भिः, सूरिऽभ्यः॑, अयज्योः॑, अतिक्राम॑न्ति)
  if len(s_only_idx) == 1 and "L" not in raw_marks and "LS" not in raw_marks:
    si = s_only_idx[0]
    if si >= 1:
      out = [""] * n_syl
      if syls[si][1]:
        out[si] = "S"
      else:
        out[si - 1] = "U"
      return tuple(out), False

  # Pattern 4: Multiple S (dual-accent compounds / devatā-dvandva / stray final S)
  if sum(1 for m in raw_marks if m in ("S", "LS")) >= 2:
    s_indices = [i for i, m in enumerate(raw_marks) if m in ("S", "LS")]
    if len(s_indices) == 2 and "-" in hyph_bare:
      p0_cnt = ss._fast_syllable_count(hyph_bare.split("-")[0])
      if s_indices[0] < p0_cnt <= s_indices[1]:
        u0 = 0 if (s_indices[0] == 0 and not syls[0][1]) else max(0, s_indices[0] - 1)
        u1 = max(p0_cnt, s_indices[1] - 1) if not syls[s_indices[1]][1] else s_indices[1]
        out = [""] * n_syl
        out[u0] = "U"
        out[u1] = "S" if (syls[s_indices[1]][1] and u1 == s_indices[1]) else "U"
        return tuple(out), False
    if len(s_indices) == 2:
      norm_c = clean_bare.replace("ँ", "ं")
      if any(norm_c.startswith(p) for p in DEVATA_DVANDVA_PREFIXES) or ss._is_dual_accent_word(ss._normalize_lookup_key(norm_c)):
        out = [""] * n_syl
        for si in s_indices:
          if si == 0 or syls[si][1]:
            out[si] = "S" if syls[si][1] else "U"
          else:
            out[si - 1] = "U"
        return tuple(out), False
    if raw_marks[-1] in ("S", "LS") and not syls[-1][1]:
      trimmed = raw_marks[:-1] + [""]
      std3 = _decode_standard(trimmed)
      if std3 is not None and sum(1 for m in std3 if m) == 1:
        return tuple(std3), False

  # Pattern 5: LS on final syllable after L+ run (ज॒ना॒सः॒॑)
  if raw_marks[-1] in ("S", "LS") and not syls[-1][1] and raw_marks.count("S") + raw_marks.count("LS") == 1:
    if all(m == "L" for m in raw_marks[:-1]):
      return tuple("" for _ in range(n_syl)), True
    idx_u = n_syl - 2 if (n_syl >= 2 and raw_marks[-2] == "") else n_syl - 1
    out = [""] * n_syl
    out[idx_u] = "U"
    return tuple(out), False

  return None, False


def normalize_raw_form_to_us(raw_form: str, *, already_us: bool = False) -> NormalizedPada | None:
  """Normalize one raw Babylon padapāṭha form (TS US or RV/AV/MS classical/mixed) to US marks."""
  if not raw_form or not _is_devanagari(raw_form):
    return None
  s = _strip_leftover_iti_gloss(raw_form)
  s = _normalize_clean_token_chars(s)
  if not s or not _is_devanagari(s):
    return None

  has_us = US_UDATTA in s or US_SVARITA in s
  has_cl = _CL_SVARITA in s or _CL_ANUDATTA in s

  hyph_bare = strip_all_accents(s)
  parts = [p for p in hyph_bare.split("-") if p]
  if not parts:
    return None
  hyph_bare = "-".join(parts)
  clean_bare = "".join(parts)

  clean_with_marks = s.replace("-", "")
  if has_us:
    clean_us_only = regex.sub(r"[\u0951\u0952]", "", clean_with_marks)
    syls = ss._fast_scan_deva_syllables(clean_us_only)
    if not syls:
      return None
    marks = tuple(
        "S" if US_SVARITA in mks else ("U" if US_UDATTA in mks else "")
        for mks, _ in syls
    )
    us_form = apply_us_marks_to_hyph(hyph_bare, marks)
    is_unacc = all(m == "" for m in marks)
    return NormalizedPada(us_form=us_form, hyph_bare=hyph_bare, clean_bare=clean_bare, marks=marks, is_unaccented=is_unacc)

  if already_us and not has_cl:
    n_syl = ss._fast_syllable_count(clean_bare)
    if n_syl == 0:
      return None
    marks = tuple("" for _ in range(n_syl))
    is_unacc = n_syl > 1 or clean_bare not in ENCLITIC_PARTICLES
    return NormalizedPada(us_form=hyph_bare, hyph_bare=hyph_bare, clean_bare=clean_bare, marks=marks, is_unaccented=is_unacc)

  syls = ss._fast_scan_deva_syllables(clean_with_marks)
  marks_opt, is_unacc = _classical_syls_to_marks(syls, hyph_bare, clean_bare)
  if marks_opt is None:
    return None
  us_form = apply_us_marks_to_hyph(hyph_bare, marks_opt)
  return NormalizedPada(
      us_form=us_form,
      hyph_bare=hyph_bare,
      clean_bare=clean_bare,
      marks=marks_opt,
      is_unaccented=is_unacc,
  )


def build_compound_extra_headwords(
    forms: Iterable[str],
    join_sandhi: Callable[[str], str],
) -> dict[str, set[str]]:
  """Build sandhi-joined compound headword aliases keyed by hyphenless bare form."""
  extras: dict[str, set[str]] = defaultdict(set)
  for form in forms:
    if "-" not in form:
      continue
    hyph_bare = strip_all_accents(form).strip("-")
    if "-" not in hyph_bare:
      continue
    no_hyph = hyph_bare.replace("-", "")
    joined = join_sandhi(hyph_bare)
    if joined and joined != no_hyph:
      extras[no_hyph].add(joined)
  return extras


def convert_counts_and_loci_to_us(
    raw_counts: dict[str, int],
    raw_loci: dict[str, Sequence[str]],
    *,
    already_us: bool = False,
) -> tuple[Counter[str], dict[str, list[str]], int]:
  """Convert a ``counts`` + ``loci`` dictionary of padapāṭha forms to clean US notation.

  Unrecoverable corrupt classical markings fall back to unaccented clean Devanagari so zero
  classical accent marks remain anywhere in the output.
  """
  us_counts: Counter[str] = Counter()
  us_loci: dict[str, dict[str, None]] = defaultdict(dict)
  fallback_count = 0

  for raw_form, cnt in raw_counts.items():
    npada = normalize_raw_form_to_us(raw_form, already_us=already_us)
    if npada is not None:
      us_form = npada.us_form
    else:
      fallback = _normalize_clean_token_chars(strip_all_accents(_strip_leftover_iti_gloss(raw_form)))
      if not fallback or not _is_devanagari(fallback):
        continue
      us_form = fallback
      fallback_count += 1
    us_counts[us_form] += cnt
    for loc in raw_loci.get(raw_form, ()):
      if loc:
        us_loci[us_form].setdefault(loc, None)

  loci_out = {w: list(loc_map.keys()) for w, loc_map in us_loci.items()}
  return us_counts, loci_out, fallback_count

_SYLLABLE_RE = regex.compile(
    r"[\u0905-\u0914\u0960\u0961][\u0901-\u0903]?"
    r"|(?:[\u0915-\u0939\u0958-\u095f\u0979-\u097f]\u094d)*"
    r"[\u0915-\u0939\u0958-\u095f\u0979-\u097f]"
    r"(?:[\u093e-\u094c\u0962\u0963])?"
    r"(?:[\u0901-\u0903]|(?:[\u0915-\u0939]\u094d)+)?"
)


def us_to_dependent_pada(us_word: str) -> str:
  """Convert a single US-accented Devanagari pada (with optional ``ऽ``) to dependent (``॒``/``॑``) notation."""
  if "\u1cd3" not in us_word and "\u1cd9" not in us_word:
    # Sarvānudātta pada: mark every syllable's vowel nucleus / visarga with anudātta ॒
    def _mark_syl(m: regex.Match) -> str:
      s = m.group(0)
      # Place ॒ right before trailing halant cluster / anusvāra / visarga? In Śākala/TS:
      # after vowel matra (before anusvāra/candrabindu/final consonant cluster), or after ः if final visarga?
      # Wait: in Śākala/TS padapāṭha: अ॒भ॒वः॒ (after ः), ध॒त्त॒म् (before म्), श्र॒य॒न्ता॒म् (before म्), इ॒न्दो॒.
      hm = regex.search(r"(?:[\u0915-\u0939]\u094d)+$", s)
      if hm:
        return s[:hm.start()] + "॒" + s[hm.start():]
      return s + "॒"

    parts = us_word.split("ऽ")
    return "ऽ".join(_SYLLABLE_RE.sub(_mark_syl, p) for p in parts)

  dep = accent.add_dependent_accents(us_word)
  dep = dep.replace("\u1cd3", "").replace("\u1cdc", "॑").replace("\u1cd9", "॑")
  return dep


def build_visvara_headwords(visvara_word: str, *, include_optitrans: bool = False) -> tuple[str, ...]:
  """Build deduplicated Devanagari (and optionally OPTITRANS) lookup headwords."""
  base_hws: list[str] = [visvara_word]
  if visvara_word.endswith("ः") and len(visvara_word) > 2:
    base_hws.append(visvara_word[:-1])
  elif visvara_word.endswith("म्") and len(visvara_word) > 3:
    base_hws.append(visvara_word[:-2])

  expanded: list[str] = []
  for hw in base_hws:
    expanded.append(hw)
    if "ँ" in hw:
      expanded.append(hw.replace("ँ", "ं"))

  if include_optitrans:
    with_roman: list[str] = []
    for hw in expanded:
      with_roman.append(hw)
      rom = sanscript.transliterate(hw, sanscript.DEVANAGARI, sanscript.OPTITRANS)
      if rom and rom != hw:
        with_roman.append(rom)
    expanded = with_roman

  return tuple(dict.fromkeys(h for h in expanded if h))


def _merge_headwords(
    visvara_word: str,
    extras: set[str] | list[str] | tuple[str, ...] | None,
    *,
    include_optitrans: bool,
) -> tuple[str, ...]:
  """Combine canonical ``visvara_word`` headwords with any optional extra bare aliases."""
  merged = list(build_visvara_headwords(visvara_word, include_optitrans=include_optitrans))
  if extras:
    for extra in sorted(extras):
      if extra and extra != visvara_word:
        merged.extend(build_visvara_headwords(extra, include_optitrans=include_optitrans))
  return tuple(dict.fromkeys(h for h in merged if h))


_READONLY_DICT_PATH_MARKERS: tuple[str, ...] = (
    "raw_etexts/koshaH/indic-dict",
)


def assert_writable_dict_dest(dest_path: str) -> None:
  """Refuse writes to read-only dictionary mirrors (e.g. ``raw_etexts/koshaH/indic-dict``)."""
  norm = os.path.realpath(os.path.abspath(dest_path)).replace("\\", "/")
  for marker in _READONLY_DICT_PATH_MARKERS:
    if marker in norm or marker in dest_path.replace("\\", "/"):
      raise PermissionError(
          f"Refusing to write dictionary output to read-only mirror path: {dest_path}"
      )


def dump_padasvara_babylon(
    counts: dict[str, int],
    loci: dict[str, list[str]],
    dest_dir: str,
    *,
    write_final: bool = False,
    citation_sep: str = ", ",
    max_citations: int | None = None,
    extra_headwords: dict[str, set[str] | list[str] | tuple[str, ...]] | None = None,
) -> tuple[str, str | None]:
  """Write ``<name>.babylon`` (and optionally ``<name>.babylon_final``) with frequencies.

  Multi-variant headwords are ordered by descending frequency ``(-count, sasvara_word)``
  so the most attested accentuation always appears first.
  """
  assert_writable_dict_dest(dest_dir)
  visvara_to_sasvara: dict[str, list[str]] = defaultdict(list)
  for sasvara_word in counts:
    visvara_word = regex.sub(fr"{accent.ACCENTS_PATTERN}|[ऽ\-]", "", sasvara_word).strip()
    visvara_word = regex.sub(r"[१२३123]", "", visvara_word)
    if not visvara_word:
      continue
    visvara_to_sasvara[visvara_word].append(sasvara_word)

  defs_dev: list[Definition] = []
  defs_final: list[Definition] = []

  for visvara_word in sorted(visvara_to_sasvara.keys()):
    variants = sorted(
        visvara_to_sasvara[visvara_word],
        key=lambda w: (-counts[w], w),
    )
    extras = extra_headwords.get(visvara_word) if extra_headwords else None
    hws_dev = _merge_headwords(visvara_word, extras, include_optitrans=False)
    hws_final = _merge_headwords(visvara_word, extras, include_optitrans=True) if write_final else ()

    for sasvara_word in variants:
      freq = counts[sasvara_word]
      word_loci = loci.get(sasvara_word, [])
      if max_citations is not None and len(word_loci) > max_citations:
        shown = citation_sep.join(word_loci[:max_citations]) + f"{citation_sep}… (+{len(word_loci) - max_citations})"
      else:
        shown = citation_sep.join(word_loci)
      if shown:
        meaning = f"{sasvara_word} ({freq})<br>{shown}"
      else:
        meaning = f"{sasvara_word} ({freq})"
      defs_dev.append(Definition(headwords_tuple=hws_dev, meaning=meaning))
      if write_final:
        defs_final.append(Definition(headwords_tuple=hws_final, meaning=meaning))

  dict_name = os.path.basename(os.path.normpath(dest_dir))
  bab_path = os.path.join(dest_dir, f"{dict_name}.babylon")
  headers = {
      "bookname": f"{dict_name} (sa-sa)",
      "sametypesequence": "h",
      "stripmethod": "keep",
  }
  babylon.dump(dest_path=bab_path, definitions=defs_dev, headers=headers)
  logging.info("Wrote %d definitions to %s", len(defs_dev), bab_path)

  final_path = None
  if write_final:
    final_path = os.path.join(dest_dir, f"{dict_name}.babylon_final")
    babylon.dump(dest_path=final_path, definitions=defs_final, headers=dict(headers))
    logging.info("Wrote %d definitions to %s", len(defs_final), final_path)

  return bab_path, final_path
