import glob
from pathlib import Path

from curation_utils.archive_utility import ArchiveItem

def update_dictionary_collection(collection_name):
  metadata = {
    "title" : "Definitions from various %s dictionaries" % collection_name,
    "description" : """
        Definitions from various %s dictionaries as plain text YAML+MD files.
      """ % collection_name
  }
  item = ArchiveItem(archive_id="definition-tree-sanskrit", metadata=metadata, repo_base="/home/vvasuki/indic-dict/definition-tree-%s" % collection_name)
  item.update_from_dir(file_pattern="*.md")

if __name__ == '__main__':
    update_dictionary_collection(collection_name="sanskrit")