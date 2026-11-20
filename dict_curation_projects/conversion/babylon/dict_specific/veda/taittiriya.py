"""Build ``kyv-ts-padasvara`` Babylon lexicon from Taittirīya Saṁhitā padapāṭha in US accent notation."""

from __future__ import annotations

from collections import Counter, defaultdict
import glob
import logging
import os
import regex

from indic_transliteration.sanscript.schemes.brahmic import accent

from .padasvara_common import dump_padasvara_babylon

PADA_BASE_DIR = "/home/vvasuki/gitland/sanskrit/raw_etexts_private/vedaH/taittirIyA/padapAThaH/saMhitA"
DEFAULT_DEST_DIRS = (
    "/home/vvasuki/gitland/sanskrit/raw_etexts/koshaH/indic-dict/kAvya/kyv-ts-padasvara",
    "/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-kAvya/kyv-ts-padasvara",
    "/home/vvasuki/gitland/indic-dict/stardict/stardict-sanskrit-kAvya/kyv-ts-padasvara",
)

_UDATTA = "\u1cd3"
_SVARITA = "\u1cd9"
_US_ACCENTS_RE = regex.compile(r"[\u1cd3\u1cd9]")
_DEVA_LETTER_RE = regex.compile(r"[\u0905-\u0939]")
_PLUTA_RE = regex.compile(r"\([०-९0-9]+\)")
_HALANT_ACCENT_RE = regex.compile(r"((?:[\u0915-\u0939\u0958-\u095f]\u094d)+)([\u0951\u0952]+)")
_DUP_CLASSICAL_RE = regex.compile(r"([\u0951\u0952])\1+")
_ITI_COMPOUND_RE = regex.compile(r"([इेीि])([\u0951\u0952]?त)(्य[ाुूृॄेैोौ]?|ी|ि)([\u0951\u0952]?)(\s*)")
_SYLLABLE_RE = regex.compile(
    r"(?:[\u0905-\u0914\u0960\u0961][\u0901-\u0903\u1cd3\u1cd9]*)"
    r"|(?:(?:[\u0915-\u0939\u0958-\u095f\u0979-\u097f]\u094d)*"
    r"[\u0915-\u0939\u0958-\u095f\u0979-\u097f]"
    r"(?:[\u093e-\u094c\u0962\u0963])?"
    r"(?:[\u0901-\u0903\u1cd3\u1cd9]|(?:[\u0915-\u0939\u0958-\u095f]\u094d)+)*)"
)
_LABEL_BOUNDARY_RE = regex.compile(r"(?:^|\s)(\d+[A-Z]*|[A-Z]+)\s*।")
_LEADING_LABEL_RE = regex.compile(r"^(?:\d+[A-Z]*|[A-Z]+)\s+")
_TOKEN_BLOCK_RE = regex.compile(r"([^।॥]+)([।॥]+)")

_IND_VOWELS = frozenset("अआइईउऊऋॠऌएऐओऔ")
_MATRA_TO_IND: dict[str, str] = {
    "ा": "आ", "ि": "इ", "ी": "ई", "ु": "उ", "ू": "ऊ",
    "ृ": "ऋ", "ॄ": "ॠ", "े": "ए", "ै": "ऐ", "ो": "ओ", "ौ": "औ",
}
_VOWEL_MERGE: dict[tuple[str, str], str] = {
    ("अ", "अ"): "आ", ("अ", "आ"): "आ", ("आ", "अ"): "आ", ("आ", "आ"): "आ",
    ("अ", "इ"): "ए", ("अ", "ई"): "ए", ("आ", "इ"): "ए", ("आ", "ई"): "ए",
    ("अ", "उ"): "ओ", ("अ", "ऊ"): "ओ", ("आ", "उ"): "ओ", ("आ", "ऊ"): "ओ",
    ("अ", "ऋ"): "अर्", ("आ", "ऋ"): "अर्",
    ("अ", "ए"): "ऐ", ("अ", "ऐ"): "ऐ", ("आ", "ए"): "ऐ", ("आ", "ऐ"): "ऐ",
    ("अ", "ओ"): "औ", ("अ", "औ"): "औ", ("आ", "ओ"): "औ", ("आ", "औ"): "औ",
    ("इ", "इ"): "ई", ("इ", "ई"): "ई", ("ई", "इ"): "ई", ("ई", "ई"): "ई",
    ("उ", "उ"): "ऊ", ("उ", "ऊ"): "ऊ", ("ऊ", "उ"): "ऊ", ("ऊ", "ऊ"): "ऊ",
    ("ऋ", "ऋ"): "ॠ",
}
_IND_TO_MATRA: dict[str, str] = {
    "अ": "", "आ": "ा", "इ": "ि", "ई": "ी", "उ": "ु", "ऊ": "ू",
    "ऋ": "ृ", "ॠ": "ॄ", "ऌ": "ॢ", "ए": "े", "ऐ": "ै", "ओ": "ो", "औ": "ौ",
}
_MATRA_TO_VOWEL: dict[str, str] = {v: k for k, v in _IND_TO_MATRA.items() if v}

