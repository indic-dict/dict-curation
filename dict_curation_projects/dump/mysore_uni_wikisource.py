import os

from curation_utils import scraping
from dict_curation.babylon import language, cleaner
from dict_curation.scrape import dump_babylon, dump_babylon_parallel
from doc_curation.scraping import wikisource
from doc_curation.scraping.html_scraper import souper

base_dir = "/home/vvasuki/indic-dict/stardict_all/stardict-kannada/kn-head/kn-entries/maisUru-vishvakosha"
babylon_file = os.path.join(base_dir, os.path.basename(base_dir) + ".babylon.local")


def url_gatherer(soup, url):
  return souper.gather_urls(soup=soup, css="li>a[title]", base_url=url, link_filter=lambda x: "ಮೈಸೂರು ವಿಶ್ವವಿದ್ಯಾನಿಲಯ ವಿಶ್ವಕೋಶ/" in x.text)


def get_definition(url):
  soup = scraping.get_soup(url)
  souper.strip_comments(soup=soup)
  souper.element_remover(soup=soup, css_selector="h2")
  headword_element = soup.select_one('#firstHeading')
  if headword_element is None:
    return (None, None)
  headword = headword_element.text.split("/")[-1].strip()
  definition_element = soup.select_one("div.mw-parser-output")
  if definition_element is None:
    return (None, None)
  
  definition_text = str(definition_element).replace("\n", "").replace(" ", "").replace("<p></p>", "")
  definition = f"{headword}<br><br>{definition_text}"
  return ([headword], definition)


def dump():
  urls = souper.get_indexed_urls(start_url="https://kn.wikisource.org/wiki/ವರ್ಗ:ಮೈಸೂರು_ವಿಶ್ವವಿದ್ಯಾನಿಲಯ_ವಿಶ್ವಕೋಶ", next_url_getter=lambda x, y: wikisource.next_url_getter(x, y, next_url_text="ಮುಂದಿನ ಪುಟ"), url_gatherer=url_gatherer, url_file_path=os.path.join(base_dir, "urls.tsv"))
  dump_babylon_parallel(urls=urls, get_definition=get_definition, dest_path=babylon_file)


if __name__ == '__main__':
  # language.set_languages(file_path=babylon_file)
  cleaner.split_to_chunks(input_path=babylon_file, num_chunks=4)