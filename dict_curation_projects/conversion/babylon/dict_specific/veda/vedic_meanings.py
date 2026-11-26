"""Extract brief contextual Sanskrit, English, and fallback Hindi meanings for Vedic svara dictionaries.

Every emitted meaning is grounded strictly in the corpus's own accompanying
translations and commentaries (expanding ``<js-include>`` blocks where used).
Local ``sa-en`` Babylon dictionaries are used solely as alignment anchors and
corroborators against the corpus's accompanying English translations—never as
unverified standalone dictionary dumps.
"""

from __future__ import annotations

import glob
import logging
import os
import pickle
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from indic_transliteration import sanscript
from vidyut.kosha import PadaEntry

from doc_curation.sanskrit.accent import provenance as accent_prov
from doc_curation.sanskrit.accent import shatapatha_solver as ss
from dict_curation_projects.conversion.babylon.dict_specific.veda import (
    padasvara_common,
    prakrti_svara,
)

LOGGER = logging.getLogger(__name__)

_CACHE_DIR = os.path.expanduser("~/.cache/dict_curation")
_LEX_CACHE_PATH = os.path.join(_CACHE_DIR, "vedic_en_lexicon_v5.pkl")
_ANNOT_RE = re.compile(r"\[\[[^|\]]*\|([^|\]]+)\]\]")
_NORM_CACHE: dict[str, str] = {}
_US_CACHE: dict[str, str] = {}
_DEITY_NOUNS: frozenset[str] = frozenset({
    "agni", "indra", "soma", "rudra", "varuna", "mitra", "surya", "vayu",
    "yama", "brihaspati", "savitar", "pushan", "ashvins", "maruts", "vishnu",
    "prajapati", "brahma", "sarasvati", "ushas", "aditi", "aryaman", "bhaga",
})

_LEX_SOURCES: tuple[tuple[str, int], ...] = (
    ("macdonell/macdonell.babylon", 16),
    ("lanman/lanman.babylon", 16),
    ("whitney-roots/whitney-roots.babylon", 10),
    ("capeller-sanskrit-english/capeller-sanskrit-english.babylon", 16),
    ("mw-cologne/mw-cologne.babylon", 10),
)
_SA_EN_DIR = "/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit/sa-head/en-entries"

# Words too generic/grammatical to serve as alignment targets or brief glosses.
STOP_EN: frozenset[str] = frozenset({
    "a", "an", "the", "of", "to", "in", "for", "by", "with", "from", "at", "on",
    "into", "unto", "upon", "through", "over", "under", "about", "after", "before",
    "between", "among", "against", "and", "or", "but", "nor", "if", "as", "so",
    "that", "this", "these", "those", "which", "who", "whom", "whose", "what",
    "when", "where", "how", "why", "than", "then", "thus", "there", "here", "he",
    "she", "it", "they", "we", "you", "ye", "thou", "thee", "thy", "thine", "i",
    "me", "my", "mine", "us", "our", "him", "his", "her", "its", "their", "them",
    "himself", "itself", "myself", "yourself", "themselves", "is", "are", "was",
    "were", "be", "been", "being", "am", "art", "have", "has", "had", "do", "does",
    "did", "will", "would", "shall", "should", "may", "might", "can", "could",
    "must", "let", "hath", "doth", "verily", "indeed", "also", "even", "now",
    "all", "one", "two", "not", "no", "o", "oh", "yea", "etc", "viz", "esp", "cf",
    "fr", "lit", "fig", "prob", "comp", "dat", "gen", "acc", "nom", "voc", "loc",
    "ins", "abl", "sg", "du", "pl", "m", "f", "n", "ind", "cl", "pr", "pf", "aor",
    "fut", "pass", "caus", "des", "int", "p", "pp", "ved", "rv", "av", "ts", "vs",
    "ms", "ks", "sbr", "tb", "mbh", "ram", "bhag", "manu", "pan", "comm", "schol",
    "accord", "word", "form", "sense", "meaning", "name", "epithet", "applied",
    "used", "called", "mfn", "mf", "fn", "ib", "ifc", "vpr", "cs", "desid",
    "intens", "pot", "impf", "ipv", "subj", "inf", "ger", "part", "prep", "adv",
    "conj", "interj", "pron", "num", "neg", "px", "dim", "superl", "compar",
    "denom", "onomat", "perf", "pres", "impers", "intr", "tr", "trans", "act",
    "mid", "atm", "par", "se", "met", "opp", "syn", "sc", "q", "v", "w", "lc",
    "ab", "ac", "d", "g", "l", "scil", "eg", "ie", "generalized", "see", "note",
    "notes", "compare", "another", "something", "someone", "person", "anything",
    "thing", "things", "way", "manner", "state", "condition", "action", "having",
    "possessing", "belonging", "relating", "made", "like", "being", "self", "some",
    "any", "such", "other", "more", "most", "own", "same", "only", "just", "very",
    "much", "many", "both", "either", "neither", "each", "every", "therefore",
    "however", "whereas", "because", "since", "while", "thereby", "herein",
    "therein", "thereof", "said", "make", "makes", "become", "becomes",
    "one's", "ones", "na", "others", "down", "up", "off", "out", "away",
    "forth", "back",
})

_NON_CLOSED_SINGLE_STOP: frozenset[str] = frozenset({
    "down", "up", "off", "out", "away", "forth", "back", "na", "others",
    "one's", "ones",
})

_BAD_GLOSS_SUBS: tuple[str, ...] = (
    "plumbago", "[word]", "bot.", "cautery", "medical", "name of", "n. of",
    "q.v.", "see ", "cf.", "gram.", "dimin.",
)

# Accent-sensitive closed-class words (exact US form -> candidate English glosses).
CLOSED_US_EN: dict[str, tuple[str, ...]] = {
    "मा᳓": ("not", "do not"),
    "मा": ("me",),
    "ते᳓": ("they", "those"),
    "ते": ("thee", "thy", "to thee"),
    "मे": ("me", "my", "to me"),
    "मे᳓": ("my", "me"),
    "नः": ("us", "our"),
    "वः": ("you", "your"),
    "वा": ("or",),
    "वा᳓": ("verily", "or"),
    "वै᳓": ("verily", "indeed"),
    "वै": ("verily", "indeed"),
    "न᳓": ("not", "like"),
    "न": ("not",),
    "त्वा": ("thee", "you"),
    "त्वा᳓": ("thee", "you"),
    "त्वा᳓म्": ("thee", "you"),
    "इ᳓ति": ("thus",),
    "इति": ("thus",),
    "इव": ("like", "as", "as it were"),
    "च": ("and",),
    "हि": ("for", "indeed", "verily"),
    "हि᳓": ("for", "indeed", "verily"),
    "उ": ("indeed", "also", "and"),
    "ह": ("verily", "indeed"),
    "ह᳓": ("verily", "indeed"),
    "एव᳓": ("verily", "just", "only"),
    "ए᳓व": ("verily", "just", "only"),
    "अ᳓थ": ("then", "now"),
    "अ᳓थो": ("then", "moreover", "also"),
    "अध᳓": ("then", "now"),
    "स्वः᳓": ("heaven", "sun", "light"),
    "स्व᳓र्": ("heaven", "light"),
    "स्वा᳓हा": ("svāhā", "hail"),
    "न᳓मः": ("homage", "obeisance", "reverence"),
    "व᳓षट्": ("vaṣaṭ",),
}

# Bare/stem-level closed-class English priors (matched only when attested in translation).
CLOSED_BARE_EN: dict[str, tuple[str, ...]] = {
    "च": ("and",),
    "वा": ("or",),
    "इव": ("like", "as"),
    "न": ("not",),
    "हि": ("for", "indeed"),
    "वै": ("verily", "indeed"),
    "उ": ("indeed", "also"),
    "ह": ("verily",),
    "इति": ("thus",),
    "एव": ("verily", "just", "only"),
    "अथ": ("then", "now"),
    "अथो": ("then", "moreover"),
    "अध": ("then", "now"),
    "त्वा": ("thee", "you"),
    "त्वाम्": ("thee", "you"),
    "ते": ("thee", "thy", "they"),
    "मे": ("me", "my"),
    "नः": ("us", "our"),
    "वः": ("you", "your"),
    "असि": ("art", "are"),
    "अस्मि": ("am",),
    "अस्ति": ("is",),
    "स्थ": ("are", "ye are"),
    "सः": ("he", "that"),
    "सा": ("she", "that"),
    "तत्": ("that", "it", "therefore"),
    "तम्": ("him", "that"),
    "ताम्": ("her", "that"),
    "तेन": ("by that", "thereby", "therefore"),
    "यत्": ("which", "that", "when"),
    "यः": ("who", "which"),
    "या": ("who", "which"),
    "ये": ("who", "which"),
    "अयम्": ("this",),
    "इयम्": ("this",),
    "इदम्": ("this",),
    "एषः": ("this",),
    "एतत्": ("this",),
    "अस्य": ("of this", "his"),
    "अस्मै": ("to this", "for him"),
    "अस्मिन्": ("in this",),
    "ताः": ("they", "those"),
    "तानि": ("those", "they"),
    "अहम्": ("I",),
    "वयम्": ("we",),
    "त्वम्": ("thou", "you"),
    "यूयम्": ("ye", "you"),
    "कः": ("who",),
    "किम्": ("what",),
    "यत्र": ("where",),
    "तत्र": ("there",),
    "यथा": ("as",),
    "तथा": ("so", "thus"),
    "यदा": ("when",),
    "तदा": ("then",),
    "इह": ("here",),
    "अद्य": ("today",),
    "श्वः": ("tomorrow",),
    "पुनः": ("again",),
    "सह": ("with", "together with"),
    "अनु": ("after", "along"),
    "प्र": ("forth", "forward"),
    "आ": ("to", "hither", "from"),
    "उप": ("unto", "near", "by"),
    "अभि": ("towards", "unto", "over"),
    "परि": ("around", "about"),
    "प्रति": ("towards", "against"),
    "वि": ("apart", "away"),
    "सम्": ("together", "with"),
    "नि": ("down", "in"),
    "उत्": ("up", "forth"),
    "अधि": ("over", "upon", "above"),
    "अव": ("down", "off"),
    "अप": ("away", "off"),
    "अति": ("beyond", "over"),
    "सु": ("well", "good"),
    "स्वाहा": ("svāhā", "hail"),
    "वषट्": ("vaṣaṭ",),
    "नमः": ("homage", "obeisance"),
    "स्वः": ("heaven", "sun", "light"),
    "स्वर्": ("heaven", "light"),
}

CLOSED_STEM_EN: dict[str, tuple[str, ...]] = {
    "अस्मद्": ("I", "we", "me", "us", "my", "our"),
    "युष्मद्": ("thou", "you", "thee", "thy", "ye", "your"),
    "तद्": ("that", "he", "she", "it", "they", "those"),
    "यद्": ("who", "which", "that"),
    "एतद्": ("this", "these"),
    "इदम्": ("this", "these"),
    "अदस्": ("that", "yonder"),
    "किम्": ("who", "what"),
    "सर्व": ("all", "every"),
    "विश्व": ("all", "every"),
    "अन्य": ("other", "another"),
    "त्व": ("indeed", "now"),
    "स्म": ("indeed", "formerly"),
}

_STOP_SA_GRAMMAR_SUBS: tuple[str, ...] = (
    "पा.सू", "पा॰", "पा.", "उ.सू", "उ०", "निरु०", "प्रत्यय",
    "विभक्ति", "लट्", "लोट्", "लुङ्", "लिट्", "लङ्", "विधिलिङ्", "उदात्त",
    "अनुदात्त", "स्वरित", "निघात", "छन्दसि", "छान्दस", "व्यत्यय",
    "बहुव्रीहि", "तत्पुरुष", "विनियोग", "द्रष्टव्य", "गतम्", "इत्याह",
    "अध्याहार", "निष्पन्न", "प्रयुक्त", "उदाहरण", "कात्यायन", "आश्वलायन",
    "गायत्री", "त्रिष्टुप्", "जगती", "अनुष्टुप्", "पङ्क्ति", "उष्णिक्", "बृहती",
    "द्विपदा", "एकपदा", "अर्थविपर्यास", "वर्णविपर्यास", "स्वरेण", "प्रथमा", "द्वितीया",
    "तृतीया", "चतुर्थी", "पञ्चमी", "षष्ठी", "सप्तमी", "सम्बोधन", "आमन्त्रित",
    "एकवचन", "द्विवचन", "बहुवचन", "पुंलिङ्ग", "स्त्रीलिङ्ग", "नपुंसक",
    "क्विप्", "शतृ", "शानच्", "ल्युट्", "घञ्", "णिनि", "ण्यत्", "क्यप्",
    "तै.सं", "तै.ब्रा", "ऋ.सं", "अ.वे", "वा.सं", "श.ब्रा", "व्याख्यात",
)

_STOP_SA_GRAMMAR_TOKENS: frozenset[str] = frozenset({
    "पा", "धातुः", "धातौ", "समासः", "आर्षः", "निपातः", "छन्दः", "प्रकृतिः",
    "श्रुतिः", "ब्राह्मणम्", "सूत्रम्", "प्रयोगः", "लोपः", "आदेशः", "आगमः",
    "गुणः", "वृद्धिः", "लिङ्गम्", "क्त", "अर्थः", "अत्र", "कथम्", "अतः",
    "यतः", "तस्मात्", "मन्त्रः",
})

_US_HOMOGRAPH_BARES: frozenset[str] = frozenset({"मा", "ते", "मे", "वा", "न"})


def _has_sa_grammar_marker(text: str) -> bool:
    if any(m in text for m in _STOP_SA_GRAMMAR_SUBS):
        return True
    toks = {norm_sa(t) for t in text.split()}
    return bool(toks & _STOP_SA_GRAMMAR_TOKENS)

