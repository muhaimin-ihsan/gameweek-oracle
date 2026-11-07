import os
H=os.path.dirname(os.path.abspath(__file__))
s=open(os.path.join(H,'template.html'),encoding='utf8').read()
d=open(os.path.join(H,'data.json'),encoding='utf8').read().replace('</','<'+chr(92)+'/')
open(os.path.join(H,'..','gameweek-oracle.html'),'w',encoding='utf8').write(s.replace('__DATA__',d))
