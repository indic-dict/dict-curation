"""Tests for Maitrāyaṇī (MS) and Kāṭhaka (KS) US-accented padasvara Babylon extraction."""

from pathlib import Path

from dict_curation_projects.conversion.babylon.dict_specific.veda import (
    krishna_yajur_ks_ms,
    prakrti_svara,
)


def test_ms_and_ks_locus_parsing():
  assert krishna_yajur_ks_ms._locus_for_ms_file(Path("1/01/02.md")) == ((1, 1, 2), "1.1.2")
  assert krishna_yajur_ks_ms._locus_for_ms_file(Path("1/01/_index.md")) is None
  assert krishna_yajur_ks_ms._locus_for_ks_file(
      Path("1_iThimikA/01_puroDAshasthAnakam/03.md")
  ) == ((1, 1, 3), "1.3")
  assert krishna_yajur_ks_ms._locus_for_ks_file(
      Path("1_iThimikA/15_shrIrAjasUyam/02-04.md")
  ) == ((1, 15, 2), "15.2-4")
  assert krishna_yajur_ks_ms._locus_for_ks_file(
      Path("5_ashvamedhaH/01_panthAnuvachanam/10.md")
  ) == ((5, 1, 10), "5.1.10")


def test_collect_excludes_yantra_svara_and_corrections(tmp_path):
  ks_dir = tmp_path / "1_iThimikA" / "01_test"
  ks_dir.mkdir(parents=True)
  (ks_dir / "01.md").write_text(
      """+++
title = "०१"
+++

<details open><summary>विश्वास-प्रस्तुतिः</summary>

इषे᳓ त्वा ।
</details>

<details><summary>सर्वाष् टीकाः</summary>

<details><summary>पद-पाठः (यान्त्रिकः)</summary>

- इषे᳓ (*TS*-1)
- त्वा (अनुदात्तम्, पा॰ ८.१.१८)
- गलत → **शुद्ध᳓** (स्वर-लोपः)
</details>
</details>

<details open><summary>विश्वास-प्रस्तुतिः (यन्त्र-स्वरः)</summary>

अ᳓ग्निम् ।
</details>

<details><summary>सर्वाष् टीकाः</summary>

<details><summary>पद-पाठः (यान्त्रिकः)</summary>

- अ᳓ग्निम् (*TS*-10)
</details>
</details>
""",
      encoding="utf-8",
  )
  counts, loci, skipped = krishna_yajur_ks_ms.collect_ks_ms_padasvara(
      str(tmp_path), corpus="ks", include_yantra_svara=False
  )
  assert counts == {"इषे᳓": 1, "त्वा": 1}
  assert loci == {"इषे᳓": ["1.1"], "त्वा": ["1.1"]}
  assert "अ᳓ग्निम्" not in counts
  assert skipped == 1

  # Verify prakrti_svara specs register both MS and KS cleanly
  spec_map = {s.key: s for s in prakrti_svara.VEDA_SPECS}
  assert spec_map["ms"].dest_name == "kyv-ms-prakRti-svara"
  assert spec_map["ms"].source_name == "kyv-ms-pada-svara"
  assert spec_map["ks"].dest_name == "kyv-ks-prakRti-svara"
  assert spec_map["ks"].source_name == "kyv-ks-pada-svara"
