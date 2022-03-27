import codecs
import os

from dict_curation.babylon.headwords_helper import get_headwords
from dict_curation.babylon.definitions_helper import get_definitions_map
import logging

# Remove all handlers associated with the root logger object.

for handler in logging.root.handlers[:]:
  logging.root.removeHandler(handler)
logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")




def dump_headwords_file(in_path, out_path):
  headwords = get_headwords(in_path=in_path)
  os.makedirs(os.path.dirname(out_path), exist_ok=True)
  with codecs.open(out_path, "w", 'utf-8') as file_out:
    for headword in headwords:
      file_out.write(headword + "\n")


def dump_definitions_file(in_path, out_path):
  definitions = get_definitions_map(in_path=in_path)
  os.makedirs(os.path.dirname(out_path), exist_ok=True)
  with codecs.open(out_path, "w", 'utf-8') as file_out:
    for definition in definitions.values():
      file_out.write(definition + "\n")


def to_slob(in_path, out_path):
  from dict_curation import slob
  definitions = get_definitions_map(in_path=in_path)
  os.makedirs(os.path.dirname(out_path), exist_ok=True)
  if os.path.exists(out_path):
    os.remove(out_path)
  with slob.create(out_path) as w:
    for definition in set(definitions.values()):
      w.add(definition.meaning.encode('utf-8'), *(definition.headwords_tuple), content_type=slob.MIME_HTML)