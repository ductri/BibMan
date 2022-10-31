import json
from tqdm import tqdm
import bibtexparser


# def get_papers():
#     return [p['title'] for p in papers]
#
# class DataManager():
#     def __init__(self):
#         with open('./data/data_from_zotero.txt',  'rt') as file_handler:
#             papers = file_handler.readlines()
#         self.papers = [json.loads(item[:-1]) for item in papers]
#         for i in range(len(self.papers)):
#             tags = self.papers[i].get('tags', [])
#             tags.append('DEFAULT')
#             self.papers[i]['tags'] = tags
#             self.papers[i]['authors'] = self.papers[i]['authors'].split(';')
#
#     def get_paper_property(paper_id):
#         return {'name': 'Convex opt in ' + paper_id + ' in fastest manner', 'authors': ['tri nguyen']}
#
#     def get_all_papers(self):
#         """return everything"""
#         return self.papers


class DatabaseManager(object):
    def __init__(self):
        def preprocessing(papers):
            result = []
            for paper in papers:
                default_item = {'title': '',  'author': '', 'year': '', 'journal': '', 'file': ''}
                paper['tags'] = set([item.strip() for item in paper['tags'].split(',')])
                default_item.update(paper)
                result.append(default_item)
            return result

        self.collection_tree = {'community_detection':{'related_works': {'active':  {}}, },
                               }
        with open('./data/bib_collection.bib', 'rt') as bibfile:
            self.all_papers = preprocessing(bibtexparser.load(bibfile).entries)

    def get_collection(self):
        return self.collection_tree

    def get_list_papers(self, tags):
        result = []
        tags = set(tags)
        return [paper for paper in self.all_papers if tags.issubset(paper['tags'])]


if __name__ == "__main__":
    db = DatabaseManager()
    __import__('pdb').set_trace()

