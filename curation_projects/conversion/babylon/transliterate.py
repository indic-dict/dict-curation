import codecs
import subprocess

import aksharamukha.transliterate
import tqdm
import logging

for handler in logging.root.handlers[:]:
  logging.root.removeHandler(handler)
logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")



def convert_with_aksharamukha(source_path, dest_path, source_script, dest_script, pre_options = [], post_options = []):
  logging.info("\nTransliterating (%s > %s) %s to %s", source_script, dest_script, source_path, dest_path)
  with codecs.open(source_path, "r", "utf-8") as in_file, codecs.open(dest_path, "w", "utf-8") as out_file:
    progress_bar = tqdm.tqdm(total=int(subprocess.check_output(['wc', '-l', source_path]).split()[0]), desc="Lines", position=0)
    for line in in_file:
      dest_line = aksharamukha.transliterate.process(src=source_script, tgt=dest_script, txt=line, nativize = True, pre_options = pre_options, post_options = post_options)
      out_file.write(dest_line)
      progress_bar.update(1)


def process_ml_dicts():
  convert_with_aksharamukha(source_path="/home/vvasuki/indic-dict/stardict-malayalam/en-head/olam-enml/olam-enml.babylon", dest_path="/home/vvasuki/indic-dict/stardict-malayalam/en-head_en-script/olam-enml_en-script/olam-enml_en-script.babylon", source_script="Malayalam", dest_script="ISO")
  convert_with_aksharamukha(source_path="/home/vvasuki/indic-dict/stardict-malayalam/en-head/olam-enml/olam-enml.babylon", dest_path="/home/vvasuki/indic-dict/stardict-malayalam/en-head_en-script/olam-enml_en-script/olam-enml_en-script.babylon", source_script="Malayalam", dest_script="ISO")


def process_tamil_dicts():
  pre_options = ["TamilTranscribe"]

  # convert_with_aksharamukha(source_path="/home/vvasuki/indic-dict/stardict-tamil/en-head_en-script/pals_english-tamil_dictionary_en-script/pals_english-tamil_dictionary.txt", dest_path="/home/vvasuki/indic-dict/stardict-tamil/en-head_en-script/pals_english-tamil_dictionary_en-script/pals_english-tamil_dictionary_en-script.babylon", source_script="Tamil", dest_script="ISO", pre_options=pre_options)
  # convert_with_aksharamukha(source_path="/home/vvasuki/indic-dict/stardict-tamil/en-head_en-script/english-tamizh_dictionary_tamilvu_en-script/english-tamizh_dictionary_tamilvu.txt", dest_path="/home/vvasuki/indic-dict/stardict-tamil/en-head_en-script/english-tamizh_dictionary_tamilvu_en-script/english-tamizh_dictionary_tamilvu_en-script.babylon", source_script="Tamil", dest_script="ISO", pre_options=pre_options)
  convert_with_aksharamukha(source_path="/home/vvasuki/indic-dict/stardict-tamil/ta-dev/tamil_lexicon_decorated_dev/tamil_lexicon_decorated.txt", dest_path="/home/vvasuki/indic-dict/stardict-tamil/ta-dev/tamil_lexicon_decorated_dev/tamil_lexicon_decorated_dev.babylon", source_script="Tamil", dest_script="Devanagari", pre_options=pre_options)



if __name__ == '__main__':
  process_ml_dicts()