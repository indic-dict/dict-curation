import regex

from dict_curation.babylon import headwords_helper


def fix_sheth(dry_run=False):
  def headword_extractor(def_line):
    headwords = regex.findall(r"\[.+?\]", def_line)
    headwords = [x[1:-1].strip() for x in headwords]
    headwords = [regex.sub(r" *\+ *", "", x) for x in headwords]
    headwords = [x for x in headwords if not x.startswith("°")]
    return headwords
  headwords_helper.add_headwords_from_definitions(file_path="/home/vvasuki/indic-dict/stardict_all/stardict-prakrit/prakrit-head/hi-entries/sheth/sheth.babylon", headword_extractor=headword_extractor, dry_run=dry_run)


if __name__ == '__main__':
  fix_sheth(dry_run=False)
  pass