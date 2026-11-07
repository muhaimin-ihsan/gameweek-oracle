#!/usr/bin/env bash
# Pull fresh FPL data, rebuild the model and the page. Run from this folder.
set -e
cd "$(dirname "$0")"
UA="Mozilla/5.0"
curl -s -A "$UA" https://fantasy.premierleague.com/api/bootstrap-static/ -o bs.json
curl -s -A "$UA" https://fantasy.premierleague.com/api/fixtures/ -o fixtures.json
CUR=$(python -I -c "import json;print(next(e['id'] for e in json.load(open('bs.json',encoding='utf8'))['events'] if e['is_current']))")
for g in $(seq 1 "$CUR"); do curl -s -A "$UA" "https://fantasy.premierleague.com/api/event/$g/live/" -o "live$g.json"; done
python -I build_data.py
python -I assemble.py
