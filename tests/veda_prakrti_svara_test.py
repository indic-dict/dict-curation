"""Tests for Vedic prakṛti-svara normalization, stemming, vocative guard, and Babylon export."""

from dict_curation_projects.conversion.babylon.dict_specific.veda import prakrti_svara


def test_normalize_raw_form_us_and_classical_repairs():
  # Mixed US + classical (MS)
  n1 = prakrti_svara.normalize_raw_form_to_us("अ॒प॒स्यः᳙", already_us=False)
  assert n1 is not None and n1.us_form == "अपस्यः᳙"
  # VS aggravated svarita \u1cd6
  n2 = prakrti_svara.normalize_raw_form_to_us("अ॒व॒ट्या᳖य", already_us=False)
  assert n2 is not None and n2.us_form == "अवट्या᳙य"

  # Initial non-jātya svarita in MS/AV
  n3 = prakrti_svara.normalize_raw_form_to_us("अ॑क्षऽरा॒जाय॑", already_us=False)
  assert n3 is not None and n3.us_form == "अक्ष-राजा᳓य"
  n4 = prakrti_svara.normalize_raw_form_to_us("अँ॑ह॒ऽमुचः॑", already_us=False)
  assert n4 is not None and n4.us_form == "अँह-मु᳓चः"
  n5 = prakrti_svara.normalize_raw_form_to_us("अ॑कल्पयन्", already_us=False)
  assert n5 is not None and n5.us_form == "अ᳓कल्पयन्"
  n6 = prakrti_svara.normalize_raw_form_to_us("अ॑गृभ्ण॒न्", already_us=False)
  assert n6 is not None and n6.us_form == "अ᳓गृभ्णन्"
  n7 = prakrti_svara.normalize_raw_form_to_us("प॑रि॒धिम्", already_us=False)
  assert n7 is not None and n7.us_form == "परिधि᳓म्"

  # Leftover iti glosses vs real -iti nouns (अक॒रित्यकः॑ = augment aorist अ᳓कः)
  n8 = prakrti_svara.normalize_raw_form_to_us("अक॒रित्यकः॑", already_us=False)
  assert n8 is not None and n8.us_form == "अ᳓कः"
  n9 = prakrti_svara.normalize_raw_form_to_us("अथो॒ऽइति॑", already_us=False)
  assert n9 is not None and n9.us_form == "अ᳓थो" and not n9.is_unaccented
  n_real = prakrti_svara.normalize_raw_form_to_us("अ᳓नु-इतिः", already_us=True)
  assert n_real is not None and n_real.us_form == "अ᳓नु-इतिः"

  # Missing leading ॒, dropped trailing ॑, dual accent, unaccented multi vs monosyllable
  n10 = prakrti_svara.normalize_raw_form_to_us("अनू॒ची", already_us=False)
  assert n10 is not None and n10.us_form == "अनूची᳓"
  n11 = prakrti_svara.normalize_raw_form_to_us("अ॒स्माकम्", already_us=False)
  assert n11 is not None and n11.us_form == "अस्मा᳓कम्"
  n12 = prakrti_svara.normalize_raw_form_to_us("इन्द्रा॒वरु॑णा", already_us=False)
  assert n12 is not None and n12.us_form == "इ᳓न्द्राव᳓रुणा"
  n13 = prakrti_svara.normalize_raw_form_to_us("एत॒वै", already_us=False)
  assert n13 is not None and n13.us_form == "ए᳓तवै᳓"

  n_unacc = prakrti_svara.normalize_raw_form_to_us("अग्ने", already_us=False)
  assert n_unacc is not None and n_unacc.is_unaccented
  n_mono_u = prakrti_svara.normalize_raw_form_to_us("प्र", already_us=False)
  assert n_mono_u is not None and n_mono_u.us_form == "प्र᳓"
  n_encl = prakrti_svara.normalize_raw_form_to_us("च", already_us=False)
  assert n_encl is not None and n_encl.us_form == "च"

  # Matra-iti and iva-iti glosses + MS initial-S fix on अँहसःपतये
  n_iva = prakrti_svara.normalize_raw_form_to_us("अ॒क्षी इ॒वेत्य॒क्षीऽइ॑व", already_us=False)
  assert n_iva is not None and n_iva.us_form == "अक्षी᳓-इव"
  n_rt = prakrti_svara.normalize_raw_form_to_us("ऋ॒तव॑री॒ इत्यृ॒तऽव॑री", already_us=False)
  assert n_rt is not None and n_rt.us_form == "ऋत᳓-वरी"
  n_amh = prakrti_svara.normalize_raw_form_to_us("अँ॑हसःऽप॒तये॑", already_us=False)
  assert n_amh is not None and n_amh.us_form == "अँहसः-पत᳓ये"


