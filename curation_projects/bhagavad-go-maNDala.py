import argparse
import codecs
import logging
import os
from functools import partial
from multiprocessing import Pool

import regex
import requests
import tqdm
from indic_transliteration import sanscript
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.select import Select

from curation_utils import scraping
from dict_curation import babylon

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")


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
        page_dropdown = None
        num_pages = 1
        try:
            page_dropdown = browser.find_element_by_name("pgInd")
            num_pages = len(page_dropdown.find_elements_by_css_selector("option"))
        except NoSuchElementException:
            logging.warning("Got no pages for %s", letter)
        logging.info("Number of pages: %d for %s", num_pages, letter)
        browser.implicitly_wait(250)
    
        word_count = 0 
        for option_index in range(0, num_pages):
            if page_dropdown is not None:
                Select(page_dropdown).select_by_index(option_index)
                page_dropdown = browser.find_element_by_name("pgInd")
            if word_count % 10 == 0:
                logging.info("Page %s, index %d", letter, option_index)
            word_elements = browser.find_elements_by_css_selector("a.word")
            words = [w.text for w in word_elements]
            word_count = word_count + len(words)
            file_out.write("\n".join(words) + "\n")
            
        browser.close()
        return word_count


def get_headwords(letters, out_path):
    pool = Pool(4)
    f = partial(get_letter_headwords, out_path_dir=out_path)
    counts = pool.map(f, letters)
    logging.info(list(zip(letters, counts)))


def get_definition(headword, existing_definitions={}, log=None):
    if headword in existing_definitions:
        existing_definition = existing_definitions[headword]
        existing_definition = existing_definition.replace("%s<br>" % headword, "").strip()
        if existing_definition != "" and "શોધી રહ્યા છે" not in existing_definition:
            return existing_definitions[headword]
    
    # type=3 sometimes fails while type=1 succeeds.
    url = "http://www.bhagavadgomandal.com/index.php?action=dictionary&sitem=%s&type=1&page=0" % headword
    
    if log is not None:
        log.set_description_str("Getting %s: %s" % (headword, url))
    soup = scraping.get_soup(url)
    # except TimeoutException:
    #     log.set_description_str("ERROR: Timed out getting  %s: %s" % (headword, url))
    #     raise 
    detail_links = soup.select("a.detaillink")
    for detail_link in detail_links:
        js = detail_link["onclick"] # ClickonDetails(80404,156152);
        detail_parts = js.replace("ClickonDetails(", "").replace(")", "").replace(";", "").split(",")
        assert len(detail_parts) == 2
        detail_url = "http://www.bhagavadgomandal.com/index.php?action=getotherdetails&fkword=%s&fkmeaning=%s" % (detail_parts[0], detail_parts[1])
        result = requests.get(detail_url)
        if "DB Select Error" in result.text:
            logging.warning("Could not expand details! %s %s" % (url, detail_url))
            detail_link.string = "શોધી રહ્યા છે  ॥ "
        else:
            detail_link.string = result.text
    rows = soup.select("div.right_middle table table tr")
    definition_body = ""
    for row in rows[1:]:
        columns = row.find_all("td")
        meta_text = [column.string if column.string is not None else "" for column in columns]
        if len(columns) < 4:
            row_definition = " ".join(row.stripped_strings)
            logging.warning("Could not get definition! %s %s" % (url, row_definition))
        else:
            definition_texts = columns[3].stripped_strings
            definition_item = "<br>".join(definition_texts).replace(".", "  ॥ ")
            definition_item = regex.sub("\n+", "<br>", definition_item)
            row_definition = "%s<br>%s<br><br>" % (" ".join(meta_text[0:2]), definition_item)
        definition_body = definition_body + row_definition
    if definition_body.strip() == "":
        return ""
    return ("%s<br>%s" % (headword, definition_body)).replace(":", "ઃ")


