import os
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
import tarfile
import platform

index_indexorum = "https://raw.githubusercontent.com/indic-dict/stardict-index/master/dictionaryIndices.md"

# download the url into dir
# if dir does not exist create it
def dlfile(url, dir, force_download=True):
  os.makedirs(dir, exist_ok=True)
  # Open the url
  try:
    f = urlopen(url)
    localpath = dir + "/" + os.path.basename(url)
    # Open our local file for writing
    if not force_download:
      if os.path.isfile(localpath):  # check if this file exists
        print("skipped %s as it already exists" % localpath)
        return
    with open(localpath, "wb") as local_file:
      local_file.write(f.read())

  # handle errors
  except HTTPError as e:
    print("HTTP Error:", e.code, url)
  except URLError as e:
    print("URL Error:", e.reason, url)


def get_url_list(indexURL, verbose=False):
  encoding = 'utf-8'
  returnlist = []
  if verbose:
    print("Processing index %s" % indexURL)
  # download this index and go through it line by line
  response = urlopen(indexURL)
  for line in response:
    line = line.decode(encoding)
    line = line.strip()
    # dict_URL is a URl to a .tar.gz file
    if line != "" and not line.startswith("#"):
      if line.startswith("<") and line.endswith(">"):
        line = line[1:-1]
      returnlist.append(line)
  return returnlist


def download_extract(dict_URL, tmp_directory, download_dir,
                     force_download=False):
  dictfilename = os.path.basename(dict_URL)
  print("downloading file=%s, to dir=%s" % (
    dictfilename,
    tmp_directory))
  dlfile(dict_URL, tmp_directory, force_download)
  assert (dictfilename[-7:] == ".tar.gz", dictfilename)
  t = tarfile.open(tmp_directory + "/" + dictfilename, 'r')
  thedictfilenamelen = len(dictfilename)
  # Handle filenames like: kRdanta-rUpa-mAlA__2016-02-20_23-22-27
  subDirnameToExtract = dictfilename[:-8].split("__")[0]
  fullpathofsubdir = download_dir + subDirnameToExtract
  print("extract to %s" % fullpathofsubdir)
  t.extractall(fullpathofsubdir)


def download_dictionaries(tgz_download_directory,
                          dict_extract_dir, indexes=None,
                          maxcount=1, force_download=False, verbose=False):
  if indexes is None:
    indexes = get_url_list(index_indexorum)
  count = 0
  for index in indexes:
    # download this index
    if verbose:
      print("============================================")
      print("Processing index %s" % index)
    dictlist = get_url_list(index, verbose=True)
    for adict in dictlist:
      download_extract(adict, tgz_download_directory,
                       dict_extract_dir, force_download)
      count += 1
      if count == -1:
        continue  # no limit to download
      if count == maxcount:
        return
    if verbose:
      print("============================================")


def get_dict_list(base, listOfIndexes, verbose=False):
  masterlist = []
  for indexUrl in listOfIndexes:
    fullIndexPath = base + indexUrl
    # download this index
    if verbose:
      print("============================================")
      print("Processing index %s" % fullIndexPath)
    dictlist = get_url_list(fullIndexPath, verbose=True)
    masterlist.extend(dictlist)
    return masterlist


def set_dir():
  tmp_dir = "/sdcard/Download/dicttars"
  dict_dir = "/sdcard/dictdata/"
  onMac = True  # (platform.system() == 'Darwin')
  if onMac:
    tmp_dir = "." + tmp_dir
    dict_dir = "." + dict_dir
  return (tmp_dir, dict_dir)


if __name__ == '__main__':
  dict_dir = "/opt/dicts/indic-dict/stardict"
  tmp_dir = os.path.join(dict_dir, "tmp")
  download_dictionaries(tmp_dir, dict_dir, indexes=None, maxcount=-1, force_download=False,
                        verbose=True)
