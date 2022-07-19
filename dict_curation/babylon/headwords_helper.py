import codecs
import logging

from tqdm import tqdm

# Remove all handlers associated with the root logger object.

for handler in logging.root.handlers[:]:
  logging.root.removeHandler(handler)
logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")



def get_headwords(in_path):
  headwords = []
  with codecs.open(in_path, "r", 'utf-8') as file_in:
    current_headwords = []
    for (index, line) in tqdm(enumerate(file_in.readlines())):
      if index % 3 == 0:
        current_headwords = [hw for hw in line.strip().split("|") if hw != ""]
        headwords.extend(current_headwords)
  headwords = list(set(headwords))
  headwords.sort()
  return headwords


