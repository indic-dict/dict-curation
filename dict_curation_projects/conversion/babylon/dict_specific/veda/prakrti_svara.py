"""Vedic prakṛti-svara (stem & dhātu accent) Babylon dictionary builders.

Derives US-accented (``᳓`` / ``᳙``) nominal prātipadika stems, avyayas,
and dhātu (verbal) finite-form synopses from existing Vedic padapāṭha
svara dictionaries (TS, RV, AV, VS-M, VS-K, ŚB-M, TB, TK), writing ``.babylon``
and ``README.md`` outputs into all mirrored kAvya directories.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import logging
import math
import os
from pathlib import Path
import re
from typing import Iterable, Sequence

from dict_curation import Definition, babylon
from doc_curation.sanskrit.accent import shatapatha_solver as ss
from indic_transliteration import sanscript
import regex
from vidyut.kosha import Kosha, PadaEntry, PratipadikaEntry
from vidyut.prakriya import Krt, Lakara, Linga, Pratipadika, Vacana, Vibhakti, Vyakarana

from . import taittiriya
from .padasvara_common import (
    ALL_ACCENTS_RE as _ALL_ACCENTS_RE,
    DEVATA_DVANDVA_PREFIXES as _DEVATA_DVANDVA_PREFIXES,
    ENCLITIC_PARTICLES as _ENCLITIC_PARTICLES,
    NormalizedPada,
    US_SVARITA,
    US_UDATTA,
    _is_devanagari,
    apply_us_marks_to_hyph as _apply_us_marks_to_hyph,
    assert_writable_dict_dest,
    is_dual_accent_candidate as _is_dual_accent_candidate,
    normalize_raw_form_to_us,
    strip_all_accents as _strip_all_accents,
)

DEFAULT_MIRROR_ROOTS: tuple[str, ...] = (
    "/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit-kAvya",
)
PRIMARY_KAVYA_ROOT = DEFAULT_MIRROR_ROOTS[0]
VEDAWEB_RK_DIR = "/home/vvasuki/gitland/vishvAsa/vedAH_Rk/static/shAkalam/saMhitA/sarvASh_TIkAH"


@dataclass(frozen=True)
class VedaDictSpec:
  """Configuration for one Vedic prakṛti-svara dictionary."""

  key: str
  dest_name: str
  source_name: str
  already_us: bool
  description: str


VEDA_SPECS: tuple[VedaDictSpec, ...] = (
    VedaDictSpec(
        key="ts",
        dest_name="kyv-ts-prakRti-svara",
        source_name="kyv-ts-padasvara",
        already_us=True,
        description="Kṛṣṇa Yajurveda Taittirīya Saṁhitā prakṛti-svara (stems & dhātus, US notation)",
    ),
    VedaDictSpec(
        key="rv",
        dest_name="rv-prakRti-svara-dev",
        source_name="rv-padasvara-dev",
        already_us=True,
        description="Ṛgveda Śākala Saṁhitā prakṛti-svara (stems & dhātus, US notation)",
    ),
    VedaDictSpec(
        key="av",
        dest_name="av-prakRti-svara",
        source_name="av-padasvara",
        already_us=True,
        description="Atharvaveda Śaunaka Saṁhitā prakṛti-svara (stems & dhātus, US notation)",
    ),
    VedaDictSpec(
        key="vs-m",
        dest_name="syv-vs-m-prakRti-svara",
        source_name="syv-vs-m-padasvara",
        already_us=True,
        description="Śukla Yajurveda Vājasaneyi Mādhyandina Saṁhitā prakṛti-svara (stems & dhātus, US notation)",
    ),
    VedaDictSpec(
        key="vs-k",
        dest_name="syv-vs-k-prakRti-svara",
        source_name="syv-vs-k-padasvara",
        already_us=True,
        description="Śukla Yajurveda Vājasaneyi Kāṇva Saṁhitā prakṛti-svara (stems & dhātus, US notation)",
    ),
    VedaDictSpec(
        key="sb",
        dest_name="syv-sb-m-prakRti-svara",
        source_name="syv-sb-m-pada-svara",
        already_us=True,
        description="Śukla Yajurveda Mādhyandina Śatapatha Brāhmaṇa prakṛti-svara (stems & dhātus, US notation)",
    ),
    VedaDictSpec(
        key="tb",
        dest_name="kyv-tb-prakRti-svara",
        source_name="kyv-tb-pada-svara",
        already_us=True,
        description="Kṛṣṇa Yajurveda Taittirīya Brāhmaṇa prakṛti-svara (stems & dhātus, US notation)",
    ),
    VedaDictSpec(
        key="tk",
        dest_name="kyv-tk-prakRti-svara",
        source_name="kyv-tk-pada-svara",
        already_us=True,
        description="Kṛṣṇa Yajurveda Taittirīya Kāṭhaka prakṛti-svara (stems & dhātus, US notation)",
    ),
    VedaDictSpec(
        key="ms",
        dest_name="kyv-ms-prakRti-svara",
        source_name="kyv-ms-pada-svara",
        already_us=True,
        description="Kṛṣṇa Yajurveda Maitrāyaṇī Saṁhitā prakṛti-svara (stems & dhātus, US notation)",
    ),
    VedaDictSpec(
        key="ks",
        dest_name="kyv-ks-prakRti-svara",
        source_name="kyv-ks-pada-svara",
        already_us=True,
        description="Kṛṣṇa Yajurveda Kāṭhaka Saṁhitā prakṛti-svara (stems & dhātus, US notation)",
    ),
)

_SUP_COMPOUND_ENDS: frozenset[str] = frozenset({"भिः", "भ्यः", "भ्याम्", "सु", "षु"})

_KNOWN_AVYAYAS: frozenset[str] = _ENCLITIC_PARTICLES | frozenset({
    "प्र", "परा", "अप", "सम्", "सं", "अनु", "अव", "निः", "निर्", "निस्", "दुः", "दुर्", "दुस्",
    "वि", "आ", "नि", "अधि", "अपि", "अति", "सु", "उत्", "अभि", "प्रति", "परि", "उप",
    "इत्", "उ", "ओ", "ऐ", "आः", "उत", "उता", "एव", "एवा", "एवम्", "अथ", "अथो", "अथा", "न", "मा", "नु",
    "नू", "हि", "तु", "खलु", "किल्", "किल", "ननु", "वाव", "इति", "इह", "तत्र", "यत्र",
    "अत्र", "कुत्र", "विश्वत्र", "अन्यत्र", "सर्वत्र", "एकत्र", "उभयत्र", "तथा", "यथा", "कथा",
    "इत्था", "अन्यथा", "सर्वथा", "उभयथा", "तदा", "यदा", "कदा", "सदा", "सर्वदा", "एकदा",
    "इदानीम्", "तदानीम्", "अद्य", "श्वः", "ह्यः", "सद्यः", "सपदि", "सह", "साकम्", "सार्धम्",
    "सत्रा", "विना", "नाना", "अधः", "पुरः", "परः", "उपरि", "अन्तः", "बहिः", "पुनः", "प्राक्",
    "प्रत्यक्", "उदक्", "सम्यक्", "तिर्यक्", "विश्वक्", "सचा", "मिथः", "मुहुः", "मक्षु",
    "स्वः", "स्वर्", "भुवः", "भूः", "स्वाहा", "वषट्", "स्वधा", "वौषट्", "श्रौषट्", "वेत्",
    "हन्त", "अरे", "बट्", "बत", "अद्धा", "मनाक्", "ईषत्", "पृथक्", "किम्", "कथम्", "कुतः",
    "ततः", "यतः", "अतः", "इतः", "आत्", "अध", "अधा", "अभिः", "समया", "निकषा", "अभितः",
    "परितः", "उभयतः", "सर्वतः", "विश्वतः", "अग्रतः", "पृष्ठतः", "दक्षिणतः", "उत्तरतः", "अधस्तात्",
    "पुरस्तात्", "उपरिष्टात्", "पश्चात्", "अवस्तात्", "आरात्", "तस्मात्", "कच्चित्", "चत्", "श्वित्",
    "भूयः", "तूर्णि", "आशु", "मृषा", "साध्व्", "ऋते", "तूष्णीम्", "जातु", "श्वश्वत्", "शश्वत्",
    "युगपत्", "सकृत्", "द्विः", "त्रिः", "चतुः", "सप्तकृत्वः", "पञ्चकृत्वः", "उच्चैः", "नीचैः", "शनैः",
    "कामम्", "प्रातः", "सायम्", "दोषा", "नक्तम्", "दिवा", "चिरम्", "सुष्ठु", "दुष्ठु",
})

# Common single-vowel / 1-syllable dhātus so rare śabda roots like 'उ' don't beat 'अव्' on आ᳓वत
_COMMON_MONO_DHATUS: frozenset[str] = frozenset({
    "अद्", "अस्", "इ", "ऋ", "कृ", "दा", "धा", "नु", "नी", "पा", "भू",
    "मा", "या", "रा", "वा", "वी", "सू", "हा", "हि", "हु", "हू", "हे",
})

# Irregular pronominal and Vedic nominal paradigms (normalizedSLP1 -> canonical Devanagari stem)
# Built conservatively for core irregulars whose oblique forms deviate from mechanical rules.
_IRREGULAR_SURFACE_TO_STEM: dict[str, str] = {
    # अस्मद्
    "अहम्": "अस्मद्", "आवाम्": "अस्मद्", "वयम्": "अस्मद्",
    "माम्": "अस्मद्", "मा": "अस्मद्", "आवयोः": "अस्मद्", "अस्मान्": "अस्मद्", "नः": "अस्मद्",
    "मया": "अस्मद्", "आवाभ्याम्": "अस्मद्", "अस्माभिः": "अस्मद्",
    "मह्यम्": "अस्मद्", "मे": "अस्मद्", "अस्मभ्यम्": "अस्मद्",
    "मत्": "अस्मद्", "मत्तः": "अस्मद्", "अस्मत्": "अस्मद्",
    "मम": "अस्मद्", "अस्माकम्": "अस्मद्", "अस्माक": "अस्मद्",
    "मयि": "अस्मद्", "अस्मासु": "अस्मद्", "अस्मे": "अस्मद्",
    # युष्मद्
    "त्वम्": "युष्मद्", "युवाम्": "युष्मद्", "यूयम्": "युष्मद्",
    "त्वाम्": "युष्मद्", "त्वा": "युष्मद्", "युवयोः": "युष्मद्", "युवोः": "युष्मद्", "युष्मान्": "युष्मद्", "वः": "युष्मद्",
    "त्वया": "युष्मद्", "त्वाया": "युष्मद्", "युवाभ्याम्": "युष्मद्", "युष्माभिः": "युष्मद्",
    "तुभ्यम्": "युष्मद्", "ते": "युष्मद्", "युष्मभ्यम्": "युष्मद्",
    "त्वत्": "युष्मद्", "युष्मत्": "युष्मद्",
    "तव": "युष्मद्", "युष्माकम्": "युष्मद्", "युष्माक": "युष्मद्",
    "त्वयि": "युष्मद्", "युष्मासु": "युष्मद्", "युष्मे": "युष्मद्",
    # तद् (स/तत्)
    "सः": "तद्", "स": "तद्", "सा": "तद्", "तत्": "तद्",
    "तम्": "तद्", "ताम्": "तद्", "तौ": "तद्", "तेन": "तद्", "तया": "तद्",
    "ताभ्याम्": "तद्", "तस्मै": "तद्", "तस्यै": "तद्", "तस्मात्": "तद्",
    "तस्य": "तद्", "तस्याः": "तद्", "तयोः": "तद्", "तस्मिन्": "तद्", "तस्याम्": "तद्",
    "ताः": "तद्", "तान्": "तद्", "तानि": "तद्", "ताभिः": "तद्", "ताभ्यः": "तद्",
    "तासाम्": "तद्", "तासु": "तद्", "तेषाम्": "तद्", "तेषु": "तद्",
    "तेभ्यः": "तद्", "तेभिः": "तद्", "तैः": "तद्",
    # स्य/त्य
    "स्यः": "त्यद्", "स्या": "त्यद्", "त्यत्": "त्यद्", "त्यम्": "त्यद्", "त्याः": "त्यद्", "त्या": "त्यद्",
    # यद्
    "यः": "यद्", "या": "यद्", "यत्": "यद्", "यम्": "यद्", "याम्": "यद्", "यौ": "यद्", "ये": "यद्",
    "येन": "यद्", "यया": "यद्", "याभ्याम्": "यद्", "यस्मै": "यद्", "यस्यै": "यद्", "यस्मात्": "यद्",
    "यस्य": "यद्", "यस्याः": "यद्", "ययोः": "यद्", "यस्मिन्": "यद्", "यस्याम्": "यद्",
    "याः": "यद्", "यान्": "यद्", "यानि": "यद्", "याभिः": "यद्", "याभ्यः": "यद्",
    "यासाम्": "यद्", "यासु": "यद्", "येषाम्": "यद्", "येषु": "यद्",
    "येभ्यः": "यद्", "येभिः": "यद्", "यैः": "यद्",
    # एतद्
    "एषः": "एतद्", "एष": "एतद्", "एषा": "एतद्", "एतत्": "एतद्",
    "एतम्": "एतद्", "एताम्": "एतद्", "एतौ": "एतद्", "एते": "एतद्", "एतेन": "एतद्", "एतया": "एतद्",
    "एताभ्याम्": "एतद्", "एतस्मै": "एतद्", "एतस्यै": "एतद्", "एतस्मात्": "एतद्",
    "एतस्य": "एतद्", "एतस्याः": "एतद्", "एतयोः": "एतद्", "एतस्मिन्": "एतद्", "एतस्याम्": "एतद्",
    "एताः": "एतद्", "एतान्": "एतद्", "एतानि": "एतद्", "एताभिः": "एतद्", "एताभ्यः": "एतद्",
    "एतासाम्": "एतद्", "एतासु": "एतद्", "एतेषाम्": "एतद्", "एतेषु": "एतद्",
    "एतेभ्यः": "एतद्", "एतेभिः": "एतद्", "एतैः": "एतद्",
    # इदम्
    "अयम्": "इदम्", "इयम्": "इदम्", "इदम्": "इदम्",
    "इमम्": "इदम्", "इमाम्": "इदम्", "इमौ": "इदम्", "इमे": "इदम्", "इमाः": "इदम्", "इमान्": "इदम्", "इमानि": "इदम्",
    "अनेन": "इदम्", "अनया": "इदम्", "आभ्याम्": "इदम्", "अस्मै": "इदम्", "अस्यै": "इदम्",
    "अस्मात्": "इदम्", "अस्य": "इदम्", "अस्याः": "इदम्", "अनयोः": "इदम्", "अयोः": "इदम्",
    "अस्मिन्": "इदम्", "अस्याम्": "इदम्", "आभिः": "इदम्", "आभ्यः": "इदम्", "आसाम्": "इदम्", "आसु": "इदम्",
    "एभिः": "इदम्", "एभ्यः": "इदम्", "एषाम्": "इदम्", "एषु": "इदम्", "एभिः": "इदम्",
    # अदस्
    "असौ": "अदस्", "अदः": "अदस्",
    "अमुम्": "अदस्", "अमूम्": "अदस्", "अमू": "अदस्", "अमी": "अदस्", "अमून्": "अदस्", "अमूनि": "अदस्", "अमूः": "अदस्",
    "अमुना": "अदस्", "अमुया": "अदस्", "अमूभ्याम्": "अदस्", "अमीभिः": "अदस्", "अमूभिः": "अदस्",
    "अमुष्मै": "अदस्", "अमुष्यै": "अदस्", "अमुष्मात्": "अदस्", "अमुष्याः": "अदस्", "अमुष्य": "अदस्",
    "अमुयोः": "अदस्", "अमुष्मिन्": "अदस्", "अमुष्याम्": "अदस्", "अमीभ्यः": "अदस्", "अमूभ्यः": "अदस्",
    "अमीषाम्": "अदस्", "अमूषाम्": "अदस्", "अमीषु": "अदस्", "अमूषु": "अदस्",
    # किम्
    "कः": "किम्", "का": "किम्", "किम्": "किम्", "कम्": "किम्", "काम्": "किम्", "कौ": "किम्", "के": "किम्",
    "केन": "किम्", "कया": "किम्", "काभ्याम्": "किम्", "कस्मै": "किम्", "कस्यै": "किम्", "कस्मात्": "किम्",
    "कस्य": "किम्", "कस्याः": "किम्", "कयोः": "किम्", "कस्मिन्": "किम्", "कस्याम्": "किम्",
    "काः": "किम्", "कान्": "किम्", "कानि": "किम्", "काभिः": "किम्", "काभ्यः": "किम्", "कासाम्": "किम्", "कासु": "किम्",
    "केभ्यः": "किम्", "केभिः": "किम्", "कैः": "किम्", "केषाम्": "किम्", "केषु": "किम्", "कत्": "किम्",
    # Core irregular Vedic nominals: अप्, गो, द्यौ/दिव्, नौ, पथिन्, अहन्, अक्षि, अस्थि, दधि, सक्थि, मास्
    "आपः": "अप्", "अपः": "अप्", "अद्भिः": "अप्", "अद्भ्यः": "अप्", "अद्भ्याम्": "अप्", "अपाम्": "अप्", "अप्सु": "अप्",
    "गौः": "गो", "गाम्": "गो", "गावः": "गो", "गावौ": "गो", "गवा": "गो", "गवे": "गो", "गोः": "गो", "गवि": "गो",
    "गवोः": "गो", "गवाम्": "गो", "गोभिः": "गो", "गोभ्यः": "गो", "गोभ्याम्": "गो", "गोषु": "गो", "गाः": "गो", "गोनाम्": "गो",
    "द्यौः": "दिव्", "द्याम्": "दिव्", "द्यावः": "दिव्", "द्यावा": "दिव्", "दिवः": "दिव्", "दिवा": "दिव्",
    "दिवे": "दिव्", "दिवि": "दिव्", "द्युः": "दिव्", "द्युभिः": "दिव्", "द्युभ्यः": "दिव्", "द्युषु": "दिव्", "दिवाम्": "दिव्",
    "नौः": "नौ", "नावम्": "नौ", "नावः": "नौ", "नावा": "नौ", "नावे": "नौ", "नावि": "नौ", "नौभिः": "नौ", "नौषु": "नौ",
    "पन्थाः": "पथिन्", "पन्थाम्": "पथिन्", "पन्थानम्": "पथिन्", "पन्थानौ": "पथिन्", "पन्थानः": "पथिन्",
    "पथः": "पथिन्", "पथा": "पथिन्", "पथे": "पथिन्", "पथि": "पथिन्", "पथोः": "पथिन्", "पथाम्": "पथिन्",
    "पथिभिः": "पथिन्", "पथिभ्यः": "पथिन्", "पथिषु": "पथिन्",
    "अहः": "अहन्", "अह्ना": "अहन्", "अह्ने": "अहन्", "अह्नः": "अहन्", "अह्नि": "अहन्", "अहनि": "अहन्",
    "अहानि": "अहन्", "अहा": "अहन्", "अहोभिः": "अहन्", "अहोभ्यः": "अहन्", "अहःसु": "अहन्", "अह्नाम्": "अहन्",
    "अक्षि": "अक्षि", "अक्षिणी": "अक्षि", "अक्ष्णा": "अक्षि", "अक्ष्णे": "अक्षि", "अक्ष्णः": "अक्षि", "अक्ष्णि": "अक्षि",
    "अक्ष्णोः": "अक्षि", "अक्ष्णाम्": "अक्षि", "अक्षिभिः": "अक्षि", "अक्षिभ्यः": "अक्षि", "अक्षिभ्याम्": "अक्षि", "अक्ष्योः": "अक्षि",
    "अस्थि": "अस्थि", "अस्थ्ना": "अस्थि", "अस्थ्ने": "अस्थि", "अस्थ्नः": "अस्थि", "अस्थ्नि": "अस्थि",
    "अस्थीनि": "अस्थि", "अस्था": "अस्थि", "अस्थ्नाम्": "अस्थि", "अस्थिभिः": "अस्थि", "अस्थिभ्यः": "अस्थि",
    "दधि": "दधि", "दध्ना": "दधि", "दध्ने": "दधि", "दध्नः": "दधि", "दध्नि": "दधि",
    "श्वः": "श्वन्", "श्वा": "श्वन्", "श्वानम्": "श्वन्", "शुनः": "श्वन्", "शुना": "श्वन्", "शुने": "श्वन्", "शुनि": "श्वन्", "शुनाम्": "श्वन्",
    "युवा": "युवन्", "युवानम्": "युवन्", "युवानः": "युवन्", "यूनः": "युवन्", "यूना": "युवन्", "यूने": "युवन्", "यूनी": "युवन्", "यूनाम्": "युवन्",
    "मघवा": "मघवन्", "मघवानम्": "मघवन्", "मघवानः": "मघवन्", "मघोनः": "मघवन्", "मघोना": "मघवन्", "मघोने": "मघवन्", "मघवद्भिः": "मघवन्",
}

# Canonical Pāṇinian Devanagari dhātu normalizations (e.g. Vidyut internal codes -> standard dhātu)
_SLP_DHATU_CANONICAL: dict[str, str] = {
    "BU": "भू",
    "kf": "कृ",
    "as": "अस्",
    "DA": "धा",
    "dA": "दा",
    "pA": "पा",
    "i": "इ",
    "ik": "इ",
    "in": "इ",
    "gam": "गम्",
    "han": "हन्",
    "brU": "ब्रू",
    "vac": "वच्",
    "dfS": "दृश्",
    "sTA": "स्था",
    "sad": "सद्",
    "jan": "जन्",
    "man": "मन्",
    "yaj": "यज्",
    "hu": "हु",
    "yu": "यु",
    "yuj": "युज्",
    "vid": "विद्",
    "vfd": "वृध्",
    "vfD": "वृध्",
    "vf": "वृ",
    "vft": "वृत्",
    "sfj": "सृज्",
    "sf": "सृ",
    "stf": "स्तृ",
    "stu": "स्तु",
    "Sru": "श्रु",
    "Sak": "शक्",
    "Sam": "शम्",
    "Sas": "शंस्",
    "SaMs": "शंस्",
    "su": "सु",
    "sU": "सू",
    "pU": "पू",
    "vah": "वह्",
    "vas": "वस्",
    "vA": "वा",
    "ji": "जि",
    "nI": "नी",
    "BI": "भी",
    "rA": "रा",
    "rAD": "राध्",
    "raB": "रभ्",
    "laB": "लभ्",
    "tap": "तप्",
    "tan": "तन्",
    "tyaj": "त्यज्",
    "pfc": "पृच्",
    "pf": "पृ",
    "pF": "पॄ",
    "gfh": "गृह्",
    "grah": "ग्रह्",
    "svap": "स्वप्",
    "jAgf": "जागृ",
    "cakz": "चक्ष्",
    "KAd": "खाद्",
    "f": "ऋ",
    "fc": "अर्च्",
    "fj": "अर्ज्",
    "arD": "ऋध्",
    "fD": "ऋध्",
    "Ap": "आप्",
    "IS": "ईश्",
    "Ikz": "ईक्ष्",
    "Ir": "ईर्",
    "uh": "ऊह्",
    "ruh": "रुह्",
    "rud": "रुद्",
    "ruc": "रुच्",
    "rih": "रिह्",
    "lih": "लिह्",
    "dah": "दह्",
    "du": "दु",
    "duh": "दुह्",
    "druh": "द्रुह्",
    "muh": "मुह्",
    "sah": "सह्",
    "mih": "मिह्",
    "sruc": "स्रु",
    "sru": "स्रु",
    "plu": "प्लु",
    "dru": "द्रु",
    "cyu": "च्यु",
    "Svi": "श्वि",
    "hve": "ह्वे",
    "hU": "हू",
    "kram": "क्रम्",
    "nam": "नम्",
    "ram": "रम्",
    "yam": "यम्",
    "dam": "दम्",
    "Sam": "शम्",
    "kzam": "क्षम्",
    "pAc": "पच्",
    "pac": "पच्",
    "pat": "पत्",
    "sad": "सद्",
    "ad": "अद्",
    "pad": "पद्",
    "mad": "मद्",
    "nad": "नद्",
    "vad": "वद्",
    "Cid": "छिद्",
    "Bid": "भिद्",
    "nud": "नुद्",
    "tud": "तुद्",
    "rudh": "रुध्",
    "ruD": "रुध्",
    "buD": "बुध्",
    "yuD": "युध्",
    "kuD": "क्रुध्",
    "kruD": "क्रुध्",
    "kzuD": "क्षुध्",
    "SuD": "शुध्",
    "siD": "सिध्",
    "sAD": "साध्",
    "bAD": "बाध्",
    "spfd": "स्पर्ध्",
    "spfD": "स्पर्ध्",
    "spfS": "स्पृश्",
    "dfp": "दृप्",
    "tfp": "तृप्",
    "sarp": "सृप्",
    "sfp": "सृप्",
    "klp": "कॢप्",
    "kxp": "कॢप्",
}

# Genuine productive kṛt suffixes whose derived stems are valid prātipadikas (vs bare root kvi~p/ac/Ga homographs)
_PRODUCTIVE_KRTS: frozenset[str] = frozenset({
    "kta", "ktavatu~", "Satf~", "SAnac", "tavya", "tavya~t", "anIyar",
    "yat", "Ryat", "kyap", "tfc", "tfn", "ktic", "ktin", "lyuw",
    "kvasu~", "kAnac", "ktvA", "tumun", "lyap", "Ra", "Rvul", "tf", "in",
    "izWan", "Iyasun",
})

_VYAKARANA = Vyakarana()
_DERIVE_CACHE: dict[tuple[str, str], tuple[str, ...]] = {}


def _clean_loci(tail: str) -> tuple[str, ...]:
  """Normalize corpus citations across TS/RV/AV/MS into clean comma tokens."""
  if not tail:
    return ()
  seen: dict[str, None] = {}
  for piece in re.split(r"(?:<br>|,|\n)+", tail):
    tok = piece.strip()
    if not tok or tok.startswith("…"):
      continue
    # AV citations can contain "/06/004/02: mantra_text..."
    if ":" in tok:
      tok = tok.split(":", 1)[0].strip()
    m_av = re.match(r"^/+(\d+)/(\d+)/(\d+)\s*$", tok)
    if m_av:
      a, b, c = (str(int(g)) for g in m_av.groups())
      tok = f"{a}.{b}.{c}"
    tok = tok.strip(" ,;")
    if tok:
      seen.setdefault(tok, None)
  return tuple(seen.keys())


def load_padasvara_entries(babylon_path: str | Path) -> list[tuple[str, int, tuple[str, ...]]]:
  """Read ``(sasvara_form, freq, loci)`` entries from an existing padasvara Babylon file."""
  text = Path(babylon_path).read_text(encoding="utf-8")
  entries: list[tuple[str, int, tuple[str, ...]]] = []
  for block in text.split("\n\n"):
    lines = block.splitlines()
    if len(lines) < 2 or lines[0].startswith("#"):
      continue
    body = "<br>".join(lines[1:])
    if "<br>" in body:
      head_part, loci_part = body.split("<br>", 1)
    else:
      head_part, loci_part = body, ""
    head_part = head_part.strip()
    m = re.match(r"^(.+?)\s*\((\d+)\)\s*$", head_part)
    if not m:
      continue
    form = m.group(1).strip()
    freq = int(m.group(2))
    loci = _clean_loci(loci_part)
    entries.append((form, freq, loci))
  return entries


@dataclass(frozen=True)
class VedawebEntry:
  """Aggregated Vedaweb annotation prior for one bare surface."""

  pos: str  # "nominal", "pronoun", "invariable", "root_verb", "root_participle", ""
  stems: tuple[str, ...]  # canonical Devanagari stems / roots when mapped cleanly
  has_voc: bool
  only_voc: bool


def _clean_vedaweb_iast_to_deva(iast: str) -> str:
  s = re.sub(r"[\u0300\u0301\u0302\u030d0-9]", "", iast.strip())
  s = s.replace("r̥̄", "ṝ").replace("r̥", "ṛ").replace("l̥̄", "ḹ").replace("l̥", "ḷ")
  deva = sanscript.transliterate(s, sanscript.IAST, sanscript.DEVANAGARI)
  return deva.replace("ँ", "ं").strip("-")


def _clean_vedaweb_root_to_deva(vw_lem: str) -> str:
  """Convert Vedaweb ``√kr̥- 1`` or ``√dhā-`` to clean Devanagari dhātu (or empty if ambiguous)."""
  s = vw_lem.split("~", 1)[0].strip()
  s = re.sub(r"^[√\s]+", "", s)
  s = re.sub(r"\s+\d+$", "", s).replace("-", "").replace("ⁱ", "").strip()
  if not s:
    return ""
  s = s.replace("r̥̄", "ṝ").replace("r̥", "ṛ").replace("l̥", "ḷ")
  deva = sanscript.transliterate(s, sanscript.IAST, sanscript.DEVANAGARI)
  return deva


def load_vedaweb_prior(vedaweb_dir: str | Path = VEDAWEB_RK_DIR) -> dict[str, VedawebEntry]:
  """Load Vedaweb bare-surface POS & vocative priors if the RK directory exists."""
  root = Path(vedaweb_dir)
  if not root.exists():
    return {}
  pos_counts: dict[str, Counter[str]] = defaultdict(Counter)
  voc_flags: dict[str, list[bool]] = defaultdict(list)
  root_counts: dict[str, Counter[str]] = defaultdict(Counter)

  for p in root.rglob("*.md"):
    txt = p.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"<summary>Vedaweb annotation</summary>(.*?)</details>", txt, re.S)
    if not m:
      continue
    for blk in m.group(1).split("\n\n"):
      lines = [l.strip() for l in blk.splitlines() if l.strip()]
      if not lines or "←" not in lines[0] or "(" not in lines[0]:
        continue
      surf_iast, rest = lines[0].split("←", 1)
      raw_pos = rest.rsplit("(", 1)[-1].rstrip(") ").strip()
      raw_lem = rest.rsplit("(", 1)[0].strip()
      morph = lines[1] if len(lines) > 1 and lines[1].startswith("{") else ""
      is_voc = "case:VOC" in morph
      has_case = "case:" in morph
      surf_deva = _clean_vedaweb_iast_to_deva(surf_iast)
      if not surf_deva or not _is_devanagari(surf_deva):
        continue
      if raw_pos == "root" or (raw_pos == "UNK_TYPE" and raw_lem.startswith("√")):
        kind = "root_participle" if has_case else "root_verb"
        rt = _clean_vedaweb_root_to_deva(raw_lem)
        if rt:
          root_counts[surf_deva][rt] += 1
      elif raw_pos in ("nominal stem", "UNK_TYPE"):
        kind = "nominal"
      elif raw_pos == "pronoun":
        kind = "pronoun"
      elif raw_pos == "invariable":
        kind = "invariable"
      else:
        kind = raw_pos
      pos_counts[surf_deva][kind] += 1
      voc_flags[surf_deva].append(is_voc)

  prior: dict[str, VedawebEntry] = {}
  for surf, cnts in pos_counts.items():
    dom_pos = cnts.most_common(1)[0][0]
    flags = voc_flags[surf]
    top_roots = tuple(r for r, _ in root_counts[surf].most_common(2)) if surf in root_counts else ()
    prior[surf] = VedawebEntry(
        pos=dom_pos,
        stems=top_roots,
        has_voc=any(flags),
        only_voc=bool(flags) and all(flags),
    )
  logging.info("Loaded Vedaweb prior for %d RV surfaces", len(prior))
  return prior


def _slp_variants(slp: str) -> list[str]:
  """Generate standard Vidyut SLP1 padānta & parasavarṇa variants for lookup."""
  out: list[str] = [slp]
  if slp.endswith("H"):
    out.append(slp[:-1] + "s")
    out.append(slp[:-1] + "r")
  elif slp.endswith("M"):
    out.append(slp[:-1] + "m")
  elif slp.endswith("d"):
    out.append(slp[:-1] + "t")
  elif slp.endswith("q"):
    out.append(slp[:-1] + "w")

  if "M" in slp:
    extra: list[str] = []
    for base in out:
      # Replace M before varga consonants with homorganic nasal
      b = re.sub(r"M(?=[kKgGN])", "N", base)
      b = re.sub(r"M(?=[cCjJY])", "Y", b)
      b = re.sub(r"M(?=[wWqQR])", "R", b)
      b = re.sub(r"M(?=[tTdDn])", "n", b)
      b = re.sub(r"M(?=[pPbBm])", "m", b)
      b = b.replace("M", "m")
      extra.append(b)
      if b != base:
        extra.append(base.replace("M", "n"))
        extra.append(base.replace("M", "m"))
    out.extend(extra)
  return list(dict.fromkeys(out))


def _vedic_alias_slps(slp: str) -> list[str]:
  """Generate classical SLP1 analogs of Vedic nominal/verbal surfaces."""
  aliases: list[str] = []
  if slp.endswith("AsaH"):
    aliases.append(slp[:-4] + "AH")
  if slp.endswith("eBiH"):
    aliases.append(slp[:-4] + "EH")
  if "L" in slp:
    aliases.append(slp.replace("L", "q"))
  if "gfB" in slp:
    aliases.append(slp.replace("gfB", "gfh"))
  if slp.endswith("masi") and len(slp) > 4:
    aliases.append(slp[:-4] + "maH")
  if slp.endswith("A") and len(slp) > 2:
    aliases.append(slp[:-1] + "O")
    aliases.append(slp[:-1] + "Ani")
  if slp.endswith("I") and len(slp) > 2:
    aliases.append(slp[:-1] + "Ini")
  if slp.endswith("U") and len(slp) > 2:
    aliases.append(slp[:-1] + "Uni")
  # Epenthetic Vedic svarabhakti -iy- / -uv- -> -y- / -v-
  if "iya" in slp or "iyA" in slp or "iyo" in slp or "iye" in slp or "iyE" in slp:
    aliases.append(re.sub(r"iy([aAoOeEi])", r"y\1", slp))
  if "uva" in slp or "uvA" in slp or "uvo" in slp or "uve" in slp:
    aliases.append(re.sub(r"uv([aAoOeEi])", r"v\1", slp))
  # Pluta / lengthened final vowels in Vedic particles/dual/voc: उता -> उत, एवा -> एव
  if slp.endswith(("utA", "evA", "aTA", "adyA", "yaTA", "taTA", "smA")):
    aliases.append(slp[:-1] + "a")
  return list(dict.fromkeys(aliases))


def _derive_krdanta_stems(dhatu_entry, krt_val) -> tuple[str, ...]:
  """Derive SLP1 prātipadika stems for a Vidyut ``PratipadikaEntry.Krdanta`` entry."""
  d_clean = dhatu_entry.clean_text
  k_str = str(krt_val)
  key = (d_clean, k_str)
  if key in _DERIVE_CACHE:
    return _DERIVE_CACHE[key]
  try:
    prakriyas = _VYAKARANA.derive(Pratipadika.krdanta(dhatu=dhatu_entry.dhatu, krt=krt_val))
    stems = tuple(dict.fromkeys(p.text for p in prakriyas if p.text))
  except Exception:
    stems = ()
  _DERIVE_CACHE[key] = stems
  return stems


def _dhatu_slp_to_deva(dhatu_slp: str) -> str:
  if dhatu_slp in _SLP_DHATU_CANONICAL:
    return _SLP_DHATU_CANONICAL[dhatu_slp]
  # Map i-ending Vidyut curādi / anudātta base names cleanly where obvious
  return sanscript.transliterate(dhatu_slp, sanscript.SLP1, sanscript.DEVANAGARI)


def _match_derived_krdanta_stem(surf_slp: str, cand_stems: tuple[str, ...]) -> str:
  """Pick the best-matching derived Kṛdanta stem for an inflected surface."""
  if not cand_stems:
    return ""
  if len(cand_stems) == 1:
    return cand_stems[0]
  # Prefer longest common prefix with surface SLP1
  def _score(st: str) -> tuple[int, int]:
    lcp = 0
    for a, b in zip(st, surf_slp):
      if a == b:
        lcp += 1
      else:
        break
    return (lcp, -len(st))
  return max(cand_stems, key=_score)


@dataclass(frozen=True)
class SurfaceCandidate:
  """One grammatical interpretation of a bare Sanskrit target word."""

  pos: str  # "nominal", "avyaya", "tinanta"
  stem_deva: str  # Canonical Devanagari prātipadika / avyaya / dhātu
  source_tier: int  # Higher = higher structural preference
  can_be_voc: bool
  only_voc: bool
  stem_slp: str


def _peel_upasarga_tinanta(slp: str, kosha: Kosha) -> str | None:
  """Peel a leading Sanskrit upasarga on an unmatched fused finite verb and return dhātu SLP1."""
  prefixes = (
      "prati", "pari", "anu", "aBi", "aDi", "api", "ati", "apa", "ava", "upa",
      "pra", "parA", "sam", "nir", "dur", "vi", "ni", "ut", "A",
  )
  for pf in prefixes:
    if not slp.startswith(pf) or len(slp) <= len(pf) + 2:
      continue
    rem = slp[len(pf):]
    for cand in [rem] + (["a" + rem] if pf.endswith(("a", "A")) and rem.startswith(("k", "g", "c", "j", "t", "d", "n", "p", "b", "m", "y", "r", "l", "v", "S", "z", "s", "h")) else []):
      for v in _slp_variants(cand):
        entries = list(kosha.get(v))
        tins = [e for e in entries if isinstance(e, PadaEntry.Tinanta)]
        if tins and tins[0].lakara not in (Lakara.Lot, Lakara.Lit):
          return tins[0].dhatu_entry.clean_text
  # Also vowel-sandhi preverbs: vy- -> vi + , ny- -> ni + , aBy- -> aBi + , anv- -> anu + , praty- -> prati +
  sandhi_pfs = (
      ("praty", "prati"), ("aBy", "aBi"), ("aDy", "aDi"), ("aty", "ati"),
      ("vy", "vi"), ("ny", "ni"), ("anv", "anu"), ("sam", "saM"),
  )
  for s_pf, _ in sandhi_pfs:
    if slp.startswith(s_pf) and len(slp) > len(s_pf) + 2:
      rem = slp[len(s_pf):]
      for v in _slp_variants(rem):
        entries = list(kosha.get(v))
        tins = [e for e in entries if isinstance(e, PadaEntry.Tinanta)]
        if tins:
          return tins[0].dhatu_entry.clean_text
  return None


def _sup_padanta_to_stems(padanta_deva: str, kosha: Kosha) -> list[SurfaceCandidate]:
  """Convert the stem side of ``X-भिः/-भ्यः/-भ्याम्/-सु/-षु`` into verified nominal stems."""
  lookup = padanta_deva.replace("ँ", "ं")
  if lookup in _IRREGULAR_SURFACE_TO_STEM:
    st = _IRREGULAR_SURFACE_TO_STEM[lookup]
    return [SurfaceCandidate("nominal", st, 95, False, False, ss._deva_to_slp(st))]

  # Candidate stem endings from Pāṇinian padānta phonology before bh/su
  raw_cands: list[str] = [lookup]
  if lookup.endswith("ः"):
    base = lookup[:-1]
    raw_cands = [base + "स्", base + "र्", base + "ः", base]
  elif lookup.endswith(("क्", "ग्")):
    base = lookup[:-2]
    raw_cands = [base + "च्", base + "ज्", base + "श्", base + "भ्", base + "प्", lookup]
  elif lookup.endswith(("ट्", "ड्")):
    base = lookup[:-2]
    raw_cands = [base + "ष्", base + "ज्", base + "श्", lookup]
  elif lookup.endswith("त्"):
    raw_cands = [lookup, lookup[:-2] + "द्", lookup[:-2] + "न्त्"]
  elif lookup.endswith("न्"):
    raw_cands = [lookup, lookup[:-2]]

  # Verify against Kosha by testing stem+BiH / stem+am / stem+e / stem+aH
  slp_base = ss._deva_to_slp(lookup)
  verified: list[SurfaceCandidate] = []
  for rc in raw_cands:
    rc_slp = ss._deva_to_slp(rc)
    # Test inflected form matching stem
    probes = [
        rc_slp + "BiH", rc_slp + "am", rc_slp + "aH", rc_slp + "i", rc_slp + "su",
        slp_base + "BiH",
    ]
    for pb in probes:
      for v in _slp_variants(pb):
        for e in kosha.get(v):
          if isinstance(e, PadaEntry.Subanta) and isinstance(e.pratipadika_entry, PratipadikaEntry.Basic):
            pe_txt = e.pratipadika_entry.pratipadika.text
            # Check pe_txt matches rc_slp closely
            if pe_txt == rc_slp or (len(rc_slp) >= 2 and pe_txt.startswith(rc_slp[:-1])):
              st_deva = sanscript.transliterate(pe_txt, sanscript.SLP1, sanscript.DEVANAGARI)
              # Restore candrabindu if padanta had ँ
              st_deva = _restore_candrabindu(padanta_deva, st_deva)
              verified.append(SurfaceCandidate("nominal", st_deva, 85, False, False, pe_txt))
              return verified

  # Fallback: use reconstructed canonical consonant/vowel stem (e.g. अङ्गिरस् from अङ्गिरः, मुच् from मुक्)
  chosen = raw_cands[0]
  if chosen.endswith("ः"):
    chosen = chosen[:-1] + "स्"
  chosen = _restore_candrabindu(padanta_deva, chosen)
  return [SurfaceCandidate("nominal", chosen, 60, False, False, ss._deva_to_slp(chosen))]


def _restore_candrabindu(orig_deva: str, resolved_stem_deva: str) -> str:
  """Keep authentic ``ँ`` in a resolved Devanagari stem when the corpus form carried ``ँ``."""
  if "ँ" not in orig_deva or "ं" not in resolved_stem_deva:
    return resolved_stem_deva
  # Match character prefix with ँ <-> ं equivalence
  out = list(resolved_stem_deva)
  for i, ch in enumerate(orig_deva):
    if i >= len(out):
      break
    if ch == "ँ" and out[i] == "ं":
      out[i] = "ँ"
    elif ch != out[i] and ch != "ं":
      break
  return "".join(out)


class MorphResolver:
  """Two-pass morphological analyzer & disambiguator using Vidyut Kosha + Vedaweb prior."""

  def __init__(self, vedaweb_prior: dict[str, VedawebEntry] | None = None):
    self.kosha: Kosha = ss.get_vidyut_kosha()
    self.vedaweb = vedaweb_prior or {}
    self.stem_support: Counter[str] = Counter()
    self.dhatu_support: Counter[str] = Counter()
    self._cand_cache: dict[tuple[str, bool], list[SurfaceCandidate]] = {}

  def _candidates_for_word(self, bare_deva: str, *, allow_tinanta: bool = True) -> list[SurfaceCandidate]:
    """Enumerate ranked structural candidates for one bare Devanagari word."""
    key = (bare_deva, allow_tinanta)
    if key in self._cand_cache:
      return self._cand_cache[key]

    norm_deva = bare_deva.replace("ँ", "ं")
    cands: list[SurfaceCandidate] = []

    # 1. Closed-class avyayas
    if norm_deva in _KNOWN_AVYAYAS:
      cands.append(SurfaceCandidate("avyaya", _restore_candrabindu(bare_deva, norm_deva), 110, False, False, ss._deva_to_slp(norm_deva)))
      if norm_deva not in ("ते", "मे", "नः", "वः", "त्वम्", "तव", "किम्", "न"):
        self._cand_cache[key] = cands
        return cands

    # 2. Irregular pronominals & core nouns
    if norm_deva in _IRREGULAR_SURFACE_TO_STEM:
      st = _IRREGULAR_SURFACE_TO_STEM[norm_deva]
      # Exceptions where irregular pronoun collides with common verb (e.g. कत्, स, मे, ते)
      cands.append(SurfaceCandidate("nominal", st, 105, False, False, ss._deva_to_slp(st)))

    slp_orig = ss._deva_to_slp(norm_deva)
    probes = _slp_variants(slp_orig)
    entries = self._query_kosha_entries(probes)
    alias_used = False
    if not entries:
      alias_probes: list[str] = []
      for al in _vedic_alias_slps(slp_orig):
        alias_probes.extend(_slp_variants(al))
      if alias_probes:
        entries = self._query_kosha_entries(alias_probes)
        alias_used = bool(entries)

    if entries:
      tier_pen = 5 if alias_used else 0
      # Separate Subanta-Basic, Subanta-Krdanta, Tinanta
      by_stem: dict[tuple[str, str], dict] = {}
      by_dhatu: dict[str, list[PadaEntry.Tinanta]] = defaultdict(list)

      for e in entries:
        if isinstance(e, PadaEntry.Subanta):
          pe = e.pratipadika_entry
          if isinstance(pe, PratipadikaEntry.Basic):
            p_obj = pe.pratipadika
            p_slp = p_obj.text
            # Distinguish avyayas (`lingas=[]` and invariant) vs declinable prātipadikas
            is_avy = bool(getattr(p_obj, "is_avyaya", False)) or (len(pe.lingas) == 0 and p_slp == slp_orig)
            pos = "avyaya" if is_avy else "nominal"
            is_true_neuter_sg_nom = (
                Linga.Napumsaka in pe.lingas
                and e.linga == Linga.Napumsaka
                and e.vacana == Vacana.Eka
                and e.vibhakti in (Vibhakti.Prathama, Vibhakti.Dvitiya)
            )
            vib_voc = False if is_avy else (e.vibhakti == Vibhakti.Sambodhana)
            linga_match = (not pe.lingas) or (e.linga in pe.lingas)
            tier = (92 if linga_match else 82) - tier_pen
            if p_slp == slp_orig and len(pe.lingas) > 0 and e.vibhakti != Vibhakti.Prathama and not p_slp.endswith(("s", "r", "t", "d", "n")):
              tier -= 4
            k_st = (pos, p_slp)
            slot = by_stem.setdefault(k_st, {"tier": tier, "vocs": [], "neuter_sg": False, "has_core_case": False})
            slot["tier"] = max(slot["tier"], tier)
            slot["vocs"].append(vib_voc)
            if is_true_neuter_sg_nom:
              slot["neuter_sg"] = True
            if linga_match and e.vibhakti not in (Vibhakti.Saptami, Vibhakti.Sambodhana):
              slot["has_core_case"] = True
          elif isinstance(pe, PratipadikaEntry.Krdanta):
            k_str = str(pe.krt)
            vib_voc = (e.vibhakti == Vibhakti.Sambodhana)
            if k_str in ("ktvA", "tumun", "lyap"):
              k_st = ("avyaya", slp_orig)
              slot = by_stem.setdefault(k_st, {"tier": 88 - tier_pen, "vocs": [], "neuter_sg": False, "has_core_case": True})
              slot["vocs"].append(False)
            elif k_str in _PRODUCTIVE_KRTS:
              derived = _derive_krdanta_stems(pe.dhatu_entry, pe.krt)
              picked = _match_derived_krdanta_stem(slp_orig, derived)
              if picked:
                k_st = ("nominal", picked)
                tier = 78 - tier_pen
                slot = by_stem.setdefault(k_st, {"tier": tier, "vocs": [], "neuter_sg": False, "has_core_case": False})
                slot["tier"] = max(slot["tier"], tier)
                slot["vocs"].append(vib_voc)
                if e.vibhakti not in (Vibhakti.Saptami, Vibhakti.Sambodhana):
                  slot["has_core_case"] = True
        elif isinstance(e, PadaEntry.Tinanta) and allow_tinanta:
          by_dhatu[e.dhatu_entry.clean_text].append(e)

      has_lat_tinanta = any(
          t.lakara == Lakara.Lat for tl in by_dhatu.values() for t in tl
      )
      for (pos, st_slp), info in by_stem.items():
        st_deva = sanscript.transliterate(st_slp, sanscript.SLP1, sanscript.DEVANAGARI)
        st_deva = _restore_candrabindu(bare_deva, st_deva)
        vocs = info["vocs"]
        is_neuter_sg = info.get("neuter_sg", False)
        adj_tier = info["tier"]
        # Finite -ati verbs (भवति, गच्छति, चरति, तिष्ठति) collide with loc.sg/voc of -at/-atI participles
        if has_lat_tinanta and pos == "nominal" and not info.get("has_core_case", False):
          adj_tier -= 18
        cands.append(SurfaceCandidate(
            pos=pos,
            stem_deva=st_deva,
            source_tier=adj_tier,
            can_be_voc=False if is_neuter_sg else any(vocs),
            only_voc=False if is_neuter_sg else (all(vocs) and pos != "avyaya"),
            stem_slp=st_slp,
        ))

      for d_slp, tin_list in by_dhatu.items():
        # Score non-imperative / non-lṛt / non-luṭ above unlikely imperative/perfect homographs
        good_lak = any(t.lakara in (Lakara.Lat, Lakara.Lan, Lakara.Lun, Lakara.VidhiLin, Lakara.Lit) for t in tin_list)
        d_deva = _dhatu_slp_to_deva(d_slp)
        tier = (83 if good_lak else 70) - tier_pen
        if len(d_deva) <= 1 and d_deva not in _COMMON_MONO_DHATUS:
          tier -= 12
        cands.append(SurfaceCandidate("tinanta", d_deva, tier, False, False, d_slp))

    # 3. Fallback if Vidyut found nothing
    if not cands:
      cands.extend(self._fallback_candidates(bare_deva, slp_orig, allow_tinanta=allow_tinanta))

    self._cand_cache[key] = cands
    return cands

  def _query_kosha_entries(self, probes: list[str]) -> list:
    out: list = []
    for p in probes:
      res = list(self.kosha.get(p))
      if res:
        out.extend(res)
    return out

  def _fallback_candidates(self, bare_deva: str, slp_orig: str, *, allow_tinanta: bool) -> list[SurfaceCandidate]:
    """Handle missing Vedic forms: nañ compounds, preverb-verbs, augment verbs, and suffix heuristics."""
    norm_deva = bare_deva.replace("ँ", "ं")
    cands: list[SurfaceCandidate] = []

    # 3a. Upasarga-prefixed verb (e.g., व्यसृजन्त -> सृज्)
    if allow_tinanta:
      up_rt = _peel_upasarga_tinanta(slp_orig, self.kosha)
      if up_rt:
        cands.append(SurfaceCandidate("tinanta", _dhatu_slp_to_deva(up_rt), 75, False, False, up_rt))

    # 3b. Unhyphenated nañ compound (e.g., अकॢप्तम् -> अ-कॢप्तम्) or augment finite verb (अ-करोत् / अ-गृभ्णन्)
    if slp_orig.startswith("an") and len(slp_orig) > 4 and slp_orig[2] in "aAiIuUfFxXeEoO":
      sub_deva = sanscript.transliterate(slp_orig[2:], sanscript.SLP1, sanscript.DEVANAGARI)
      sub = [c for c in self._candidates_for_word(sub_deva, allow_tinanta=False) if c.pos == "nominal"]
      if sub:
        st_sub = sub[0].stem_deva
        cands.append(SurfaceCandidate("nominal", "अन्" + st_sub, 68, sub[0].can_be_voc, sub[0].only_voc, "an" + sub[0].stem_slp))
    elif slp_orig.startswith("a") and len(slp_orig) > 3:
      rem_slp = slp_orig[1:]
      # Vedic bh<->h inside augment verbs (अगृभ्णन् -> गृह्णन् -> ग्रह्)
      if "gfB" in rem_slp:
        cands.append(SurfaceCandidate("tinanta", "ग्रह्", 72, False, False, "grah"))
      else:
        sub_deva = sanscript.transliterate(rem_slp, sanscript.SLP1, sanscript.DEVANAGARI)
        sub = self._candidates_for_word(sub_deva, allow_tinanta=True)
        for sc in sub:
          if sc.pos == "tinanta" and allow_tinanta:
            cands.append(SurfaceCandidate("tinanta", sc.stem_deva, 70, False, False, sc.stem_slp))
            break
          if sc.pos == "nominal":
            cands.append(SurfaceCandidate("nominal", "अ" + sc.stem_deva, 65, sc.can_be_voc, sc.only_voc, "a" + sc.stem_slp))
            break

    if cands:
      return cands

    # 3c. Suffix heuristic using doc_curation.sanskrit.accent.provenance._infer_candidate_stems-inspired nominal patterns
    stem_guess = _heuristic_nominal_stem(norm_deva)
    stem_guess = _restore_candrabindu(bare_deva, stem_guess)
    cands.append(SurfaceCandidate("nominal", stem_guess, 30, False, False, ss._deva_to_slp(stem_guess)))
    return cands

  def collect_corpus_support(self, normalized_items: Sequence[tuple[NormalizedPada, int]]) -> None:
    """Pass 1: accumulate corpus paradigm support for every stem & dhātu."""
    for npada, freq in normalized_items:
      hyph = npada.hyph_bare
      parts = hyph.split("-")
      if len(parts) >= 2 and parts[-1] in _SUP_COMPOUND_ENDS:
        target = parts[-2]
        for sc in _sup_padanta_to_stems(target, self.kosha):
          if not sc.only_voc:
            self.stem_support[sc.stem_deva] += freq
        continue
      target = parts[-1]
      cands = self._candidates_for_word(target, allow_tinanta=(len(parts) == 1 or target != parts[0]))
      for sc in cands:
        if sc.pos in ("nominal", "avyaya"):
          if not sc.only_voc and sc.source_tier >= 75:
            # Avoid counting single-form pseudo-Basic lemma==surface unless avyaya or corroborated later
            if sc.stem_slp != ss._deva_to_slp(target.replace("ँ", "ं")) or sc.pos == "avyaya":
              self.stem_support[sc.stem_deva] += freq
            else:
              # Record minor fractional support so real stems appearing identically (प्रजा) still register
              self.stem_support[sc.stem_deva] += min(freq, 1)
        elif sc.pos == "tinanta":
          self.dhatu_support[sc.stem_deva] += freq

  def resolve_word(self, npada: NormalizedPada) -> tuple[str, str, bool, bool]:
    """Pass 2: return ``(pos, stem_hyph_bare, can_be_voc, only_voc)`` for one NormalizedPada."""
    parts = npada.hyph_bare.split("-")
    norm_full = npada.clean_bare.replace("ँ", "ं")
    vw_full = self.vedaweb.get(norm_full)

    # Case 1: Padapāṭha trailing sup-suffix `-भिः/-भ्यः/-भ्याम्/-सु/-षु`
    if len(parts) >= 2 and parts[-1] in _SUP_COMPOUND_ENDS:
      stem_last = _sup_padanta_to_stems(parts[-2], self.kosha)[0].stem_deva
      prefix = "-".join(parts[:-2])
      stem_hyph = f"{prefix}-{stem_last}" if prefix else stem_last
      return "nominal", stem_hyph, False, False

    # Case 2: Hyphenated compound `p1-...-pk` (check if pk is a finite verb with preverb or nominal compound)
    if len(parts) >= 2:
      last = parts[-1]
      norm_last = last.replace("ँ", "ं")
      vw = vw_full or self.vedaweb.get(norm_last)
      # Almost all Padapāṭha hyphenated compounds are nominal/kṛdanta stems, except rare preverb-tiṅanta in AV/MS
      cands = self._candidates_for_word(last, allow_tinanta=(parts[0] in _KNOWN_AVYAYAS))
      chosen = self._pick_best_candidate(norm_last, cands, vw, is_compound_tail=True)
      if chosen.pos == "tinanta":
        # Group preverb-prefixed finite verbs under dhātu (or prefix-dhātu? keep canonical dhātu)
        return "tinanta", chosen.stem_deva, False, False
      prefix = "-".join(parts[:-1])
      return chosen.pos, f"{prefix}-{chosen.stem_deva}", chosen.can_be_voc, chosen.only_voc

    # Case 3: Unhyphenated single word
    cands = self._candidates_for_word(npada.clean_bare, allow_tinanta=True)
    chosen = self._pick_best_candidate(norm_full, cands, vw_full, is_compound_tail=False)
    return chosen.pos, chosen.stem_deva, chosen.can_be_voc, chosen.only_voc

  def _pick_best_candidate(
      self,
      norm_bare: str,
      cands: list[SurfaceCandidate],
      vw: VedawebEntry | None,
      *,
      is_compound_tail: bool,
  ) -> SurfaceCandidate:
    norm_slp = ss._deva_to_slp(norm_bare)

    def _score(c: SurfaceCandidate) -> float:
      s = float(c.source_tier)
      if c.pos in ("nominal", "avyaya"):
        sup = self.stem_support.get(c.stem_deva, 0)
        # Gentle log-bonus for multi-form corpus corroboration (breaks 'tena'/'nama'/'rAj' ties without swallowing 'pitryA')
        s += min(10.0, math.log1p(sup) * 2.0)
        # Penalize pseudo-Basic where stem_slp == surface AND there is zero oblique paradigm support
        if c.stem_slp == norm_slp and c.pos == "nominal" and sup <= 2:
          s -= 26.0
        # Penalize vocative-only gently so genuine vocative nouns (देव) still beat implausible lo~w verbs (दिव्)
        if c.only_voc:
          s -= 8.0
      else:
        dsup = self.dhatu_support.get(c.stem_deva, 0)
        s += min(10.0, math.log1p(dsup) * 1.5)
        if is_compound_tail:
          s -= 20.0

      # Apply Vedaweb annotation prior when present
      if vw is not None:
        if vw.pos == "root_verb":
          if c.pos == "tinanta":
            s += 45.0
            if vw.stems and c.stem_deva in vw.stems:
              s += 15.0
          else:
            s -= 35.0
        elif vw.pos in ("nominal", "pronoun", "root_participle"):
          if c.pos == "nominal":
            s += 30.0
          elif c.pos == "tinanta":
            s -= 30.0
        elif vw.pos == "invariable":
          if c.pos == "avyaya":
            s += 35.0
          elif c.pos == "tinanta":
            s -= 35.0
      return s

    best = max(cands, key=_score)
    # If Vedaweb clearly identifies a root_verb missed by Vidyut, emit dhātu cleanly
    if vw is not None and vw.pos == "root_verb" and best.pos != "tinanta" and vw.stems and not is_compound_tail:
      rt = vw.stems[0]
      return SurfaceCandidate("tinanta", rt, 85, False, False, ss._deva_to_slp(rt))
    return best


def _heuristic_nominal_stem(norm_deva: str) -> str:
  """Conservative Vedic suffix-stripping fallback when Vidyut & Vedaweb miss a compound noun."""
  if len(norm_deva) <= 3:
    return norm_deva
  slp = ss._deva_to_slp(norm_deva)
  slp_rules: tuple[tuple[str, str], ...] = (
      ("AnAm", "a"), ("InAm", "i"), ("UnAm", "u"), ("FnAm", "f"),
      ("eByaH", "a"), ("AByaH", "A"), ("iByaH", "i"), ("uByaH", "u"),
      ("AByAm", "a"), ("iByAm", "i"), ("uByAm", "u"),
      ("eBiH", "a"), ("ABiH", "A"), ("iBiH", "i"), ("uBiH", "u"),
      ("ezu", "a"), ("Asu", "A"), ("izu", "i"), ("uzu", "u"),
      ("AsaH", "a"), ("Aya", "a"), ("aye", "i"), ("asya", "a"), ("ena", "a"), ("eRa", "a"),
      ("EH", "a"), ("At", "a"), ("An", "a"), ("Ani", "a"),
      ("as", "as"), ("aH", "a"), ("am", "a"),
  )
  for suf, rep in slp_rules:
    if slp.endswith(suf) and len(slp) - len(suf) >= 2:
      cand_slp = slp[:-len(suf)] + rep
      return sanscript.transliterate(cand_slp, sanscript.SLP1, sanscript.DEVANAGARI)
  return norm_deva


def project_form_to_stem_marks(
    form_hyph: str,
    form_marks: tuple[str, ...],
    stem_hyph: str,
    *,
    had_sup_suffix: bool = False,
) -> tuple[str, ...]:
  """Project US accent marks from an inflected form onto its bare prātipadika stem.

  Handles:
  - Sarvānudātta -> returns all ``""`` marks of ``len(stem_hyph)``
  - Padapāṭha ``-भिः/-भ्यः/-भ्याम्/-सु/-षु`` suffix accent -> antodātta ``n_stem - 1``
  - Dual-accent compounds -> preserves accent in ``P1..P_{k-1}`` and projects ``Pk`` accent
  - Semivowel contraction (``पृथिव्याः᳙`` / ``पृथिव्या᳓म्`` -> ``पृथिवी᳓``, ``तन्वाः᳙`` -> ``तनू᳓``, ``पित्रा᳓`` -> ``पितृ᳓``)
  """
  stem_clean = stem_hyph.replace("-", "")
  stem_syls = ss._fast_scan_deva_syllables(stem_clean)
  n_stem = len(stem_syls)
  if n_stem == 0:
    return ()
  if not form_marks or all(m == "" for m in form_marks):
    return tuple("" for _ in range(n_stem))

  # Compound-level split if both form and stem preserve hyphenation
  f_parts = form_hyph.split("-")
  s_parts = stem_hyph.split("-")
  if had_sup_suffix and len(f_parts) >= 2:
    # Remove trailing sup suffix from form_hyph; project suffix accent to end of stem_last
    sup_len = ss._fast_syllable_count(f_parts[-1])
    stem_side_hyph = "-".join(f_parts[:-1])
    n_stem_side = len(form_marks) - sup_len
    remapped = list(form_marks[:n_stem_side])
    if any(m for m in form_marks[n_stem_side:]) and not any(m for m in remapped):
      if remapped:
        remapped[-1] = "U"
    return project_form_to_stem_marks(stem_side_hyph, tuple(remapped), stem_hyph, had_sup_suffix=False)

  if len(s_parts) >= 2 and len(f_parts) == len(s_parts):
    # Project each compound member offset-wise (last member uses tail rule, prior members copy verbatim)
    out: list[str] = []
    f_off = 0
    for idx in range(len(s_parts)):
      fn = ss._fast_syllable_count(f_parts[idx])
      sub_f_marks = form_marks[f_off:f_off + fn]
      f_off += fn
      if idx < len(s_parts) - 1:
        sn = ss._fast_syllable_count(s_parts[idx])
        sub_proj = list(sub_f_marks[:sn])
        while len(sub_proj) < sn:
          sub_proj.append("")
        out.extend(sub_proj)
      else:
        out.extend(project_form_to_stem_marks(f_parts[idx], sub_f_marks, s_parts[idx], had_sup_suffix=False))
    return tuple(out)

  # Single-member projection from form_bare -> stem_clean
  form_clean = form_hyph.replace("-", "")
  form_syls = ss._fast_scan_deva_syllables(form_clean)
  n_form = len(form_syls)
  out_marks = [""] * n_stem

  for acc_idx, mk in enumerate(form_marks):
    if not mk:
      continue
    # Check semivocalic / -ऋ collapse at the final accented syllable when n_form <= n_stem:
    # e.g. पृथिव्याः᳙ (n_form=2, S at 1) -> पृथिवी᳓ (n_stem=3); पृथिव्या᳓म् (n_form=2, U at 1) -> पृथिवी᳓ (n_stem=3);
    # तन्वाः᳙ / तन्वा᳓ (n_form=2, S/U at 1) -> तनू᳓ (n_stem=2); पित्रा᳓ (n_form=2, U at 1) -> पितृ᳓ (n_stem=2).
    is_final_glide = (
        acc_idx == n_form - 1
        and n_form >= 2
        and (
            form_syls[acc_idx][1]
            or stem_clean.endswith(("इ", "ई", "उ", "ऊ", "ऋ"))
            or any(c in form_syls[acc_idx][0] for c in ("य", "व", "र", "त्र", "ध्र", "भ्र"))
        )
        and (
            stem_clean.endswith(("ि", "ी", "ु", "ू", "ृ", "इ", "ई", "उ", "ऊ", "ऋ"))
            or n_form < n_stem
        )
    )
    if acc_idx >= n_stem or (is_final_glide and n_form < n_stem):
      out_marks[n_stem - 1] = "U"
    elif acc_idx == n_stem - 1 and mk == "S" and not stem_syls[acc_idx][1]:
      # Reversed jātya (तन्वाः᳙ -> तनू᳓, नद्याः᳙ -> नदी᳓) when stem lacks glide
      out_marks[acc_idx] = "U"
    else:
      # Preserve genuine jātya S on stem iff stem itself has a jātya glide at acc_idx!
      if mk == "S" and not stem_syls[acc_idx][1]:
        out_marks[acc_idx] = "U"
      else:
        out_marks[acc_idx] = mk

  return tuple(out_marks)


def _format_citations(loci: Iterable[str], max_citations: int | None = 40) -> str:
  """Deduplicate and format corpus citations compactly for Babylon HTML definitions."""
  uniq = list(dict.fromkeys(l for l in loci if l))
  if not uniq:
    return ""
  if max_citations is not None and len(uniq) > max_citations:
    return ", ".join(uniq[:max_citations]) + f", … (+{len(uniq) - max_citations})"
  return ", ".join(uniq)


def build_stem_headwords(
    bare_stem: str,
    extras: set[str] | None = None,
    *,
    include_optitrans: bool = False,
) -> tuple[str, ...]:
  """Build deduplicated lookup headwords for bare stems / dhātus without chopping stem endings."""
  raw_hws: list[str] = []
  no_hyphen = bare_stem.replace("-", "")
  if no_hyphen:
    raw_hws.append(no_hyphen)
  sandhi_joined = taittiriya._join_compound_sandhi(bare_stem) if "-" in bare_stem else ""
  if sandhi_joined and sandhi_joined not in raw_hws:
    raw_hws.append(sandhi_joined)
  if bare_stem not in raw_hws:
    raw_hws.append(bare_stem)
  if extras:
    for ex in sorted(extras):
      if ex and ex not in raw_hws:
        raw_hws.append(ex)

  expanded: list[str] = []
  for hw in raw_hws:
    expanded.append(hw)
    if "ँ" in hw:
      expanded.append(hw.replace("ँ", "ं"))

  if include_optitrans:
    with_rom: list[str] = []
    for hw in expanded:
      with_rom.append(hw)
      rom = sanscript.transliterate(hw, sanscript.DEVANAGARI, sanscript.OPTITRANS)
      if rom and rom != hw:
        with_rom.append(rom)
    expanded = with_rom

  return tuple(dict.fromkeys(h for h in expanded if h))


@dataclass
class _StemVariantObs:
  """Mutable accumulator for one accented prātipadika realization."""

  nonvoc_freq: int = 0
  ambig_voc_freq: int = 0
  onlyvoc_freq: int = 0
  loci_nonvoc: list[str] | None = None
  loci_voc: list[str] | None = None

  def __post_init__(self) -> None:
    if self.loci_nonvoc is None:
      self.loci_nonvoc = []
    if self.loci_voc is None:
      self.loci_voc = []


def _strip_enclitic_iva(npada: NormalizedPada) -> NormalizedPada:
  """Peel padapāṭha-joined enclitic ``-इव`` so inflected nouns resolve to their stem."""
  parts = npada.hyph_bare.split("-")
  if len(parts) < 2 or parts[-1] != "इव" or len(npada.marks) <= 2:
    return npada
  if npada.marks[-2:] != ("", ""):
    return npada
  prefix_hyph = "-".join(parts[:-1])
  if not prefix_hyph:
    return npada
  prefix_marks = npada.marks[:-2]
  return NormalizedPada(
      us_form=_apply_us_marks_to_hyph(prefix_hyph, prefix_marks),
      hyph_bare=prefix_hyph,
      clean_bare=prefix_hyph.replace("-", ""),
      marks=prefix_marks,
      is_unaccented=all(m == "" for m in prefix_marks),
  )


def generate_prakrti_definitions(
    raw_entries: Sequence[tuple[str, int, tuple[str, ...]]],
    *,
    already_us: bool,
    vedaweb_prior: dict[str, VedawebEntry] | None = None,
    resolver: MorphResolver | None = None,
    max_citations: int | None = 40,
) -> tuple[list[Definition], list[Definition], dict[str, int]]:
  """Convert normalized padasvara entries into Devanagari and OPTITRANS Babylon ``Definition`` lists."""
  normalized: list[tuple[NormalizedPada, int, tuple[str, ...]]] = []
  dropped_normalize = 0
  for raw_form, freq, loci in raw_entries:
    npada = normalize_raw_form_to_us(raw_form, already_us=already_us)
    if npada is None:
      dropped_normalize += 1
      continue
    normalized.append((_strip_enclitic_iva(npada), freq, loci))

  if resolver is None:
    resolver = MorphResolver(vedaweb_prior=vedaweb_prior)
  resolver.collect_corpus_support([(n, f) for n, f, _ in normalized])

  # Nominal/Avyaya buckets:
  # stem_key (normalized bare) -> {sasvara_stem -> _StemVariantObs}
  nom_obs: dict[str, dict[str, _StemVariantObs]] = defaultdict(dict)
  nom_unacc_only: dict[str, Counter[str]] = defaultdict(Counter)
  nom_unacc_loci: dict[str, list[str]] = defaultdict(list)
  nom_extras: dict[str, set[str]] = defaultdict(set)

  # Dhātu buckets:
  # dhatu_bare -> {us_form -> freq}, dhatu_bare -> loci
  dhatu_forms: dict[str, Counter[str]] = defaultdict(Counter)
  dhatu_unacc_forms: dict[str, Counter[str]] = defaultdict(Counter)
  dhatu_loci: dict[str, list[str]] = defaultdict(list)

  pos_counts = Counter()
  for npada, freq, loci in normalized:
    pos, stem_hyph, can_be_voc, only_voc = resolver.resolve_word(npada)
    pos_counts[pos] += 1

    if pos == "tinanta":
      dhatu_forms_bucket = dhatu_unacc_forms if npada.is_unaccented else dhatu_forms
      dhatu_forms_bucket[stem_hyph][npada.us_form] += freq
      dhatu_loci[stem_hyph].extend(loci)
      continue

    parts = npada.hyph_bare.split("-")
    had_sup = len(parts) >= 2 and parts[-1] in _SUP_COMPOUND_ENDS
    stem_bare_nohyph = stem_hyph.replace("-", "")
    if had_sup and len(parts) >= 2:
      # Collect pre-sandhi joined compound alias like अँहोमुच् if any
      nom_extras[stem_bare_nohyph.replace("ँ", "ं")].add(stem_hyph.replace("-", ""))

    stem_marks = project_form_to_stem_marks(
        npada.hyph_bare, npada.marks, stem_hyph, had_sup_suffix=had_sup
    )
    sasvara_stem = _apply_us_marks_to_hyph(stem_hyph, stem_marks)
    stem_group_key = stem_bare_nohyph.replace("ँ", "ं")

    if npada.is_unaccented or (all(m == "" for m in npada.marks) and pos != "avyaya"):
      # Sarvānudātta / unaccented token: do not let it add a fake unaccented stem over accented tokens
      nom_unacc_only[stem_group_key][stem_hyph] += freq
      nom_unacc_loci[stem_group_key].extend(loci)
      continue

    if pos == "avyaya":
      can_be_voc = False
      only_voc = False

    # Sarvānudātta genuinely unaccented enclitic avyayas (e.g. च, वा, इव, स्म)
    if all(m == "" for m in stem_marks) and pos == "avyaya":
      can_be_voc = False
      only_voc = False

    slot = nom_obs[stem_group_key].get(sasvara_stem)
    if slot is None:
      slot = _StemVariantObs()
      nom_obs[stem_group_key][sasvara_stem] = slot

    if only_voc:
      slot.onlyvoc_freq += freq
      slot.loci_voc.extend(loci)
    elif can_be_voc:
      slot.ambig_voc_freq += freq
      slot.loci_nonvoc.extend(loci)
    else:
      slot.nonvoc_freq += freq
      slot.loci_nonvoc.extend(loci)

  defs_dev: list[Definition] = []
  defs_final: list[Definition] = []

  # 1. Emit Nominal Prātipadikas & Avyayas (applying 3-bucket vocative guard)
  all_stem_keys = sorted(set(nom_obs.keys()) | set(nom_unacc_only.keys()))
  for key in all_stem_keys:
    variants_map = nom_obs.get(key)
    emitted: list[tuple[str, int, str, str]] = []  # (sasvara_stem, freq, tag, loci_str)
    if variants_map:
      has_pure_nonvoc = any(v.nonvoc_freq > 0 for v in variants_map.values())
      has_any_non_onlyvoc = any((v.nonvoc_freq + v.ambig_voc_freq) > 0 for v in variants_map.values())

      if has_any_non_onlyvoc:
        max_nonvoc_freq = max((v.nonvoc_freq for v in variants_map.values()), default=0)
        unacc_encl_freq = (
            (variants_map[key].nonvoc_freq if key in variants_map else 0)
            + sum(nom_unacc_only[key].values())
        ) if key in _ENCLITIC_PARTICLES else 0
        for sas_stem, obs in variants_map.items():
          # Guard Bucket B vocative pollution: if pure nonvoc variants exist (with >=2x weight) and THIS variant
          # ONLY got ambig_voc evidence with initial accent acc_idx=0 while pure nonvoc has non-0 accent -> suppress!
          if (
              has_pure_nonvoc
              and obs.nonvoc_freq == 0
              and obs.ambig_voc_freq > 0
              and max_nonvoc_freq >= 2 * obs.ambig_voc_freq
          ):
            syl_m = [
                (US_UDATTA in mks or US_SVARITA in mks)
                for mks, _ in ss._fast_scan_deva_syllables(sas_stem.replace("-", ""))
            ]
            non0_nonvoc_exists = any(
                v.nonvoc_freq > 0 and any(
                    (US_UDATTA in mks or US_SVARITA in mks)
                    for idx, (mks, _) in enumerate(ss._fast_scan_deva_syllables(st.replace("-", "")))
                    if idx > 0
                )
                for st, v in variants_map.items()
            )
            if len(syl_m) >= 2 and syl_m[0] and non0_nonvoc_exists:
              continue
          tot = obs.nonvoc_freq + obs.ambig_voc_freq
          if key in _ENCLITIC_PARTICLES and (US_UDATTA in sas_stem or US_SVARITA in sas_stem) and unacc_encl_freq >= 5 * max(tot, 1):
            continue
          if tot > 0:
            emitted.append((sas_stem, tot, "", _format_citations(obs.loci_nonvoc, max_citations)))
      if not emitted:
        # Bucket C: Vocative-only fallback
        for sas_stem, obs in variants_map.items():
          if obs.onlyvoc_freq > 0:
            emitted.append((sas_stem, obs.onlyvoc_freq, " [सम्बोधनमात्रम्]", _format_citations(obs.loci_voc, max_citations)))
    elif key in nom_unacc_only:
      best_unacc, u_freq = nom_unacc_only[key].most_common(1)[0]
      emitted.append((best_unacc, u_freq, " [अनुदात्त/अस्वरित]", _format_citations(nom_unacc_loci[key], max_citations)))

    if not emitted:
      continue
    emitted.sort(key=lambda x: (-x[1], x[0]))
    canonical_bare = _strip_all_accents(emitted[0][0])
    extras = nom_extras.get(key)
    hws_dev = build_stem_headwords(canonical_bare, extras, include_optitrans=False)
    hws_final = build_stem_headwords(canonical_bare, extras, include_optitrans=True)

    for sas_stem, freq, tag, loci_str in emitted:
      meaning = f"{sas_stem}{tag} ({freq})<br>{loci_str}" if loci_str else f"{sas_stem}{tag} ({freq})"
      defs_dev.append(Definition(headwords_tuple=hws_dev, meaning=meaning))
      defs_final.append(Definition(headwords_tuple=hws_final, meaning=meaning))

  # 2. Emit Dhātus with attested accented finite forms & frequencies
  for dhatu in sorted(set(dhatu_forms.keys()) | set(dhatu_unacc_forms.keys())):
    merged_cnts = Counter(dhatu_forms.get(dhatu, Counter()))
    merged_cnts.update(dhatu_unacc_forms.get(dhatu, Counter()))
    # Always show explicitly accented (U/S) finite/augment forms first, then sarvānudātta/unaccented forms
    combined = sorted(
        merged_cnts.items(),
        key=lambda x: (0 if (US_UDATTA in x[0] or US_SVARITA in x[0]) else 1, -x[1], x[0]),
    )
    total_freq = sum(c for _, c in combined)
    forms_str = " · ".join(f"{form} ({cnt})" for form, cnt in combined)
    loci_str = _format_citations(dhatu_loci[dhatu], max_citations)
    meaning = f"{dhatu} [धातुः] ({total_freq})<br>{forms_str}"
    if loci_str:
      meaning += f"<br>{loci_str}"

    hws_dev = build_stem_headwords(dhatu, include_optitrans=False)
    hws_final = build_stem_headwords(dhatu, include_optitrans=True)
    defs_dev.append(Definition(headwords_tuple=hws_dev, meaning=meaning))
    defs_final.append(Definition(headwords_tuple=hws_final, meaning=meaning))

  stats = {
      "input_entries": len(raw_entries),
      "normalized": len(normalized),
      "dropped_normalize": dropped_normalize,
      "nominals": pos_counts["nominal"],
      "avyayas": pos_counts["avyaya"],
      "tinantas": pos_counts["tinanta"],
      "emitted_defs": len(defs_dev),
      "emitted_nominals": sum(1 for d in defs_dev if "[धातुः]" not in d.meaning),
      "emitted_dhatus": sum(1 for d in defs_dev if "[धातुः]" in d.meaning),
  }
  return defs_dev, defs_final, stats


def build_single_prakrti_svara(
    spec: VedaDictSpec,
    *,
    primary_root: str = PRIMARY_KAVYA_ROOT,
    mirror_roots: Sequence[str] = DEFAULT_MIRROR_ROOTS,
    vedaweb_prior: dict[str, VedawebEntry] | None = None,
    write_final: bool = False,
) -> dict[str, int]:
  """Build one prakṛti-svara dictionary (``.babylon`` and ``README.md``) across mirror dirs."""
  src_bab = os.path.join(primary_root, spec.source_name, f"{spec.source_name}.babylon")
  raw_entries = load_padasvara_entries(src_bab)
  defs_dev, defs_final, stats = generate_prakrti_definitions(
      raw_entries,
      already_us=spec.already_us,
      vedaweb_prior=vedaweb_prior,
  )

  headers = {
      "bookname": f"{spec.dest_name} (sa-sa)",
      "sametypesequence": "h",
      "stripmethod": "keep",
  }
  readme_text = (
      f"## {spec.dest_name}\n"
      f"- {spec.description}.\n"
      f"- Derived from `{spec.source_name}` using `dict_curation_projects.conversion.babylon.dict_specific.veda.prakrti_svara`.\n"
      f"- Nominal prātipadikas and avyayas exclude vocative/sarvānudātta pollution from shifting genuine stem accent.\n"
      f"- Verbal dhātus list attested accented finite/augment forms and corpus frequencies.\n"
  )

  for root in mirror_roots:
    dest_dir = os.path.join(root, spec.dest_name)
    assert_writable_dict_dest(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    bab_path = os.path.join(dest_dir, f"{spec.dest_name}.babylon")
    babylon.dump(dest_path=bab_path, definitions=defs_dev, headers=dict(headers))
    if write_final:
      final_path = os.path.join(dest_dir, f"{spec.dest_name}.babylon_final")
      babylon.dump(dest_path=final_path, definitions=defs_final, headers=dict(headers))
    Path(os.path.join(dest_dir, "README.md")).write_text(readme_text, encoding="utf-8")
    logging.info("Wrote %s (%d entries) in %s", spec.dest_name, len(defs_dev), dest_dir)

  return stats


def build_all_prakrti_svara(
    keys: Sequence[str] | None = None,
    *,
    primary_root: str = PRIMARY_KAVYA_ROOT,
    mirror_roots: Sequence[str] = DEFAULT_MIRROR_ROOTS,
) -> dict[str, dict[str, int]]:
  """Build all selected Vedic prakṛti-svara dictionaries sharing the Vedaweb prior cache."""
  vedaweb_prior = load_vedaweb_prior(VEDAWEB_RK_DIR)
  selected = {k.lower() for k in keys} if keys else {s.key for s in VEDA_SPECS}
  all_stats: dict[str, dict[str, int]] = {}
  for spec in VEDA_SPECS:
    if spec.key not in selected:
      continue
    st = build_single_prakrti_svara(
        spec,
        primary_root=primary_root,
        mirror_roots=mirror_roots,
        vedaweb_prior=vedaweb_prior,
    )
    all_stats[spec.dest_name] = st
    print(f"{spec.dest_name}: {st}")
  return all_stats


if __name__ == "__main__":
  import sys

  logging.basicConfig(level=logging.INFO)
  req_keys = [a for a in sys.argv[1:] if a != "all"] or None
  build_all_prakrti_svara(req_keys)
