#!/usr/bin/python

import pandas as pd
import scipy as sp
import scipy.sparse as sps
import scipy.sparse.linalg as sls
import numpy as np

import irc.bot
import irc.strings

import time



import subprocess
import threading

def fullrefresh():
	subprocess.call('./getVotes.sh')
	refresh()
	threading.Timer(6*60*60, fullrefresh).start()

refreshLock = threading.Lock();
def refresh():
	global votes, vtab, pids, uids, m;

	votes2 = pd.read_csv('votes.tsv', '\t', header=None, names=['pid','uid','vote'])
	votes2.drop_duplicates(['pid','uid'], inplace=True)

	vtab2 = votes2.pivot('uid','pid','vote')
	vtab2.fillna(0, inplace=True)


	pids2 = pd.read_csv('pids.tsv', '\t', header=None, names=['pname','pid'])

	uids2 = pd.read_csv('uids.tsv', '\t', header=None, names=['uid','uname'])
	uids2.drop_duplicates(inplace=True)
	uids2.set_index('uname', inplace=True)

	svtab = sps.csr_matrix(vtab2)

	svtab /= np.linalg.norm(vtab2.as_matrix(), axis=0, keepdims=True)

	m2 = svtab2.transpose().dot(svtab2)
	
	with refreshLock:
		votes, vtab, pids, uids, m = votes2, vtab2, pids2, uids2, m2

# GetUserName

def recommend(uname):

	with refreshLock:
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
	def __init__(self, channel, nickname, server, port=6667, password=''):
		irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
		self.channel = channel
		self.password = password

	def on_nicknameinuse(self, c, e):
		c.nick(c.get_nickname() + "_")

	def on_welcome(self, c, e):
		print "authenticating..."
		c.privmsg("NickServ", "IDENTIFY " + self.password)
		time.sleep(0.5);
		print "joining..."
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
			rec = nick + ": " + recommend( cmd[4:].strip())
			c.privmsg(self.channel, rec)
			print "query:", cmd
			print "recommendation: ", rec


def main():
	import sys

	refresh()
	threading.Timer(60*60, fullrefresh).start()

	if len(sys.argv) != 5:
		print("Usage: scpRank.py <server[:port]> <channel> <nickname> <password>")
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
	password = sys.argv[4]

	bot = TestBot(channel, nickname, server, port, password)

	bot.start()

#if __name__ == "__main__":
#	main()