"""Regenerate feed + jobs.json dump from DB, sync to web/data, validate XML."""
import sys, os, json, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import all_rows
from filter import classify
import feed

deduped = [classify(j) for j in all_rows()]
for j in deduped:
    j.pop("_db_salary", None)

json.dump(deduped, open("out/jobs.json", "w"), indent=2, ensure_ascii=False)
feed.write(deduped)
shutil.copyfile("out/jobs.json", "web/data/jobs.json")
shutil.copyfile("out/feed.xml", "web/data/feed.xml")

import xml.etree.ElementTree as ET
ET.parse("web/data/feed.xml")
print("feed VALID XML")
d = json.load(open("web/data/jobs.json"))
print("jobs items:", len(d), "| created_at:", "created_at" in d[0], "| id:", "id" in d[0])