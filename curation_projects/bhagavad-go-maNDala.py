import codecs
import logging
import os
from functools import partial
from multiprocessing import Pool

from indic_transliteration import sanscript
from selenium.webdriver.support.select import Select

from curation_utils import scraping

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")



letters = "અ આ ઇ ઈ ઉ ઊ ઋ ઌ ઍ એ ઐ ઑ ઓ ઔ ક ખ ગ ઘ ઙ ચ છ જ ઝ ઞ ટ ઠ ડ ઢ ણ ત થ દ ધ ન પ ફ બ ભ મ ય ર લ ળ વ શ ષ સ હ ૐ ૠ ૡ".split()



def get_letter_headwords(letter, out_path_dir):
    browser = scraping.get_selenium_browser(headless=True)
    out_path = os.path.join(out_path_dir, letter + ".csv")
    if os.path.exists(out_path):
        logging.warning("Skipping %s as %s exists", letter, out_path)
        return 0 
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with codecs.open(out_path, "w", 'utf-8') as file_out:
        url = "http://www.bhagwadgomandal.com/index.php?action=dictionary&sitem=%s&type=1&page=0" % letter
        logging.info("Processing %s", letter)
        browser.get(url=url)
        page_dropdown = browser.find_element_by_name("pgInd")
        page_options = list(page_dropdown.find_elements_by_css_selector("option"))
        logging.info("Number of pages: %d", len(page_options))
        browser.implicitly_wait(250)
    
        word_count = 0 
        for option_index in range(0, len(page_options)):
            Select(page_dropdown).select_by_index(option_index)
            if word_count % 10 == 0:
                logging.info("Page %s, index %d", letter, option_index)
            page_dropdown = browser.find_element_by_name("pgInd")
            word_elements = browser.find_elements_by_css_selector("a.word")
            words = [w.text for w in word_elements]
            word_count = word_count + len(words)
            file_out.write("\n".join(words) + "\n")
            
        browser.close()
        return word_count


def get_headwords(out_path):
    pool = Pool(4)
    f = partial(get_letter_headwords, out_path_dir=out_path)
    counts = pool.map(f, letters)
    logging.info(zip(letters, counts))


def get_definition(headword, browser):
    url = "http://www.bhagavadgomandal.com/index.php?action=dictionary&sitem=%s&type=3&page=0" % headword
    browser.get(url=url)
    for detail_link in browser.find_elements_by_css_selector("a.detaillink"):
        detail_link.click()
    rows = browser.find_elements_by_css_selector("div.right_middle tr")
    definition = ""
    for row in rows:
        column_data = [c.text for c in row.find_elements_by_css_selector("td")]
        row_definition = " ".join(column_data[0:2]) + "<br><br>" + column_data[3].replace("\n", "<br>")
        definition = definition + row_definition + "<br><br>"
    return definition.replace(":", "ઃ")


def dump_letter_definitions(letter, in_path_dir, out_path_dir, out_path_dir_devanagari):
    browser = scraping.get_selenium_browser(headless=True)
    in_path = os.path.join(in_path_dir, letter + ".csv")
    out_path = os.path.join(out_path_dir, letter + ".babylon")
    out_path_devanagari_entries = os.path.join(out_path_dir_devanagari, letter + ".babylon")
    if os.path.exists(out_path):
        logging.warning("Skipping %s since %s exists", letter, out_path)
    
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    os.makedirs(os.path.dirname(out_path_devanagari_entries), exist_ok=True)
    count = 0
    with codecs.open(in_path, "r", 'utf-8') as file_in, codecs.open(out_path, "w", 'utf-8') as file_out, codecs.open(out_path_devanagari_entries, "w", 'utf-8') as file_out_devanagari:
        while True:
            headword = file_in.readline()
            if not headword:
                break
            if count % 10 == 0:
                logging.info("Letter: %s, count: %d, headword: %s", letter, count, headword)
            definition = get_definition(headword=headword, browser=browser)
            headword = headword.strip().replace(":", "ઃ")
            devanagari_headword = sanscript.transliterate(data=headword, _from=sanscript.GUJARATI, _to=sanscript.DEVANAGARI)
            definition_devanagari = sanscript.transliterate(data=definition, _from=sanscript.GUJARATI, _to=sanscript.DEVANAGARI)
            file_out.writelines(["%s|%s\n%s\n\n" % (headword, devanagari_headword, definition)])
            file_out_devanagari.writelines(["%s|%s\n%s\n\n" % (headword, devanagari_headword, definition_devanagari)])
            count = count + 1
    browser.close()
    return count


def dump_definitions(in_path_dir, out_path_dir, out_path_dir_devanagari):
    from tqdm.contrib.concurrent import process_map  # or thread_map
    f = partial(dump_letter_definitions, in_path_dir=in_path_dir, out_path_dir=out_path_dir, out_path_dir_devanagari=out_path_dir_devanagari)
    results = process_map(f, letters, max_workers=4)
    logging.info(zip(letters, results))


if __name__ == '__main__':
    get_headwords(out_path="/home/vvasuki/indic-dict/stardict-gujarati/gu-head/bhagavad-go-maNDala/mUlam/")
    dump_definitions(in_path_dir="/home/vvasuki/indic-dict/stardict-gujarati/gu-head/bhagavad-go-maNDala/mUlam/", out_path_dir="/home/vvasuki/indic-dict/stardict-gujarati/gu-head/gu-entries/bhagavad-go-maNDala/mUlam/", out_path_dir_devanagari="/home/vvasuki/indic-dict/stardict-gujarati/gu-head/dev-entries/bhagavad-go-maNDala/mUlam/")
