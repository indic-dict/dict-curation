"""Tests for contextual brief meaning extraction and wiring in Vedic svara dicts."""

from __future__ import annotations

from collections import Counter

from dict_curation_projects.conversion.babylon.dict_specific.veda import (
    padasvara_common,
    prakrti_svara,
    taittiriya_brahmana,
    vedic_meanings,
)


def test_dump_padasvara_babylon_includes_brief_meanings_cleanly(tmp_path):
  counts = {"अग्नि᳓ः": 3, "इ᳓ति": 2}
  loci = {"अग्नि᳓ः": ["01/001/01", "01/001/02"], "इ᳓ति": ["01/001/01"]}
  meanings = {"अग्नि᳓ः": "पावकः ·\nAgni,<br>fire"}

  bab_path, _ = padasvara_common.dump_padasvara_babylon(
      counts,
      loci,
      dest_dir=str(tmp_path),
      meanings=meanings,
  )
  with open(bab_path, encoding="utf-8") as fh:
    raw = fh.read()

  blocks = [b.splitlines() for b in raw.strip().split("\n\n") if not b.startswith("#")]
  assert len(blocks) == 2
  by_hw = {}
  for blk in blocks:
    assert len(blk) == 2, f"Expected single-line definition per entry, got {blk}"
    for hw in blk[0].split("|"):
      by_hw[hw] = blk[1]

  agni_body = by_hw["अग्निः"]
  assert agni_body == "अग्नि᳓ः (3)<br>पावकः · Agni, fire<br>01/001/01, 01/001/02"

  # Missing meaning keeps original 2-part format unchanged.
  iti_body = by_hw["इति"]
  assert iti_body == "इ᳓ति (2)<br>01/001/01"


def test_load_padasvara_entries_roundtrips_3part_and_meaning_only_blocks(tmp_path):
  bab = tmp_path / "sample.babylon"
  bab.write_text(
      "\n".join([
          "अग्नि᳓ः",
          "अग्नि᳓ः (4)<br>पावकः · Agni, fire<br>01/001/01, 01/001/02",
          "",
          "सो᳓मः",
          "सो᳓मः (2)<br>01/002/01",
          "",
          "मा᳓",
          "मा᳓ (1)<br>not, do not",
          "",
      ]),
      encoding="utf-8",
  )

  loaded = prakrti_svara.load_padasvara_entries(bab)
  assert loaded == [
      ("अग्नि᳓ः", 4, ("01/001/01", "01/001/02")),
      ("सो᳓मः", 2, ("01/002/01",)),
      ("मा᳓", 1, ()),
  ]


def test_generate_prakrti_definitions_inserts_stem_and_dhatu_meanings():
  raw_entries = [
      ("अग्नि᳓ः", 3, ("1.1.1",)),
      ("अग्न᳓ये", 2, ("1.1.2",)),
      ("द᳓दाति", 4, ("1.1.3",)),
  ]
  defs_dev, _, _ = prakrti_svara.generate_prakrti_definitions(
      raw_entries,
      already_us=True,
      stem_meanings={"अग्नि": "पावकः · fire, Agni"},
      dhatu_meanings={"दा": "give, bestow"},
  )
  by_hw = {d.headwords_tuple[0]: d.meaning for d in defs_dev}

  agni_m = by_hw["अग्नि"]
  assert "अग्नि᳓" in agni_m
  assert "<br>पावकः · fire, Agni<br>" in agni_m
  assert "1.1.1" in agni_m

  da_m = by_hw["दा"]
  assert "[धातुः]" in da_m
  assert "<br>give, bestow<br>" in da_m
  assert "द᳓दाति (4)" in da_m


def test_morph_guard_prevents_ati_verb_matching_saptami_locative():
  assert not vedic_meanings.morph_compatible("अग्नौ", "प्रवेशयति")
  assert not vedic_meanings.morph_compatible("अग्नौ", "करोति")
  assert vedic_meanings.morph_compatible("अग्नौ", "समिद्धे")