_STOP_SA_WORDS: frozenset[str] = frozenset({
    "इति", "तत्र", "अत्र", "अथ", "ततः", "किञ्च", "यथा", "तथा", "एव", "खलु",
    "हि", "वै", "च", "वा", "तु", "नु", "स्म", "अपि", "उच्यते", "भवति", "आह",
    "आहुः", "अस्ति", "सन्ति", "स्यात्", "भवन्ति", "प्रथमः", "द्वितीयः",
    "तृतीयः", "चतुर्थः", "पञ्चमः", "केचित्", "अन्ये", "अपरे", "एवम्",
    "तस्मात्", "यस्मात्", "अतः", "ननु", "तर्हि", "मन्त्रः", "ब्राह्मणम्",
    "अर्थः", "प्रकरणम्", "अनुवाकः", "गतम्", "इत्यादि", "प्रभृति", "नाम",
    "हे", "अस्य", "तस्य", "यस्य", "एषः", "सः", "सा", "तत्", "एतत्", "इदम्",
    "अयम्", "इयम्", "ते", "ताः", "तानि", "त्वम्", "अहम्", "वयम्", "मम", "तव",
    "अस्माकम्", "युष्माकम्", "मे", "नः", "वः", "त्वा", "मा", "किम्", "कथम्",
    "कुतः", "सर्वम्", "सर्वः", "सर्वा", "सर्वे", "सर्वाः", "उक्तम्", "ज्ञेयम्",
    "द्रष्टव्यम्", "अर्थात्", "अन्वेति", "सम्बन्धः",
})

_HINDI_MARKER_WORDS: frozenset[str] = frozenset({
    "है", "हैं", "था", "थे", "थी", "होता", "होती", "होते", "करता", "करती",
    "करते", "वाला", "वाली", "वाले", "चाहिये", "चाहिए", "देखो", "स्थान",
    "में", "को", "का", "की", "के", "से", "पर", "और", "तथा", "अथवा",
    "नहीं", "जो", "सो", "वह", "यह", "उन", "इस", "उस", "जिस", "अपने",
    "सब", "लोगो", "हे", "करके", "द्वारा",
})

_NON_FINAL_SA_SUFFIXES: tuple[str, ...] = (
    "इति", "इत्याह", "इत्यादि", "उच्यते", "व्यः", "तव्यम्", "नीयम्", "अनीयः",
)

_SAFE_INFLECTION_ENDINGS: tuple[str, ...] = (
    "ायाम्", "आयाम्", "एभ्यः", "आभ्यः", "एषु", "आसु", "भिः", "स्य", "आत्",
    "आय", "एन", "एण", "ओः", "ईः", "ऊः", "अन्ति", "यते", "महे", "तम्", "तु",
)

_ALL_STRIP_RE = re.compile(
    r"[\u0951-\u0957\u1cd0-\u1cff\s\-ऽ।॥,.;:()\[\]0-9०-९*\"'?!—–]"
)
_DIGIT_RE = re.compile(r"[0-9०-९]")
_DEVANAGARI_ANY_RE = re.compile(r"[\u0905-\u0939]")
_ASCII_FOLD_TABLE = str.maketrans(
    "āīūṛṝḷḹēōśṣṇñṅṭḍḥṃṁç",
    "aiurrlleossnnntdhmms",
)
_CLUSTER_START_RE = re.compile(
    r"<details(?:\s[^>]*)?>\s*<summary>\s*(विश्वास-प्रस्तुतिः[^<]*|सर्वाष् टीकाः)\s*</summary>"
)

_MORPH_CACHE: dict[str, tuple[frozenset, frozenset, frozenset, bool, tuple[str, ...]]] = {}


@dataclass(frozen=True)
class CorpusConfig:
    """Configuration describing how a Vedic corpus is laid out on disk."""

    key: str
    default_source_dir: str
    glob_pattern: str
    cluster_mode: str  # "file" or "cluster"
    expand_includes: bool
    en_priority: tuple[str, ...]
    sa_comm_prefixes: tuple[str, ...]
    hi_comm_prefixes: tuple[str, ...] = ()
    padapatha_prefixes: tuple[str, ...] = ("पद-पाठः", "पदपाठः")
    has_hellwig: bool = False
    has_ranganatha: bool = False
    has_trivedi_sa: bool = False


CORPUS_CONFIGS: dict[str, CorpusConfig] = {
    "rv": CorpusConfig(
        key="rv",
        default_source_dir="/home/vvasuki/gitland/vishvAsa/vedAH_Rk/static/shAkalam/saMhitA/sarvASh_TIkAH",
        glob_pattern="[0-9][0-9]/*/[0-9][0-9]*.md",
        cluster_mode="file",
        expand_includes=False,
        en_priority=("Jamison Brereton", "Keith", "Wilson", "Griffith", "Oldenberg", "Gemini 3.8 Flash"),
        sa_comm_prefixes=("रङ्गनाथः", "सायण-भाष्यम्"),
        hi_comm_prefixes=("दयानन्द-सरस्वती (हि) - पदार्थः", "आर्यमुनि - पदार्थः", "ब्रह्ममुनि - पदार्थः", "शिव शंकर शर्मा - पदार्थः"),
        padapatha_prefixes=("पद-पाठः", "पदपाठः"),
        has_hellwig=True,
        has_ranganatha=True,
    ),
    "av": CorpusConfig(
        key="av",
        default_source_dir="/home/vvasuki/gitland/vishvAsa/vedAH/static/atharva/shaunakam/rUDha-saMhitA/sarvASh_TIkAH",
        glob_pattern="**/[0-9][0-9]*.md",
        cluster_mode="file",
        expand_includes=False,
        en_priority=("Whitney", "Griffith", "Gemini 3.8 Flash"),
        sa_comm_prefixes=("सायण-भाष्यम्",),
        hi_comm_prefixes=("पण्डित क्षेमकरणदास त्रिवेदी - पदार्थः",),
        padapatha_prefixes=("पद-पाठः", "पदपाठः"),
        has_trivedi_sa=True,
    ),
    "ts": CorpusConfig(
        key="ts",
        default_source_dir="/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/content/taittirIyam/sArasvata-vibhAgaH/saMhitA/sarva-prastutiH",
        glob_pattern="*/*/[0-9]*.md",
        cluster_mode="cluster",
        expand_includes=True,
        en_priority=("Keith", "Griffith", "Gemini 3.8 Flash", "Jamison Brereton"),
        sa_comm_prefixes=("भट्टभास्कर-टीका", "सायण-टीका"),
        padapatha_prefixes=("पद-पाठः", "पदपाठः - तैत्तिरीयः", "पदपाठः", "पद-पाठः (यान्त्रिकः"),
    ),
    "tb": CorpusConfig(
        key="tb",
        default_source_dir="/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/content/taittirIyam/sArasvata-vibhAgaH/brAhmaNam/sarva-prastutiH",
        glob_pattern="**/[0-9]*.md",
        cluster_mode="cluster",
        expand_includes=True,
        en_priority=("Keith", "Griffith", "Gemini 3.8 Flash", "Eggeling"),
        sa_comm_prefixes=("भट्टभास्कर-टीका", "सायण-टीका"),
        padapatha_prefixes=("पद-पाठः (यान्त्रिकः", "पद-पाठः", "पदपाठः"),
    ),
    "tk": CorpusConfig(
        key="tk",
        default_source_dir="/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/content/taittirIyam/sArasvata-vibhAgaH/kAThakam/sarva-prastutiH",
        glob_pattern="**/[0-9]*.md",
        cluster_mode="cluster",
        expand_includes=True,
        en_priority=("Keith", "Griffith", "Gemini 3.8 Flash"),
        sa_comm_prefixes=("भट्टभास्कर-टीका", "सायण-टीका"),
        padapatha_prefixes=("पद-पाठः (यान्त्रिकः", "पद-पाठः", "पदपाठः"),
    ),
    "ms": CorpusConfig(
        key="ms",
        default_source_dir="/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/content/maitrAyaNIyam/saMhitA/sarva-prastutiH",
        glob_pattern="**/[0-9]*.md",
        cluster_mode="cluster",
        expand_includes=True,
        en_priority=("Gemini 3.8 Flash", "Keith", "Griffith", "Jamison Brereton"),
        sa_comm_prefixes=("भट्टभास्कर-टीका", "सायण-टीका", "उवट-टीका", "महीधर-टीका"),
        padapatha_prefixes=("पद-पाठः (यान्त्रिकः", "पद-पाठः", "पदपाठः"),
    ),
    "ks": CorpusConfig(
        key="ks",
        default_source_dir="/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/content/kAThakam/kaTha-kapiShTalAH/saMhitA/sarva-prastutiH",
        glob_pattern="**/[0-9]*.md",
        cluster_mode="cluster",
        expand_includes=True,
        en_priority=("Gemini 3.8 Flash", "Keith", "Griffith", "Jamison Brereton"),
        sa_comm_prefixes=("भट्टभास्कर-टीका", "सायण-टीका", "उवट-टीका", "महीधर-टीका"),
        padapatha_prefixes=("पद-पाठः (यान्त्रिकः", "पद-पाठः", "पदपाठः"),
    ),
    "vs-m": CorpusConfig(
        key="vs-m",
        default_source_dir="/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/content/vAjasaneyam/mAdhyandinam/saMhitA/sarva-prastutiH",
        glob_pattern="*.md",
        cluster_mode="cluster",
        expand_includes=True,
        en_priority=("Griffith", "Keith", "Gemini 3.8 Flash", "Jamison Brereton"),
        sa_comm_prefixes=("उवट-टीका", "महीधर-टीका", "सायण-टीका"),
        hi_comm_prefixes=("दयानन्द-सरस्वती (हि) - पदार्थः",),
        padapatha_prefixes=("पदपाठः - दयानन्दादि", "पदपाठः", "पद-पाठः"),
    ),
    "vs-k": CorpusConfig(
        key="vs-k",
        default_source_dir="/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/content/vAjasaneyam/kANvam/saMhitA/sarva-prastutiH",
        glob_pattern="*.md",
        cluster_mode="cluster",
        expand_includes=True,
        en_priority=("Griffith", "Keith", "Gemini 3.8 Flash", "Jamison Brereton"),
        sa_comm_prefixes=("सायण-टीका (काण्वी)", "सायण-टीका", "आनन्दबोध-टीका", "उवट-टीका", "महीधर-टीका"),
        hi_comm_prefixes=("दयानन्द-सरस्वती (हि) - पदार्थः",),
        padapatha_prefixes=("पदपाठः - काण्वः", "पदपाठः", "पदपाठः - दयानन्दादि", "पद-पाठः"),
    ),
    "sb-m": CorpusConfig(
        key="sb-m",
        default_source_dir="/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/content/vAjasaneyam/mAdhyandinam/shatapatha-brAhmaNam/sarva-prastutiH",
        glob_pattern="**/*.md",
        cluster_mode="cluster",
        expand_includes=True,
        en_priority=("Eggeling", "C R Swaminathan", "Gemini 3.8 Flash"),
        sa_comm_prefixes=("सायणः", "हरिस्वामी", "वासुदेवब्रह्म"),
        padapatha_prefixes=("पद-पाठः (यान्त्रिकः)", "पद-पाठः (यान्त्रिकः", "पद-पाठः", "पदपाठः"),
    ),
    "sb-k": CorpusConfig(
        key="sb-k",
        default_source_dir="/home/vvasuki/gitland/vishvAsa/vedAH_yajuH/content/vAjasaneyam/kANvam/shatapatha-brAhmaNam/sarva-prastutiH",
        glob_pattern="**/*.md",
        cluster_mode="cluster",
        expand_includes=True,
        en_priority=("C R Swaminathan", "Eggeling", "Gemini 3.8 Flash"),
        sa_comm_prefixes=("सायणः", "हरिस्वामी", "वासुदेवब्रह्म"),
        padapatha_prefixes=("पद-पाठः (यान्त्रिकः)", "पद-पाठः (यान्त्रिकः", "पद-पाठः", "पदपाठः"),
    ),
}


@dataclass
class MantraUnit:
    """Single mantra/kaṇḍikā unit pairing attested padas with translations & commentaries."""

    padas_bare: list[str]
    padas_us: list[str]
    locus: str = ""
    vp_text: str = ""
    en_blocks: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    sa_comms: list[tuple[str, str]] = field(default_factory=list)
    hi_comms: list[tuple[str, str]] = field(default_factory=list)
    hellwig_text: str = ""
    ranganatha_text: str = ""
    trivedi_sa_text: str = ""


@dataclass
class CorpusMeanings:
    """Extracted brief meanings for both padasvara headwords and prakṛti-svara stems."""

    by_us: dict[str, str]
    by_bare: dict[str, str]
    sa_by_bare: dict[str, Counter[str]]
    sa_by_us: dict[str, Counter[str]]
    en_by_bare: dict[str, Counter[str]]
    en_by_us: dict[str, Counter[str]]
    hi_by_bare: dict[str, Counter[str]]
    stem_sa_counts: dict[str, Counter[str]] = field(default_factory=dict)
    stem_en_counts: dict[str, Counter[str]] = field(default_factory=dict)
    stem_hi_counts: dict[str, Counter[str]] = field(default_factory=dict)
    sa_cites_by_bare: dict[str, dict[str, Counter[tuple[str, str]]]] = field(default_factory=dict)
    sa_cites_by_us: dict[str, dict[str, Counter[tuple[str, str]]]] = field(default_factory=dict)
    en_cites_by_bare: dict[str, dict[str, Counter[tuple[str, str]]]] = field(default_factory=dict)
    en_cites_by_us: dict[str, dict[str, Counter[tuple[str, str]]]] = field(default_factory=dict)
    hi_cites_by_bare: dict[str, dict[str, Counter[tuple[str, str]]]] = field(default_factory=dict)
    stem_sa_cites: dict[str, dict[str, Counter[tuple[str, str]]]] = field(default_factory=dict)
    stem_en_cites: dict[str, dict[str, Counter[tuple[str, str]]]] = field(default_factory=dict)
    stem_hi_cites: dict[str, dict[str, Counter[tuple[str, str]]]] = field(default_factory=dict)

    def lookup(self, sasvara_word: str) -> str:
        """Return brief formatted meaning for an accented padasvara word, if any."""
        if sasvara_word in self.by_us:
            return self.by_us[sasvara_word]
        is_us = "\u0951" not in sasvara_word and "\u0952" not in sasvara_word
        norm_u = _to_us_form(sasvara_word, already_us=is_us)
        if norm_u and norm_u in self.by_us:
            return self.by_us[norm_u]
        bare = norm_sa(sasvara_word)
        if bare in _US_HOMOGRAPH_BARES or (bare in CLOSED_BARE_EN and norm_u not in self.by_us):
            # Avoid leaking an opposite homograph gloss (e.g. मा vs मा᳓, ते vs ते᳓).
            return ""
        return self.by_bare.get(bare, "")


