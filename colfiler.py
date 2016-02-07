

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

row_sums = np.array(svtab.sum(axis=1))[:,0]
row_indices, col_indices = svtab.nonzero()
svtab.data /= row_sums[row_indices]

del row_sums
del row_indices
del col_indices

m = svtab.transpose().dot(svtab);

# GetUserName

while True:

	uname = input('Enter Username:')
	#uname = "AJMansfield"

	uid = uids.loc[uname,'uid']

	print "ID:", uid

	uvote = vtab.loc[uid].as_matrix()

	print pd.DataFrame(m.dot(uvote/np.linalg.norm(uvote))).join(pids).sort(0, ascending=False).head()