def test_rv_structured_extractors_and_hellwig_context_filtering(tmp_path):
  sub = tmp_path / "01" / "001"
  sub.mkdir(parents=True)
  (sub / "01.md").write_text(
      """<details><summary>सर्वाष् टीकाः</summary>
<details><summary>Jamison Brereton</summary>
I praise Agni, the household priest.
</details>
<details><summary>पद-पाठः</summary>
अग्नि᳓म्। ई᳓ळे। पुरः᳓-हितम्।
</details>
<details><summary>Hellwig Grammar</summary>
- *agním* — m. acc. sg. "fire; Agni; sacrificial fire"
- *īḷe* — v. 1st sg. pres. "praise; worship; implore"
</details>
<details><summary>रङ्गनाथः</summary>
अग्निम् - अग्निनामकं देवम्। पुरोहितम् - यज्ञस्य पुरस्तादवस्थितम्।
</details>
</details>
""",
      encoding="utf-8",
  )

  cm = vedic_meanings.extract_corpus_meanings(
      "rv",
      raw_forms=["अग्नि᳓म्", "ई᳓ळे", "पुरः᳓-हितम्"],
      already_us=True,
      source_dir=str(tmp_path),
      use_cache=False,
  )
  agni_gloss = cm.lookup("अग्नि᳓म्")
  assert "अग्निनामकं देवम्" in agni_gloss
  assert "(रङ्गनाथः 1.1.1)" in agni_gloss
  assert "Agni" in agni_gloss or "agni" in agni_gloss.lower()
  assert "(Jamison-Brereton 1.1.1)" in agni_gloss or "(Hellwig 1.1.1)" in agni_gloss
  assert "praise" in cm.lookup("ई᳓ळे")
  assert "यज्ञस्य पुरस्तादवस्थितम्" in cm.lookup("पुरः᳓-हितम्")


def test_av_trivedi_sanskrit_and_hindi_fallback_separation(tmp_path):
  sub = tmp_path / "01" / "001"
  sub.mkdir(parents=True)
  (sub / "01.md").write_text(
      """<details><summary>पद-पाठः</summary>
त्रि-सप्ताः᳓। प᳓रीयुः।
</details>
<details><summary>पण्डित क्षेमकरणदास त्रिवेदी - पादटिप्पनी</summary>
(त्रि-सप्ताः) त्रिगुणिताः सप्त। (परीयुः) पा० २.४.१२ छान्दसः प्रयोगः।
</details>
<details><summary>पण्डित क्षेमकरणदास त्रिवेदी - पदार्थः</summary>
(त्रि-सप्ताः) तीन प्रकार के। (परीयुः) सर्वत्र व्याप्त हुए।
</details>
""",
      encoding="utf-8",
  )

  cm = vedic_meanings.extract_corpus_meanings(
      "av",
      raw_forms=["त्रि-सप्ताः᳓", "परी᳓युः"],
      already_us=True,
      source_dir=str(tmp_path),
      use_cache=False,
  )
  # Sanskrit Trivedi gloss present -> Hindi पदार्थः is NOT mixed in.
  tri = cm.lookup("त्रि-सप्ताः᳓")
  assert "त्रिगुणिताः सप्त (त्रिवेदी 1.1.1)" in tri
  assert "तीन प्रकार" not in tri
  # परीयुः had only grammar citation in पादटिप्पनी -> falls back cleanly to Hindi पदार्थः.
  assert cm.lookup("परी᳓युः") == "सर्वत्र व्याप्त हुए (त्रिवेदी 1.1.1)"


def test_accent_homograph_ma_and_te_distinguished(tmp_path):
  (tmp_path / "01.md").write_text(
      """## 01
<details open><summary>विश्वास-प्रस्तुतिः</summary>
मा᳓ नः।
</details>
<details><summary>सर्वाष् टीकाः</summary>
<details><summary>Gemini 3.8 Flash</summary>
Do not harm us, Aṃśu is bright.
</details>
<details><summary>पद-पाठः (यान्त्रिकः)</summary>
- मा᳓ (अव्ययम्)
- नः (सर्वनाम)
- अं᳓शुः (सुबन्तम्)
</details>
</details>

<details open><summary>विश्वास-प्रस्तुतिः</summary>
मा᳓ वा ते᳓।
</details>
<details><summary>सर्वाष् टीकाः</summary>
<details><summary>Gemini 3.8 Flash</summary>
Hear me now, they come to thee.
</details>
<details><summary>पद-पाठः (यान्त्रिकः)</summary>
- मा (सर्वनाम)
- ते᳓ (सर्वनाम)
- ते (सर्वनाम)
</details>
</details>
""",
      encoding="utf-8",
  )

  cm = vedic_meanings.extract_corpus_meanings(
      "ms",
      raw_forms=["मा᳓", "मा", "ते᳓", "ते", "अं᳓शुः"],
      already_us=True,
      source_dir=str(tmp_path),
      use_cache=False,
  )
  assert cm.lookup("मा᳓") in ("not (Gemini 3.8 1.1)", "do not (Gemini 3.8 1.1)")
  assert cm.lookup("मा") == "me (Gemini 3.8 1.1)"
  assert cm.lookup("ते᳓") == "they (Gemini 3.8 1.1)"
  assert cm.lookup("ते").endswith("(Gemini 3.8 1.1)")
  assert "aṃśu" in cm.lookup("अं᳓शुः").lower()
  assert "(Gemini 3.8 1.1)" in cm.lookup("अं᳓शुः")