# Closed set of standalone upasarga+iti markers in TS padapāṭha (resolved to base upasarga).
_UPASARGA_ITI_MAP: dict[str, str] = {
    "प्रेति॑": f"प्र{_UDATTA}",
    "उपेति॑": f"उ{_UDATTA}प",
    "समिति॑": f"स{_UDATTA}म्",
    "अवेति॑": f"अ{_UDATTA}व",
    "वीति॑": f"वि{_UDATTA}",
    "अन्विति॑": f"अ{_UDATTA}नु",
    "प्रतीति॑": f"प्र{_UDATTA}ति",
    "निरिति॑": f"निः{_UDATTA}",
    "अ॒भीति॑": f"अभि{_UDATTA}",
    "उदिति॑": f"उ{_UDATTA}त्",
    "परीति॑": f"प{_UDATTA}रि",
    "अपेति॑": f"अ{_UDATTA}प",
    "नीति॑": f"नि{_UDATTA}",
    "अधीति॑": f"अ{_UDATTA}धि",
    "अपीति॑": f"अ{_UDATTA}पि",
    "परेति॑": f"प{_UDATTA}रा",
    "अतीति॑": f"अ{_UDATTA}ति",
    "स्विति॑": f"सु{_UDATTA}",
    "एति॑": f"आ{_UDATTA}",
}

# Genuinely multi-udātta compound stems / formations attested in TS padapāṭha.
_DUAL_ACCENT_STEMS: tuple[str, ...] = (
    "द्यावा-पृथिव", "अग्नी-सोम", "अग्नी-वरुण", "अग्ना-विष्णु",
    "इन्द्रा-वरुण", "इन्द्रा-बृहस्पत", "इन्द्रा-विष्णु",
    "मित्रा-वरुण", "शण्डा-मर्क", "शुक्रा-मन्थिन", "बम्बा-विश्ववयस",
    "वन-स्पत", "बृह-स्पत", "वनस्पत", "बृहस्पत",
    "तनू-नपा", "नरा-शँस", "नराशँस",
    "अङ्गा-परूँषि", "इध्मा-बर्हि", "अनु-एतवै", "अभि-चरितवै",
    "सत्य-राजान्",
)

