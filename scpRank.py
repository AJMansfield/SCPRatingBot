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
import signal
import os
import random

import subprocess
import threading

import ConfigParser





def slugify(arg):
	return sluggy.slugify(unicode(str(arg).decode('utf-8')));


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

nextUpdateTime = time.time() + 60*60
updateCount = 0

def refresh():
	global ut
	global nextUpdateTime, updateCount
	try:
		updateCount += 1
		if updateCount % 6 == 0:
			os.remove('pages.tsv')
			os.remove('pids.tsv')

		print datetime.datetime.now(), " Refreshing cache"

		subprocess.call('./getVotes.sh')
		reload()

		print datetime.datetime.now(), " Scheduling next refresh"
		ut = threading.Timer(60*60, refresh)
		ut.setDaemon(True)
		ut.start()
		print datetime.datetime.now(), " Refreshed."

		nextUpdateTime = time.time() + 60*60

	except Exception:
		print datetime.datetime.now(), " An error occured while refreshing the cache."

		try:
			ut.cancel()
		except Exception:
			pass

		print datetime.datetime.now(), " Scheduling next refresh"
		ut = threading.Timer(60*60, refresh)
		ut.setDaemon(True)
		ut.start()

		raise;


def reload():
	try:
		print datetime.datetime.now(), " Reloading stored tables"
		global votes, vtab, pids, uids, m, override;

		votes = pd.read_csv('votes.tsv', '\t', header=None, names=['pid','uid','vote'], dtype={'pid':np.int32, 'vote':np.int8})
		votes.dropna(inplace=True)
		votes['uid'] = votes['uid'].astype(np.int32)
		votes.drop_duplicates(['pid','uid'], inplace=True)
		votes.set_index(['uid', 'pid'], inplace=True)

		pids = pd.read_csv('pids.tsv', '\t', header=None, names=['pname','pid','ptitle','uid','date'], dtype={'pname':'string', 'ptitle':'string', 'pid':np.int32})
		pids.fillna(0, inplace=True)
		pids['uid'] = pids['uid'].astype(np.int32)
		pids['date'] = pids['date'].astype(np.int32)
		pids.set_index('pid', inplace=True)

		uids = pd.read_csv('uids.tsv', '\t', header=None, names=['uid','uname'], dtype={'uname':'string'})
		uids.drop_duplicates(inplace=True)
		uids.dropna(inplace=True);
		uids['uid'] = uids['uid'].astype(np.int32);
		uids.set_index('uid', inplace=True)

		override = pd.read_csv('override.tsv', '\t', header=None, names=['pname','uids','uname'])
		override['uids'] = override['uids'].apply(lambda s: map(int, s.split()))
		override['uid'] = override.reset_index()['index'].apply(lambda x:-x-1)
		override['uid'] = override['uid'].astype(np.int32)
		
		uids = uids.append(override[['uid','uname']].set_index('uid'))

		authors = pids.reset_index()[['pname','uid']].set_index('pname')
		authors.update(override[['pname','uid']].set_index('pname'))
		authors.reset_index(inplace=True)
		authors.index = pids.index
		pids[['pname','uid']] = authors

		pids['uid'] = pids['uid'].astype(np.int32)

		print datetime.datetime.now(), " Counting votes"

		vtab = votes.unstack()['vote']
		vcounts = vtab.apply(pd.Series.value_counts).fillna(0).transpose().reset_index().set_index('pid')
		pids['up'] = vcounts[1]
		pids['dn'] = vcounts[-1]
		pids['best'] = vcounts[1].combine(vcounts[-1], lambda a,b: confidence(a,b,2.0)) * 10
		pids['hot'] = vcounts[1].combine(vcounts[-1], lambda a,b: confidence(a,b,1.0))
		pids['hot'] = pids['hot'] / (nextUpdateTime - pids['date']).apply(math.log) * 10
		pids['worst'] = vcounts[1].combine(vcounts[-1], lambda a,b: confidence(b,a,2.0)) * 10

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
			uid = uids[uids.uname.apply(slugify) == slugify(uname)].index[0]

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

		if i < 0:
			return "Out of range."

		return ("Showing " + str(5*i+1) + "-" + str(5*i+5) + "th best: " +
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

		if i < 0:
			return "Out of range."

		return ("Showing " + str(5*i+1) + "-" + str(5*i+5) + "th hottest: " +
			("http://scp-wiki.net/" + pids.sort_values('hot',ascending=False).iloc[5*i:5*i+5]['pname']).str.cat(sep=", "))

	except Exception as e:
		print datetime.datetime.now(), " ", args
		print datetime.datetime.now(), " ", e.__doc__
		print datetime.datetime.now(), " ", e.message
		return "An unknown error occured."

def worst(args):
	try:
		if args == "":
			i = 0
		else:
			i = int(args)-1

		if i < 0:
			return "Out of range."

		return ("Showing " + str(5*i+1) + "-" + str(5*i+5) + "th worst: " +
			("http://scp-wiki.net/" + pids.sort_values('worst',ascending=False).iloc[5*i:5*i+5]['pname']).str.cat(sep=", "))

	except Exception as e:
		print datetime.datetime.now(), " ", args
		print datetime.datetime.now(), " ", e.__doc__
		print datetime.datetime.now(), " ", e.message
		return "An unknown error occured."

def rank(pref):
	# try:

	pidscore = pids.sort_values('best',ascending=False).reset_index()
	entry = pidscore[(pidscore.pname.apply(slugify) == slugify(pref)) | (pidscore.ptitle.apply(slugify) == slugify(pref))]
	pidhot = pids.sort_values('hot',ascending=False).reset_index()
	entryhot = pidhot[pidhot.pid == entry.pid.iloc[0]]

	return (entry.ptitle.iloc[0] + ", by " + uids.loc[entry.uid.iloc[0]].uname + "." +
		" #" + str(entry.index[0]+1) + " all time (score %.5f)," % entry.best.iloc[0] +
		" #" + str(entryhot.index[0]+1) + " hottest (score %.5f)." % entry.hot.iloc[0] )

	# except Exception as e:
	# 	return ''





def command(cmd):
	try:
		if cmd[:1] == ".":
			print datetime.datetime.now(), " query:", cmd
		if cmd[:5] == ".rec ":
			return recommend(cmd[5:].strip())
		elif cmd[:6].strip() == ".best":
			return best(cmd[6:].strip())
		elif cmd[:6].strip() == ".rank":
			return rank(cmd[6:].strip())
		elif cmd[:5].strip() == ".hot":
			return hot(cmd[5:].strip())
		elif cmd[:7].strip() == ".worst":
			return worst(cmd[7:].strip())
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
	global ut

	if not(os.path.isfile('./pids.tsv')) or not(os.path.isfile('./uids.tsv')) or not(os.path.isfile('./votes.tsv')):
		print 'Setting up vote database for the first time.'
		refresh()


	config = ConfigParser.RawConfigParser({'port':'6667'})
	config.read('connection.ini')

	scpRank = ScpRank(**dict(config.items('ScpRank')))

	if config.has_section('Sybil'):
		sybil = Sybil(outbot=scpRank, **dict(config.items('Sybil')))
		st = threading.Thread(target=sybil.start)
		st.setDaemon(True)
		st.start()

	reload()
	
	ut = threading.Timer(10*60, refresh)
	ut.setDaemon(True)
	ut.start()

	rt = threading.Thread(target=scpRank.start)
	rt.setDaemon(True)
	rt.start()

	def signal_handler(signal, frame):
		scpRank.disconnect("scpRank should be back soon!")

		if config.has_section('Sybil'):
			wait = random.randint(0, 30)
			print datetime.datetime.now(), " Waiting ", wait, " seconds before disconnecting sybil."
			time.sleep(wait)

			sybil.disconnect()

		sys.exit(0)

	signal.signal(signal.SIGINT, signal_handler)
	signal.pause()

if (__name__ == "__main__")  and not(sys.flags.interactive):
	main()