def test_tb_end_to_end_padasvara_to_prakrti_with_meanings(tmp_path):
  src_dir = tmp_path / "corpus" / "01"
  src_dir.mkdir(parents=True)
  (src_dir / "01.md").write_text(
      """## 01
<details open><summary>विश्वास-प्रस्तुतिः</summary>
देवं+++(=द्युतमानम्)+++ नयति।
</details>
<details><summary>सर्वाष् टीकाः</summary>
<details><summary>पद-पाठः (यान्त्रिकः)</summary>
- देव᳓म् (सुबन्तम्)
- न᳓यति (तिङन्तम्)
</details>
<details><summary>Keith</summary>
He leads the shining god.
</details>
</details>
""",
      encoding="utf-8",
  )

  out_root = tmp_path / "dicts"
  pada_dest = out_root / "kyv-tb-pada-svara"
  pada_dest.mkdir(parents=True)
  taittiriya_brahmana._dump_corpus(
      source_dir=str(tmp_path / "corpus"),
      dest_dirs=(str(pada_dest),),
      dict_name="kyv-tb-pada-svara",
      corpus="TB",
      title_desc="Test TB",
      include_meanings=True,
  )

  pada_bab = (pada_dest / "kyv-tb-pada-svara.babylon").read_text(encoding="utf-8")
  assert "(विश्वासः 1.1)" in pada_bab
  assert "(Keith 1.1)" in pada_bab

  spec = next(s for s in prakrti_svara.VEDA_SPECS if s.key == "tb")
  prakrti_svara.build_single_prakrti_svara(
      spec,
      primary_root=str(out_root),
      mirror_roots=(str(out_root),),
      vedaweb_prior={},
      include_meanings=True,
      corpus_source_dir=str(tmp_path / "corpus"),
  )

  prak_bab = (out_root / spec.dest_name / f"{spec.dest_name}.babylon").read_text(encoding="utf-8")
  assert "नी [धातुः]" in prak_bab
  assert "lead" in prak_bab.lower() or "leads" in prak_bab.lower()
  assert "(Keith 1.1)" in prak_bab
  assert "god" in prak_bab.lower() or "shining" in prak_bab.lower()


def test_format_brief_meaning_preserves_citations_under_length_cap():
  out = vedic_meanings.format_brief_meaning(
      Counter({"अतिदीर्घसमासयुक्तपदार्थः": 5}),
      Counter({"sacrificial ceremony performer": 5, "priest": 2}),
      max_len=72,
      sa_cites={"अतिदीर्घसमासयुक्तपदार्थः": Counter({("सायणः", "1.2.3"): 5})},
      en_cites={"sacrificial ceremony performer": Counter({("Griffith", "1.2.3"): 5})},
  )
  assert "(सायणः 1.2.3)" in out
  assert "(Griffith 1.2.3)" in out
  assert len(out) <= 80


def test_validate_veda_babylon_schema_and_citations(tmp_path):
  import pytest

  d = tmp_path / "kyv-test-pada-svara"
  d.mkdir()
  (d / "kyv-test-pada-svara.babylon").write_text(
      "\n".join([
          "#bookname=kyv-test-pada-svara (sa-sa)",
          "",
          "अग्निः",
          "अग्नि᳓ः (3)<br>पावकः (सायणः 1.1.1) · fire (Gemini 3.8 1.1.1)<br>1.1.1, 1.1.2",
          "",
          "इति",
          "इ᳓ति (2)<br>1.1.1",
          "",
          "दा",
          "दा [धातुः]<br>give (Griffith 1.2.3)<br>द᳓दाति (4)<br>1.2.3",
          "",
      ]),
      encoding="utf-8",
  )
  stats = padasvara_common.validate_veda_babylon_dir(d)
  assert stats == {"entries": 3, "with_meaning": 2, "bad_format": 0, "uncited": 0, "final_files": 0}

  # Uncited segment fails citation check, extra <br> fails schema, leftover .babylon_final is counted.
  (d / "kyv-test-pada-svara.babylon_final").write_text("stale", encoding="utf-8")
  bad = padasvara_common.validate_veda_babylon_text(
      "अग्निः\nअग्नि᳓ः (1)<br>fire<br>1.1\n\nसोमः\nसोमः (1)<br>a<br>b<br>c\n"
  )
  assert bad["uncited"] == 1
  assert bad["bad_format"] == 1
  assert padasvara_common.validate_veda_babylon_dir(d)["final_files"] == 1

  # Live regression check against local stardict-sanskrit-kAvya clone when present.
  repo = tmp_path.parent / "__nonexistent__"
  del repo
  from pathlib import Path
  live_root = Path("/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-kAvya")
  if not live_root.is_dir():
    pytest.skip("Local stardict-sanskrit-kAvya clone not present")
  for name in padasvara_common.VEDA_SVARA_DICT_NAMES:
    res = padasvara_common.validate_veda_babylon_dir(live_root / name)
    assert res["entries"] > 0, name
    assert res["with_meaning"] > 0, name
    assert res["bad_format"] == 0, f"{name}: {res}"
    assert res["uncited"] == 0, f"{name}: {res}"
    assert res["final_files"] == 0, f"{name}: {res}"
