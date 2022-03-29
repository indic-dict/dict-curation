import codecs
import itertools
import logging
import regex
import os


def get_headers(file_path):
  from collections import defaultdict
  with codecs.open(file_path, "r", 'utf-8') as file_in:
    headers = defaultdict()
    line = file_in.readline()
    if line.strip() != "":
      # A dict without headers
      return headers
    for line in file_in:
      line = line.strip()
      if len(headers) > 0 and not line.startswith("#"):
        # All headers read
        assert line == "", file_path
        return headers
      line = line[1:]
      if "=" not in line:
        logging.warning("Strange line: %s in %s", line, file_path)
        continue
      [key, value] = line.split("=")
      headers[key] = value


def set_headers(file_path, headers):
  from collections import defaultdict
  lines = []
  with codecs.open(file_path, "r", 'utf-8') as file_in:
    lines = file_in.readlines()
    lines = list(itertools.dropwhile(lambda x: x.strip() == "" or x.startswith("#"), lines))

  with codecs.open(file_path, "w", 'utf-8') as file_out:
    if len(headers) > 0:
      file_out.write("\n")
      for key, value in headers.items():
        file_out.write("#%s=%s\n" % (key, value))
      file_out.write("\n")
    for line in lines:
      file_out.write(line)


def set_html_headers(headers=None):
  if headers is None:
    headers = {}
  headers["sametypesequence"] = "h"
  headers["stripmethod"] = "keep"
  return headers


def get_default_headers(file_path):
  from dict_curation.babylon import language
  headers = {}
  headers["bookname"] = headers.get("bookname", regex.sub("\.babylon.*", "", os.path.basename(file_path)))
  headers["bookname"] = f"{headers['bookname']} {language.get_language_pair_string(file_path=file_path)}"
  set_html_headers(headers=headers)
  return headers


def get_non_header_line_1_index(file_path):
  headers = get_headers(file_path=file_path)
  if len(headers) == 0:
    return 1
  else:
    return len(headers) + 3