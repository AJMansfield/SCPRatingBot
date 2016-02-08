#!/usr/bin/python

import pandas as pd
import scipy as sp
import scipy.sparse as sps
import scipy.sparse.linalg as sls
import numpy as np

from scipy.spatial.distance import cosine

votes = pd.read_csv('votes.tsv', '\t', header=None, names=['pid','uid','vote'])
votes.drop_duplicates(['pid','uid'], inplace=True)

vtab = votes.pivot('uid','pid','vote')
vtab.fillna(0, inplace=True)


pids = pd.read_csv('pids.tsv', '\t', header=None, names=['pid','pname'])

uids = pd.read_csv('uids.tsv', '\t', header=None, index_col=1, names=['uid','uname'])

svtab = sps.csr_matrix(vtab)

row_sums = np.linalg.norm(vtab.as_matrix(), axis=1)
row_indices, col_indices = svtab.nonzero()
svtab.data /= row_sums[row_indices]

del row_sums
del row_indices
del col_indices

m = svtab.transpose().dot(svtab);

# GetUserName

while True:
	try:

		uname = input('Enter Username:')
		#uname = "AJMansfield"
		uid = uids.loc[uname,'uid']

	except KeyError, SyntaxError:

		if uname != "love" and uname != "hate" and uname != "random":
			print "Invalid username."
			continue;

	if uname == "love":
		uid = uids.ix[0,'uid']
		uvote = np.ones(vtab.loc[uid].as_matrix().shape)

	elif uname == "hate":
		uid = uids.ix[0,'uid']
		uvote = -np.ones(vtab.loc[uid].as_matrix().shape)

	elif uname == "random":
		uid = uids.ix[0,'uid']
		uvote = np.random.random(vtab.loc[uid].as_matrix().shape)

	else:
		print "ID:", uid
		uvote = vtab.loc[uid].as_matrix()

	print pd.DataFrame(m.dot(uvote), names=['score']).join(pids).sort(0, ascending=False).head()

