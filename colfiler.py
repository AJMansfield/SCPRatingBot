

import pandas as pd
import scipy as sp
import scipy.sparse as sps
import scipy.sparse.linalg as sls
import numpy as np

from scipy.spatial.distance import cosine

votes = pd.read_csv('votes.tsv', '\t', header=None)
votes.drop_duplicates([0,1], inplace=True)

vtab = votes.pivot(1,0,2)
vtab.fillna(0, inplace=True)

pids = pd.read_csv('pids.tsv', '\t', header=None, names=['pid','pname'])

uids = pd.read_csv('uids.tsv', '\t', header=None, index_col=1, names=['uid','uname'])

svtab = sps.csr_matrix(vtab)
u, s, v = sls.svds(svtab)
s = np.diag(s)

# GetUserName

uname = input('Enter Username:')
#uname = "AJMansfield"

uid = uids.loc[uname,'uid']

uvote = vtab.loc[uid].as_matrix()[:,None]

print pd.DataFrame(v.transpose().dot(s.dot(v.dot(uvote)))).join(pids).sort(0, ascending=False).head()