def norm_sa(word: str) -> str:
    """Strip accents, punctuation, hyphens, and normalize candrabindu -> anusvāra."""
    cached = _NORM_CACHE.get(word)
    if cached is not None:
        return cached
    w = _ALL_STRIP_RE.sub("", word).replace("ँ", "ं")
    if len(_NORM_CACHE) < 200000:
        _NORM_CACHE[word] = w
    return w


def _to_us_form(word: str, *, already_us: bool = True) -> str:
    """Normalize classical or US accented Devanagari token into canonical US form."""
    cache_key = f"{int(already_us)}:{word}"
    cached = _US_CACHE.get(cache_key)
    if cached is not None:
        return cached
    tok = word.strip(" ,;:-।॥'\"*ऽ—–!?()[]")
    out = ""
    if tok:
        effective_us = already_us and ("\u0951" not in tok and "\u0952" not in tok)
        np = padasvara_common.normalize_raw_form_to_us(tok, already_us=effective_us)
        if np and np.us_form:
            out = np.us_form.replace("ँ", "ं")
    if len(_US_CACHE) < 200000:
        _US_CACHE[cache_key] = out
    return out


def _en_stem(word: str) -> str:
    """Lightweight English stemmer for lexicon/translation alignment."""
    w = word.lower().strip("'")
    if w.endswith("'s"):
        w = w[:-2]
    if len(w) <= 3:
        return w
    if (w.endswith("ies") or w.endswith("ied")) and len(w) > 4:
        return w[:-3] + "y"
    for suf in ("ing", "ers", "ed", "es", "er", "ly", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)]
    return w


def _fold_ascii(text: str) -> str:
    """Fold IAST/HOS accents (`ā`, `ś`, `ç`, etc.) into plain lowercase ASCII letters."""
    return re.sub(r"[^a-z]", "", text.lower().translate(_ASCII_FOLD_TABLE))


def _fold_ascii_loose(text: str) -> str:
    """Fold ASCII and collapse `sh` -> `s` to bridge alternate transliterations."""
    return _fold_ascii(text).replace("sh", "s")


_LEX_ANCHOR_RE = re.compile(r"<a\b[^>]*>[^<]*</a>")
_LEX_TAG_RE = re.compile(r"<[^>]+>")
_LEX_BRACKET_RE = re.compile(r"\[[^\]]*\]|\([^)]*\)")
_LEX_N_OF_RE = re.compile(r"\bN\.\s*of\b[^;,.]*")
_LEX_CITE_SPLIT_RE = re.compile(r"\b(?:RV|AV|TS|VS|ŚBr|TB|MBh|Mn|Pāṇ|Dhātup)\b")
_LEX_GRAM_PREFIX_RE = re.compile(
    r"^(?:[mfn]\.|ind\.|adj\.|pn\.|pr\.|p\.|cl\.\s*\d+\.|to\s+be\s+|to\s+)+",
    re.I,
)
_LEX_DEVA_RE = re.compile(r"[\u0900-\u097f]+")
_LEX_EN_WORD_RE = re.compile(r"[A-Za-z][A-Za-z']*")


def load_sa_en_lexicon(cache_path: str = _LEX_CACHE_PATH) -> dict[str, list[str]]:
    """Build or load cached Sanskrit -> candidate English phrases anchor index."""
    if os.path.isfile(cache_path):
        try:
            with open(cache_path, "rb") as fh:
                data = pickle.load(fh)
            if isinstance(data, dict) and len(data) > 10000:
                return data
        except Exception:
            pass

    lex: dict[str, list[str]] = defaultdict(list)
    for rel_path, max_cands in _LEX_SOURCES:
        full_path = os.path.join(_SA_EN_DIR, rel_path)
        if not os.path.isfile(full_path):
            continue
        with open(full_path, encoding="utf-8", errors="ignore") as fh:
            txt = fh.read()
        for blk in txt.split("\n\n"):
            lines = [ln for ln in blk.splitlines() if ln.strip()]
            if len(lines) < 2 or lines[0].startswith("#"):
                continue
            hws = [h.strip() for h in lines[0].split("|") if h.strip()]
            if not hws:
                continue
            body = " ".join(lines[1:])
            if "<a" in body:
                body = _LEX_ANCHOR_RE.sub("", body)
            body = body.replace("<BR>", "; ").replace("<br>", "; ")
            if "<" in body:
                body = _LEX_TAG_RE.sub(" ", body)
            if "[" in body or "(" in body:
                body = _LEX_BRACKET_RE.sub(" ", body)
            if "N." in body:
                body = _LEX_N_OF_RE.sub(" ", body)
            body = _LEX_CITE_SPLIT_RE.split(body, maxsplit=1)[0]
            cands: list[str] = []
            hw_folded: set[str] | None = None
            for raw_piece in re.split(r"[;:,]", body):
                p_str = raw_piece.strip(" .-–—0123456789'\"")
                if not p_str:
                    continue
                if "-" in p_str:
                    parts_h = p_str.split()
                    if len(parts_h) <= 2 and any("-" in x and len(x) <= 8 for x in parts_h):
                        continue
                p_str = _LEX_GRAM_PREFIX_RE.sub("", p_str).strip()
                if not p_str:
                    continue
                p_str = _LEX_DEVA_RE.sub("", p_str).strip()
                if not p_str:
                    continue
                # Also split concise `"A or B"` options into separate searchable glosses.
                sub_pieces = [p_str]
                if " or " in p_str and len(p_str.split()) <= 5:
                    sub_pieces.extend(sp.strip() for sp in p_str.split(" or "))
                for sub_p in sub_pieces:
                    words = _LEX_EN_WORD_RE.findall(sub_p)
                    if not words or len(words) > 5:
                        continue
                    while words and words[0].lower() in (
                        "m", "f", "n", "p", "a", "an", "the", "to", "of", "in", "by", "with", "for",
                        "du", "pl", "sg", "i", "e", "or"
                    ):
                        words.pop(0)
                    if not words:
                        continue
                    content = [w for w in words if w.lower() not in STOP_EN and len(w) >= 2]
                    if not content:
                        continue
                    phrase = " ".join(words).lower()
                    if phrase in _DEITY_NOUNS:
                        if hw_folded is None:
                            hw_folded = {
                                _fold_ascii_loose(
                                    sanscript.transliterate(
                                        norm_sa(h), sanscript.DEVANAGARI, sanscript.IAST
                                    )
                                )
                                for h in hws[:2]
                            }
                        if not any(phrase in hf or hf in phrase for hf in hw_folded if hf):
                            continue
                    if any(b in phrase for b in _BAD_GLOSS_SUBS):
                        continue
                    if phrase not in cands:
                        cands.append(phrase)
                    if len(cands) >= max_cands:
                        break
                if len(cands) >= max_cands:
                    break
            if cands:
                for hw in hws[:2]:
                    k = norm_sa(hw)
                    if not k or len(lex[k]) >= 80:
                        continue
                    for c in cands:
                        if c not in lex[k]:
                            lex[k].append(c)

    result = dict(lex)
    if result and os.path.isdir(_SA_EN_DIR):
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "wb") as fh:
            pickle.dump(result, fh)
    return result


def _morph_info(
    deva_w: str,
) -> tuple[frozenset, frozenset, frozenset, bool, tuple[str, ...]]:
    """Return Vidyut `(sub_tags, sub_saptami_satr, tin_tags, is_avy, root_deva_cands)`."""
    if deva_w in _MORPH_CACHE:
        return _MORPH_CACHE[deva_w]
    try:
        kosha = ss.get_vidyut_kosha()
        slp = ss._deva_to_slp(deva_w)
    except Exception:
        res = (frozenset(), frozenset(), frozenset(), False, ())
        _MORPH_CACHE[deva_w] = res
        return res

    cands = [slp]
    if slp.endswith("H"):
        cands.extend([slp[:-1] + "s", slp[:-1] + "r"])
    elif slp.endswith("M"):
        cands.append(slp[:-1] + "m")
    elif slp.endswith("d"):
        cands.append(slp[:-1] + "t")

    sub_tags: set[tuple[str, str]] = set()
    sub_saptami_on_tinanta: set[tuple[str, str]] = set()
    tin_tags: set[tuple[str, str]] = set()
    is_avy = False
    roots: list[str] = []

    raw_entries = []
    has_tinanta = False
    for c in cands:
        for e in kosha.get(c):
            raw_entries.append(e)
            if isinstance(e, PadaEntry.Tinanta):
                has_tinanta = True

    for e in raw_entries:
        if isinstance(e, PadaEntry.Subanta):
            pe = e.pratipadika_entry
            if getattr(pe, "is_avyaya", False) or (
                hasattr(pe, "lingas") and len(pe.lingas) == 0
            ):
                is_avy = True
            else:
                tag = (str(e.vibhakti), str(e.vacana))
                # Vidyut parses present-active -ati/-nti verbs as locative singular of satr;
                # isolate that tag when the token is also a finite Tinanta ending in ति/न्ति.
                if (
                    has_tinanta
                    and str(e.vibhakti) == "saptamI"
                    and str(e.vacana) == "eka"
                    and deva_w.endswith(("ति", "न्ति"))
                ):
                    sub_saptami_on_tinanta.add(tag)
                else:
                    sub_tags.add(tag)
            de = getattr(pe, "dhatu_entry", None)
            if de is not None and getattr(de, "clean_text", None):
                r_deva = sanscript.transliterate(
                    de.clean_text, sanscript.SLP1, sanscript.DEVANAGARI
                )
                if r_deva and r_deva not in roots:
                    roots.append(r_deva)
        elif isinstance(e, PadaEntry.Tinanta):
            tin_tags.add((str(e.purusha), str(e.vacana)))
            de = getattr(e, "dhatu_entry", None)
            if de is not None and getattr(de, "clean_text", None):
                r_deva = sanscript.transliterate(
                    de.clean_text, sanscript.SLP1, sanscript.DEVANAGARI
                )
                if r_deva and r_deva not in roots:
                    roots.append(r_deva)

    res = (
        frozenset(sub_tags),
        frozenset(sub_saptami_on_tinanta),
        frozenset(tin_tags),
        is_avy,
        tuple(roots),
    )
    _MORPH_CACHE[deva_w] = res
    return res


def morph_compatible(w1: str, w2: str) -> bool:
    """Return True if two unaccented Devanagari words share compatible Sanskrit morphology."""
    if len(w2) <= 2:
        return False
    sub1, sap1, tin1, avy1, _ = _morph_info(w1)
    sub2, sap2, tin2, avy2, _ = _morph_info(w2)
    eff_sub1 = sub1 | (sap1 if tin2 else frozenset())
    eff_sub2 = sub2 | (sap2 if tin1 else frozenset())
    if eff_sub1 and eff_sub2 and (eff_sub1 & eff_sub2):
        return True
    if tin1 and tin2 and (tin1 & tin2):
        return True
    if avy1 and avy2 and not eff_sub1 and not eff_sub2 and not tin1 and not tin2:
        return True
    for sfx in _SAFE_INFLECTION_ENDINGS:
        if w1.endswith(sfx) and w2.endswith(sfx):
            if not eff_sub1 or not eff_sub2 or (eff_sub1 & eff_sub2):
                return True
    return False


def _clean_sa_gloss(raw: str) -> str:
    """Normalize and validate a candidate brief Sanskrit commentary gloss."""
    g = raw.strip(" ,;:-।॥'\"*ऽ—–!?()[]")
    g = re.sub(r"\[[^\]]*\]|\([^)]*\)", "", g).strip()
    g = re.sub(r"^(?:खलु|हि|वै|नाम|इति|अर्थात्)\s+", "", g).strip()
    g = re.sub(
        r"\s+(?:इति\s*(?:केचित्|उच्यते|अर्थः|भवति|स्तुतिः|आहुः)?|उच्यते)$",
        "",
        g,
    ).strip()
    g = g.split("**")[0].split("।")[0].split("॥")[0].split(";")[0].strip(" ,;:-")
    if not g or len(g) <= 2 or len(g) > 45:
        return ""
    if _DIGIT_RE.search(g) or re.search(r"[A-Za-z]", g):
        return ""
    if any(m in g for m in _STOP_SA_GRAMMAR_SUBS):
        return ""
    if "\u0951" in g or "\u0952" in g:
        return ""
    words = [w for w in g.split() if _DEVANAGARI_ANY_RE.search(w)]
    if not (1 <= len(words) <= 4):
        return ""
    if any(norm_sa(w) in _STOP_SA_GRAMMAR_TOKENS for w in words):
        return ""
    if all(w in _STOP_SA_WORDS or len(norm_sa(w)) <= 2 for w in words):
        return ""
    if any(w in _HINDI_MARKER_WORDS for w in words):
        return ""
    return " ".join(words)


def _clean_hi_gloss(raw: str) -> str:
    """Normalize a brief Hindi पदार्थः fallback gloss."""
    g = re.sub(r"\[[^\]]*\]", "", raw)
    g = re.split(r"[।॥]", g)[0]
    g = re.sub(r"\([^)]*\)", "", g)
    g = g.strip(" ,;:-।॥!—–'\"१२३४५६७८९०0123456789")
    g = re.sub(r"^(?:जो|सो|और|तथा|अथवा)\s+", "", g).strip(" ,;:-")
    if not g or len(g) <= 2 or len(g) > 45 or _DIGIT_RE.search(g):
        return ""
    if not (1 <= len(g.split()) <= 6):
        return ""
    return g


