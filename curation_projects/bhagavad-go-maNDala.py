from curation_utils import scraping

letters = "અ આ ઇ ઈ ઉ ઊ ઋ ઌ ઍ એ ઐ ઑ ઓ ઔ ક ખ ગ ઘ ઙ ચ છ જ ઝ ઞ ટ ઠ ડ ઢ ણ ત થ દ ધ ન પ ફ બ ભ મ ય ર લ ળ વ શ ષ સ હ ૐ ૠ ૡ".split()


browser = scraping.get_selenium_browser(headless=False)

def get_headwords(letter):
    url = "http://www.bhagwadgomandal.com/index.php?action=dictionary&sitem=%s&type=1&page=0" % letter
    browser.get(url=url)
    page_dropdown = browser.find_element_by_css_selector("select[name=pgInd]")
    page_dropdown_length = len(browser.find_element_by_css_selector("select[name=pgInd] option"))

    for option_index in range(1, page_dropdown_length+1):
        page_dropdown.select_by_index(option_index)


if __name__ == '__main__':
    get_headwords("અ")
