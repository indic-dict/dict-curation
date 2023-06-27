import regex

import dict_curation.babylon
import dict_curation.babylon.definitions_helper
from dict_curation.babylon import headwords_helper
from doc_curation.utils import sanskrit_helper


def add_sanskrit_roots(file_path, dry_run=False):
  def root_adder(headwords, definition):
    new_headwords = []
    for headword in headwords:
      new_headwords.append(sanskrit_helper.deduce_root(text=headword))
    return (new_headwords, definition)
  dict_curation.babylon.definitions_helper.transform_entries(file_path=file_path, transformer=root_adder, dry_run=dry_run)


def fix_sheth(dry_run=False):
  def headword_extractor(headwords, definition):
    headwords = regex.findall(r"\[.+?\]", definition)
    headwords = [x[1:-1].strip() for x in headwords]
    headwords = [regex.sub(r" *\+ *", "", x) for x in headwords]
    headwords = [x for x in headwords if not x.startswith("°")]
    return (headwords, definition)
  dict_curation.babylon.definitions_helper.transform_entries(file_path="/home/vvasuki/indic-dict/stardict_all/stardict-prakrit/prakrit-head/hi-entries/sheth/sheth.babylon", transformer=headword_extractor, dry_run=dry_run)


if __name__ == '__main__':
  add_sanskrit_roots(file_path="/home/vvasuki/gitland/indic-dict_stardict/stardict-sanskrit-kAvya/mahAbhArata-kRShNAchArya/mahAbhArata-kRShNAchArya.babylon", dry_run=False)
  pass