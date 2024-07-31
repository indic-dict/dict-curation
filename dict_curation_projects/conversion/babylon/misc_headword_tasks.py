import regex

from indic_transliteration import sanscript, aksharamukha_helper, detect
from indic_transliteration.sanscript.schemes.brahmic import accent

from dict_curation import babylon
import dict_curation.babylon.definitions_helper
from dict_curation.babylon import headwords_helper, lipi
from doc_curation.utils import sanskrit_helper


def add_sanskrit_roots(file_path, dry_run=False):
  def root_adder(headwords, definition):
    new_headwords = []
    for headword in headwords:
      new_headwords.append(sanskrit_helper.deduce_root(text=headword))
    return (new_headwords, definition)
  babylon.transform(file_path=file_path, transformer=root_adder, dry_run=dry_run)


def fix_sheth(dry_run=False):
  def headword_extractor(headwords, definition):
    headwords = regex.findall(r"\[.+?\]", definition)
    headwords = [x[1:-1].strip() for x in headwords]
    headwords = [regex.sub(r" *\+ *", "", x) for x in headwords]
    headwords = [x for x in headwords if not x.startswith("°")]
    return (headwords, definition)
  babylon.transform(file_path="/home/vvasuki/indic-dict/stardict_all/stardict-prakrit/prakrit-head/hi-entries/sheth/sheth.babylon", transformer=headword_extractor, dry_run=dry_run)




def fix_whitney():
  def headword_extractor(headwords, definition):
    extra_headwords = regex.findall(r"(?<=<b>).+?(?=</b>)", definition)
    extra_headwords = [x.strip() for x in extra_headwords]
    headwords.extend(extra_headwords)
    headwords = [sanscript.transliterate(data=x, _from=sanscript.IAST, _to=sanscript.DEVANAGARI) for x in headwords if not x.startswith("√")]
    headwords = [accent.strip_accents(x) for x in headwords]
    italics = regex.findall(r"(?<=<i>).+?(?=</i>)", definition)
    if len(italics) > 0:
      short_meaning = italics[0].strip().replace("'", "").strip()
      if not short_meaning.startswith("see"):
        headwords.append(short_meaning)
    return (headwords, definition)
  babylon.transform(file_path="/home/vvasuki/gitland/indic-dict/dicts/stardict-sanskrit/sa-head/en-entries/whitney-roots/whitney-roots.babylon", transformer=headword_extractor, dry_run=False)


def transliterate_headwords():
  babylon.transform(file_path="/home/vvasuki/gitland/indic-dict/dicts/stardict-pali/pali-head/en-entries/myAnmAr-abhidhAna_en/myAnmAr-abhidhAna_en.babylon", transformer=lipi.transliterate_headword_with_sanscript, dry_run=False)


if __name__ == '__main__':
  transliterate_headwords()
  # fix_whitney()
  # add_sanskrit_roots(file_path="/home/vvasuki/gitland/indic-dict_stardict/stardict-sanskrit-kAvya/mahAbhArata-kRShNAchArya/mahAbhArata-kRShNAchArya.babylon", dry_run=False)
  pass