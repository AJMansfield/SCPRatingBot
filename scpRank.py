#!/usr/bin/python

import pandas as pd
import scipy as sp
import scipy.sparse as sps
import scipy.sparse.linalg as sls
import numpy as np

import irc.bot
import irc.strings

import time
import datetime
import sys

import subprocess
import threading

np.seterr(all='raise', divide='raise', over='raise', under='raise', invalid='raise')

def fullrefresh():
	print datetime.datetime.now(), " Refreshing cache"
	subprocess.call('./getVotes.sh')
	refresh()
	print "Scheduling next refresh"
	t = threading.Timer(1*60*60, fullrefresh)
	t.setDaemon(True)
	t.start()
	print datetime.datetime.now(), " Refreshed."


def refresh():
	print datetime.datetime.now(), " Refreshing stored tables"
	global votes, vtab, pids, uids, m;

	votes = pd.read_csv('votes.tsv', '\t', header=None, names=['pid','uid','vote'], dtype={'pid':np.int32, 'uid':np.int32, 'vote':np.int8})
	votes.drop_duplicates(['pid','uid'], inplace=True)
	votes.set_index(['uid', 'pid'], inplace=True)

	vtab = votes.unstack().fillna(0).astype(np.int16)

	svtab = sps.csr_matrix(vtab)

	print datetime.datetime.now(), " Computing transform"

	m = svtab.transpose().dot(svtab)

	del svtab

	print datetime.datetime.now(), " Updating tables"

	pids = pd.read_csv('pids.tsv', '\t', header=None, names=['pname','pid'], dtype={'pid':np.int32, 'pname':'string'})

	uids = pd.read_csv('uids.tsv', '\t', header=None, names=['uid','uname'], dtype={'uid':np.int32, 'uname':'string'})
	uids.drop_duplicates(inplace=True)
	uids.set_index('uname', inplace=True)


def recommend(uname):
	uname = uname.lower()
	try:
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

		data = np.concatenate((uvote[:,np.newaxis], (m.dot(uvote) / m.diagonal().astype(np.float16))[:,np.newaxis] ), axis=1)

		data = pd.DataFrame(data, columns=['vote', 'score']).join(pids)

		data = data[data['vote'].isin([0])].sort_values(by='score', ascending=False)

		data = data[data['score'] > 0]

		#print data.head(10)

		return "http://scp-wiki.net/" + data.head(20).sample(weights='score')['pname'].iloc[0]
	except Exception as e:
		print datetime.datetime.now(), " ", uname
		print datetime.datetime.now(), " ", e.__doc__
		print datetime.datetime.now(), " ", e.message
		return "An unknown error occured."




class TestBot(irc.bot.SingleServerIRCBot):
	def __init__(self, channel, nickname, server, port=6667, password=''):
		irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
		self.channel = channel
		self.password = password

	def on_nicknameinuse(self, c, e):
		c.nick(c.get_nickname() + "_")

	def on_welcome(self, c, e):
		print datetime.datetime.now(), " Authenticating"
		c.privmsg("NickServ", "IDENTIFY " + self.password)
		time.sleep(0.5);
		print datetime.datetime.now(), " Joining channel"
		c.join(self.channel)
		print datetime.datetime.now(), " Connected."

	def on_privmsg(self, c, e):
		nick = e.source.nick
		c = self.connection

		if e.arguments[0][:4] == ".rec":
			print datetime.datetime.now(), " query:", e.arguments[0]
			rec = nick + ": " + recommend( e.arguments[0][4:].strip())
			c.privmsg(nick, rec)
			print datetime.datetime.now(), " recommendation: ", rec

	def on_pubmsg(self, c, e):
		nick = e.source.nick
		c = self.connection

		if e.arguments[0][:4] == ".rec":
			print datetime.datetime.now(), " query:", e.arguments[0]
			rec = nick + ": " + recommend( e.arguments[0][4:].strip())
			c.privmsg(self.channel, rec)
			print datetime.datetime.now(), " recommendation: ", rec

	def on_dccmsg(self, c, e):
		pass

	def on_dccchat(self, c, e):
		pass


def main():

	refresh()
	t = threading.Timer(60*60, fullrefresh)
	t.setDaemon(True)
	t.start()

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

if __name__ == "__main__":
	main()