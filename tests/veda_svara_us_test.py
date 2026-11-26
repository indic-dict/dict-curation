"""Tests for US-notation svara conversion across RV, AV, VS-M/VS-K, ŚB padapāṭha, and Dhātupāṭha."""

from pathlib import Path
import pytest

from dict_curation_projects.conversion.babylon.dict_specific.veda import (
    dhatupatha_svara,
    madhyandina,
    padasvara_common,
    rgveda,
    shatapatha,
    taittiriya,
)


def test_shatapatha_collect_and_dump_skips_corrections(tmp_path: Path):
  src = tmp_path / "sarva-prastutiH"
  b1 = src / "01" / "01" / "01.md"
  b1.parent.mkdir(parents=True)
  b1.write_text(
      "---\ntitle: 01\n---\n\n"
      "## ०१\n"
      "संहिता पाठः\n\n"
      "<details><summary>पद-पाठः (यान्त्रिकः)</summary>\n\n"
      "- वृ᳓ते\n"
      "- ह\n"
      "- वै᳓ → **वै** (कण्डिका)\n"
      "- ब्र᳓ह्म-\n"
      "- मेध्यँ᳙ [[संशयः]]\n"
      "- ष्वा॒? \n"
      "</details>\n\n"
      "## ०२\n"
      "<details><summary>पद-पाठः (यान्त्रिकः)</summary>\n\n"
      "- वृ᳓ते (footnote note)\n"
      "</details>\n",
      encoding="utf-8",
  )

  # Kāṇḍa 14 nested under 01-05_bRhad-AraNyakopaniShat/.../<adhyaya>/<brahmana>.md
  b14 = src / "14" / "01-05_bRhad-AraNyakopaniShat" / "03" / "01_foo.md"
  b14.parent.mkdir(parents=True)
  b14.write_text(
      "## ०५\n"
      "<details><summary>पद-पाठः (यान्त्रिकः)</summary>\n\n"
      "- अ᳓श्वस्य\n"
      "- क᳓स्य → **कस्य॑**\n"
      "</details>\n",
      encoding="utf-8",
  )

  # Non-content index file should be ignored
  (src / "01" / "01" / "_index.md").write_text(
      "## ०१\n<details><summary>पद-पाठः (यान्त्रिकः)</summary>\n\n- इ᳓दम्\n</details>\n",
      encoding="utf-8",
  )

  counts, loci, skipped = shatapatha.collect_sb_padasvara(source_dir=str(src))
  assert skipped == 3
  assert counts == {"वृ᳓ते": 2, "ह": 1, "ब्र᳓ह्म": 1, "अ᳓श्वस्य": 1}
  assert loci["वृ᳓ते"] == ["1.1.1.1", "1.1.1.2"]
  assert loci["अ᳓श्वस्य"] == ["14.3.1.5"]
  assert all("\u0951" not in k and "\u0952" not in k and "\u1cd6" not in k for k in counts)

  dest = tmp_path / "syv-sb-m-pada-svara"
  shatapatha.dump_all(dest_dirs=(str(dest),), source_dir=str(src))
  bab = (dest / "syv-sb-m-pada-svara.babylon").read_text(encoding="utf-8")
  assert not (dest / "syv-sb-m-pada-svara.babylon_final").exists()
  assert (dest / "README.md").is_file()
  assert "वृ᳓ते" in bab and "अ᳓श्वस्य" in bab
  assert "वै᳓" not in bab and "मेध्यँ᳙" not in bab
  assert "\u0951" not in bab and "\u0952" not in bab and "\u1cd6" not in bab


def test_shatapatha_kanva_named_kanda_dirs_and_dump_kanva(tmp_path: Path):
  src = tmp_path / "sarva-prastutiH"
  b_k1 = src / "01_ekapAtkANDam" / "01" / "1.md"
  b_k1.parent.mkdir(parents=True)
  b_k1.write_text(
      "## ०२\n"
      "<details><summary>पद-पाठः (यान्त्रिकः)</summary>\n\n"
      "- अ᳓थ\n"
      "- ह\n"
      "</details>\n",
      encoding="utf-8",
  )
  b_k17 = src / "17_bRhadAraNyakam" / "04" / "2.md"
  b_k17.parent.mkdir(parents=True)
  b_k17.write_text(
      "## ०१\n"
      "<details><summary>पद-पाठः (यान्त्रिकः)</summary>\n\n"
      "- ब्र᳓ह्म\n"
      "</details>\n",
      encoding="utf-8",
  )
  dest = tmp_path / "syv-sb-k-pada-svara"
  counts, skipped = shatapatha.dump_kanva(dest_dirs=(str(dest),), source_dir=str(src))
  assert skipped == 0
  assert counts == {"अ᳓थ": 1, "ह": 1, "ब्र᳓ह्म": 1}
  bab = (dest / "syv-sb-k-pada-svara.babylon").read_text(encoding="utf-8")
  assert "1.1.1.2" in bab and "17.4.2.1" in bab
  readme = (dest / "README.md").read_text(encoding="utf-8")
  assert "syv-sb-k-pada-svara" in readme and "Kāṇva" in readme