def _parse_padapatha_tokens(
    body: str,
    *,
    is_mechanical: bool,
) -> tuple[list[str], list[str]]:
    """Extract aligned `(bare_tokens, us_tokens)` from a padapāṭha block body."""
    bares: list[str] = []
    us_list: list[str] = []
    block_has_classical = "\u0951" in body or "\u0952" in body
    block_is_us = is_mechanical or (
        not block_has_classical
        and (
            padasvara_common.US_UDATTA in body
            or padasvara_common.US_SVARITA in body
        )
    )

    if is_mechanical:
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        has_bullets = any(ln.startswith("- ") for ln in lines)
        if has_bullets:
            for ln in lines:
                if not ln.startswith("- ") or "→" in ln or "[[" in ln:
                    continue
                tok = ln[2:].split("(", 1)[0].split("[", 1)[0].strip()
                b = norm_sa(tok)
                if b and _DEVANAGARI_ANY_RE.search(b):
                    bares.append(b)
                    us_list.append(_to_us_form(tok, already_us=True) or b)
            if bares:
                return bares, us_list

    for seg in re.split(r"[।॥\n]+", body):
        seg = seg.strip()
        if not seg:
            continue
        words = seg.split()
        # Handle `X इति Y` pragṛhya / compound restatements (`अग्नी इति`, `सुप्रयाः इति सु-प्रयाः`).
        if "इति" in words and len(words) <= 5:
            iti_idx = words.index("इति")
            cand_tok = words[-1] if iti_idx + 1 < len(words) else words[0]
            if iti_idx > 0 and len(words[iti_idx - 1]) >= 2:
                raw_toks = [words[iti_idx - 1]]
                if cand_tok != words[iti_idx - 1]:
                    raw_toks.append(cand_tok)
            else:
                raw_toks = [cand_tok]
        else:
            raw_toks = words
        for tok in raw_toks:
            tok_c = tok.strip(" ,;:-।॥'\"*—–")
            if not tok_c or tok_c == "इति":
                continue
            b = norm_sa(tok_c)
            if b and _DEVANAGARI_ANY_RE.search(b):
                bares.append(b)
                us_list.append(_to_us_form(tok_c, already_us=block_is_us) or b)
    return bares, us_list


def _expand_includes(text: str, include_cache: dict[str, list[tuple[str, str, str]]]) -> str:
    """Resolve `<js-include>` directives using a shared in-memory URL cache."""
    spans = accent_prov.find_js_include_spans(text)
    if not spans:
        return text
    parts: list[str] = []
    cur = 0
    for a, b in spans:
        parts.append(text[cur:a])
        tag_end = text.find(">", a)
        url = accent_prov.extract_js_include_url(text[a : tag_end + 1]) if tag_end != -1 else None
        if url:
            if url not in include_cache:
                try:
                    include_cache[url] = accent_prov._collect_include_leaf_blocks(url)
                except Exception:
                    include_cache[url] = []
            blks = include_cache[url]
            if blks:
                parts.append(
                    "\n".join(
                        f"<details><summary>{hdr}</summary>\n{bd}\n</details>"
                        for hdr, bd, _ in blks
                    )
                )
            else:
                parts.append(text[a:b])
        else:
            parts.append(text[a:b])
        cur = b
    parts.append(text[cur:])
    return "\n".join(parts)


_DEVA_TO_ASCII_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_HEADING_NUM_RE = re.compile(r"(?m)^#{1,3}\s+([०-९0-9]+)(?=\s|$)")

_SOURCE_LABEL_MAP: dict[str, str] = {
    "Jamison Brereton": "Jamison-Brereton",
    "Gemini 3.8 Flash": "Gemini 3.8",
    "Hellwig Grammar": "Hellwig",
    "C R Swaminathan": "Swaminathan",
    "विश्वास-प्रस्तुतिः": "विश्वासः",
    "रङ्गनाथः": "रङ्गनाथः",
    "सायणः": "सायणः",
    "सायण-भाष्यम्": "सायणः",
    "सायण-टीका": "सायणः",
    "सायण-टीका (काण्वी)": "सायणः",
    "भट्टभास्कर-टीका": "भट्टभास्करः",
    "उवट-टीका": "उवटः",
    "महीधर-टीका": "महीधरः",
    "आनन्दबोध-टीका": "आनन्दबोधः",
    "हरिस्वामी": "हरिस्वामी",
    "वासुदेवब्रह्म": "वासुदेवब्रह्म",
    "दयानन्द-सरस्वती (हि) - पदार्थः": "दयानन्दः",
    "आर्यमुनि - पदार्थः": "आर्यमुनिः",
    "ब्रह्ममुनि - पदार्थः": "ब्रह्ममुनिः",
    "शिव शंकर शर्मा - पदार्थः": "शिवशङ्करः",
    "पण्डित क्षेमकरणदास त्रिवेदी - पादटिप्पनी": "त्रिवेदी",
    "पण्डित क्षेमकरणदास त्रिवेदी - पदार्थः": "त्रिवेदी",
}


def _format_source_label(header: str) -> str:
    """Return concise human-readable source name for a `<summary>` header."""
    h = header.strip()
    if h in _SOURCE_LABEL_MAP:
        return _SOURCE_LABEL_MAP[h]
    for k, v in _SOURCE_LABEL_MAP.items():
        if h.startswith(k):
            return v
    if h.startswith("सायण"):
        return "सायणः"
    if h.startswith("भट्टभास्कर"):
        return "भट्टभास्करः"
    if h.startswith("हरिस्वाम"):
        return "हरिस्वामी"
    if h.startswith("वासुदेव"):
        return "वासुदेवः"
    return h


def _derive_file_locus(corpus_key: str, root: str, file_path: str) -> str:
    """Derive canonical dotted locus (e.g. ``1.2.3``) from a corpus file path."""
    from pathlib import Path

    rel = Path(os.path.relpath(file_path, root))
    if rel.name.startswith("_") or rel.name == "file_list.md":
        return ""
    if corpus_key == "ks" and len(rel.parts) >= 3:
        p_head = rel.parts[0].split("_")[0].translate(_DEVA_TO_ASCII_DIGITS)
        s_head = rel.parts[1].split("_")[0].translate(_DEVA_TO_ASCII_DIGITS)
        anu_raw = rel.stem.translate(_DEVA_TO_ASCII_DIGITS)
        anu_m = re.match(r"^(\d+)", anu_raw)
        if p_head.isdigit() and s_head.isdigit() and anu_m:
            p_num, s_num = int(p_head), int(s_head)
            if p_num == 5:
                return f"5.{s_num}.{anu_raw.lstrip('0') or '0'}"
            a_disp = "-".join(seg.lstrip("0") or "0" for seg in anu_raw.split("-"))
            return f"{s_num}.{a_disp}"

    nums: list[str] = []
    for part in rel.parts[:-1]:
        head = part.split("_")[0].translate(_DEVA_TO_ASCII_DIGITS)
        m = re.match(r"^(\d+)", head)
        if m:
            nums.append(str(int(m.group(1))))

    stem_parts = rel.stem.translate(_DEVA_TO_ASCII_DIGITS).split("_")
    if corpus_key == "tk":
        if stem_parts and stem_parts[0].isdigit():
            nums.append(str(int(stem_parts[0])))
            if len(stem_parts) >= 2 and stem_parts[1].isdigit():
                nums.append(str(int(stem_parts[1])))
    elif stem_parts:
        m = re.match(r"^(\d+)", stem_parts[0])
        if m:
            nums.append(str(int(m.group(1))))
    return ".".join(nums)


def _norm_gloss_key(gloss: str) -> str:
    """Canonicalize a gloss string consistently for citation lookup."""
    return re.sub(r"\s+", " ", gloss.replace("<br>", " ").replace("\n", " ")).strip(" ,;:-")


def parse_corpus_units(
    config: CorpusConfig,
    *,
    source_dir: str | None = None,
    include_yantra: bool = False,
) -> list[MantraUnit]:
    """Parse a Vedic corpus directory into aligned :class:`MantraUnit` objects."""
    root = source_dir or config.default_source_dir
    if not os.path.isdir(root):
        LOGGER.warning("Corpus directory missing for %s: %s", config.key, root)
        return []

    files = sorted(
        fp
        for fp in glob.glob(os.path.join(root, config.glob_pattern), recursive=True)
        if not os.path.basename(fp).startswith("_") and os.path.basename(fp) != "file_list.md"
    )
    if not files and config.glob_pattern != "**/*.md":
        files = sorted(
            fp
            for fp in glob.glob(os.path.join(root, "**/*.md"), recursive=True)
            if not os.path.basename(fp).startswith("_") and os.path.basename(fp) != "file_list.md"
        )

    include_cache: dict[str, list[tuple[str, str, str]]] = {}
    units: list[MantraUnit] = []

    pad_rank = {pref: idx for idx, pref in enumerate(config.padapatha_prefixes)}

    def _pad_score(summary: str) -> int | None:
        for pref, r in pad_rank.items():
            if summary == pref or summary.startswith(pref):
                return r
        return None

    for fp in files:
        file_locus = _derive_file_locus(config.key, root, fp)
        with open(fp, encoding="utf-8", errors="ignore") as fh:
            raw_txt = fh.read()
        txt = _expand_includes(raw_txt, include_cache) if (
            config.expand_includes or "<js-include" in raw_txt
        ) else raw_txt

        if config.cluster_mode == "file":
            _parse_file_unit(txt, config, _pad_score, units, file_locus=file_locus)
        else:
            _parse_cluster_units(txt, config, _pad_score, include_yantra, units, file_locus=file_locus)

    return units


def _classify_leaf(
    hdr: str,
    bd: str,
    config: CorpusConfig,
    pad_score_fn,
    state: dict,
) -> None:
    """Dispatch a single leaf `<details>` block into mutable unit state."""
    score = pad_score_fn(hdr)
    if score is not None:
        is_mech = "यान्त्रिक" in hdr
        bares, us_list = _parse_padapatha_tokens(bd, is_mechanical=is_mech)
        if bares and (state["pad_best"] is None or score < state["pad_best"]):
            state["pad_best"] = score
            state["bares"] = bares
            state["us"] = us_list
        return
    if hdr in config.en_priority:
        state["en"][hdr].append(bd)
        return
    if config.has_hellwig and hdr == "Hellwig Grammar":
        state["hellwig"].append(bd)
        return
    if config.has_ranganatha and hdr == "रङ्गनाथः":
        state["ranganatha"].append(bd)
        return
    if config.has_trivedi_sa and "पादटिप्पनी" in hdr:
        state["trivedi_sa"].append(bd)
        return
    if any(hdr == p or hdr.startswith(p) for p in config.sa_comm_prefixes):
        state["sa"].append((hdr, bd))
        return
    if any(hdr == p or hdr.startswith(p) for p in config.hi_comm_prefixes):
        state["hi"].append((hdr, bd))


def _new_state(locus: str = "") -> dict:
    return {
        "locus": locus,
        "skip": False,
        "saw_tika": False,
        "vp": "",
        "pad_best": None,
        "bares": [],
        "us": [],
        "en": defaultdict(list),
        "sa": [],
        "hi": [],
        "hellwig": [],
        "ranganatha": [],
        "trivedi_sa": [],
    }


def _flush_state(state: dict, out: list[MantraUnit]) -> None:
    if state["skip"] or not state["bares"]:
        return
    out.append(
        MantraUnit(
            padas_bare=state["bares"],
            padas_us=state["us"],
            locus=state["locus"],
            vp_text=state["vp"],
            en_blocks=state["en"],
            sa_comms=state["sa"],
            hi_comms=state["hi"],
            hellwig_text="\n".join(state["hellwig"]),
            ranganatha_text="\n".join(state["ranganatha"]),
            trivedi_sa_text="\n".join(state["trivedi_sa"]),
        )
    )


def _parse_file_unit(
    txt: str,
    config: CorpusConfig,
    pad_score_fn,
    out: list[MantraUnit],
    *,
    file_locus: str = "",
) -> None:
    state = _new_state(file_locus)
    for m in accent_prov.LEAF_DETAILS_RE.finditer(txt):
        hdr = m.group(1).strip()
        bd = _ANNOT_RE.sub(r"\1", m.group(2).strip()) if "[[" in m.group(2) else m.group(2).strip()
        if hdr.startswith("विश्वास-प्रस्तुतिः"):
            state["vp"] = bd
        else:
            _classify_leaf(hdr, bd, config, pad_score_fn, state)
    _flush_state(state, out)


def _parse_cluster_units(
    txt: str,
    config: CorpusConfig,
    pad_score_fn,
    include_yantra: bool,
    out: list[MantraUnit],
    *,
    file_locus: str = "",
) -> None:
    use_sec_num = config.key in ("vs-m", "vs-k", "sb-m", "sb-k") or "." not in file_locus
    events: list[tuple[int, str, str, str]] = []
    if use_sec_num:
        for m in _HEADING_NUM_RE.finditer(txt):
            num_s = str(int(m.group(1).translate(_DEVA_TO_ASCII_DIGITS)))
            events.append((m.start(), "heading", num_s, ""))
    for m in _CLUSTER_START_RE.finditer(txt):
        hdr = m.group(1).strip()
        if hdr == "सर्वाष् टीकाः":
            events.append((m.start(), "tika", hdr, ""))
    for m in accent_prov.LEAF_DETAILS_RE.finditer(txt):
        bd = _ANNOT_RE.sub(r"\1", m.group(2).strip()) if "[[" in m.group(2) else m.group(2).strip()
        events.append((m.start(), "leaf", m.group(1).strip(), bd))
    events.sort(key=lambda x: x[0])

    cur_sec = ""

    def _cur_locus() -> str:
        if use_sec_num and cur_sec:
            return f"{file_locus}.{cur_sec}" if file_locus else cur_sec
        return file_locus

    state = _new_state(_cur_locus())
    for _, kind, hdr, bd in events:
        if kind == "heading":
            cur_sec = hdr
            if not state["vp"] and not state["saw_tika"] and not state["bares"]:
                state["locus"] = _cur_locus()
            continue
        if kind == "tika":
            if state["saw_tika"]:
                _flush_state(state, out)
                state = _new_state(_cur_locus())
            state["saw_tika"] = True
            continue
        if hdr.startswith("विश्वास-प्रस्तुतिः"):
            _flush_state(state, out)
            state = _new_state(_cur_locus())
            if (not include_yantra and "यन्त्र-स्वरः" in hdr) or "व्यत्यस्त-स्वराः" in hdr:
                state["skip"] = True
            else:
                state["vp"] = bd
            continue
        _classify_leaf(hdr, bd, config, pad_score_fn, state)
    _flush_state(state, out)


