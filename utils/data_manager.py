import json
from tqdm import tqdm
import bibtexparser
import shutil
import os

from bibtexparser.bibdatabase import BibDatabase


class DatabaseManager(object):
    """VERY BUGGY"""
    def preprocessing(papers):
        result = []
        for paper in papers:
            new_paper = paper.copy()
            default_item = {'title': '',  'author': '', 'year': '', 'journal': '', 'file': '', 'booktitle': '', 'tags': ','}
            new_paper['tags'] = set([item.strip() for item in paper['tags'].split(',')])
            default_item.update(new_paper)
            result.append(default_item)
        return result

    def __init__(self):
        self.collection_tree = {'community_detection':{'related_works': {'active':  {'test': {}}}, },
                'reading': {'diffusion': {}}}
        with open('./data/bib_collection.bib', 'rt') as bibfile:
            self.bib_database = bibtexparser.load(bibfile)
            self.all_papers = DatabaseManager.preprocessing(self.bib_database.entries)

        self.current_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

    def get_collection(self):
        return self.collection_tree

    def get_list_papers(self, tags):
        result = []
        tags = set(tags)
        return [paper for paper in self.all_papers if tags.issubset(paper['tags'])]

    def reload(self):
        with open('./data/bib_collection.bib', 'rt') as bibfile:
            self.bib_database = bibtexparser.load(bibfile)
            self.all_papers = DatabaseManager.preprocessing(self.bib_database.entries)

    def update_paper(self, paper_id, key, value):
        def post_preprocess(papers):
            for i in range(len(papers)):
                papers[i]['tags'] = ','.join(papers[i]['tags'])
            return papers

        self.reload()
        for ind, paper in enumerate(self.all_papers):
            if paper['ID'] == paper_id:
                paper[key] = value

        self.bib_database = BibDatabase()
        self.bib_database.entries = post_preprocess(self.all_papers)
        self.dump()

    def dump(self):
        """
        DANGEROUS
        """
        src = os.path.join(self.current_path, 'data', 'bib_collection.bib')
        dst = os.path.join(self.current_path, 'data', '.bib_collection.bib')
        shutil.copyfile(src, dst)
        with open(src, 'wt') as bibtex_file:
            bibtexparser.dump(self.bib_database, bibtex_file)

    def get_paper_attributes(self, paper_id):
        paper = self.bib_database.entries_dict[paper_id]
        return ['Title: ' + paper['title'].strip(),
                'Authors: ' + paper['author'].strip(),
                'Year: ' + str(paper['year']),
                'Venue: ' + str(paper['booktitle']),
                ]
    def get_paper_path(self, paper_id):
        paper = self.look_paper_up(paper_id)
        return os.path.join(self.current_path, 'data', paper['file'])

    def look_paper_up(self, paper_id):
        for paper in self.all_papers:
            if paper['ID'] == paper_id:
                return paper



if __name__ == "__main__":
    import others
    db = DatabaseManager()
    # db.update_paper('test', 'file', 'filefile')
    # db.dump()
    # db.get_paper_attributes('test')
    print(others.export_bib_format(db.bib_database.entries[0]))