# Standard internal compound sandhi rules for lookup headword aliases.
_INTERNAL_SANDHI_RULES: tuple[tuple[regex.Pattern[str], str], ...] = (
    (regex.compile(r"प्(?=[भधदगघजझब])"), "द्"),
    (regex.compile(r"त्(?=[भधदगघब])"), "द्"),
    (regex.compile(r"क्(?=[भधदगघब])"), "ग्"),
    (regex.compile(r"त्(?=[नलम])"), "न्"),
    (regex.compile(r"म्(?=[यरलवशषसह])"), "ं"),
    (regex.compile(r"([िीुूृेोौ])ः([कखपफ])"), r"\1ष्\2"),
    (regex.compile(r"ः([कखपफ])"), r"स्\1"),
    (regex.compile(r"ःअ"), "र"),
    (regex.compile(r"ःआ"), "रा"),
    (regex.compile(r"ःइ"), "रि"),
    (regex.compile(r"ःई"), "री"),
    (regex.compile(r"ःउ"), "रु"),
    (regex.compile(r"ःऊ"), "रू"),
    (regex.compile(r"ःऋ"), "रृ"),
    (regex.compile(r"ःए"), "रे"),
    (regex.compile(r"ःओ"), "रो"),
    (regex.compile(r"(?<=[ाआ])ः(?=र)"), ""),
    (regex.compile(r"(?<=[ािीुूृॄेैोौआइईउऊऋएऐओऔ])ः(?=[गघदधबभयवरलहजझमन])"), "र्"),
    (regex.compile(r"(?<![ािीुूृॄेैोौआइईउऊऋएऐओऔ\u094d])ः(?=[गघदधबभयवरलहजझमन])"), "ो"),
)


def _split_syls_with_hyphens(word: str) -> list[str]:
  """Split ``word`` into syllable segments preserving ``-`` separators."""
  out: list[str] = []
  for pi, part in enumerate(word.split("-")):
    if pi > 0:
      out.append("-")
    pos = 0
    for m in _SYLLABLE_RE.finditer(part):
      if m.start() > pos:
        out.append(part[pos:m.start()])
      out.append(m.group(0))
      pos = m.end()
    if pos < len(part):
      out.append(part[pos:])
  return [seg for seg in out if seg]


def _syl_marks(word: str) -> list[str]:
  """Return per-syllable US accent marks (``'U'``, ``'S'``, or ``''``)."""
  return [
      "S" if _SVARITA in seg else ("U" if _UDATTA in seg else "")
      for seg in _split_syls_with_hyphens(word)
      if seg != "-" and _DEVA_LETTER_RE.search(seg)
  ]


def _keep_accent_indices(word: str, keep_indices: set[int]) -> str:
  """Retain US accents only on syllable positions in ``keep_indices``."""
  segs = _split_syls_with_hyphens(word)
  syl_i = -1
  out: list[str] = []
  for seg in segs:
    if seg != "-" and _DEVA_LETTER_RE.search(seg):
      syl_i += 1
      if syl_i not in keep_indices:
        seg = _US_ACCENTS_RE.sub("", seg)
    out.append(seg)
  return "".join(out)


def _keep_only_last_accent(word: str) -> str:
  ms = _syl_marks(word)
  idxs = [i for i, mk in enumerate(ms) if mk]
  return _keep_accent_indices(word, {idxs[-1]}) if len(idxs) > 1 else word


def _add_udatta_on_syl(word: str, target_syl: int) -> str:
  """Place ``᳓`` on syllable ``target_syl`` (before any trailing halant cluster)."""
  segs = _split_syls_with_hyphens(word)
  syl_indices = [i for i, s in enumerate(segs) if s != "-" and _DEVA_LETTER_RE.search(s)]
  if not syl_indices:
    return word
  seg_i = syl_indices[target_syl]
  seg = _US_ACCENTS_RE.sub("", segs[seg_i])
  hm = regex.search(r"(?:[\u0915-\u0939\u0958-\u095f]\u094d)+$", seg)
  if hm:
    segs[seg_i] = seg[:hm.start()] + _UDATTA + seg[hm.start():]
  else:
    segs[seg_i] = seg + _UDATTA
  return "".join(segs)


def _norm_classical(s: str, *, bare_pluta_as_udatta: bool = True) -> str:
  """Normalize pluta markers, post-virāma classical accents, and duplicate marks."""
  has_cl = "\u0951" in s or "\u0952" in s
  if bare_pluta_as_udatta and "(" in s and not has_cl:
    s = _PLUTA_RE.sub(_UDATTA, s)
  else:
    s = _PLUTA_RE.sub("", s)
  s = _HALANT_ACCENT_RE.sub(r"\2\1", s)
  return _DUP_CLASSICAL_RE.sub(r"\1", s)