def _resolve_unit_pada_lookup(
    unit: MantraUnit,
) -> tuple[set[str], dict[str, str], dict[str, str]]:
    """Build `(pada_bare_set, bare_to_us, joined_sandhi_to_bare)` for a single unit."""
    from .taittiriya import _join_compound_sandhi

    pset = set(unit.padas_bare)
    b2u: dict[str, str] = {}
    alias_to_bare: dict[str, str] = {}
    for b, u in zip(unit.padas_bare, unit.padas_us):
        b2u.setdefault(b, u)
        if b.endswith("म्") and len(b) > 2:
            alias_to_bare.setdefault(b[:-2] + "ं", b)
        elif b.endswith("ं") and len(b) > 1:
            alias_to_bare.setdefault(b[:-1] + "म्", b)
        if "-" in u:
            bare_hyph = padasvara_common.strip_all_accents(u).replace("ँ", "ं")
            joined = _join_compound_sandhi(bare_hyph)
            if joined:
                jb = norm_sa(joined)
                if jb and jb not in pset:
                    alias_to_bare[jb] = b
                    if jb.endswith("म्") and len(jb) > 2:
                        alias_to_bare.setdefault(jb[:-2] + "ं", b)
        elif "ः" in b:
            # Handle unhyphenated visarga-sandhi compounds (`पुरःहितम्` -> `पुरोहितम्`).
            joined = norm_sa(_join_compound_sandhi(b.replace("ः", "ः-", 1)))
            if joined and joined != b and joined not in pset:
                alias_to_bare[joined] = b
                if joined.endswith("म्") and len(joined) > 2:
                    alias_to_bare.setdefault(joined[:-2] + "ं", b)
    return pset, b2u, alias_to_bare


def _extract_unit_en_context(
    en_texts: list[str],
) -> tuple[list[str], str, set[str], dict[str, list[str]], dict[str, str]]:
    """Preprocess an English translation string for O(1) alignment."""
    combined = " ".join(en_texts)
    cleaned = re.sub(r"\[\^[^\]]+\]|\([^)]*\)|\[[^\]]*\]", " ", combined)
    tokens = re.findall(r"[A-Za-z\u00C0-\u024F\u1E00-\u1EFF']+", cleaned)
    word_set: set[str] = set()
    stems_map: dict[str, list[str]] = defaultdict(list)
    folded_map: dict[str, str] = {}
    lower_toks: list[str] = []
    for et in tokens:
        el = et.lower()
        lower_toks.append(el)
        word_set.add(el)
        if el in STOP_EN or len(el) < 2:
            continue
        stems_map[_en_stem(el)].append(et)
        fa = _fold_ascii(et)
        if len(fa) >= 4 and fa not in folded_map:
            folded_map[fa] = et
        fal = _fold_ascii_loose(et)
        if len(fal) >= 4 and fal not in folded_map:
            folded_map[fal] = et
    lower_str = " " + " ".join(lower_toks) + " "
    return tokens, lower_str, word_set, stems_map, folded_map


def _phrase_in_en(cand: str, en_word_set: set[str], en_lower_str: str) -> bool:
    """Fast boundary-safe check whether an English word or phrase appears in unit text."""
    if " " not in cand and "'" not in cand:
        return cand in en_word_set
    if cand not in en_lower_str:
        return False
    return f" {cand} " in en_lower_str or bool(re.search(rf"\b{re.escape(cand)}\b", en_lower_str))


CiteMap = dict[str, dict[str, Counter[tuple[str, str]]]]


def _add_gloss(
    bare_cnts: dict[str, Counter[str]],
    us_cnts: dict[str, Counter[str]],
    pw: str,
    us_w: str,
    gloss: str,
    weight: int,
    *,
    bare_cites: CiteMap | None = None,
    us_cites: CiteMap | None = None,
    source: str = "",
    locus: str = "",
) -> None:
    bare_cnts[pw][gloss] += weight
    if us_w:
        us_cnts[us_w][gloss] += weight * 2
    if source:
        gk = _norm_gloss_key(gloss)
        cite = (source, locus)
        if bare_cites is not None:
            pw_d = bare_cites.get(pw)
            if pw_d is None:
                pw_d = {}
                bare_cites[pw] = pw_d
            g_cnt = pw_d.get(gk)
            if g_cnt is None:
                g_cnt = Counter()
                pw_d[gk] = g_cnt
            g_cnt[cite] += weight
        if us_w and us_cites is not None:
            us_d = us_cites.get(us_w)
            if us_d is None:
                us_d = {}
                us_cites[us_w] = us_d
            g_cnt = us_d.get(gk)
            if g_cnt is None:
                g_cnt = Counter()
                us_d[gk] = g_cnt
            g_cnt[cite] += weight * 2


def _extract_structured_and_commentary(
    unit: MantraUnit,
    en_stems: set[str],
    lex: dict[str, list[str]],
    sa_bare: dict[str, Counter[str]],
    sa_us: dict[str, Counter[str]],
    en_bare: dict[str, Counter[str]],
    en_us: dict[str, Counter[str]],
    hi_bare: dict[str, Counter[str]],
    hi_us: dict[str, Counter[str]],
    en_lower_str: str,
    *,
    sa_cites_bare: CiteMap | None = None,
    sa_cites_us: CiteMap | None = None,
    en_cites_bare: CiteMap | None = None,
    en_cites_us: CiteMap | None = None,
    hi_cites_bare: CiteMap | None = None,
    hi_cites_us: CiteMap | None = None,
) -> None:
    """Extract VP inline glosses, Ranganātha, Hellwig, Trivedi, and morph-verified commentary."""
    pset, b2u, alias_to_bare = _resolve_unit_pada_lookup(unit)
    loc = unit.locus

    def _canon_pw(raw_pw: str) -> str:
        return alias_to_bare.get(raw_pw, raw_pw)

    # 1. विश्वास-प्रस्तुतिः `word+++(=gloss)+++`
    if unit.vp_text:
        for m in re.finditer(r"([^\s।॥,]+)\s*\+\+\+\(=([^)]+)\)\+\+\+", unit.vp_text):
            pw = _canon_pw(norm_sa(m.group(1)))
            if pw not in pset:
                continue
            g = _clean_sa_gloss(m.group(2))
            if g and norm_sa(g) != pw:
                _add_gloss(
                    sa_bare, sa_us, pw, b2u.get(pw, pw), g, 6,
                    bare_cites=sa_cites_bare, us_cites=sa_cites_us,
                    source="विश्वासः", locus=loc,
                )

    # 2. रङ्गनाथः (`pada- gloss`)
    if unit.ranganatha_text:
        for seg in re.split(r"[।॥\n]+", unit.ranganatha_text):
            md = re.match(r"^\s*([^\s\-–—]+)\s*[-–—]\s*(.+)$", seg.strip())
            if not md:
                continue
            pw = _canon_pw(norm_sa(md.group(1)))
            if pw not in pset:
                continue
            g = _clean_sa_gloss(md.group(2))
            if g and norm_sa(g) != pw:
                _add_gloss(
                    sa_bare, sa_us, pw, b2u.get(pw, pw), g, 5,
                    bare_cites=sa_cites_bare, us_cites=sa_cites_us,
                    source="रङ्गनाथः", locus=loc,
                )

    # 3. Hellwig Grammar context-filtered against unit English translation
    if unit.hellwig_text:
        en_words = set(en_lower_str.split())
        for bm in re.finditer(r"-\s+\*([^*]+)\*[^\n\"“]*[“\"]([^”\"\n]+)[”\"]", unit.hellwig_text):
            surf_iast = bm.group(1).strip()
            surf_deva = _canon_pw(
                norm_sa(
                    sanscript.transliterate(surf_iast, sanscript.IAST, sanscript.DEVANAGARI)
                )
            )
            if surf_deva not in pset:
                continue
            raw_glosses = [
                g.strip(" .")
                for g in bm.group(2).split(";")
                if g.strip() and "[word]" not in g and len(g.strip()) <= 40
            ]
            if not raw_glosses:
                continue
            attested = [
                g for g in raw_glosses
                if (
                    _phrase_in_en(g.lower(), en_words, en_lower_str)
                    or all(_en_stem(w) in en_stems for w in re.findall(r"[A-Za-z]+", g) if w.lower() not in STOP_EN)
                )
            ]
            chosen = attested[:2] if attested else raw_glosses[:1]
            us_w = b2u.get(surf_deva, surf_deva)
            for idx, cg in enumerate(chosen):
                if cg.lower() not in STOP_EN:
                    _add_gloss(
                        en_bare, en_us, surf_deva, us_w, cg,
                        4 if attested and idx == 0 else 2,
                        bare_cites=en_cites_bare, us_cites=en_cites_us,
                        source="Hellwig", locus=loc,
                    )

    # 4. AV Trivedi Paadatippani `(pada) Sanskrit gloss`
    if unit.trivedi_sa_text:
        for pm in re.finditer(r"\(([^)]+)\)\s*([^()]+)", unit.trivedi_sa_text):
            pw = _canon_pw(norm_sa(pm.group(1)))
            if pw not in pset:
                continue
            for clause in re.split(r"[।॥]+", pm.group(2)):
                g = _clean_sa_gloss(clause)
                if g and norm_sa(g) != pw:
                    _add_gloss(
                        sa_bare, sa_us, pw, b2u.get(pw, pw), g, 3,
                        bare_cites=sa_cites_bare, us_cites=sa_cites_us,
                        source="त्रिवेदी", locus=loc,
                    )
                    break

    # 5. Morphology-verified Sanskrit commentary glosses (Bhāskara, Sāyaṇa, Uvaṭa, Mahīdhara...)
    for comm_name, comm_txt in unit.sa_comms:
        _extract_comm_unit(
            comm_txt,
            pset,
            b2u,
            en_stems,
            lex,
            sa_bare,
            sa_us,
            alias_to_bare=alias_to_bare,
            sa_cites_bare=sa_cites_bare,
            sa_cites_us=sa_cites_us,
            source=_format_source_label(comm_name),
            locus=loc,
        )

    # 6. Hindi पदार्थः fallback
    for hi_name, hi_txt in unit.hi_comms:
        hi_src = _format_source_label(hi_name)
        for pm in re.finditer(r"\(([^)]+)\)\s*([^()]+)", hi_txt):
            pw = _canon_pw(norm_sa(pm.group(1)))
            if pw not in pset:
                continue
            g = _clean_hi_gloss(pm.group(2))
            if g and norm_sa(g) != pw:
                _add_gloss(
                    hi_bare, hi_us, pw, b2u.get(pw, pw), g, 2,
                    bare_cites=hi_cites_bare, us_cites=hi_cites_us,
                    source=hi_src, locus=loc,
                )


def _tok_clean(tok: str) -> str:
    return tok.strip(" ,;:-।॥'\"*ऽ—–!?()[]")


def _extract_comm_unit(
    comm_txt: str,
    pset: set[str],
    b2u: dict[str, str],
    en_stems: set[str],
    lex: dict[str, list[str]],
    sa_bare: dict[str, Counter[str]],
    sa_us: dict[str, Counter[str]],
    *,
    alias_to_bare: dict[str, str] | None = None,
    sa_cites_bare: CiteMap | None = None,
    sa_cites_us: CiteMap | None = None,
    source: str = "",
    locus: str = "",
) -> None:
    """Extract bolded and morph-verified adjacent Sanskrit glosses from commentary text."""
    aliases = alias_to_bare or {}
    # Bold pratikas first (`**word** gloss`), common in TS/TB.
    for pm in re.finditer(r"\*\*([^*]+)\*\*\s+([^।॥\n;]+)", comm_txt):
        pw_raw = norm_sa(pm.group(1))
        pw = aliases.get(pw_raw, pw_raw)
        if pw not in pset:
            continue
        g = _clean_sa_gloss(pm.group(2))
        if g and norm_sa(g) != pw:
            _add_gloss(
                sa_bare, sa_us, pw, b2u.get(pw, pw), g, 4,
                bare_cites=sa_cites_bare, us_cites=sa_cites_us,
                source=source, locus=locus,
            )

    for sent in re.split(r"[।॥\n]+", comm_txt):
        # Classical accents inside commentary usually mark quoted mantra lines; skip.
        if "\u0951" in sent or "\u0952" in sent:
            continue
        if _has_sa_grammar_marker(sent):
            continue
        sent_clean = re.sub(r"\([^)]*\)|\[[^\]]*\]|\*\*", " ", sent)
        for clause in re.split(r"[;]", sent_clean):
            toks = [_tok_clean(t) for t in clause.split()]
            toks = [t for t in toks if t and _DEVANAGARI_ANY_RE.search(t)]
            if len(toks) < 2:
                continue
            i = 0
            while i < len(toks) - 1:
                t_i = toks[i]
                if _DIGIT_RE.search(t_i):
                    i += 1
                    continue
                pw_raw = norm_sa(t_i)
                pw = aliases.get(pw_raw, pw_raw)
                if pw in pset and pw not in _STOP_SA_WORDS:
                    g1 = toks[i + 1]
                    gn1 = norm_sa(g1)
                    if (
                        len(gn1) > 2
                        and gn1 not in pset
                        and gn1 not in _STOP_SA_WORDS
                        and not gn1.endswith(_NON_FINAL_SA_SUFFIXES)
                        and not _DIGIT_RE.search(g1)
                    ):
                        if morph_compatible(pw, gn1):
                            cg = _clean_sa_gloss(g1)
                            if cg and norm_sa(cg) != pw:
                                bonus = 2 if _sa_corroborated_by_en(gn1, en_stems, lex) else 0
                                _add_gloss(
                                    sa_bare, sa_us, pw, b2u.get(pw, pw), cg, 2 + bonus,
                                    bare_cites=sa_cites_bare, us_cites=sa_cites_us,
                                    source=source, locus=locus,
                                )
                                i += 2
                                continue
                        if i + 2 < len(toks):
                            g2 = toks[i + 2]
                            gn2 = norm_sa(g2)
                            if (
                                len(gn2) > 2
                                and gn2 not in pset
                                and gn2 not in _STOP_SA_WORDS
                                and not gn2.endswith(_NON_FINAL_SA_SUFFIXES)
                                and not _DIGIT_RE.search(g2)
                                and morph_compatible(pw, gn2)
                            ):
                                cg2 = _clean_sa_gloss(f"{g1} {g2}")
                                if cg2 and norm_sa(cg2) != pw:
                                    bonus = 2 if _sa_corroborated_by_en(gn2, en_stems, lex) else 0
                                    _add_gloss(
                                        sa_bare, sa_us, pw, b2u.get(pw, pw), cg2, 2 + bonus,
                                        bare_cites=sa_cites_bare, us_cites=sa_cites_us,
                                        source=source, locus=locus,
                                    )
                                    i += 3
                                    continue
                i += 1