def test_project_form_to_stem_marks():
  # Semivowel jātya reversal onto vowel stems (पृ, थि, व्याः = 3 syllables)
  assert prakrti_svara.project_form_to_stem_marks("पृथिव्याः", ("", "", "S"), "पृथिवी") == ("", "", "U")
  assert prakrti_svara.project_form_to_stem_marks("पृथिव्याम्", ("", "", "U"), "पृथिवी") == ("", "", "U")
  assert prakrti_svara.project_form_to_stem_marks("तन्वाः", ("", "S"), "तनू") == ("", "U")
  assert prakrti_svara.project_form_to_stem_marks("पित्रा", ("", "U"), "पितृ") == ("", "U")

  # Authentic jātya preserved when stem itself carries glide
  assert prakrti_svara.project_form_to_stem_marks("सत्यम्", ("", "S"), "सत्य") == ("", "S")

  # Suffix-accented sup-compounds & dual-accent compounds
  assert prakrti_svara.project_form_to_stem_marks(
      "प्रजा-वत्-भ्यः", ("", "", "U", ""), "प्रजा-वत्", had_sup_suffix=True
  ) == ("", "", "U")
  assert prakrti_svara.project_form_to_stem_marks(
      "स्रुक्-भ्यः", ("", "U"), "स्रुच्", had_sup_suffix=True
  ) == ("U",)
  assert prakrti_svara.project_form_to_stem_marks(
      "द्यावा-पृथिवीभ्याम्", ("U", "", "", "", "U", ""), "द्यावा-पृथिवी"
  ) == ("U", "", "", "", "U")


