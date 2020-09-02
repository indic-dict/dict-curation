
from dict_curation import babylon

def dump_vedic_dicts():
    # babylon.dump_headwords_file(in_path="/home/vvasuki/indic-dict/stardict-sanskrit-kAvya/kyv-ts-padasvara/kyv-ts-padasvara.babylon", out_path="/home/vvasuki/sanskrit-coders/autocomplete-sa/dicts/kyv-ts.csv")
    # babylon.dump_definitions_file(in_path="/home/vvasuki/indic-dict/stardict-sanskrit-kAvya/kyv-ts-padasvara/kyv-ts-padasvara.babylon", out_path="/home/vvasuki/sanskrit-coders/autocomplete-sa/dicts/kyv-ts-padasvara.csv")
    babylon.dump_headwords_file(in_path="/home/vvasuki/indic-dict/stardict-sanskrit-kAvya/rv-padasvara-dev/rv-padasvara-dev.babylon", out_path="/home/vvasuki/sanskrit-coders/autocomplete-sa/dicts/kaavya/rv.csv")
    babylon.dump_definitions_file(in_path="/home/vvasuki/indic-dict/stardict-sanskrit-kAvya/rv-padasvara-dev/rv-padasvara-dev.babylon", out_path="/home/vvasuki/sanskrit-coders/autocomplete-sa/dicts/svara/rv.csv")


def dump_declined():
    # babylon.dump_headwords_file(in_path="/home/vvasuki/indic-dict/stardict-sanskrit-vyAkaraNa/dhaval-tiNanta/dhaval-tiNanta.babylon", out_path="/home/vvasuki/sanskrit-coders/autocomplete-sa/dicts/declined/tiNanta-dhaval.csv")
    babylon.dump_headwords_file(in_path="/home/vvasuki/indic-dict/stardict-sanskrit/sa-head/sa-entries/kalpadruma-sa/kalpadruma-original-hw.babylon", sanskrit_dataout_path="/home/vvasuki/sanskrit-coders/autocomplete-sa/dicts/declined/kalpadruma.csv")


def dump_stem():
    babylon.dump_headwords_file(in_path="/home/vvasuki/indic-dict/stardict-sanskrit-kAvya/dcs-frequency/dcs-frequency.babylon", out_path="/home/vvasuki/sanskrit-coders/autocomplete-sa/dicts/stem/dcs.csv")


if __name__ == '__main__':
    dump_declined()
    # dump_vedic_dicts()
    # dump_stem()