def _sa_corroborated_by_en(gn: str, en_stems: set[str], lex: dict[str, list[str]]) -> bool:
    if not en_stems:
        return False
    for cand in lex.get(gn, [])[:10]:
        for w in cand.split():
            if w not in STOP_EN and len(w) >= 3 and _en_stem(w) in en_stems:
                return True
    return False


def _fallback_lookup_keys(
    pw: str,
    stem_bare: str,
    lex: dict[str, list[str]],
) -> list[str]:
    """Generate ordered candidate keys for Sanskrit-English lexicon lookup."""
    keys: list[str] = [pw]
    if stem_bare and stem_bare not in keys:
        keys.append(stem_bare)

    # Augment stripping for Vedic past verbs (`अवेनत्` -> `वेन्` / `वेनत्`), superlatives, ṣa->sa.
    extra: list[str] = []
    for base in (pw, stem_bare):
        if not base or len(base) < 4:
            continue
        if base.startswith("ष") and ("स" + base[1:]) in lex:
            extra.append("स" + base[1:])
        if base.startswith("अ") and len(base) >= 5:
            extra.append(base[1:])
        for suf in ("इष्ठ", "ईयस्", "तम", "तर"):
            if base.endswith(suf) and len(base) - len(suf) >= 2:
                extra.append(base[: -len(suf)])
        _, _, _, _, roots = _morph_info(base)
        for r in roots:
            rb = norm_sa(r)
            if rb and len(rb) >= 2:
                extra.append(rb)

    for ek in extra:
        if ek and ek not in keys:
            keys.append(ek)
    return keys


def _align_unit_en(
    unit: MantraUnit,
    en_lower_str: str,
    en_word_set: set[str],
    en_stems_map: dict[str, list[str]],
    en_folded_map: dict[str, str],
    lex: dict[str, list[str]],
    bare_to_stem: dict[str, tuple[str, str]],
    en_bare: dict[str, Counter[str]],
    en_us: dict[str, Counter[str]],
    *,
    en_cites_bare: CiteMap | None = None,
    en_cites_us: CiteMap | None = None,
    en_source: str = "",
    weight_mult: int = 1,
) -> tuple[list[str], set[str]]:
    """Align unit padas against one accompanying English translation block."""
    content_sa: list[str] = []
    aligned_sa: set[str] = set()
    aligned_en_stems: set[str] = set()
    loc = unit.locus
    for pw, us_w in zip(unit.padas_bare, unit.padas_us):
        stem_info = bare_to_stem.get(pw)
        st_hyph = stem_info[1] if stem_info else pw
        st_bare = st_hyph.replace("-", "").replace("ँ", "ं")

        # 1. Accent-sensitive closed-class priority (`मा᳓`="not" vs `मा`="me", etc.)
        if us_w in CLOSED_US_EN:
            cands = CLOSED_US_EN[us_w]
            for cg in cands:
                if _phrase_in_en(cg.lower(), en_word_set, en_lower_str):
                    _add_gloss(
                        en_bare, en_us, pw, us_w, cg, 4 * weight_mult,
                        bare_cites=en_cites_bare, us_cites=en_cites_us,
                        source=en_source, locus=loc,
                    )
                    aligned_en_stems.update(_en_stem(w) for w in cg.split())
                    break
            continue

        if pw in CLOSED_BARE_EN or st_bare in CLOSED_STEM_EN:
            cands = CLOSED_BARE_EN.get(pw) or CLOSED_STEM_EN.get(st_bare, ())
            for cg in cands:
                if _phrase_in_en(cg.lower(), en_word_set, en_lower_str):
                    _add_gloss(
                        en_bare, en_us, pw, us_w, cg, 2 * weight_mult,
                        bare_cites=en_cites_bare, us_cites=en_cites_us,
                        source=en_source, locus=loc,
                    )
                    aligned_en_stems.update(_en_stem(w) for w in cg.split())
                    break
            continue

        content_sa.append(pw)
        lookup_keys = _fallback_lookup_keys(pw, st_bare, lex)
        matched = False

        # 2. Direct full-word / resolved-stem match against anchor lexicon
        for idx_k, lk in enumerate(lookup_keys):
            wt = (3 if idx_k < 2 else 2) * weight_mult
            for cand in lex.get(lk, []):
                if _phrase_in_en(cand, en_word_set, en_lower_str):
                    _add_gloss(
                        en_bare, en_us, pw, us_w, cand, wt,
                        bare_cites=en_cites_bare, us_cites=en_cites_us,
                        source=en_source, locus=loc,
                    )
                    aligned_sa.add(pw)
                    aligned_en_stems.update(_en_stem(w) for w in cand.split())
                    matched = True
                    break
                cw = [w for w in cand.split() if w not in STOP_EN]
                if len(cw) == 1:
                    cs = _en_stem(cw[0])
                    if cs in en_stems_map and len(cs) >= 3:
                        _add_gloss(
                            en_bare, en_us, pw, us_w, cw[0], max(1, wt - 1),
                            bare_cites=en_cites_bare, us_cites=en_cites_us,
                            source=en_source, locus=loc,
                        )
                        aligned_sa.add(pw)
                        aligned_en_stems.add(cs)
                        matched = True
                        break
            if matched:
                break

        # 3. Compound member alignment (never let bare prefix like सु alone match सु-जात)
        parts = [p.replace("ँ", "ं") for p in st_hyph.split("-") if len(p.replace("ँ", "ं")) >= 2]
        if not matched and len(parts) >= 2:
            part_hits: list[tuple[int, str]] = []
            for idx_p, pt in enumerate(parts):
                for cand in lex.get(pt, []):
                    cw = [w for w in cand.split() if w not in STOP_EN]
                    if len(cw) == 1:
                        cs = _en_stem(cw[0])
                        if cs in en_stems_map and len(cs) >= 3:
                            part_hits.append((idx_p, cw[0]))
                            aligned_en_stems.add(cs)
                            break
            if len(part_hits) >= 2:
                comp = " + ".join(w for _, w in part_hits[:2])
                _add_gloss(
                    en_bare, en_us, pw, us_w, comp, 2 * weight_mult,
                    bare_cites=en_cites_bare, us_cites=en_cites_us,
                    source=en_source, locus=loc,
                )
                aligned_sa.add(pw)
                matched = True
            elif (
                len(part_hits) == 1
                and part_hits[0][0] == len(parts) - 1
                and len(parts[-1]) >= 3
                and parts[0] not in prakrti_svara._KNOWN_AVYAYAS
            ):
                _add_gloss(
                    en_bare, en_us, pw, us_w, part_hits[0][1], weight_mult,
                    bare_cites=en_cites_bare, us_cites=en_cites_us,
                    source=en_source, locus=loc,
                )
                aligned_sa.add(pw)
                matched = True

        # 4. IAST / Harvard Oriental Series proper-noun transliteration match (`Açvin`, `Amçu`)
        if not matched:
            for lk in lookup_keys[:2]:
                iast_raw = sanscript.transliterate(lk, sanscript.DEVANAGARI, sanscript.IAST)
                for fold_fn in (_fold_ascii, _fold_ascii_loose):
                    iast_f = fold_fn(iast_raw)
                    if len(iast_f) < 4:
                        continue
                    for fa, orig_et in en_folded_map.items():
                        if fa == iast_f or (
                            len(iast_f) >= 5
                            and (fa.startswith(iast_f[:5]) or iast_f.startswith(fa[:5]))
                        ):
                            _add_gloss(
                                en_bare, en_us, pw, us_w, orig_et, 3 * weight_mult,
                                bare_cites=en_cites_bare, us_cites=en_cites_us,
                                source=en_source, locus=loc,
                            )
                            aligned_sa.add(pw)
                            aligned_en_stems.add(_en_stem(orig_et))
                            matched = True
                            break
                    if matched:
                        break
                if matched:
                    break

    unaligned_sa = [pw for pw in content_sa if pw not in aligned_sa]
    return unaligned_sa, aligned_en_stems


def _run_ibm1_stem_alignment(
    unit_pairs: list[tuple[list[str], list[str], dict[str, list[str]], dict[str, tuple[str, str]]]],
    bare_to_stem: dict[str, tuple[str, str]],
) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    """Run 5 EM iterations of IBM Model 1 on stem pairs, returning ``(stem -> gloss, stem -> cite)``."""
    if len(unit_pairs) < 5:
        return {}, {}

    def _stem_of(pw: str) -> str:
        st_info = bare_to_stem.get(pw)
        return st_info[1].replace("-", "").replace("ँ", "ं") if st_info else pw

    stem_pairs: list[tuple[list[str], list[str], dict[str, tuple[str, str]]]] = []
    surf_for_enstem: dict[str, Counter[str]] = defaultdict(Counter)
    for sa_list, en_list, emap, estem_cites in unit_pairs:
        st_list = list(dict.fromkeys(_stem_of(w) for w in sa_list))
        stem_pairs.append((st_list, en_list, estem_cites))
        for es, surfs in emap.items():
            for sf in surfs:
                surf_for_enstem[es][sf.lower()] += 1

    cooc: dict[str, Counter[str]] = defaultdict(Counter)
    cooc_cites: dict[tuple[str, str], Counter[tuple[str, str]]] = defaultdict(Counter)
    sa_cnt: Counter[str] = Counter()
    en_cnt: Counter[str] = Counter()
    for st_list, en_list, estem_cites in stem_pairs:
        for s in st_list:
            sa_cnt[s] += 1
        for e in en_list:
            en_cnt[e] += 1
        for s in st_list:
            for e in en_list:
                cooc[s][e] += 1
                cite = estem_cites.get(e)
                if cite:
                    cooc_cites[(s, e)][cite] += 1

    t_prob: dict[str, dict[str, float]] = {}
    for s, ec in cooc.items():
        tot = sum(ec.values())
        if tot > 0:
            t_prob[s] = {e: c / tot for e, c in ec.items()}

    for _ in range(5):
        counts_se: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        totals_s: dict[str, float] = defaultdict(float)
        for st_list, en_list, _ in stem_pairs:
            for e in en_list:
                s_norm = sum(t_prob.get(s, {}).get(e, 0.0) for s in st_list)
                if s_norm <= 0.0:
                    continue
                for s in st_list:
                    d = t_prob.get(s, {}).get(e, 0.0) / s_norm
                    if d > 0.0:
                        counts_se[s][e] += d
                        totals_s[s] += d
        for s, ed in counts_se.items():
            tot = totals_s[s]
            if tot > 0.0:
                t_prob[s] = {e: c / tot for e, c in ed.items() if c / tot > 0.01}

    ibm_stem_gloss: dict[str, str] = {}
    ibm_stem_cite: dict[str, tuple[str, str]] = {}
    for s, ed in t_prob.items():
        if not ed or s in CLOSED_BARE_EN or s in CLOSED_STEM_EN:
            continue
        best_e, prob = max(ed.items(), key=lambda x: x[1])
        c_se = cooc[s][best_e]
        min_cooc = 2 if sa_cnt[s] <= 3 else 3
        dice = (2.0 * c_se) / (sa_cnt[s] + en_cnt[best_e]) if (sa_cnt[s] + en_cnt[best_e]) else 0.0
        if c_se >= min_cooc and prob >= 0.35 and dice >= 0.08 and best_e in surf_for_enstem:
            ibm_stem_gloss[s] = surf_for_enstem[best_e].most_common(1)[0][0]
            if (s, best_e) in cooc_cites:
                ibm_stem_cite[s] = cooc_cites[(s, best_e)].most_common(1)[0][0]
    return ibm_stem_gloss, ibm_stem_cite


def _dedup_en_glosses(
    cnts: Counter[str],
    max_items: int = 3,
    *,
    allow_closed: bool = False,
) -> list[str]:
    """Select up to `max_items` non-redundant, concise English glosses."""
    chosen: list[str] = []
    seen_stems: set[str] = set()
    for g, _ in cnts.most_common():
        g_clean = re.sub(r"\s+", " ", g.replace("<br>", " ").replace("\n", " ")).strip(" ,;:-")
        if not g_clean or len(g_clean) > 36:
            continue
        low = g_clean.lower()
        if not allow_closed and (low in _NON_CLOSED_SINGLE_STOP or low in STOP_EN):
            continue
        words = [w for w in re.findall(r"[A-Za-z]+", g_clean) if w.lower() not in STOP_EN]
        if not words and not allow_closed:
            continue
        stem_key = tuple(sorted(_en_stem(w) for w in words)) or (low,)
        if stem_key in seen_stems:
            continue
        # Also skip single-word duplicates if already represented inside a 2-word gloss.
        if len(stem_key) == 1 and any(stem_key[0] in sk for sk in seen_stems):
            continue
        seen_stems.add(stem_key)
        chosen.append(g_clean)
        if len(chosen) >= max_items:
            break
    return chosen