def test_clean_loci_and_generate_prakrti_definitions():
  assert prakrti_svara._clean_loci("/06/004/02: विदे॑वस्त्वा<br><br>/20/059/03") == ("6.4.2", "20.59.3")

  raw_entries = [
      ("दे॒वम्", 20, ("1.1.1",)),
      ("दे॒वाय॑", 15, ("1.1.2",)),
      ("दे॒वाः", 12, ("1.1.3",)),
      ("देव॑", 30, ("1.1.4",)),        # voc.sg. — must NOT pollute देव᳓
      ("देवाः॑", 10, ("1.1.5",)),       # voc.pl. — must NOT pollute देव᳓
      ("दे॒व॒", 5, ("1.1.6",)),         # sarvānudātta — must NOT pollute देव᳓
      ("म॒रुद्भिः॑", 9, ("1.2.1",)),
      ("मरु॑तः", 4, ("1.2.2",)),         # voc.pl. — must NOT pollute मरु᳓त्
      ("अँ॒हः॒ऽमुचः॑", 3, ("4.13",)),
      ("तेन॑", 40, ("1.3.1",)),
      ("भ्व॑ति", 1, ("1.4.1",)),
      ("भ॒वति॑", 25, ("1.4.2",)),
      ("अभ॑वत्", 11, ("1.4.3",)),
      ("प्र", 50, ("1.1.2",)),
  ]
  # Fix typo भ्व॑ति -> भव॑ति ('भ᳓वति' vs 'भ॒वति॑' = 'भव᳓ति')
  raw_entries = [(("भव॑ति", f, l) if w == "भ्व॑ति" else (w, f, l)) for w, f, l in raw_entries]

  defs_dev, defs_final, _ = prakrti_svara.generate_prakrti_definitions(raw_entries, already_us=False)
  by_hw = {}
  for d in defs_dev:
    for hw in d.headwords_tuple:
      by_hw.setdefault(hw, []).append(d.meaning)

  # देव should have ONLY देव᳓ (no दे᳓व vocative pollution, and no false 'दिव्' dhātu!)
  assert len(by_hw["देव"]) == 1
  assert by_hw["देव"][0].startswith("देव᳓ (")
  assert "दिव्" not in by_hw

  # दारु (neuter nom/acc दा᳓रु x4 must NOT be suppressed by 1x दा॒रुम्)
  raw_daru = [("दारु॑", 4, ("1.1",)), ("दा॒रुम्", 1, ("1.2",)), ("ओ", 2, ("1.3",)), ("प्र॒जा॒ऽपत॑ये", 3, ("1.4",))]
  d_dev, _, _ = prakrti_svara.generate_prakrti_definitions(raw_daru, already_us=False)
  d_by_hw = {}
  for d in d_dev:
    for hw in d.headwords_tuple:
      d_by_hw.setdefault(hw, []).append(d.meaning)
  assert d_by_hw["दारु"][0].startswith("दा᳓रु (4)")
  assert d_by_hw["ओ"][0].startswith("ओ᳓ (2)")
  assert "प्रजापति" in d_by_hw and d_by_hw["प्रजापति"][0].startswith("प्रजा-प᳓ति")

  # मरुत् should have ONLY मरु᳓त् (no म᳓रुत्)
  assert len(by_hw["मरुत्"]) == 1
  assert by_hw["मरुत्"][0].startswith("मरु᳓त् (")

  # Compound hyphenation + candrabindu + sandhi alias preserved
  assert "अँहःमुच्" in by_hw and "अँहोमुच्" in by_hw
  assert by_hw["अँहःमुच्"][0].startswith("अँहः-मु᳓च् (3)")

  # Pronoun तेन resolves to तद् without spurious Tinanta
  assert any(m.startswith("त᳓द् (40)") for m in by_hw["तद्"])

  # Avyaya प्र
  assert any(m.startswith("प्र᳓ (50)") for m in by_hw["प्र"])

  # Finite verbs aggregate under भू [धातुः] with accented forms ordered before sarvānudātta/unaccented forms
  raw_entries_dhatu = raw_entries + [("भ॒व॒ति॒", 30, ("1.4.4",))]
  defs_dev2, _, _ = prakrti_svara.generate_prakrti_definitions(raw_entries_dhatu, already_us=False)
  bhu_entries = [d.meaning for d in defs_dev2 if "भू" in d.headwords_tuple and "[धातुः]" in d.meaning]
  assert len(bhu_entries) == 1
  assert bhu_entries[0].index("अ᳓भवत् (11)") < bhu_entries[0].index("भवति (30)")

  dhatu_entries = [m for m in by_hw["भू"] if "[धातुः]" in m]
  assert len(dhatu_entries) == 1
  assert "अ᳓भवत् (11)" in dhatu_entries[0]

  # Final OPTITRANS headwords present in defs_final
  assert any("bhu" in d.headwords_tuple or "bhU" in d.headwords_tuple or "deva" in d.headwords_tuple for d in defs_final)

  # Padapāṭha-joined enclitic `-इव` (अग्निःऽइव, रथैःऽइव) resolves to base stem (अग्नि, रथ), never अग्निः-इव
  raw_iva = [
      ("अ᳓ग्निः", 5, ("1.1.1",)),
      ("अ᳓ग्निः-इव", 6, ("2.25.4",)),
      ("र᳓थैः-इव", 2, ("5.60.1",)),
      ("इव", 10, ("1.1.2",)),
  ]
  iva_defs, _, _ = prakrti_svara.generate_prakrti_definitions(raw_iva, already_us=True)
  iva_hws: dict[str, list[str]] = {}
  for d in iva_defs:
    for hw in d.headwords_tuple:
      iva_hws.setdefault(hw, []).append(d.meaning)
  assert "अग्निः-इव" not in iva_hws and "रथैः-इव" not in iva_hws
  assert iva_hws["अग्नि"][0].startswith("अ᳓ग्नि (11)")
  assert "2.25.4" in iva_hws["अग्नि"][0]
  assert iva_hws["रथ"][0].startswith("र᳓थ (2)")
