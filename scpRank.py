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

np.seterr(all='warn')

def fullrefresh():
	try:
		print datetime.datetime.now(), " Refreshing cache"
		subprocess.call('./getVotes.sh')
		refresh()
		print datetime.datetime.now(), " Scheduling next refresh"
		t = threading.Timer(6*60*60, fullrefresh)
		t.setDaemon(True)
		t.start()
		print datetime.datetime.now(), " Refreshed."

	except Exception:
		print datetime.datetime.now(), " An error occured while refreshing the cache."

		try:
			t.cancel()
		except Exception:
			pass

		print datetime.datetime.now(), " Scheduling next refresh"
		t = threading.Timer(6*60*60, fullrefresh)
		t.setDaemon(True)
		t.start()

		raise;
	
def refresh():
	try:
		print datetime.datetime.now(), " Refreshing stored tables"
		global votes, vtab, pids, uids, m;

		votes = pd.read_csv('votes.tsv', '\t', header=None, names=['pid','uid','vote'], dtype={'pid':np.int32, 'uid':np.int32, 'vote':np.int8})
		votes.drop_duplicates(['pid','uid'], inplace=True)
		votes.set_index(['uid', 'pid'], inplace=True)

		vtab = votes.unstack().fillna(0).astype(np.float16)

		svtab = sps.csr_matrix(vtab)

		print datetime.datetime.now(), " Computing transform"

		svtab = svtab / np.linalg.norm(vtab.as_matrix(), axis=0, keepdims=True)

		m = svtab.transpose().dot(svtab)
		
		del svtab

		print datetime.datetime.now(), " Updating tables"

		pids = pd.read_csv('pids.tsv', '\t', header=None, names=['pname','pid'], dtype={'pid':np.int32, 'pname':'string'})

		uids = pd.read_csv('uids.tsv', '\t', header=None, names=['uid','uname'], dtype={'uid':np.int32, 'uname':'string'})
		uids.drop_duplicates(inplace=True)
		uids.set_index('uname', inplace=True)
	except Exception:
		print datetime.datetime.now(), "An error occured while reloading the tables."
		raise


def recommend(uname):

	uname = uname.lower()
	try:
		try:
			uid = uids.loc[uname,'uid']

		except KeyError, SyntaxError:

			return "Username not recognised."

		uvote = vtab.loc[uid].as_matrix()

		data = np.concatenate((uvote[:,np.newaxis], m.dot(uvote).T), axis=1)

		data = pd.DataFrame(data, columns=['vote', 'score']).join(pids)

		data = data[data['vote'].isin([0])].sort_values(by='score', ascending=False)

		data = data[data['score'] > 0]

		#print data.head(10)

		return ("http://scp-wiki.net/" + data.head(20).sample(n=3, weights='score')['pname']).str.cat(sep=", ")
	except Exception as e:
		print datetime.datetime.now(), " ", uname
		print datetime.datetime.now(), " ", e.__doc__
		print datetime.datetime.now(), " ", e.message
		return "An unknown error occured."

def command(cmd):
	if cmd[:1] == ".":
		print datetime.datetime.now(), " query:", cmd

	if cmd[:5] == ".rec ":
		return recommend(cmd[5:].strip())
	elif cmd[:4] == ".top":
		return "This feature has not yet been implemented."
	elif cmd[:4] == ".new":
		return "This feature has not yet been implemented."
	else:
		return ""




class ScpRankBot(irc.bot.SingleServerIRCBot):
	def __init__(self, channel, nickname, server, port=6667, password=''):
		irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
		self.channel = channel
		self.password = password

	def on_nicknameinuse(self, c, e):
		c.nick(c.get_nickname() + "_")

	def on_welcome(self, c, e):
		if self.password != "none":
			print datetime.datetime.now(), " Authenticating"
			c.privmsg("NickServ", "IDENTIFY " + self.password)
			time.sleep(0.5);
		print datetime.datetime.now(), " Joining channel"
		c.join(self.channel)
		print datetime.datetime.now(), " Connected."

	def on_privmsg(self, c, e):
		nick = e.source.nick
		c = self.connection

		result = command(e.arguments[0])
		if result != "":
			c.privmsg(nick, nick + ": " + result);
			print datetime.datetime.now(), " Sent PM: ", nick, ": ", result

	def on_pubmsg(self, c, e):
		nick = e.source.nick
		c = self.connection

		result = command(e.arguments[0])
		if result != "":
			c.privmsg(self.channel, nick + ": " + result);
			print datetime.datetime.now(), " Sent Chat: ", self.channel, ": ", nick, ": ", result

	def on_dccmsg(self, c, e):
		pass

	def on_dccchat(self, c, e):
		pass

class ScpRankLurker(irc.bot.SingleServerIRCBot):
	def __init__(self, channel, nickname, server, port=6667, password='', outbot=None):
		irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
		self.channel = channel
		self.password = password
		self.outbot = outbot

	def on_nicknameinuse(self, c, e):
		c.nick(c.get_nickname() + "_")

	def on_welcome(self, c, e):
		if self.password != "none":
			print datetime.datetime.now(), " Lurker: Authenticating"
			c.privmsg("NickServ", "IDENTIFY " + self.password)
			time.sleep(0.5);
		print datetime.datetime.now(), " Lurker: Joining channel"
		c.join(self.channel)
		print datetime.datetime.now(), " Lurker: Connected."

	def on_privmsg(self, c, e):
		pass

	def on_pubmsg(self, c, e):
		nick = e.source.nick
		c = self.outbot.connection
		if(e.arguments[0][:8] == "scpRank:")
			result = command(e.arguments[0][8:])
			if result != "":
				c.privmsg(nick, nick + ": " + result);
				print datetime.datetime.now(), " Lurker: Sent notice: ", nick, ": ", result

	def on_dccmsg(self, c, e):
		pass

	def on_dccchat(self, c, e):
		pass


def main():

	if len(sys.argv) != 8 and len(sys.argv) != 5:
		print("Usage: scpRank.py <server[:port]> <channel1> <nickname1> <password1> [<channel2> <nickname2> <password2>]")
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

	channel1 = sys.argv[2]
	nickname1 = sys.argv[3]
	password1 = sys.argv[4]
	if len(sys.argv) == 8:
		channel2 = sys.argv[5]
		nickname2 = sys.argv[6]
		password2 = sys.argv[7]

	refresh()
	ut = threading.Timer(60*60, fullrefresh)
	ut.setDaemon(True)
	ut.start()

	scpRank = ScpRankBot(channel1, nickname1, server, port, password1)
	if len(sys.argv) == 8:
		lurker = ScpRankLurker(channel2, nickname2, server, port, password2, scpRank)

		lt = threading.Thread(target=lurker.start)
		lt.setDaemon(True)
		lt.start()

	scpRank.start()

if __name__ == "__main__":
	main()