import codecs
import logging
import multiprocessing
import os


def dump_babylon(urls, get_definition, dest_path):
  os.makedirs(os.path.dirname(dest_path), exist_ok=True)
  with codecs.open(dest_path, "w") as f:
    for url in urls:
      (headwords, definition) = get_definition(url=url)
      if definition is not None:
        f.write(f"{'|'.join(headwords)}\n{definition}\n\n")
      else:
        logging.warning(f"Bad definition parsing at {url}")




def dump_babylon_parallel(urls, get_definition, dest_path, num_parallel_threads=5):
  os.makedirs(os.path.dirname(dest_path), exist_ok=True)
  pool = multiprocessing.Pool(num_parallel_threads)
  chunk_size = 100
  url_chunks = [urls[i * chunk_size:(i + 1) * chunk_size] for i in range((len(urls) + chunk_size - 1) // chunk_size )]
  with codecs.open(dest_path, "w") as f:
    for chunk_index, url_chunk in enumerate(url_chunks):
      logging.info(f"Processing chunk index {chunk_index}")
      defintions = pool.map(get_definition, url_chunk)
      for url_index, (headwords, definition) in enumerate(defintions):
        url = url_chunk[url_index]
        if definition is not None:
          f.write(f"{'|'.join(headwords)}\n{definition}\n\n")
        else:
          logging.warning(f"Bad definition parsing at {url}")