def _batch_to_us(texts: list[str]) -> list[str]:
  """Convert classical-accented strings to US notation in fast newline-delimited batches."""
  out = list(texts)
  to_run_idx: list[int] = []
  to_run_txt: list[str] = []
  for idx, t in enumerate(texts):
    if "\u0951" in t or "\u0952" in t:
      to_run_idx.append(idx)
      to_run_txt.append(t)

  chunk_size = 500
  for start in range(0, len(to_run_txt), chunk_size):
    chunk = to_run_txt[start : start + chunk_size]
    c_idx = to_run_idx[start : start + chunk_size]
    joined = "\n".join(chunk)
    conv = accent.to_US_accents(joined)
    parts = conv.split("\n")
    if len(parts) == len(chunk):
      for i, res in zip(c_idx, parts):
        out[i] = res
    else:
      for i, t in zip(c_idx, chunk):
        out[i] = accent.to_US_accents(t)
  return out


def _strip_accents_and_pluta(s: str) -> str:
  s = _PLUTA_RE.sub("", s)
  return regex.sub(r"[\u0951\u0952\u1cd3\u1cd9\u1cdc\s]+", "", s)


def _apply_seam_sandhi(left: str, right: str) -> str:
  if not left or not right:
    return left + right
  if left.endswith("्") and right[0] in _IND_VOWELS:
    stem = left[:-1]
    if left.endswith("त्") and right[0] != "ऋ":
      stem = left[:-2] + "द"
    return stem + _IND_TO_MATRA[right[0]] + right[1:]

  if right[0] in _IND_VOWELS:
    last_ch = left[-1]
    if last_ch in _MATRA_TO_VOWEL or last_ch in _IND_VOWELS or ("\u0915" <= last_ch <= "\u0939"):
      if last_ch in _IND_VOWELS:
        v1, base_l = last_ch, left[:-1]
      elif last_ch in _MATRA_TO_VOWEL:
        v1, base_l = _MATRA_TO_VOWEL[last_ch], left[:-1]
      else:
        v1, base_l = "अ", left
      v2, rest_r = right[0], right[1:]
      merged_v = _VOWEL_MERGE.get((v1, v2))
      if merged_v:
        if merged_v == "अर्":
          return (base_l + "र्" if base_l == left[:-1] and last_ch in _MATRA_TO_VOWEL else left + "र्") + rest_r
        if base_l.endswith("्") or last_ch in _IND_VOWELS:
          return base_l + merged_v + rest_r
        cons = left[:-1] if last_ch in _MATRA_TO_VOWEL else left
        return cons + _IND_TO_MATRA[merged_v] + rest_r
      if v1 in ("इ", "ई"):
        cons = left[:-1] if last_ch in _MATRA_TO_VOWEL else left
        return cons + "्य" + _IND_TO_MATRA[v2] + rest_r
      if v1 in ("उ", "ऊ"):
        cons = left[:-1] if last_ch in _MATRA_TO_VOWEL else left
        return cons + "्व" + _IND_TO_MATRA[v2] + rest_r

  cand = left + right
  seam = len(left)
  for pat, rep in _INTERNAL_SANDHI_RULES:
    for m in pat.finditer(cand):
      if m.start() < seam <= m.end():
        return cand[:m.start()] + m.expand(rep) + cand[m.end():]
  return cand


def _join_compound_sandhi(y_bare: str) -> str:
  """Join ``-`` seams using standard internal compound sandhi for lookup aliases."""
  parts = [p for p in y_bare.split("-") if p]
  if len(parts) < 2:
    return y_bare.replace("-", "")
  joined = parts[0]
  for nxt in parts[1:]:
    joined = _apply_seam_sandhi(joined, nxt)
  return joined