def test_shatapatha_rejects_classical_accents_in_uncorrected_pada(tmp_path: Path):
  src = tmp_path / "sarva-prastutiH" / "01" / "01" / "01.md"
  src.parent.mkdir(parents=True)
  src.write_text(
      "## ०१\n<details><summary>पद-पाठः (यान्त्रिकः)</summary>\n\n- अ॒ग्निः\n</details>\n",
      encoding="utf-8",
  )
  with pytest.raises(ValueError):
    shatapatha.collect_sb_padasvara(source_dir=str(tmp_path / "sarva-prastutiH"))


def test_dhatupatha_segment_and_token_conversion():
  cases = [
      ("एधँ॒", "एधँ"),
      ("भ॒जँ॑", "भजँ᳙"),
      ("डुप॒चँ॑ष्", "डुपचँ᳙ष्"),
      ("तनुँ॑", "तनुँ᳙"),
      ("अ॒दँ", "अदँ᳓"),
      ("क॒ल्याणे॑ सु॒खे च॑", "कल्या᳓णे सुखे᳓ च"),
      ("सत्ता॑याम्", "स᳓त्तायाम्"),
      ("भा॒ष्य॑म्", "भाष्य᳙म्"),
      ("दीप्ता॑व॒भिप्री॑तौ", "दी᳓प्तावभि᳓प्रीतौ"),
      ("सङ्घा॒ते", "सङ्घाते᳓"),
      ("परि॒भाष॑णे", "परिभा᳓षणे"),
      ("श्रमुँ त॑पसि खे॒दे च॑।", "श्रमुँ त᳓पसि खेदे᳓ च।"),
      ("[न] ऽचमा॑म् [मित्]।", "[न] ऽच᳓माम् [मित्]।"),
  ]
  for classical, expected_us in cases:
    out = dhatupatha_svara.convert_dhatupatha_segment_to_us(classical)
    assert out == expected_us, f"{classical!r} -> {out!r} != {expected_us!r}"
    assert "\u0951" not in out and "\u0952" not in out


def test_dhatupatha_babylon_conversion_and_mirror(tmp_path: Path):
  src_bab = tmp_path / "src.babylon"
  src_bab.write_text(
      "भ॒जँ॑|भजँ\nभ॒जँ॑ सेवा॑याम्\n\n"
      "एधँ॒|एधँ\nएधँ॒ वृद्धौ॑\n\n",
      encoding="utf-8",
  )
  m1 = tmp_path / "m1"
  m2 = tmp_path / "m2"
  converted, leftover = dhatupatha_svara.convert_dhatupatha_babylon_to_us(
      src_babylon=str(src_bab),
      mirror_dirs=(str(m1), str(m2)),
  )
  assert converted == 2
  assert leftover == []
  t1 = (m1 / "dhAtupAThaH_sasvaraH.babylon").read_text(encoding="utf-8")
  t2 = (m2 / "dhAtupAThaH_sasvaraH.babylon").read_text(encoding="utf-8")
  assert t1 == t2
  assert "भजँ᳙|भजँ\nभजँ᳙ से᳓वायाम्" in t1
  assert "एधँ|एधँ\nएधँ वृ᳓द्धौ" in t1
  assert "\u0951" not in t1 and "\u0952" not in t1


