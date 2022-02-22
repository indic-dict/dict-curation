from curation_utils.google import sheets
from sanskrit_data import collection_helper

from dict_curation import Definition


def append_taxonomy_entries(outfile, tree):
  subtags = [node for node in tree.keys() if node != collection_helper.LEAVES_KEY]
  for subtag in subtags:
    outfile.write("%s\n%s<BR><BR>%s\n\n" % (subtag, " ".join(subtags), " ".join(tree[subtag][collection_helper.LEAVES_KEY])))
    append_taxonomy_entries(outfile=outfile, tree=tree[subtag])
  
    


def import_from_google_sheets(out_path):
  sheet = sheets.get_sheet(spreadhsheet_id="1ejrjwktg9jcBeZUYndawSggGaOoy1jDf2w44vLYLEc0", worksheet_name="પરિ", google_key = '/home/vvasuki/sysconf/kunchikA/google/sanskritnlp/service_account_key.json')
  tree = {}

  rows = sheet.get_all_values()
  with open(out_path, "w") as outfile:
    for r, row in enumerate(rows):
      if len(row)< 3 or row[0].strip() == "" or r < 61:
        continue
      taxon = row[0].replace(",", "/")
      headwords = list(filter(lambda x: x.strip() != "", row[2:]))
      for headword in headwords:
        collection_helper.insert_to_tree(tree=tree, path=taxon, leaf=headword)
      entry = "%s<br><br>%s" % (taxon, " ".join(headwords))
      outfile.write("%s\n%s\n\n" % ("|".join(headwords), entry))
    append_taxonomy_entries(outfile=outfile, tree=tree)
  pass


if __name__ == '__main__':
  import_from_google_sheets(out_path="/home/vvasuki/indic-dict/stardict_all/stardict-gujarati/en-head/saad/saad.babylon")