def _extract_x_sandhi_alias(
    x_part_bare: str,
    y_bare: str,
    *,
    v_pre: str = "",
    has_sp_before: bool = False,
) -> str | None:
  """Recover sandhi-joined lookup alias from ``X`` (reverting external ``इति`` sandhi)."""
  xb = x_part_bare.replace("ᳶ", "ः").strip()
  yb_clean = y_bare.replace("-", "")
  if not xb or xb == yb_clean:
    return None
  if v_pre == "ि" and not has_sp_before and yb_clean.endswith("्") and len(yb_clean) >= 2 and xb[-1] == yb_clean[-2]:
    return xb + "्"
  if yb_clean.endswith("ः") and xb.endswith("र्"):
    return xb[:-2] + "ः"
  if xb.endswith(("म्", "त्", "न्", "ः", "ङ्", "क्", "ट्")) and xb[-1] == yb_clean[-1]:
    return xb
  last_mem = y_bare.rsplit("-", 1)[-1]
  # Match last member prefix up to retroflexion (ष/स, ण/न) for `निषद्य` / `सुषदा` / `अँहोमुचे`
  norm_nat = lambda s: s.replace("ष", "स").replace("ण", "न")
  if len(last_mem) >= 2 and len(xb) >= len(last_mem) - 1:
    lm_stem = norm_nat(last_mem[:-1])
    if len(xb) >= len(lm_stem) and norm_nat(xb[-len(lm_stem):]) == lm_stem:
      return xb + last_mem[-1]
    if len(xb) >= len(last_mem) and norm_nat(xb[-len(last_mem):-1]) == lm_stem:
      return xb[:-1] + last_mem[-1]
  if norm_nat(xb).endswith(norm_nat(last_mem)):
    return xb
  return None