def test_convert_counts_and_loci_to_us_tricky_veda_forms():
  raw_counts = {
      "अ॒मृ॑ताः": 2,
      "सो॒मापू॒षऽभ्या॑म्": 1,
      "सु॒ऽउक्तस्य॑": 3,
      "ग्नाःपत्नी॑भिः": 1,
      "र॒थिना॒मितिं॑ र॒थिऽना॑म्": 1,
  }
  raw_loci = {
      "अ॒मृ॑ताः": ["1.1.1"],
      "सो॒मापू॒षऽभ्या॑म्": ["2.40.1"],
      "सु॒ऽउक्तस्य॑": ["10.1.1"],
      "ग्नाःपत्नी॑भिः": ["5.46.8"],
      "र॒थिना॒मितिं॑ र॒थिऽना॑म्": ["15.61"],
  }
  counts, loci, fallback_count = padasvara_common.convert_counts_and_loci_to_us(
      raw_counts, raw_loci, already_us=False
  )
  assert fallback_count == 0
  assert counts["अमृ᳓ताः"] == 2
  assert counts["सोमा᳓पूष᳓-भ्याम्"] == 1
  assert counts["सु-उक्तस्य᳙"] == 3
  assert counts["ग्नाःप᳓त्नीभिः"] == 1
  assert counts["रथि᳓-नाम्"] == 1
  assert "ंरथि᳓-नाम्" not in counts
  assert loci["अमृ᳓ताः"] == ["1.1.1"]
  assert all("\u0951" not in k and "\u0952" not in k and "\u1cd6" not in k for k in counts)


def test_strip_leftover_iti_gloss_and_compound_sandhi_regressions():
  # Compounds whose first member ends in -ti/-tya must NOT be split on ऽ
  preserved = [
      ("स्वधि॑तिःऽइव", "स्व᳓धितिः-इव"),
      ("अ॒दि॒ति॒ऽत्वे", "अदिति-त्वे᳓"),
      ("आ॒दि॒त्यऽजू॑तः", "आदित्य᳓-जूतः"),
      ("वी॒तिऽहो॑त्रम्", "वीति᳓-होत्रम्"),
      ("शितिऽपृ॒ष्ठः", "शिति-पृष्ठः᳓"),
      ("नित्य॑ऽहोता", "नि᳓त्य-होता"),
      ("धी॒तिऽभिः॑", "धीति᳓-भिः"),
  ]
  for raw_tok, expected_us in preserved:
    np = padasvara_common.normalize_raw_form_to_us(raw_tok, already_us=False)
    assert np is not None and np.us_form == expected_us, f"{raw_tok!r} -> {np}"

  # Merged -ityu- / multi-ti glosses restore proper vowel (never 'अु')
  glosses = [
      ("उप॑स्तुते॒ इत्युप॑ऽस्तुते", "उ᳓प-स्तुते"),
      ("उदो॑जस॒मित्युत्ऽओ॑जसम्", "उ᳓त्-ओजसम्"),
      ("उज्जि॑ति॒मित्युत्ऽजि॑तिम्", "उ᳓त्-जितिम्"),
      ("ओत॒मित्याऽउ॑तम्", "आ᳓-उतम्"),
      ("नः॒इ॒न्द्रा॒ग्नीइती॑न्द्रा॒ग्नी", "इन्द्राग्नी᳓"),
      ("उ॒प॒धी इ॒वेत्यु॑प॒धीऽइ॑व", "उपधी᳓-इव"),
  ]
  for raw_tok, expected_us in glosses:
    np = padasvara_common.normalize_raw_form_to_us(raw_tok, already_us=False)
    assert np is not None and np.us_form == expected_us, f"{raw_tok!r} -> {np}"
    assert "अु" not in np.us_form

  # Seam-anchored sandhi & visarga rules
  assert taittiriya._join_compound_sandhi("म्रक्ष-कृत्वा") == "म्रक्षकृत्वा"
  assert taittiriya._join_compound_sandhi("उच्चैः-घोषः") == "उच्चैर्घोषः"
  assert taittiriya._join_compound_sandhi("स्थाः-रश्मानः") == "स्थारश्मानः"

  # MS long-ī iti recovery and RV pragṛhya/bracket cleanup
  assert madhyandina.strip_gloss("ई॒र्मान्ता॑स॒इती॒र्मऽअ॑न्तासः") == ["ईर्मऽअ॑न्तासः"]
  assert rgveda.strip_rk_iti("द॒धा॒थे॒ इति॒॑") == "द॒धा॒थे॒"
  assert padasvara_common.normalize_raw_form_to_us("द॒धा॒थे॒").us_form == "दधाथे"
  assert rgveda.strip_rk_iti("स्य॒स्वेति॑ स्यस्व") == "स्यस्व"
  assert rgveda.strip_rk_iti("प्रणी॒तीति॒ प्र-नी॒ती॒") == "प्र-नी॒ती॒"
  assert rgveda.strip_rk_iti("पा॒तु॒ [धा॒तु॒]") == "पा॒तु॒"


