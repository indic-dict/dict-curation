"""Tests for Taittirīya Saṁhitā US-accented padasvara extraction and Babylon export."""

from collections import Counter

from dict_curation_projects.conversion.babylon.dict_specific.veda import padasvara_common, taittiriya


def _convert_single_compound(raw: str) -> tuple[str, set[str]]:
  info = taittiriya._split_iti_compound(raw)
  assert info is not None, f"Failed to split: {raw}"
  joined_out = taittiriya._batch_to_us([f"{info['left_norm']}§{info['y_norm_for_us']}"])[0]
  y_al_us = taittiriya._batch_to_us([info["y_standalone_norm"]])[0]
  x_al_us = taittiriya._batch_to_us([info["x_pure_norm"]])[0]
  _, y_us_raw = joined_out.split("§", 1)
  if info["fused_pat"]:
    import regex
    m_fp = regex.match(info["fused_pat"] + r"([\u1cd3\u1cd9]*)", y_us_raw)
    y_us = info["init_v"] + m_fp.group(1) + y_us_raw[m_fp.end():] if m_fp else y_us_raw
  else:
    y_us = y_us_raw
  final_y = taittiriya._resolve_compound(info, y_us, y_al_us, x_al_us)
  y_bare = taittiriya._US_ACCENTS_RE.sub("", final_y).strip()
  aliases = {taittiriya._join_compound_sandhi(y_bare)}
  x_alias = taittiriya._extract_x_sandhi_alias(
      info["x_bare_for_alias"],
      y_bare,
      v_pre=info["alias_v_pre"],
      has_sp_before=info["alias_has_sp_before"],
  )
  if x_alias:
    aliases.add(x_alias)
  return final_y, aliases


def test_taittiriya_compound_us_resolution_and_sandhi_aliases():
  assert _convert_single_compound("अँ॒हो॒मुच॒ इत्यँ॑हः-मुचे॑") == ("अँहः-मु᳓चे", {"अँहोमुचे"})
  assert _convert_single_compound("अ॒द्भिरित्य॑त्-भिः") == ("अत्-भिः᳓", {"अद्भिः"})
  assert _convert_single_compound("अँ॒शु॒मदित्यँ॑शु-मत्") == ("अँशु-म᳓त्", {"अँशुमत्"})
  assert _convert_single_compound("अ॒भि॒मा॒ति॒षाह॒मित्य॑भिमाति-साह॑म्") == ("अभिमाति-सा᳓हम्", {"अभिमातिषाहम्", "अभिमातिसाहम्"})
  assert _convert_single_compound("नि॒षद्येति॑ नि-सद्य॑") == ("नि-स᳓द्य", {"निसद्य", "निषद्य"})
  assert _convert_single_compound("सु॒षदेति॑ सु-सदा॑") == ("सु-स᳓दा", {"सुसदा", "सुषदा"})
  assert _convert_single_compound("व॒रि॒वो॒वित्त॒रेति॑ वरिवोवि॒त्-त॒रा॒") == ("वरिवोवि᳓त्-तरा", {"वरिवोवित्तरा"})
  assert _convert_single_compound("म॒हाव्री॑हीणा॒मिति॑ महा-व्री॒ही॒णा॒म्") == ("महा᳓-व्रीहीणाम्", {"महाव्रीहीणाम्"})
  assert _convert_single_compound("द्यावा॑पृथि॒वीभ्या॒मिति॒ द्यावा॑-पृ॒थि॒वीभ्या॑म्") == (
      "द्या᳓वा-पृथिवी᳓भ्याम्",
      {"द्यावापृथिवीभ्याम्"},
  )
  assert _convert_single_compound("दे॒व॒य॒ज॒नीति॑ देव-य॒ज॒नि॒")[0] == "देव-यजनि"


def test_taittiriya_plain_pluta_and_headword_dump(tmp_path):
  w_ashvan = taittiriya._norm_classical("अश्वान्॑", bare_pluta_as_udatta=True)
  assert taittiriya._batch_to_us([w_ashvan])[0] == "अ᳓श्वान्"
  assert taittiriya._norm_classical("ब्रह्मा(३)न्", bare_pluta_as_udatta=True) == "ब्रह्मा᳓न्"
  assert taittiriya._convert_plain_token("वाव", "वाव") == "वा᳓व᳓"
  assert taittiriya._convert_plain_token("उ", "उ") == "उ"

  dest = tmp_path / "kyv-ts-padasvara"
  dest.mkdir()
  counts = Counter({"अँहः-मु᳓चे": 11})
  loci = {"अँहः-मु᳓चे": ["1.6.12"]}
  bab_path, final_path = padasvara_common.dump_padasvara_babylon(
      counts,
      loci,
      str(dest),
      write_final=False,
      extra_headwords={"अँहःमुचे": {"अँहोमुचे"}},
  )
  with open(bab_path, encoding="utf-8") as f:
    text = f.read()
  assert "अँहःमुचे|अंहःमुचे|अँहोमुचे|अंहोमुचे" in text
  assert "अँहः-मु᳓चे (11)<br>1.6.12" in text
  assert final_path is None
  assert not (dest / "kyv-ts-padasvara.babylon_final").exists()