def dump_letter_definitions(letter, in_path_dir, out_path_dir, out_path_dir_devanagari):
    in_path = os.path.join(in_path_dir, letter + ".csv")
    out_path = os.path.join(out_path_dir, letter + ".babylon")
    out_path_devanagari_entries = os.path.join(out_path_dir_devanagari, letter + ".babylon")
    if os.path.exists(out_path) and os.path.exists(out_path_devanagari_entries) :
        logging.warning("Skipping %s since %s exists", letter, out_path)
        return 0
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    os.makedirs(os.path.dirname(out_path_devanagari_entries), exist_ok=True)
    count = 0
    empty_count = 0
    incomplete_count = 0
    existing_definitions = babylon.get_definitions(out_path)
    with codecs.open(in_path, "r", 'utf-8') as file_in, codecs.open(out_path, "w", 'utf-8') as file_out, codecs.open(out_path_devanagari_entries, "w", 'utf-8') as file_out_devanagari:
        headwords = file_in.readlines()
        progress_bar = tqdm.tqdm(total=len(headwords), desc="Headwords for %s" % letter, position=0)
        log = tqdm.tqdm(total=0, position=3, bar_format='{desc}')
        for headword in headwords:
            headword = headword.strip()
            headword = headword.replace(":", "ઃ")
            if headword == "":
                continue
            definition = get_definition(headword=headword,  existing_definitions=existing_definitions, log=log)
            if definition == "":
                empty_count = empty_count + 1
                continue
            if "શોધી રહ્યા છે" in definition:
                incomplete_count = incomplete_count + 1
            devanagari_headword = sanscript.transliterate(data=headword, _from=sanscript.GUJARATI, _to=sanscript.DEVANAGARI)
            devanagari_headword = sanscript.SCHEMES[sanscript.DEVANAGARI].fix_lazy_anusvaara(devanagari_headword)
            definition_devanagari = sanscript.transliterate(data=definition, _from=sanscript.GUJARATI, _to=sanscript.DEVANAGARI)
            devanagari_entry = "%s|%s\n%s\n\n" % (headword, devanagari_headword, definition_devanagari.replace("  ॥", "।"))
            file_out.writelines(["%s|%s\n%s\n\n" % (headword, devanagari_headword, definition)])
            file_out_devanagari.writelines([devanagari_entry])
            progress_bar.update(1)
            # log.set_description_str(devanagari_entry)
            count = count + 1
    return (count, empty_count, incomplete_count)


def dump_definitions(letters, in_path_dir, out_path_dir, out_path_dir_devanagari):
    from tqdm.contrib.concurrent import process_map  # or thread_map
    f = partial(dump_letter_definitions, in_path_dir=in_path_dir, out_path_dir=out_path_dir, out_path_dir_devanagari=out_path_dir_devanagari)
    results = process_map(f, letters, max_workers=8)
    logging.info(list(zip(letters, results)))
    babylon.join_babylon_segments_in_dir(out_path_dir=out_path_dir)
    babylon.join_babylon_segments_in_dir(out_path_dir=out_path_dir_devanagari)


def test_get_definition(x):
    existing_definitions = babylon.get_definitions("/home/vvasuki/indic-dict/stardict-gujarati/gu-head/gu-entries/bhagavad-go-maNDala-a-Na/mUlam/આ.babylon")
    logging.debug(get_definition(headword=x, existing_definitions=existing_definitions))
    exit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--part", dest="part", default=1, type=int, help="..")
    args = parser.parse_args()
    # get_headwords(out_path="/home/vvasuki/indic-dict/stardict-gujarati/gu-head/gu-entries/bhagavad-go-maNDala/headwords/")
    # test_get_definition("આપોશાન")
    letters_a_Na = "ૐ ૠ ૡ અ આ ઇ ઈ ઉ ઊ ઋ ઌ ઍ એ ઐ ઑ ઓ ઔ ક ખ ગ ઘ ઙ ચ છ જ ઝ ઞ ટ ઠ ડ ઢ ણ".split()
    letters_ta_La = "ત થ દ ધ ન પ ફ બ ભ મ ય ર લ ળ વ શ ષ સ હ".split()

    if args.part == 1:
        dump_definitions(letters=letters_a_Na, in_path_dir="/home/vvasuki/indic-dict/stardict-gujarati/gu-head/gu-entries/bhagavad-go-maNDala-a-Na/headwords/", out_path_dir="/home/vvasuki/indic-dict/stardict-gujarati/gu-head/gu-entries/bhagavad-go-maNDala-a-Na/mUlam/", out_path_dir_devanagari="/home/vvasuki/indic-dict/stardict-gujarati/gu-head/dev-entries/bhagavad-go-maNDala-dev-a-Na/mUlam/")
        
    elif args.part == 2:
        dump_definitions(letters=letters_ta_La, in_path_dir="/home/vvasuki/indic-dict/stardict-gujarati/gu-head/gu-entries/bhagavad-go-maNDala-ta-La/headwords/", out_path_dir="/home/vvasuki/indic-dict/stardict-gujarati/gu-head/gu-entries/bhagavad-go-maNDala-ta-La/mUlam/", out_path_dir_devanagari="/home/vvasuki/indic-dict/stardict-gujarati/gu-head/dev-entries/bhagavad-go-maNDala-dev-ta-La/mUlam/")
