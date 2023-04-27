import pdf2bib
from pdf2bib import pdf2bib_singlefile
pdf2bib.config.set('verbose',False)
path = r'./data/pdfs/1014052.1014062.pdf'
result = pdf2bib_singlefile(path)
print(result['metadata'])
print('\n')
print(result['bibtex'])
__import__('pdb').set_trace()