def _split_iti_compound(raw: str) -> dict | None:
  """Split ``X इति Y`` (with optional ``इति`` vowel coalescence onto ``Y``)."""
  dash = raw.find("-")
  if dash < 0:
    return None
  left = raw[:dash]
  best: tuple[int, int, regex.Match[str]] | None = None
  for i in range(1, len(left)):
    if left[i] not in "इेीि":
      continue
    m = _ITI_COMPOUND_RE.match(raw, i)
    if not m or m.end() > dash + 1:
      continue
    v_pre, _ta, end_sfx, _post_acc, sp = m.groups()
    x_head = raw[:m.start()]
    rest_after = raw[m.end():]
    if not x_head.strip() or "-" not in rest_after or " " in rest_after.strip():
      continue
    has_sp_before = raw[m.start() - 1].isspace()
    has_sp_after = bool(sp)
    if has_sp_after:
      score = 12 if (has_sp_before and v_pre == "इ") else (11 if v_pre in ("इ", "े", "ी") else 7)
    elif end_sfx == "ि":
      score = 3 if (has_sp_before and v_pre == "इ") else 1
    else:
      score = 10 if (has_sp_before and v_pre == "इ") else (8 if v_pre in ("इ", "े", "ी") else 5)
    cand = (score, m.start(), m)
    if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[1] > best[1]):
      best = cand

  if best is None:
    return None

  _, _, m = best
  v_pre, ta, end_sfx, post_acc, sp = m.groups()
  x_bare_for_vowel = _strip_accents_and_pluta(raw[:m.start()])
  rest_after = raw[m.end():].strip()
  rest_0 = regex.sub(r"^[\u0951\u0952]+", "", rest_after)[:1]

  if sp or end_sfx == "ि" or (end_sfx == "्य" and rest_0 in _IND_VOWELS):
    left_for_us = regex.sub(r"\s+", "", raw[:m.end()])
    y_for_us = rest_after
    y_standalone_raw = rest_after
    fused_pat = None
    init_v = ""
    if v_pre == "इ" and raw[m.start() - 1].isspace():
      x_pure_raw = regex.sub(r"\s+", "", raw[:m.start()])
      fused_e_i = False
    elif v_pre in ("े", "ी"):
      x_pure_raw = regex.sub(r"\s+", "", raw[:m.start()] + v_pre)
      fused_e_i = True
    else:
      x_pure_raw = regex.sub(r"\s+", "", raw[:m.start()])
      fused_e_i = False
    x_bare_for_alias = _strip_accents_and_pluta(raw[:m.start()])
  else:
    ta_clean = ta.lstrip("\u0951\u0952")
    pre_acc = ta[: len(ta) - len(ta_clean)]
    left_for_us = regex.sub(r"\s+", "", raw[:m.start()] + v_pre) + pre_acc
    y_for_us = ta_clean + end_sfx + post_acc + rest_after
    if end_sfx == "ी":
      init_v = "ई" if (x_bare_for_vowel.startswith("ई") and not x_bare_for_vowel.startswith("ईङ्")) else "इ"
      fused_pat = r"^ती"
    elif end_sfx == "्य":
      init_v = "अ"
      fused_pat = r"^त्य"
    else:
      init_v = _MATRA_TO_IND[end_sfx[-1]]
      fused_pat = r"^" + regex.escape("त" + end_sfx)
    # Post-त्य/ती svarita (॑, optionally after ँ/ं) comes from preceding `इ᳓ति`, not an independent svarita on Y.
    rest_for_standalone = regex.sub(r"^([\u0901\u0902]?)\u0951", r"\1", post_acc + rest_after)
    y_standalone_raw = init_v + rest_for_standalone
    fused_e_i = v_pre != "इ"
    x_pure_raw = regex.sub(r"\s+", "", raw[:m.start()] + ("" if v_pre == "इ" else v_pre))
    x_bare_for_alias = _strip_accents_and_pluta(raw[:m.start()] + ("" if v_pre == "इ" else v_pre))

  return {
      "left_norm": _norm_classical(left_for_us, bare_pluta_as_udatta=False),
      "y_norm_for_us": _norm_classical(y_for_us, bare_pluta_as_udatta=False),
      "y_standalone_raw": y_standalone_raw,
      "y_standalone_norm": _norm_classical(y_standalone_raw, bare_pluta_as_udatta=True),
      "x_pure_norm": _norm_classical(x_pure_raw, bare_pluta_as_udatta=False),
      "x_bare_for_alias": x_bare_for_alias,
      "alias_v_pre": v_pre,
      "alias_has_sp_before": raw[m.start() - 1].isspace(),
      "fused_pat": fused_pat,
      "init_v": init_v,
      "fused_e_i": fused_e_i,
  }


def _resolve_compound(info: dict, y_us: str, y_alone_us: str, x_alone_us: str) -> str:
  """Resolve exact US-accented form for a split ``X इति Y`` compound."""
  y_bare = _US_ACCENTS_RE.sub("", y_us)
  y_bare_no_hyph = y_bare.replace("-", "")
  ym = _syl_marks(y_us)
  ny = sum(1 for mk in ym if mk)

  if ny >= 2:
    if any(st in y_bare or st in y_bare_no_hyph for st in _DUAL_ACCENT_STEMS):
      return y_us
    return _keep_only_last_accent(y_us)

  if ny == 1:
    ym_alone = _syl_marks(y_alone_us)
    if (
        ym[0] != "U"
        and sum(1 for mk in ym_alone if mk) == 1
        and ym_alone[0] == "U"
        and len(ym) >= 2
        and ym[1] == "U"
    ):
      xm = _syl_marks(x_alone_us)
      if xm and xm[0] == "U":
        return y_alone_us
    return y_us

  ym_alone = _syl_marks(y_alone_us)
  na = sum(1 for mk in ym_alone if mk)
  if na == 1:
    return y_alone_us

  if na >= 2:
    xm = _syl_marks(x_alone_us)
    check_limit = max(0, len(ym) - (1 if info["fused_e_i"] else 0))
    genuine_x = [i for i, mk in enumerate(xm[:check_limit]) if mk]
    if len(genuine_x) == 1:
      target_i = genuine_x[0]
      if ym_alone[target_i]:
        return _keep_accent_indices(y_alone_us, {target_i})
      return _add_udatta_on_syl(y_bare, target_i)
    return y_bare

  y_sr = info["y_standalone_raw"]
  if "(" in y_sr:
    return _PLUTA_RE.sub(_UDATTA, regex.sub(r"[\u0951\u0952]", "", y_sr))
  if y_sr.rstrip().endswith("\u0952"):
    return y_bare
  xm = _syl_marks(x_alone_us)
  if not any(xm):
    return y_bare
  return _add_udatta_on_syl(y_bare, len(ym) - 1)