def _dedup_sa_glosses(cnts: Counter[str], max_items: int = 2) -> list[str]:
    """Select up to `max_items` distinct, clean Sanskrit glosses."""
    chosen: list[str] = []
    seen_bare: set[str] = set()
    for g, _ in cnts.most_common():
        g_clean = re.sub(r"\s+", " ", g.replace("<br>", " ").replace("\n", " ")).strip(" ,;:-")
        if not g_clean or len(g_clean) > 40:
            continue
        b = norm_sa(g_clean)
        if not b or b in seen_bare:
            continue
        seen_bare.add(b)
        chosen.append(g_clean)
        if len(chosen) >= max_items:
            break
    return chosen


def _format_cite_suffix(cite: tuple[str, str] | None) -> str:
    if not cite:
        return ""
    src, loc = cite
    if src and loc:
        return f"({src} {loc})"
    if src:
        return f"({src})"
    return ""


def _shorten_before_cite(gloss: str, cite_suffix: str, budget: int) -> str:
    """Shorten gloss text while keeping its `(Source Locus)` citation intact."""
    full = f"{gloss} {cite_suffix}".strip() if cite_suffix else gloss
    if len(full) <= budget:
        return full
    if not cite_suffix:
        return gloss[: max(1, budget - 1)].rstrip(" ,;") + "…"
    avail = budget - len(cite_suffix) - 2  # space + ellipsis
    if avail >= 3:
        return gloss[:avail].rstrip(" ,;-") + "… " + cite_suffix
    return f"{gloss} {cite_suffix}"


def _format_cited_clause(
    glosses: list[str],
    cites: dict[str, Counter[tuple[str, str]]] | None,
) -> str:
    """Format glosses grouped with their top `(Source Locus)` citations."""
    if not glosses:
        return ""
    if not cites:
        return ", ".join(glosses)
    groups: list[tuple[tuple[str, str] | None, list[str]]] = []
    cite_to_idx: dict[tuple[str, str] | None, int] = {}
    for g in glosses:
        c_cnt = cites.get(_norm_gloss_key(g))
        cite = c_cnt.most_common(1)[0][0] if c_cnt else None
        if cite in cite_to_idx:
            groups[cite_to_idx[cite]][1].append(g)
        else:
            cite_to_idx[cite] = len(groups)
            groups.append((cite, [g]))
    parts: list[str] = []
    for cite, g_items in groups:
        suf = _format_cite_suffix(cite)
        txt = ", ".join(g_items)
        parts.append(f"{txt} {suf}" if suf else txt)
    return ", ".join(parts)


def format_brief_meaning(
    sa_cnt: Counter[str] | None,
    en_cnt: Counter[str] | None,
    hi_cnt: Counter[str] | None = None,
    *,
    max_len: int = 150,
    allow_closed: bool = False,
    sa_cites: dict[str, Counter[tuple[str, str]]] | None = None,
    en_cites: dict[str, Counter[tuple[str, str]]] | None = None,
    hi_cites: dict[str, Counter[tuple[str, str]]] | None = None,
) -> str:
    """Format extracted gloss counters + `(Source Locus)` citations into ONE single-line string."""
    sa_list = _dedup_sa_glosses(sa_cnt, max_items=2) if sa_cnt else []
    en_list = _dedup_en_glosses(en_cnt, max_items=3, allow_closed=allow_closed) if en_cnt else []

    if sa_list and en_list:
        for n_sa, n_en in ((len(sa_list), len(en_list)), (len(sa_list), 2), (1, 2), (1, 1)):
            s_sub = sa_list[:n_sa]
            e_sub = en_list[:n_en]
            if not s_sub or not e_sub:
                continue
            sa_str = _format_cited_clause(s_sub, sa_cites)
            en_str = _format_cited_clause(e_sub, en_cites)
            joined = f"{sa_str} · {en_str}"
            if len(joined) <= max_len:
                return joined
        # Still over max_len with 1+1: shorten gloss body before citations, preserving both cites.
        sa_c = sa_cites.get(_norm_gloss_key(sa_list[0])).most_common(1)[0][0] if sa_cites and _norm_gloss_key(sa_list[0]) in sa_cites else None
        en_c = en_cites.get(_norm_gloss_key(en_list[0])).most_common(1)[0][0] if en_cites and _norm_gloss_key(en_list[0]) in en_cites else None
        half = (max_len - 3) // 2
        sa_str = _shorten_before_cite(sa_list[0], _format_cite_suffix(sa_c), max(half, len(_format_cite_suffix(sa_c)) + 8))
        en_str = _shorten_before_cite(en_list[0], _format_cite_suffix(en_c), max(max_len - 3 - len(sa_str), len(_format_cite_suffix(en_c)) + 8))
        return f"{sa_str} · {en_str}"

    if sa_list or en_list:
        items = sa_list or en_list
        cites = sa_cites if sa_list else en_cites
        for k in range(len(items), 0, -1):
            out = _format_cited_clause(items[:k], cites)
            if len(out) <= max_len:
                return out
        top_c = cites.get(_norm_gloss_key(items[0])).most_common(1)[0][0] if cites and _norm_gloss_key(items[0]) in cites else None
        return _shorten_before_cite(items[0], _format_cite_suffix(top_c), max_len)

    if hi_cnt:
        hi_list = _dedup_sa_glosses(hi_cnt, max_items=2)
        if hi_list:
            for k in range(len(hi_list), 0, -1):
                out = _format_cited_clause(hi_list[:k], hi_cites)
                if len(out) <= max_len:
                    return out
            top_c = hi_cites.get(_norm_gloss_key(hi_list[0])).most_common(1)[0][0] if hi_cites and _norm_gloss_key(hi_list[0]) in hi_cites else None
            return _shorten_before_cite(hi_list[0], _format_cite_suffix(top_c), max_len)
    return ""


def _build_stem_map(
    bare_padas: Iterable[str],
    us_by_bare: dict[str, str],
) -> dict[str, tuple[str, str]]:
    """Map bare Devanagari padas -> `(pos, stem_hyph)` using `MorphResolver`."""
    resolver = prakrti_svara.MorphResolver()
    bare_to_stem: dict[str, tuple[str, str]] = {}
    for b in bare_padas:
        if b in bare_to_stem:
            continue
        raw = us_by_bare.get(b, b)
        npada = prakrti_svara.normalize_raw_form_to_us(raw, already_us=True)
        if npada:
            cleaned = prakrti_svara._strip_enclitic_iva(npada)
            pos, st_hyph, _, _ = resolver.resolve_word(cleaned)
            bare_to_stem[b] = (pos, st_hyph)
    return bare_to_stem


def _lemmatize_sa_for_stem(sa_gloss: str) -> str:
    """Keep Prathamā / Avyaya / single-word stem-clean Sanskrit gloss for prakṛti-svara."""
    words = sa_gloss.split()
    if len(words) != 1:
        return ""
    b = norm_sa(words[0])
    if len(b) <= 2:
        return ""
    try:
        kosha = ss.get_vidyut_kosha()
        slp = ss._deva_to_slp(b)
    except Exception:
        return ""
    cands = [slp]
    if slp.endswith("H"):
        cands.extend([slp[:-1] + "s", slp[:-1] + "r"])
    elif slp.endswith("M"):
        cands.append(slp[:-1] + "m")
    for c in cands:
        for e in kosha.get(c):
            if isinstance(e, PadaEntry.Subanta):
                pe = e.pratipadika_entry
                if getattr(pe, "is_avyaya", False) or (
                    hasattr(pe, "lingas") and len(pe.lingas) == 0
                ):
                    return b
                if str(e.vibhakti) == "praTamA":
                    return sa_gloss
                if getattr(pe, "lemma", None):
                    lem = sanscript.transliterate(
                        pe.lemma, sanscript.SLP1, sanscript.DEVANAGARI
                    )
                    if len(lem) >= 3:
                        return lem
    return ""


_CORPUS_ALIASES: dict[str, str] = {"sb": "sb-m"}


def get_corpus_config(corpus_key: str) -> CorpusConfig:
    """Return canonical :class:`CorpusConfig`, resolving aliases like ``sb -> sb-m``."""
    canonical = _CORPUS_ALIASES.get(corpus_key.lower(), corpus_key.lower())
    return CORPUS_CONFIGS[canonical]


def _cache_path(corpus_key: str, include_yantra: bool) -> str:
    canonical = _CORPUS_ALIASES.get(corpus_key.lower(), corpus_key.lower())
    suffix = "_yantra" if include_yantra else ""
    return os.path.join(_CACHE_DIR, f"vedic_meanings_{canonical}{suffix}_v2.pkl")