def test_veda_builders_never_target_readonly_kosha_or_secondary_mirror():
  from dict_curation_projects.conversion.babylon.dict_specific.veda import (
      atharva,
      prakrti_svara,
      taittiriya_brahmana,
  )

  all_defaults = (
      *atharva.DEFAULT_DEST_DIRS,
      *rgveda.DEFAULT_DEST_DIRS,
      *taittiriya.DEFAULT_DEST_DIRS,
      *madhyandina.DEFAULT_DEST_DIRS,
      *shatapatha.DEFAULT_DEST_DIRS,
      *shatapatha.KANVA_DEFAULT_DEST_DIRS,
      *taittiriya_brahmana.TB_DEFAULT_DEST_DIRS,
      *taittiriya_brahmana.TK_DEFAULT_DEST_DIRS,
      *prakrti_svara.DEFAULT_MIRROR_ROOTS,
      prakrti_svara.PRIMARY_KAVYA_ROOT,
      *dhatupatha_svara.DEFAULT_DHATUPATHA_MIRRORS,
      dhatupatha_svara.PRIMARY_DHATUPATHA_BABYLON,
  )
  for path in all_defaults:
    assert "raw_etexts/koshaH/indic-dict" not in path, path
    assert "indic-dict/stardict/" not in path, path
    assert "/indic-dict/dicts/" in path, path

  with pytest.raises(PermissionError):
    padasvara_common.assert_writable_dict_dest(
        "/home/vvasuki/gitland/sanskrit/raw_etexts/koshaH/indic-dict/kAvya/syv-sb-k-pada-svara"
    )


def test_taittiriya_brahmana_and_kathaka_padasvara_dump(tmp_path: Path):
  from dict_curation_projects.conversion.babylon.dict_specific.veda import taittiriya_brahmana

  tb_src = tmp_path / "tb"
  tb_f = tb_src / "1" / "1_agnyAdheyAdi" / "01_shukra.md"
  tb_f.parent.mkdir(parents=True)
  tb_f.write_text(
      "<details><summary>पद-पाठः (यान्त्रिकः)</summary>\n\n"
      "ब्र᳓ह्म । स᳓म् । धत्तम् । स᳓म्-भूतम् । अ᳓ग्नेः᳓ ।\n"
      "</details>\n"
      '<div class="js_include" url="/vedAH_yajuH/foo.md">\n'
      "<details><summary>पद-पाठः (यान्त्रिकः)</summary>\n\n"
      "छाय᳓म् ।\n"
      "</details>\n"
      "</div>\n",
      encoding="utf-8",
  )
  tb_dest = tmp_path / "kyv-tb-pada-svara"
  counts_tb, skipped_tb = taittiriya_brahmana.dump_tb(dest_dirs=(str(tb_dest),), source_dir=str(tb_src))
  assert skipped_tb == 1  # multi-udātta अ᳓ग्नेः᳓ excluded
  assert counts_tb == {"ब्र᳓ह्म": 1, "स᳓म्": 1, "धत्तम्": 1, "स᳓म्-भूतम्": 1}
  bab_tb = (tb_dest / "kyv-tb-pada-svara.babylon").read_text(encoding="utf-8")
  assert "1.1.1" in bab_tb and "छाय᳓म्" not in bab_tb
  assert not (tb_dest / "kyv-tb-pada-svara.babylon_final").exists()

  tk_src = tmp_path / "tk"
  tk_f = tk_src / "1" / "01_1.md"
  tk_f.parent.mkdir(parents=True)
  tk_f.write_text(
      "<details><summary>पद-पाठः (यान्त्रिकः)</summary>\n\n"
      "सम्-ज्ञा᳓नम् । वि-ज्ञा᳓नम् ।\n"
      "</details>\n",
      encoding="utf-8",
  )
  tk_dest = tmp_path / "kyv-tk-pada-svara"
  counts_tk, skipped_tk = taittiriya_brahmana.dump_tk(dest_dirs=(str(tk_dest),), source_dir=str(tk_src))
  assert skipped_tk == 0
  assert counts_tk == {"सम्-ज्ञा᳓नम्": 1, "वि-ज्ञा᳓नम्": 1}
  bab_tk = (tk_dest / "kyv-tk-pada-svara.babylon").read_text(encoding="utf-8")
  assert "1.1.1" in bab_tk and "सम्ज्ञानम्" in bab_tk


