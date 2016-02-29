#!/usr/bin/python

import pandas as pd
import scipy as sp
import scipy.sparse as sps
import scipy.sparse.linalg as sls
import numpy as np

import slugify as sluggy

import math

import irc.bot
import irc.strings

import time
import datetime
import sys
import os
import random

import subprocess
import threading

import ConfigParser

def slugify(arg):
	return sluggy.slugify(unicode(arg));


def confidence(ups, downs, z = 1.0, lb=True): #z = 1.44 for 85%, z = 1.96 for 95%
    n = ups + downs

    if n == 0:
        return 0

    phat = float(ups) / n
    if lb:
    	return ((phat + z*z/(2*n) - z * math.sqrt((phat*(1-phat)+z*z/(4*n))/n))/(1+z*z/n))
    else:
    	return ((phat + z*z/(2*n) + z * math.sqrt((phat*(1-phat)+z*z/(4*n))/n))/(1+z*z/n))


np.seterr(all='warn')

nextUpdateTime = time.time() + 6*60*60

def fullrefresh():
	global nextUpdateTime
	try:
		print datetime.datetime.now(), " Refreshing cache"
		subprocess.call('./getVotes.sh')
		refresh()
		print datetime.datetime.now(), " Scheduling next refresh"
		t = threading.Timer(6*60*60, fullrefresh)
		t.setDaemon(True)
		t.start()
		print datetime.datetime.now(), " Refreshed."

		nextUpdateTime = time.time() + 6*60*60

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

		pids = pd.read_csv('pids.tsv', '\t', header=None, names=['pname','pid','aid','date'], dtype={'pname':'string', 'pid':np.int32})
		pids.fillna(0, inplace=True)
		pids['aid'] = pids['aid'].astype(np.int32)
		pids['date'] = pids['date'].astype(np.int32)
		pids.set_index('pid', inplace=True)

		uids = pd.read_csv('uids.tsv', '\t', header=None, names=['uid','uname'], dtype={'uid':np.int32, 'uname':'string'})
		uids.drop_duplicates(inplace=True)
		uids.set_index('uid', inplace=True)

		print datetime.datetime.now(), " Counting votes"

		vtab = votes.unstack()['vote']
		vcounts = vtab.apply(pd.Series.value_counts).fillna(0).transpose().reset_index().set_index('pid')
		pids['best'] = vcounts[1].combine(vcounts[-1], lambda a,b: confidence(a,b)) * 10
		pids['hot'] = pids['best'] / (nextUpdateTime - pids['date']).apply(math.log) * 100
		
		print datetime.datetime.now(), " Computing transform"

		vtab = vtab.fillna(0).astype(np.float16)
		svtab = sps.csr_matrix(vtab)

		svtab = svtab / np.linalg.norm(vtab.as_matrix(), axis=0, keepdims=True)

		m = svtab.transpose().dot(svtab)

		del svtab

		print datetime.datetime.now(), " Done."

	except Exception:
		print datetime.datetime.now(), "An error occured while reloading the tables."
		raise


def recommend(uname):

	try:
		try:
			uid = uids[uids.name.apply(slugify) == slugify(uname)].index[0]

		except KeyError, SyntaxError:

			return "Username not recognised."

		uvote = vtab.loc[uid:uid].transpose()
		uvote['score'] = m.dot(uvote)

		data = pd.merge(pids, uvote, left_index=True, right_index=True)
		data = data[data[uid] == 0].sort_values(by='score', ascending=False)
		data = data[data['score'] > 0]

		return ("http://scp-wiki.net/" + data.head(20).sample(n=3, weights='score')['pname']).str.cat(sep=", ")

	except Exception as e:
		print datetime.datetime.now(), " ", uname
		print datetime.datetime.now(), " ", e.__doc__
		print datetime.datetime.now(), " ", e.message
		return "An unknown error occured."


def best(args):
	try:
		if args == "":
			i = 0
		else:
			i = int(args)-1

		if i <= 0:
			return "Out of range."

		return ("Showing " + str(5*i+1) + "-" + str(5*i+5) + ": " +
			("http://scp-wiki.net/" + pids.sort_values('best',ascending=False).iloc[5*i:5*i+5]['pname']).str.cat(sep=", "))

	except Exception as e:
		print datetime.datetime.now(), " ", args
		print datetime.datetime.now(), " ", e.__doc__
		print datetime.datetime.now(), " ", e.message
		return "An unknown error occured."