def _iter_ts_pada_tokens(pada_base: str) -> list[tuple[str, str]]:
  """Fast tokenizer matching ``padapaaTha.parse_pada_file`` labels/anuvākas without ``strip_iti`` overhead."""
  md_files = sorted(
      glob.glob(os.path.join(pada_base, "*", "*.md")),
      key=lambda p: (int(p.split("/")[-2]), int(os.path.basename(p).replace(".md", ""))),
  )
  out: list[tuple[str, str]] = []
  for path in md_files:
    parts = path.split("/")
    kanda = int(parts[-2])
    prap = int(parts[-1].replace(".md", ""))
    with open(path, encoding="utf-8") as f:
      lines = [x.strip() for x in f.read().splitlines() if x.strip()]
    for line in lines:
      m = regex.search(r"\[(\d+)\]\s*$", line)
      if m:
        anu = m.group(1)
        body = regex.sub(r"\[\d+\]\s*$", "", line).strip()
        loc = f"{kanda}.{prap}.{anu}"
      else:
        body = line
        loc = f"{kanda}.{prap}"
      label_matches = list(_LABEL_BOUNDARY_RE.finditer(body))
      if not label_matches:
        blocks = [body]
      else:
        blocks = []
        if label_matches[0].start() > 0:
          blocks.append(body[:label_matches[0].start()])
        for idx, lm in enumerate(label_matches):
          start = lm.end()
          end = label_matches[idx + 1].start() if idx + 1 < len(label_matches) else len(body)
          blocks.append(body[start:end])
      for block in blocks:
        for tm in _TOKEN_BLOCK_RE.finditer(block):
          raw = tm.group(1).strip()
          raw = _LEADING_LABEL_RE.sub("", raw).strip()
          raw = regex.sub(r"[\u200c\u200d]+", "", raw)
          if raw and _DEVA_LETTER_RE.search(raw):
            out.append((raw, loc))
  return out


def _convert_plain_token(w: str, w_us: str) -> str:
  """Convert an isolated plain pada (no ``-`` / ``इति``) to US notation."""
  w_no_acc = _strip_accents_and_pluta(w)
  if w_no_acc == w and w in ("उ", "सु"):
    return w
  if w_no_acc == w and w == "वाव":
    return f"वा{_UDATTA}व{_UDATTA}"
  if "\u0951" not in w and "\u0952" not in w and _UDATTA not in w:
    if len(_syl_marks(w)) == 1:
      return _add_udatta_on_syl(w, 0)
  return w_us


