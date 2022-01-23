import dict_curation.babylon
from dict_curation.babylon import cleaner, language

if __name__ == '__main__':
  pass
  # cleaner.set_languages(file_path="/home/vvasuki/indic-dict/stardict_all/stardict-malayalam/en-head/olam-enml/olam-enml.babylon")
  dict_curation.babylon.process_all(dir_path="/home/vvasuki/indic-dict/stardict_all", transformer=language.set_languages)