def hot(args):
	try:
		if args == "":
			i = 0
		else:
			i = int(args)-1

		if i <= 0:
			return "Out of range."

		return ("Showing " + str(5*i+1) + "-" + str(5*i+5) + ": " +
			("http://scp-wiki.net/" + pids.sort_values('hot',ascending=False).iloc[5*i:5*i+5]['pname']).str.cat(sep=", "))

	except Exception as e:
		print datetime.datetime.now(), " ", args
		print datetime.datetime.now(), " ", e.__doc__
		print datetime.datetime.now(), " ", e.message
		return "An unknown error occured."

def rank(pname):
	try:

		pidscore = pids.sort_values('best',ascending=False).reset_index()
		entry = pidscore[pidscore.pname == slugify(pname)]
		pidhot = pids.sort_values('hot',ascending=False).reset_index()
		entryhot = pidhot[pidhot.pname == slugify(pname)]

		return ("Author: " + uids.loc[entry.aid.iloc[0]].uname + 
			"; All Time: #" + str(entry.index[0]+1) + ", score %.5f" % entry.best.iloc[0] +
			"; Hot: # " + str(entryhot.index[0]+1) + ", score %.5f" % entry.hot.iloc[0] )

	except Exception as e:
		return ''





def command(cmd):
	try:
		if cmd[:1] == ".":
			print datetime.datetime.now(), " query:", cmd
		if cmd[:5] == ".rec ":
			return recommend(cmd[5:].strip())
		elif cmd[:6].strip() == ".best":
			return best(cmd[6:].strip())
		elif cmd[:6].strip() == ".rank":
			return rank(cmd[5:].strip())
		elif cmd[:6].strip() == ".hot":
			return hot(cmd[5:].strip())
		elif cmd[:4] == ".new":
			return "This feature has not yet been implemented."
		elif cmd[:4] == ".src":
			return "https://github.com/AJMansfield/SCPRatingBot"
		else:
			return ""

	except Exception as e:
		print datetime.datetime.now(), " ", cmd
		print datetime.datetime.now(), " ", e.__doc__
		print datetime.datetime.now(), " ", e.message
		return "An unknown error occured."




class ScpRank(irc.bot.SingleServerIRCBot):
	def __init__(self, channel, nickname, server, port=6667, password=''):
		irc.bot.SingleServerIRCBot.__init__(self, [(server, int(port))], nickname, nickname)
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

class Sybil(irc.bot.SingleServerIRCBot):
	def __init__(self, channel='', nickname='', server='', port=6667, password='', outbot=None):
		irc.bot.SingleServerIRCBot.__init__(self, [(server, int(port))], nickname, nickname)
		self.channel = channel
		self.password = password
		self.outbot = outbot

	def on_nicknameinuse(self, c, e):
		c.nick(c.get_nickname() + "_")

	def on_welcome(self, c, e):
		if self.password != "none":
			print datetime.datetime.now(), " Sybil: Authenticating"
			c.privmsg("NickServ", "IDENTIFY " + self.password)
			time.sleep(0.5);
		print datetime.datetime.now(), " Sybil: Joining channel"
		c.join(self.channel)
		print datetime.datetime.now(), " Sybil: Connected."

	def on_privmsg(self, c, e):
		pass

	def on_pubmsg(self, c, e):
		nick = e.source.nick
		c = self.outbot.connection
		if e.arguments[0][:8] == "scpRank:":
			result = command(e.arguments[0][8:].strip())
		else:
			result = command(e.arguments[0])
			
		if result != "":
			c.privmsg(nick, nick + ": " + result);
			print datetime.datetime.now(), "Sybil: Sent notice: ", nick, ": ", result

	def on_dccmsg(self, c, e):
		pass

	def on_dccchat(self, c, e):
		pass


def main():
	if not(os.path.isfile('./pids.tsv')) or not(os.path.isfile('./uids.tsv')) or not(os.path.isfile('./votes.tsv')):
		print 'Setting up vote database for the first time.'
		fullrefresh()


	config = ConfigParser.RawConfigParser({'port':'6667'})
	config.read('connection.ini')

	scpRank = ScpRank(**dict(config.items('ScpRank')))

	if config.has_section('Sybil'):
		sybil = Sybil(outbot=scpRank, **dict(config.items('Sybil')))
		st = threading.Thread(target=sybil.start)
		st.setDaemon(True)
		st.start()

	refresh()
	ut = threading.Timer(60*60, fullrefresh)
	ut.setDaemon(True)
	ut.start()

	try:
		scpRank.start()
	except:

		scpRank.disconnect("scpRank should be back soon!")

		wait = random.randint(0, 30)
		print datetime.datetime.now(), " Waiting ", wait, " seconds before disconnecting sybil."
		time.sleep(wait)

		sybil.disconnect("disconnect message")

		sys.exit(0)
		
if (__name__ == "__main__")  and not(sys.flags.interactive):
	main()

