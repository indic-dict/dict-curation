import codecs
import itertools
import logging


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