def collect_ts_padasvara(
    pada_base: str = PADA_BASE_DIR,
) -> tuple[Counter, dict[str, list[str]], dict[str, set[str]]]:
  """Extract all Taittirīya Saṁhitā padapāṭha padas with US accents, frequencies, citations, and sandhi aliases."""
  raw_tokens = _iter_ts_pada_tokens(pada_base)
  n_tok = len(raw_tokens)

  unique_plain: dict[str, str] = {}
  unique_comp: dict[str, dict] = {}
  token_keys: list[tuple[tuple[str, bool], str]] = []

  for idx, (raw, loc) in enumerate(raw_tokens):
    is_finite_eti = False
    if raw == "एति॑":
      prev_raw = raw_tokens[idx - 1][0] if idx > 0 else ""
      next_raw = raw_tokens[idx + 1][0] if idx + 1 < n_tok else ""
      if (prev_raw == "यः" and next_raw == "ज॒नता॑म्") or (prev_raw == "लो॒कम्" and next_raw == "इति॑"):
        is_finite_eti = True

    key = (raw, is_finite_eti)
    token_keys.append((key, loc))

    if raw in _UPASARGA_ITI_MAP and not is_finite_eti:
      continue
    if "-" in raw:
      if raw not in unique_comp:
        sp = _split_iti_compound(raw)
        if sp is not None:
          unique_comp[raw] = sp
        else:
          unique_plain[raw] = regex.sub(r"\s+", "", raw)
    else:
      cleaned = regex.sub(r"\s+इति[\u0951\u0952]?$", "", raw) if " " in raw else raw
      cleaned = regex.sub(r"\s+", "", cleaned)
      if raw not in unique_plain:
        unique_plain[raw] = cleaned

  plain_keys = list(unique_plain.keys())
  plain_norms = [_norm_classical(unique_plain[k], bare_pluta_as_udatta=True) for k in plain_keys]
  plain_us_raw = _batch_to_us(plain_norms)
  resolved: dict[tuple[str, bool], str] = {}
  for k, w, w_us in zip(plain_keys, plain_norms, plain_us_raw):
    resolved[(k, k == "एति॑")] = _convert_plain_token(w, w_us)
  for k, val in _UPASARGA_ITI_MAP.items():
    resolved[(k, False)] = val

  comp_keys = list(unique_comp.keys())
  comp_joined_norms = [f"{unique_comp[k]['left_norm']}§{unique_comp[k]['y_norm_for_us']}" for k in comp_keys]
  comp_alone_norms = [unique_comp[k]["y_standalone_norm"] for k in comp_keys]
  comp_x_norms = [unique_comp[k]["x_pure_norm"] for k in comp_keys]

  comp_joined_us = _batch_to_us(comp_joined_norms)
  comp_alone_us = _batch_to_us(comp_alone_norms)
  comp_x_us = _batch_to_us(comp_x_norms)

  extra_headwords: dict[str, set[str]] = defaultdict(set)
  for k, joined_out, y_al_us, x_al_us in zip(comp_keys, comp_joined_us, comp_alone_us, comp_x_us):
    info = unique_comp[k]
    _, y_us_raw = joined_out.split("§", 1)
    if info["fused_pat"]:
      m_fp = regex.match(info["fused_pat"] + r"([\u1cd3\u1cd9]*)", y_us_raw)
      if m_fp:
        y_us = info["init_v"] + m_fp.group(1) + y_us_raw[m_fp.end():]
      else:
        y_us = y_us_raw
    else:
      y_us = y_us_raw
    final_y = _resolve_compound(info, y_us, y_al_us, x_al_us)
    resolved[(k, False)] = final_y

    vis = _US_ACCENTS_RE.sub("", final_y).replace("-", "").strip()
    y_bare = _US_ACCENTS_RE.sub("", final_y).strip()
    sandhi_y = _join_compound_sandhi(y_bare)
    if sandhi_y and sandhi_y != vis:
      extra_headwords[vis].add(sandhi_y)
    x_alias = _extract_x_sandhi_alias(
        info["x_bare_for_alias"],
        y_bare,
        v_pre=info["alias_v_pre"],
        has_sp_before=info["alias_has_sp_before"],
    )
    if x_alias and x_alias != vis:
      extra_headwords[vis].add(x_alias)

  counts: Counter = Counter()
  loci: dict[str, list[str]] = defaultdict(list)
  for key, loc in token_keys:
    s = resolved.get(key)
    if not s:
      continue
    counts[s] += 1
    if not loci[s] or loci[s][-1] != loc:
      loci[s].append(loc)

  logging.info("Collected %d unique TS US-accented padas (%d total tokens)", len(counts), sum(counts.values()))
  return counts, loci, extra_headwords


def dump_all(dest_dirs: tuple[str, ...] = DEFAULT_DEST_DIRS) -> None:
  counts, loci, extra_headwords = collect_ts_padasvara()
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

