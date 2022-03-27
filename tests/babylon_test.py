import logging
import os

from dict_curation.babylon import definitions_helper

test_babylon = os.path.join(os.path.dirname(__file__), "test.babylon")


def test_get_existing_definitions():
    definitions = definitions_helper.get_definitions_map(test_babylon)
    headword = 'આપોશાન'
    assert headword in definitions
    logging.info(definitions[headword])


