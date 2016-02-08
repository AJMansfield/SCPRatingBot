#!/usr/bin/python

import pandas as pd
import scipy as sp
import scipy.sparse as sps
import scipy.sparse.linalg as sls
import numpy as np

from scipy.spatial.distance import cosine


import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr


def refresh():
	global votes, vtab, pids, uids, m;

	votes = pd.read_csv('votes.tsv', '\t', header=None, names=['pid','uid','vote'])
	votes.drop_duplicates(['pid','uid'], inplace=True)

	vtab = votes.pivot('uid','pid','vote')
	vtab.fillna(0, inplace=True)


	pids = pd.read_csv('pids.tsv', '\t', header=None, names=['pname','pid'])

	uids = pd.read_csv('uids.tsv', '\t', header=None, names=['uid','uname'])
	uids.drop_duplicates(inplace=True)
	uids.set_index('uname', inplace=True)

	svtab = sps.csr_matrix(vtab)

	row_sums = np.linalg.norm(vtab.as_matrix(), axis=1)
	row_indices, _ = svtab.nonzero()
	svtab.data /= row_sums[row_indices]

	del row_sums
	del row_indices

	m = svtab.transpose().dot(svtab);

# GetUserName

def recommend(uname):

	try:
		uid = uids.loc[uname,'uid']

	except KeyError, SyntaxError:

		if uname != "love" and uname != "hate" and uname != "random":
			return "Username not recognised."

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
		uvote = vtab.loc[uid].as_matrix()

	data = np.concatenate((uvote[:,np.newaxis],m.dot(uvote)[:,np.newaxis]), axis=1)

	data = pd.DataFrame(data, columns=['vote', 'score']).join(pids)

	data = data[data['vote'].isin([0])].sort_values(by='score', ascending=False)

	data = data[data['score'] > 0]

	#print data.head(10)

	return "http://scp-wiki.net/" + data.head(10).sample(weights='score')['pname'].iloc[0]




class TestBot(irc.bot.SingleServerIRCBot):
	def __init__(self, channel, nickname, server, port=6667):
		irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
		self.channel = channel

	def on_nicknameinuse(self, c, e):
		c.nick(c.get_nickname() + "_")

	def on_welcome(self, c, e):
		c.join(self.channel)

	def on_privmsg(self, c, e):
		self.do_command(e, e.arguments[0])

	def on_pubmsg(self, c, e):
		self.do_command(e, e.arguments[0])

	def on_dccmsg(self, c, e):
		pass

	def on_dccchat(self, c, e):
		pass

	def do_command(self, e, cmd):
		nick = e.source.nick
		c = self.connection

		if cmd[:4] == ".rec":
			c.privmsg(self.channel, nick + ": " + recommend( cmd[4:].strip()))


def main():
	import sys
	refresh()

	if len(sys.argv) != 4:
		print("Usage: testbot <server[:port]> <channel> <nickname>")
		sys.exit(1)

	s = sys.argv[1].split(":", 1)
	server = s[0]
	if len(s) == 2:
		try:
			port = int(s[1])
		except ValueError:
			print("Error: Erroneous port.")
			sys.exit(1)
	else:
		port = 6667
	channel = sys.argv[2]
	nickname = sys.argv[3]

	bot = TestBot(channel, nickname, server, port)
	bot.start()

if __name__ == "__main__":
	main()