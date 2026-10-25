import json
import os

from filter.filter_json import *
from lib import config


def print_filter_json():
    try:
        dir_base_path = config.get_wfg_dir()
    except:
        return
    json_file_path = os.path.join(dir_base_path, "filter.json")
    with open(json_file_path, "w") as json_file:
        writer_filer_json(json_file)