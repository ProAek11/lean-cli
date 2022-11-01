# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean CLI v1.0. Copyright 2021 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import json
import time
import requests
from pathlib import Path

json_modules = {}
file_name = "modules-1.7.json"
directory = Path(__file__).parent
file_path = directory.parent / file_name

# check if new file is available online
url = f"https://cdn.quantconnect.com/cli/{file_name}"
error = None
try:
    # fetch if file not available or fetched before 1 day
    if not os.path.exists(file_path) or (time.time() - os.path.getmtime(file_path) >  86400):
        res = requests.get(url, timeout=5)
        if res.ok:
            new_content = res.json()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(new_content, f, ensure_ascii=False, indent=4)
        else:
            res.raise_for_status()
except Exception as e:
    # No need to do anything if file isn't available
    error = str(e)
    pass

# check if file exists
if not Path(file_path).is_file():
    error_message = f": {error}" if error is not None else ""
    raise FileNotFoundError(
        f"Modules json not found in the given path {file_path}{error_message}")

with open(file_path) as f:
    data = json.load(f)
    json_modules = data['modules']
