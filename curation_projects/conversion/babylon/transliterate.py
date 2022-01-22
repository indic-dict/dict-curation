from aksharamukha import GeneralMap

from dict_curation.babylon import transliterate


def process_oriya_dicts():
  transliterate.process_dir(source_script="Oriya", dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-oriya/or-head")


def process_sinhala_dicts():
  transliterate.process_dir(source_script=GeneralMap.SINHALA, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-sinhala/si-head/en-entries", dest_dir="/home/vvasuki/indic-dict/stardict-sinhala/si-head_dev-script/en-entries")


def process_panjabi_dicts():
  transliterate.process_dir(source_script=GeneralMap.GURMUKHI, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-panjabi/pa-head/en-entries", dest_dir="/home/vvasuki/indic-dict/stardict-panjabi/pa-head_dev-script/en-entries")

def process_bengali_dicts():
  transliterate.process_dir(source_script=GeneralMap.BENGALI, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-bengali/bn-head/en-entries", dest_dir="/home/vvasuki/indic-dict/stardict-bengali/bn-head_dev-script/en-entries")
  transliterate.process_dir(source_script=GeneralMap.BENGALI, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-bengali/bn-head/bn-entries", dest_dir="/home/vvasuki/indic-dict/stardict-bengali/bn-head_dev-script/bn-entries")


def process_as_dicts():
  transliterate.process_dir(source_script=GeneralMap.ASSAMESE, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-assamese/as-head/en-entries", dest_dir="/home/vvasuki/indic-dict/stardict-assamese/as-head_dev-script/en-entries")
  # transliterate.process_dir(source_script=GeneralMap.ASSAMESE, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict-assamese/as-head/as-entries", dest_dir="/home/vvasuki/indic-dict/stardict-assamese/as-head_dev-script/as-entries")

def process_ml_dicts():
  transliterate.process_dir(source_script=GeneralMap.MALAYALAM, dest_script=GeneralMap.ISO, source_dir="/home/vvasuki/indic-dict/stardict-malayalam/en-head")

  # remove_devanagari_headwords(source_path="/home/vvasuki/indic-dict/stardict-malayalam/ml-head/datuk/datuk.babylon")
  remove_devanagari_headwords(source_path="/home/vvasuki/indic-dict/stardict-malayalam/ml-head/gundert/gundert.babylon")
  # 
  source_dir = "/home/vvasuki/indic-dict/stardict-malayalam/ml-head/"
  transliterate.process_dir(source_script=GeneralMap.MALAYALAM, dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir)


def process_telugu_dicts():
  transliterate.process_dir(source_script=GeneralMap.TELUGU, dest_script="ISO", source_dir="/home/vvasuki/indic-dict/stardict-telugu/en-head")

  source_dir = "/home/vvasuki/indic-dict/stardict-telugu/te-head/en-entries"
  transliterate.process_dir(source_script=GeneralMap.TELUGU, dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir)

  source_dir = "/home/vvasuki/indic-dict/stardict-telugu/te-head/te-entries"
  transliterate.process_dir(source_script=GeneralMap.TELUGU, dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir)

def process_tamil_dicts():
  pre_options = ["TamilTranscribe"]
  source_dir = "/home/vvasuki/indic-dict/stardict-tamil/ta-head/en-entries"
  transliterate.process_dir(source_script="Tamil", dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir, pre_options=pre_options)

  source_dir = "/home/vvasuki/indic-dict/stardict-tamil/ta-head/ta-entries"
  transliterate.process_dir(source_script="Tamil", dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir, pre_options=pre_options)

  source_dir = "/home/vvasuki/indic-dict/stardict-tamil/en-head/"
  transliterate.process_dir(source_script="Tamil", dest_script="ISO", source_dir=source_dir, pre_options=pre_options)



def process_kannada_dicts():
  pre_options = []
  source_dir = "/home/vvasuki/indic-dict/stardict-kannada/kn-head/kn-entries"
  transliterate.process_dir(source_script="Kannada", dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir, pre_options=pre_options)
  source_dir = "/home/vvasuki/indic-dict/stardict-kannada/en-head/"
  transliterate.process_dir(source_script="Kannada", dest_script="ISO", source_dir=source_dir, pre_options=pre_options)


def process_divehi_dicts():
  source_path = "/home/vvasuki/indic-dict/stardict-divehi/dv-head/en-entries/maniku/maniku.babylon"
  transliterate.add_devanagari_headwords(source_script="Thaana", source_path=source_path)


def fix_kittel():
  source_path = "/home/vvasuki/indic-dict/stardict-kannada/kn-head/en-entries/kittel/kittel.babylon"
  transliterate.add_lazy_anusvaara_headwords(source_script="kannada", source_path=source_path)


if __name__ == '__main__':
  # process_tamil_dicts()
  process_telugu_dicts()
  # process_bengali_dicts()
  # process_divehi_dicts()
  # process_kannada_dicts()
  # fix_kittel()
  pass
