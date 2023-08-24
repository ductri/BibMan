from pyzotero import zotero
import json
from tqdm import tqdm

library_id = '8492328'
api_key =  'CKLR7GWAOgZDMbXNxQgOKXzZ'
library_type = 'user'
zot = zotero.Zotero(library_id, library_type, api_key)
# items = zot.everything(zot.items())
# with open('raw_data.txt',  'wt') as  file_handler:
#     for item in tqdm(items):
#         file_handler.write(json.dumps(item)+"\n")

cols = zot.collections()
with open('raw_collections.txt', 'wt') as file_handler:
    for item in cols:
        file_handler.write(json.dumps(item)+'\n')

