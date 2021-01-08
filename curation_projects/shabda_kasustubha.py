import logging
import os

import regex

import doc_curation.scraping.html.selenium
from dict_curation import babylon
from doc_curation.scraping import parankusha


def get_entries(browser, outfile):
    text_spans = browser.find_elements_by_css_selector("#gvResults tr[valign=\"top\"]")
    entries = {}
    for text_span in text_spans:
        columns = text_span.find_elements_by_css_selector("td")
        base_word = columns[1].text
        if base_word == "BaseWord":
            continue
        details = {}
        details["पदविभागः"] = columns[2].text.strip()
        details["कन्नडार्थः"] = columns[3].text.strip()
        details["निष्पत्तिः"] = columns[4].text.strip()
        details["व्युत्पत्तिः"] = columns[5].text.strip()
        details["प्रयोगाः"] = columns[6].text.strip()
        details["उल्लेखाः"] = columns[7].text.strip()
        details["विस्तारः"] = columns[8].text.strip()
        details = filter(lambda x: x[1].strip() != "", details.items())
        entry_details = ""
        for detail in details:
            entry_details = "%s<br><b>%s - </b>%s" % (entry_details, detail[0], detail[1])
        entry_details = regex.sub("\n+", "<br>", entry_details)
        entry = entries.get(base_word, "")
        entry = "%s%s<br>%s<br><br>" % (entry, base_word, entry_details)
        entries[base_word] = entry
    for base_word, entry in entries.items():
        logging.debug(base_word)
        outfile.writelines([base_word + "\n", entry + "\n", "\n"])


def get_dict(browser, outfile_path, start_nodes=["अ--उह्र", "अ--अग्निनक्षत्र"]):
    doc_curation.scraping.html.selenium.click_link_by_text(browser=browser, element_text="विद्यास्थानानि")
    doc_curation.scraping.html.selenium.click_link_by_text(browser=browser, element_text="संस्कृत-कन्नड-कोशः")
    doc_curation.scraping.html.selenium.click_link_by_text(browser=browser, element_text="शब्दार्थ-कौस्तुभः")
    browser.execute_script("TreeView_ToggleNode(tv_Data,383,document.getElementById('tvn383'),' ',document.getElementById('tvn383Nodes'))")
    doc_curation.scraping.html.selenium.click_link_by_text(browser=browser, element_text=start_nodes[0])
    doc_curation.scraping.html.selenium.click_link_by_text(browser=browser, element_text=start_nodes[1])
    os.makedirs(name=os.path.dirname(outfile_path), exist_ok=True)
    if start_nodes[0] == "अ--उह्र" and start_nodes[1] == "अ--अग्निनक्षत्र":
        os.remove(outfile_path)
    # with open(outfile_path, "w") as outfile:
    with open(outfile_path, "a") as outfile:
        if start_nodes[0] == "अ--उह्र" and start_nodes[1] == "अ--अग्निनक्षत्र":
            outfile.write("""
    
    #stripmethod=keep
    #sametypesequence=h
    #bookname=शब्दार्थकौस्तुभः sa-kn
    
            """)
        get_entries(browser, outfile)
        while doc_curation.scraping.html.selenium.click_link_by_text(browser=browser, element_text="Next"):
            get_entries(browser, outfile)
        

if __name__ == '__main__':
    # browser = parankusha.get_logged_in_browser(headless=False)
    # get_dict(browser=browser, outfile_path="/home/vvasuki/indic-dict/stardict-sanskrit/sa-head/other-indic-entries/shabdArtha_kaustubha/shabdArtha_kasutubha.babylon", start_nodes=["वेदान्तिन्--ह्लाद्य", "शर्करा--शालसार"])
    babylon.get_definitions(in_path="/home/vvasuki/indic-dict/stardict-sanskrit/sa-head/other-indic-entries/shabdArtha_kaustubha/shabdArtha_kaustubha.babylon", do_fix_newlines=True)
    # browser.close()    
