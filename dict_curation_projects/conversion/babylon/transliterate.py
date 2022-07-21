from aksharamukha import GeneralMap
from indic_transliteration import sanscript

from dict_curation import babylon
from dict_curation.babylon import lipi
from dict_curation.babylon.lipi import remove_devanagari_headwords


def process_oriya_dicts():
  lipi.process_dir(source_script="Oriya", dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict_all/stardict-oriya/or-head")


def process_sinhala_dicts():
  lipi.process_dir(source_script=GeneralMap.SINHALA, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict_all/stardict-sinhala/si-head/en-entries", dest_dir="/home/vvasuki/indic-dict/stardict_all/stardict-sinhala/si-head_dev-script/en-entries")


def process_panjabi_dicts():
  lipi.process_dir(source_script=GeneralMap.GURMUKHI, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict_all/stardict-panjabi/pa-head/en-entries", dest_dir="/home/vvasuki/indic-dict/stardict_all/stardict-panjabi/pa-head_dev-script/en-entries")

def process_bengali_dicts():
  lipi.process_dir(source_script=GeneralMap.BENGALI, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict_all/stardict-bengali/bn-head/en-entries", dest_dir="/home/vvasuki/indic-dict/stardict_all/stardict-bengali/bn-head_dev-script/en-entries")
  lipi.process_dir(source_script=GeneralMap.BENGALI, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict_all/stardict-bengali/bn-head/bn-entries", dest_dir="/home/vvasuki/indic-dict/stardict_all/stardict-bengali/bn-head_dev-script/bn-entries")


def process_as_dicts():
  lipi.process_dir(source_script=GeneralMap.ASSAMESE, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict_all/stardict-assamese/as-head/en-entries", dest_dir="/home/vvasuki/indic-dict/stardict_all/stardict-assamese/as-head_dev-script/en-entries")
  # lipi.process_dir(source_script=GeneralMap.ASSAMESE, dest_script=GeneralMap.DEVANAGARI, source_dir="/home/vvasuki/indic-dict/stardict_all/stardict-assamese/as-head/as-entries", dest_dir="/home/vvasuki/indic-dict/stardict_all/stardict-assamese/as-head_dev-script/as-entries")

def process_ml_dicts():
  lipi.process_dir(source_script=GeneralMap.MALAYALAM, dest_script=GeneralMap.ISO, source_dir="/home/vvasuki/indic-dict/stardict_all/stardict-malayalam/en-head")

  # remove_devanagari_headwords(source_path="/home/vvasuki/indic-dict/stardict_all/stardict-malayalam/ml-head/datuk/datuk.babylon")
  remove_devanagari_headwords(source_path="/home/vvasuki/indic-dict/stardict_all/stardict-malayalam/ml-head/gundert/gundert.babylon")
  # 
  source_dir = "/home/vvasuki/indic-dict/stardict_all/stardict-malayalam/ml-head/"
  lipi.process_dir(source_script=GeneralMap.MALAYALAM, dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir)


def process_telugu_dicts():
  lipi.process_dir(source_script=GeneralMap.TELUGU, dest_script="ISO", source_dir="/home/vvasuki/indic-dict/stardict_all/stardict-telugu/en-head")

  source_dir = "/home/vvasuki/indic-dict/stardict_all/stardict-telugu/te-head/en-entries"
  lipi.process_dir(source_script=GeneralMap.TELUGU, dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir)

  source_dir = "/home/vvasuki/indic-dict/stardict_all/stardict-telugu/te-head/te-entries"
  lipi.process_dir(source_script=GeneralMap.TELUGU, dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir)

def process_tamil_dicts(overwrite):
  pre_options = ["TamilTranscribe"]
  # source_dir = "/home/vvasuki/indic-dict/stardict_all/stardict-tamil/ta-head/en-entries"
  # lipi.process_dir(source_script="Tamil", dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir, pre_options=pre_options, overwrite=overwrite)
  # # 
  # source_dir = "/home/vvasuki/indic-dict/stardict_all/stardict-tamil/ta-head/ta-entries"
  # lipi.process_dir(source_script="Tamil", dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir, pre_options=pre_options, overwrite=overwrite)

  # source_dir = "/home/vvasuki/indic-dict/stardict_all/stardict-tamil/en-head/"
  # lipi.process_dir(source_script="Tamil", dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir, pre_options=pre_options, overwrite=overwrite)
  # 
  # source_dir = "/home/vvasuki/indic-dict/stardict_all/stardict-tamil/en-head/"
  # lipi.process_dir(source_script="Tamil", dest_script="ISO", source_dir=source_dir, pre_options=pre_options, overwrite=overwrite)
 


def process_kannada_dicts():
  pre_options = []
  source_dir = "/home/vvasuki/indic-dict/stardict_all/stardict-kannada/kn-head/kn-entries"
  lipi.process_dir(source_script="Kannada", dest_script=GeneralMap.DEVANAGARI, source_dir=source_dir, pre_options=pre_options)
  source_dir = "/home/vvasuki/indic-dict/stardict_all/stardict-kannada/en-head/"
  lipi.process_dir(source_script="Kannada", dest_script="ISO", source_dir=source_dir, pre_options=pre_options)


def process_divehi_dicts():
  source_path = "/home/vvasuki/indic-dict/stardict_all/stardict-divehi/dv-head/en-entries/maniku/maniku.babylon"
  lipi.add_devanagari_headwords(source_script="Thaana", source_path=source_path)


def fix_kittel():
  source_path = "/home/vvasuki/indic-dict/stardict_all/stardict-kannada/kn-head/en-entries/kittel/kittel.babylon"
  lipi.add_lazy_anusvaara_headwords(source_script="kannada", source_path=source_path)


def process_urdu_dicts():
  source_path = "/home/vvasuki/indic-dict/stardict_all/stardict-urdu/ur-head/en-entries/"
  babylon.process_all(dir_path=source_path, transformer=lipi.add_devanagari_headwords, source_script=sanscript.ISO)


def process_gujarati_dicts():
  source_dir = "/home/vvasuki/indic-dict/stardict_all/stardict-gujarati/en-head"
  lipi.process_dir(source_script="Gujarati", dest_script="Devanagari", source_dir=source_dir, overwrite=True)


if __name__ == '__main__':
  process_tamil_dicts(overwrite=True)
  # process_telugu_dicts()
  # process_urdu_dicts()
  # process_gujarati_dicts()
  # process_bengali_dicts()
  # process_divehi_dicts()
  # process_kannada_dicts()
  # fix_kittel()
  pass
