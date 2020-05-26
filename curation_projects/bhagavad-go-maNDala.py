import codecs
import logging
import os

from selenium.webdriver.support.select import Select

from curation_utils import scraping

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")



letters = "અ આ ઇ ઈ ઉ ઊ ઋ ઌ ઍ એ ઐ ઑ ઓ ઔ ક ખ ગ ઘ ઙ ચ છ જ ઝ ઞ ટ ઠ ડ ઢ ણ ત થ દ ધ ન પ ફ બ ભ મ ય ર લ ળ વ શ ષ સ હ ૐ ૠ ૡ".split()


browser = scraping.get_selenium_browser(headless=False)

def get_letter_headwords(letter, file_out):
    url = "http://www.bhagwadgomandal.com/index.php?action=dictionary&sitem=%s&type=1&page=0" % letter
    logging.info("Processing %s", letter)
    browser.get(url=url)
    page_dropdown = browser.find_element_by_name("pgInd")
    page_options = list(page_dropdown.find_elements_by_css_selector("option"))
    logging.info("Number of pages: %d", len(page_options))
    browser.implicitly_wait(500)

    for option_index in range(1, len(page_options)+1):
        logging.info("Page %d", option_index)
        page_dropdown = browser.find_element_by_name("pgInd")
        word_elements = browser.find_elements_by_css_selector("a.word")
        words = [w.text for w in word_elements]
        file_out.write("\n".join(words) + "\n")
        Select(page_dropdown).select_by_index(option_index)


def get_headwords(out_path):
    os.makedirs(os.path.dirname(out_path))
    with codecs.open(out_path, "w", 'utf-8') as file_out:
        for letter in letters:
            get_letter_headwords(letter=letter, file_out=file_out)


if __name__ == '__main__':
    get_headwords(out_path="/home/vvasuki/indic-dict/stardict-gujarati/gu-head/bhagavad-go-maNDala/mUlam/headwords.csv")
