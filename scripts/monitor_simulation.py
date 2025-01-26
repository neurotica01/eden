import os
import time
import json
import glob
from global_methods import log

frontend_path = "environment/frontend_server"
last_file = None

while True:
    with open(f"{frontend_path}/temp_storage/curr_sim_code.json", "r") as f:
        data = json.load(f)
        curr_sim_code = data["sim_code"]

    movement_path = f"{frontend_path}/storage/{curr_sim_code}/movement"
    path_length = len(movement_path) + 1
    list_of_files = glob.glob(f"{movement_path}/*.json")
    latest_file = sorted(list_of_files, key=lambda s: int(s[path_length:-5]))[-1]

    if latest_file != last_file:
        os.system("clear")
        with open(latest_file, "r") as f:
            log(f.read())
            log(latest_file)

        last_file = latest_file

    time.sleep(0.2)