def test_madhyandina_missing_leading_anudatta_compounds_and_chapter_collection(tmp_path: Path):
  # Regression: Mādhyandina padapāṭha omits `॒` on initial syllables before `ऽ`, which must NOT become dual-udātta!
  cases = [
      ("सुऽप्र॒जाः", "सु-प्रजाः᳓"),
      ("पुष्टि॒ऽवर्ध॑नः", "पुष्टि-व᳓र्धनः"),
      ("निऽमे॒षाः", "नि-मेषाः᳓"),
      ("सऽजा॒तानाम्", "स-जाता᳓नाम्"),
      ("वसु॒ऽधेय॑स्य", "वसु-धे᳓यस्य"),
      # Genuine dual-accent compounds still retain both udāttas!
      ("बृह॒स्पतिः॑", "बृ᳓हस्प᳓तिः"),
      ("सो॒मापू॒षऽभ्या॑म्", "सोमा᳓पूष᳓-भ्याम्"),
  ]
  for raw_tok, expected_us in cases:
    np = padasvara_common.normalize_raw_form_to_us(raw_tok, already_us=False)
    assert np is not None and np.us_form == expected_us, f"{raw_tok!r} -> {np}"

  # Chapter-level `sarva-prastutiH/03.md` collection across multiple clause blocks
  ch_dir = tmp_path / "sarva-prastutiH"
  ch_dir.mkdir()
  (ch_dir / "03.md").write_text(
      "+++\ntitle = '०३'\n+++\n\n"
      "## ४० अयमग्निः\n"
      "<details><summary>पदपाठः - दयानन्दादि</summary>\n"
      "पु॒ष्टि॒वर्ध॑न॒ इति॑ पुष्टि॒ऽवर्ध॑नः। ४०।\n"
      "</details>\n"
      "<details><summary>पदपाठः - दयानन्दादि</summary>\n"
      "सु॒प्र॒जा इति॑ सुऽप्र॒जाः।\n"
      "</details>\n",
      encoding="utf-8",
  )
  raw_counts, raw_loci = madhyandina.collect_padas(source_dir=str(ch_dir))
  us_counts, us_loci, _ = padasvara_common.convert_counts_and_loci_to_us(raw_counts, raw_loci, already_us=False)
  assert us_counts == {"पुष्टि-व᳓र्धनः": 1, "सु-प्रजाः᳓": 1}
  assert us_loci["पुष्टि-व᳓र्धनः"] == ["3.40"]
  assert us_loci["सु-प्रजाः᳓"] == ["3.40"]

  # VS-K collection resolves exact js_includes (पदपाठः - दयानन्दादि fallback) and accented पदपाठः - काण्वः
  v_root = tmp_path / "vishvasa"
  shared_yaj = v_root / "vedAH_yajuH" / "static" / "vAjasaneyam" / "mAdhyandinam" / "saMhitA" / "yajuH" / "sarva-prastutiH" / "01" / "01_barhiH.md"
  shared_yaj.parent.mkdir(parents=True)
  shared_yaj.write_text(
      "<details><summary>सर्वाष् टीकाः</summary>\n"
      "<details><summary>पदपाठः - दयानन्दादि</summary>\n\n"
      "दे॒वस्य॑। त्वा॒।\n"
      "</details>\n</details>\n",
      encoding="utf-8",
  )
  vsk_dir = v_root / "vedAH_yajuH" / "content" / "vAjasaneyam" / "kANvam" / "saMhitA" / "sarva-prastutiH"
  vsk_dir.mkdir(parents=True)
  (vsk_dir / "01.md").write_text(
      "+++\ntitle = '०१'\n+++\n\n"
      "## ०१ इषे\n"
      "<details><summary>सर्वाष् टीकाः</summary>\n"
      "<details><summary>पदपाठः</summary>\n\n"
      "इ॒षे। त्वा॒।\n"
      "</details>\n</details>\n"
      "## ०२ देवस्य\n"
      '<div class="js_include" url="/vedAH_yajuH/vAjasaneyam/mAdhyandinam/saMhitA/yajuH/sarva-prastutiH/01/01_barhiH.md"></div>\n',
      encoding="utf-8",
  )
  dest_k = tmp_path / "syv-vs-k-padasvara"
  madhyandina.dump_kanva(dest_dirs=(str(dest_k),), source_dir=str(vsk_dir), vishvasa_root=str(v_root))
  bab_k = (dest_k / "syv-vs-k-padasvara.babylon").read_text(encoding="utf-8")
  assert "#bookname=syv-vs-k-padasvara (sa-sa)" in bab_k
  assert "इषे᳓ (1)<br>1.1" in bab_k and "देव᳓स्य (1)<br>1.2" in bab_k