def extract_corpus_meanings(
    corpus_key: str,
    raw_forms: Iterable[str] | None = None,
    *,
    already_us: bool = True,
    source_dir: str | None = None,
    include_yantra: bool = False,
    use_cache: bool = True,
    refresh_cache: bool = False,
) -> CorpusMeanings:
    """Extract and format brief meanings for all attested padas & stems in a corpus.

    When ``source_dir`` differs from the corpus's default path (for instance in
    unit tests or alternate snapshots), disk caching is bypassed automatically.
    """
    config = get_corpus_config(corpus_key)
    is_default_dir = source_dir is None or os.path.abspath(source_dir) == os.path.abspath(
        config.default_source_dir
    )
    cache_file = _cache_path(corpus_key, include_yantra)

    if use_cache and is_default_dir and not refresh_cache and os.path.isfile(cache_file):
        try:
            with open(cache_file, "rb") as fh:
                cached = pickle.load(fh)
            if isinstance(cached, CorpusMeanings):
                return cached
        except Exception:
            pass

    units = parse_corpus_units(
        config,
        source_dir=source_dir,
        include_yantra=include_yantra,
    )
    if not units:
        return CorpusMeanings(
            by_us={},
            by_bare={},
            sa_by_bare={},
            sa_by_us={},
            en_by_bare={},
            en_by_us={},
            hi_by_bare={},
        )

    lex = load_sa_en_lexicon()

    # Collect every bare form & representative accented form across corpus units and caller forms.
    rep_us_by_bare: dict[str, str] = {}
    all_bare: list[str] = []
    for u in units:
        for b, us_w in zip(u.padas_bare, u.padas_us):
            if b not in rep_us_by_bare:
                rep_us_by_bare[b] = us_w
                all_bare.append(b)
    if raw_forms is not None:
        for rf in raw_forms:
            np = prakrti_svara.normalize_raw_form_to_us(rf, already_us=already_us)
            if np:
                b = np.clean_bare.replace("ँ", "ं")
                if b not in rep_us_by_bare:
                    rep_us_by_bare[b] = np.us_form.replace("ँ", "ं")
                    all_bare.append(b)

    bare_to_stem = _build_stem_map(all_bare, rep_us_by_bare)

    sa_bare: dict[str, Counter[str]] = defaultdict(Counter)
    sa_us: dict[str, Counter[str]] = defaultdict(Counter)
    en_bare: dict[str, Counter[str]] = defaultdict(Counter)
    en_us: dict[str, Counter[str]] = defaultdict(Counter)
    hi_bare: dict[str, Counter[str]] = defaultdict(Counter)
    hi_us: dict[str, Counter[str]] = defaultdict(Counter)

    sa_cites_bare: CiteMap = {}
    sa_cites_us: CiteMap = {}
    en_cites_bare: CiteMap = {}
    en_cites_us: CiteMap = {}
    hi_cites_bare: CiteMap = {}
    hi_cites_us: CiteMap = {}

    ibm_unit_pairs: list[tuple[list[str], list[str], dict[str, list[str]], dict[str, tuple[str, str]]]] = []

    for unit in units:
        # Collect up to top 2 non-empty English translations in priority order, preserving source identity.
        selected_en: list[tuple[str, str]] = []
        for en_name in config.en_priority:
            blks = unit.en_blocks.get(en_name)
            if blks:
                selected_en.append((en_name, " ".join(blks)))
            if len(selected_en) >= 2:
                break

        en_texts = [t for _, t in selected_en]
        en_tokens, en_lower, _en_ws, en_stems_map, _en_fm = _extract_unit_en_context(en_texts)
        en_stem_set = set(en_stems_map.keys())

        _extract_structured_and_commentary(
            unit=unit,
            en_stems=en_stem_set,
            lex=lex,
            sa_bare=sa_bare,
            sa_us=sa_us,
            en_bare=en_bare,
            en_us=en_us,
            hi_bare=hi_bare,
            hi_us=hi_us,
            en_lower_str=en_lower,
            sa_cites_bare=sa_cites_bare,
            sa_cites_us=sa_cites_us,
            en_cites_bare=en_cites_bare,
            en_cites_us=en_cites_us,
            hi_cites_bare=hi_cites_bare,
            hi_cites_us=hi_cites_us,
        )

        if selected_en:
            aligned_sa_all: set[str] = set()
            aligned_en_stems_all: set[str] = set()
            estem_cites: dict[str, tuple[str, str]] = {}
            for idx_en, (en_name, en_txt) in enumerate(selected_en):
                src_lbl = _format_source_label(en_name)
                _toks, loc_low, loc_ws, loc_smap, loc_fm = _extract_unit_en_context([en_txt])
                for es in loc_smap:
                    if es not in estem_cites:
                        estem_cites[es] = (src_lbl, unit.locus)
                unaligned_single, aligned_en_single = _align_unit_en(
                    unit=unit,
                    en_lower_str=loc_low,
                    en_word_set=loc_ws,
                    en_stems_map=loc_smap,
                    en_folded_map=loc_fm,
                    lex=lex,
                    bare_to_stem=bare_to_stem,
                    en_bare=en_bare,
                    en_us=en_us,
                    en_cites_bare=en_cites_bare,
                    en_cites_us=en_cites_us,
                    en_source=src_lbl,
                    weight_mult=2 if idx_en == 0 else 1,
                )
                aligned_en_stems_all.update(aligned_en_single)
                u_set = set(unaligned_single)
                for pw in unit.padas_bare:
                    if pw not in u_set and pw not in CLOSED_BARE_EN:
                        aligned_sa_all.add(pw)

            unaligned_sa = [
                pw for pw in unit.padas_bare
                if pw not in CLOSED_BARE_EN
                and (bare_to_stem[pw][1].replace("-", "").replace("ँ", "ं") if pw in bare_to_stem else pw) not in CLOSED_STEM_EN
                and pw not in aligned_sa_all
            ]
            content_en = [
                _en_stem(t.lower())
                for t in en_tokens
                if t.lower() not in STOP_EN
                and len(t) >= 3
                and _en_stem(t.lower()) not in aligned_en_stems_all
                and t.lower() not in _DEITY_NOUNS
            ]
            if unaligned_sa and content_en:
                ibm_unit_pairs.append(
                    (
                        list(dict.fromkeys(unaligned_sa)),
                        list(dict.fromkeys(content_en)),
                        en_stems_map,
                        estem_cites,
                    )
                )

    # Corpus-local IBM Model 1 stem alignment for unaligned/technical Vedic terms.
    ibm_stem_gloss, ibm_stem_cite = _run_ibm1_stem_alignment(ibm_unit_pairs, bare_to_stem)

    # Stem aggregation for English meanings & stem-safe Sanskrit glosses (with citations).
    stem_sa_counts: dict[str, Counter[str]] = defaultdict(Counter)
    stem_en_counts: dict[str, Counter[str]] = defaultdict(Counter)
    stem_hi_counts: dict[str, Counter[str]] = defaultdict(Counter)
    stem_sa_cites: CiteMap = {}
    stem_en_cites: CiteMap = {}
    stem_hi_cites: CiteMap = {}

    def _merge_cites(dst: CiteMap, key: str, gk: str, src_cnt: Counter[tuple[str, str]] | None) -> None:
        if not src_cnt:
            return
        d = dst.get(key)
        if d is None:
            d = {}
            dst[key] = d
        c = d.get(gk)
        if c is None:
            c = Counter()
            d[gk] = c
        c.update(src_cnt)

    for pw, cnts in en_bare.items():
        if pw in CLOSED_BARE_EN:
            continue
        st = bare_to_stem[pw][1].replace("-", "").replace("ँ", "ं") if pw in bare_to_stem else pw
        if st not in CLOSED_STEM_EN:
            stem_en_counts[st].update(cnts)
            for gk, c_cnt in en_cites_bare.get(pw, {}).items():
                _merge_cites(stem_en_cites, st, gk, c_cnt)
    for st, gl in ibm_stem_gloss.items():
        stem_en_counts[st][gl] += 1
        cite = ibm_stem_cite.get(st)
        if cite:
            _merge_cites(stem_en_cites, st, _norm_gloss_key(gl), Counter({cite: 1}))

    for pw, cnts in sa_bare.items():
        st = bare_to_stem[pw][1].replace("-", "").replace("ँ", "ं") if pw in bare_to_stem else pw
        pw_cites = sa_cites_bare.get(pw, {})
        for sg, c in cnts.most_common(4):
            lem = _lemmatize_sa_for_stem(sg)
            if lem and norm_sa(lem) != st:
                stem_sa_counts[st][lem] += c
                _merge_cites(stem_sa_cites, st, _norm_gloss_key(lem), pw_cites.get(_norm_gloss_key(sg)))

    for pw, cnts in hi_bare.items():
        st = bare_to_stem[pw][1].replace("-", "").replace("ँ", "ं") if pw in bare_to_stem else pw
        stem_hi_counts[st].update(cnts)
        for gk, c_cnt in hi_cites_bare.get(pw, {}).items():
            _merge_cites(stem_hi_cites, st, gk, c_cnt)

    # Format final lookups:
    # 1) Exact US-accented entries (`मा᳓` vs `मा`, etc.)
    all_us_keys = set(sa_us.keys()) | set(en_us.keys()) | set(hi_us.keys()) | set(CLOSED_US_EN.keys())
    by_us: dict[str, str] = {}
    for us_k in all_us_keys:
        if us_k in CLOSED_US_EN and us_k not in en_us and us_k not in sa_us:
            continue
        is_c = us_k in CLOSED_US_EN or norm_sa(us_k) in CLOSED_BARE_EN
        m_str = format_brief_meaning(
            sa_us.get(us_k),
            en_us.get(us_k),
            hi_us.get(us_k),
            allow_closed=is_c,
            sa_cites=sa_cites_us.get(us_k),
            en_cites=en_cites_us.get(us_k),
            hi_cites=hi_cites_us.get(us_k),
        )
        if m_str:
            by_us[us_k] = m_str

    # 2) Bare entries (direct -> IBM1 stem -> propagated English stem)
    all_b_keys = set(all_bare) | set(sa_bare.keys()) | set(en_bare.keys()) | set(hi_bare.keys())
    by_bare: dict[str, str] = {}
    for pw in all_b_keys:
        if pw in CLOSED_BARE_EN:
            # Closed-class bare words must rely on direct attested us_w/pw only.
            m_str = format_brief_meaning(
                sa_bare.get(pw),
                en_bare.get(pw),
                hi_bare.get(pw),
                allow_closed=True,
                sa_cites=sa_cites_bare.get(pw),
                en_cites=en_cites_bare.get(pw),
                hi_cites=hi_cites_bare.get(pw),
            )
            if m_str:
                by_bare[pw] = m_str
            continue
        st = bare_to_stem[pw][1].replace("-", "").replace("ँ", "ं") if pw in bare_to_stem else pw
        en_c = Counter(en_bare.get(pw, ()))
        en_c_cites = en_cites_bare.get(pw)
        if not en_c:
            if st in stem_en_counts:
                for g, c in stem_en_counts[st].most_common(4):
                    en_c[g] += c
                en_c_cites = stem_en_cites.get(st)
            elif st in ibm_stem_gloss:
                en_c[ibm_stem_gloss[st]] += 1
                if st in ibm_stem_cite:
                    en_c_cites = {_norm_gloss_key(ibm_stem_gloss[st]): Counter({ibm_stem_cite[st]: 1})}
        m_str = format_brief_meaning(
            sa_bare.get(pw),
            en_c,
            hi_bare.get(pw),
            allow_closed=False,
            sa_cites=sa_cites_bare.get(pw),
            en_cites=en_c_cites,
            hi_cites=hi_cites_bare.get(pw),
        )
        if m_str:
            by_bare[pw] = m_str

    result = CorpusMeanings(
        by_us=by_us,
        by_bare=by_bare,
        sa_by_bare=dict(sa_bare),
        sa_by_us=dict(sa_us),
        en_by_bare=dict(en_bare),
        en_by_us=dict(en_us),
        hi_by_bare=dict(hi_bare),
        stem_sa_counts=dict(stem_sa_counts),
        stem_en_counts=dict(stem_en_counts),
        stem_hi_counts=dict(stem_hi_counts),
        sa_cites_by_bare=sa_cites_bare,
        sa_cites_by_us=sa_cites_us,
        en_cites_by_bare=en_cites_bare,
        en_cites_by_us=en_cites_us,
        hi_cites_by_bare=hi_cites_bare,
        stem_sa_cites=stem_sa_cites,
        stem_en_cites=stem_en_cites,
        stem_hi_cites=stem_hi_cites,
    )

    if use_cache and is_default_dir:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with open(cache_file, "wb") as fh:
            pickle.dump(result, fh)

    return result


def reformat_corpus_meanings(cm: CorpusMeanings) -> CorpusMeanings:
    """Recompute ``by_us`` and ``by_bare`` from raw counters with current filters."""
    by_us: dict[str, str] = {}
    for us_k in set(cm.by_us.keys()) | set(cm.sa_by_us.keys()) | set(cm.en_by_us.keys()):
        is_c = us_k in CLOSED_US_EN or norm_sa(us_k) in CLOSED_BARE_EN
        m_str = format_brief_meaning(
            cm.sa_by_us.get(us_k),
            cm.en_by_us.get(us_k),
            None,
            allow_closed=is_c,
            sa_cites=cm.sa_cites_by_us.get(us_k),
            en_cites=cm.en_cites_by_us.get(us_k),
        )
        if m_str:
            by_us[us_k] = m_str

    by_bare: dict[str, str] = {}
    all_b = set(cm.by_bare.keys()) | set(cm.sa_by_bare.keys()) | set(cm.en_by_bare.keys()) | set(cm.hi_by_bare.keys())
    for pw in all_b:
        is_c = pw in CLOSED_BARE_EN
        if pw in cm.en_by_bare or is_c:
            m_str = format_brief_meaning(
                cm.sa_by_bare.get(pw),
                cm.en_by_bare.get(pw),
                cm.hi_by_bare.get(pw),
                allow_closed=is_c,
                sa_cites=cm.sa_cites_by_bare.get(pw),
                en_cites=cm.en_cites_by_bare.get(pw),
                hi_cites=cm.hi_cites_by_bare.get(pw),
            )
            if m_str:
                by_bare[pw] = m_str
            continue
        old = cm.by_bare.get(pw, "")
        if not old:
            continue
        if " · " in old:
            sa_part, en_part = old.split(" · ", 1)
            en_kept = [g.strip() for g in en_part.split(", ") if g.strip().lower() not in _NON_CLOSED_SINGLE_STOP]
            by_bare[pw] = f"{sa_part} · {', '.join(en_kept)}" if en_kept else sa_part
        elif pw in cm.sa_by_bare or pw in cm.hi_by_bare:
            m_str = format_brief_meaning(
                cm.sa_by_bare.get(pw),
                None,
                cm.hi_by_bare.get(pw),
                sa_cites=cm.sa_cites_by_bare.get(pw),
                hi_cites=cm.hi_cites_by_bare.get(pw),
            )
            if m_str:
                by_bare[pw] = m_str
        else:
            en_kept = [g.strip() for g in old.split(", ") if g.strip().lower() not in _NON_CLOSED_SINGLE_STOP]
            if en_kept:
                by_bare[pw] = ", ".join(en_kept)

    cm.by_us = by_us
    cm.by_bare = by_bare
    return cm


def format_stem_meaning(
    cm: CorpusMeanings,
    sas_stem: str,
    *,
    is_avyaya: bool = False,
) -> str:
    """Return brief contextual meaning for a prakṛti-svara nominal or avyaya stem."""
    if is_avyaya and sas_stem in cm.by_us:
        return cm.by_us[sas_stem]
    bare_nodash = norm_sa(sas_stem)
    if bare_nodash in CLOSED_BARE_EN:
        if sas_stem in CLOSED_US_EN:
            return cm.by_us.get(sas_stem, "")
        return cm.by_us.get(sas_stem, "") or cm.by_bare.get(bare_nodash, "")
    sa_c = cm.stem_sa_counts.get(bare_nodash)
    en_c = cm.stem_en_counts.get(bare_nodash)
    hi_c = cm.stem_hi_counts.get(bare_nodash)
    if sa_c or en_c or hi_c:
        return format_brief_meaning(
            sa_c,
            en_c,
            hi_c,
            sa_cites=cm.stem_sa_cites.get(bare_nodash),
            en_cites=cm.stem_en_cites.get(bare_nodash),
            hi_cites=cm.stem_hi_cites.get(bare_nodash),
        )
    return cm.by_bare.get(bare_nodash, "")


def _merge_cite_agg(
    dst: dict[str, Counter[tuple[str, str]]],
    src: dict[str, Counter[tuple[str, str]]] | None,
) -> None:
    if not src:
        return
    for gk, c_cnt in src.items():
        if gk not in dst:
            dst[gk] = Counter()
        dst[gk].update(c_cnt)


def format_dhatu_meaning(
    cm: CorpusMeanings,
    attested_forms: Iterable[str],
) -> str:
    """Aggregate brief meaning for a `[धातुः]` entry strictly from its attested verb forms."""
    sa_agg: Counter[str] = Counter()
    en_agg: Counter[str] = Counter()
    hi_agg: Counter[str] = Counter()
    sa_c_agg: dict[str, Counter[tuple[str, str]]] = {}
    en_c_agg: dict[str, Counter[tuple[str, str]]] = {}
    hi_c_agg: dict[str, Counter[tuple[str, str]]] = {}
    for f in attested_forms:
        b = norm_sa(f)
        if not b:
            continue
        if b in cm.sa_by_bare:
            sa_agg.update(cm.sa_by_bare[b])
            _merge_cite_agg(sa_c_agg, cm.sa_cites_by_bare.get(b))
        if b in cm.en_by_bare:
            en_agg.update(cm.en_by_bare[b])
            _merge_cite_agg(en_c_agg, cm.en_cites_by_bare.get(b))
        if b in cm.hi_by_bare:
            hi_agg.update(cm.hi_by_bare[b])
            _merge_cite_agg(hi_c_agg, cm.hi_cites_by_bare.get(b))
    return format_brief_meaning(
        sa_agg,
        en_agg,
        hi_agg,
        sa_cites=sa_c_agg,
        en_cites=en_c_agg,
        hi_cites=hi_c_agg,
    )


def build_meaning_lookup_map(
    corpus_key: str,
    counts: dict[str, int],
    *,
    already_us: bool = True,
    source_dir: str | None = None,
    use_cache: bool = True,
    refresh_cache: bool = False,
) -> dict[str, str]:
    """Compute a ``{sasvara_word: brief_meaning}`` map ready for ``dump_padasvara_babylon``."""
    cm = extract_corpus_meanings(
        corpus_key,
        raw_forms=counts.keys(),
        already_us=already_us,
        source_dir=source_dir,
        use_cache=use_cache,
        refresh_cache=refresh_cache,
    )
    out: dict[str, str] = {}
    for w in counts:
        m = cm.lookup(w)
        if m:
            out[w] = m
    return out
