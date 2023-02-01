import dict_curation.babylon
from dict_curation import babylon
from dict_curation.babylon import cleaner, language, definitions_helper

if __name__ == '__main__':
  pass
  # cleaner.set_languages(file_path="/home/vvasuki/indic-dict/stardict_all/stardict-malayalam/en-head/olam-enml/olam-enml.babylon")
  # dict_curation.babylon.process_all(dir_path="/home/vvasuki/indic-dict/stardict_all/stardict-urdu", transformer=language.set_languages)
  # dict_curation.babylon.process_all(dir_path="/home/vvasuki/indic-dict/stardict_all/stardict-gujarati", transformer=language.set_languages)
  definitions_helper.get_definitions_map(in_path="/home/vvasuki/gitland/indic-dict_stardict/stardict-ayurveda/WHO_Ayurveda-terms/WHO_Ayurveda-terms.babylon")