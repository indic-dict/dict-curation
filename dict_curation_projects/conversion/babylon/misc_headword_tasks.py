import regex

import dict_curation.babylon
from dict_curation.babylon import headwords_helper


def fix_sheth(dry_run=False):
  def headword_extractor(headwords, definition):
    headwords = regex.findall(r"\[.+?\]", definition)
    headwords = [x[1:-1].strip() for x in headwords]
    headwords = [regex.sub(r" *\+ *", "", x) for x in headwords]
    headwords = [x for x in headwords if not x.startswith("°")]
    return (headwords, definition)
  dict_curation.babylon.transform_entries(file_path="/home/vvasuki/indic-dict/stardict_all/stardict-prakrit/prakrit-head/hi-entries/sheth/sheth.babylon", headword_transformer=headword_extractor, dry_run=dry_run)


if __name__ == '__main__':
  fix_sheth(dry_run=False)
  pass