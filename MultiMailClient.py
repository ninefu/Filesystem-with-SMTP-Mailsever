#!/usr/bin/python

# TODO: Implement the multi-threaded client here.
# This program should be able to run with no arguments
# and should connect to "127.0.0.1" on port 8765.  It
# should run approximately 1000 operations, and be extremely likely to
# encounter all error conditions described in the README.

import sys
import socket
import time
import random
from random import *
import string
import threading
from threading import Thread, Lock

# from provided client.py
host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765

threadNumber = 32
commandPool = ["HELO ", "MAIL FROM: ", "RCPT TO: ", "DATA", "", "OTHER "]
stringPool = string.ascii_letters + string.digits
threshold = 8

class Counter():

	def __init__(self):
		self.lock = Lock()
		self.totalMsg = 0

	def getCount(self):
		return self.totalMsg

	def addCounts(self, counts):
		with self.lock:
			self.totalMsg += counts

class RandomizedClient(Thread):

	def __init__(self, id, Counter):
		Thread.__init__(self)
		self.starTime = time.time()
		self.socket = None
		self.id = id
		self.totalMessage = 0 # number of operations
		self.state = 0
		self.counter = Counter
		
	def connectSocket(self):
		# build connection
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.connect((host,port))
		self.state = 0
		# SYN-ACK

	def randomString(self,length):
		""" Randomly vary the client-provided information (hostnames, data, and email name/host)
		"""
		return "".join(sample(stringPool, length))

	def randomEmail(self):
		""" Randomly vary the client-provided information (email address)
			It may include @ or space, or neither, or both
			Error code: 
				504: invalid address
				250: valid address
		"""
		if (randint(0,100) < threshold): # no @
			if (randint(0,100) < threshold):
				address = self.randomString(6) + " " + self.randomString(6) # include space
				error = 504
			else:
				address = self.randomString(13) # exclude space
				error = 504
		else: # include @
			if (randint(0,100) < threshold):
				address = self.randomString(6) + " @" + self.randomString(6) # include space
				error = 504
			else:
				address = self.randomString(6) + "@" + self.randomString(6) # exclude space
				error = 250

		return (error, address)

	def getCommand(self):
		""" Randomly generate commands which may deviate from the protocol 
		"""
		commandType = 0
		if (randint(0,100) > threshold):
			commandType = self.state
		else:
			commandType = randint(0, len(commandPool) - 1)
		command = commandPool[commandType]
		code = 0

		if (commandType == 0): # HELO
			if (randint(0,100) < threshold):
				host = self.randomString(5) + " " + self.randomString(5) # include a space in the host name
				code = 501
			else:
				host = self.randomString(11) # valid host
				code = 250
			command += host
		elif (commandType == 1 or commandType == 2): # MAIL FROM or RCPT TO
			(code, address) = self.randomEmail()
			if (randint(0,100) < threshold):
				command = command[0:5] # command only with "MAIL " or "RCPT "
				code = 501
			command += address
		elif (commandType == 3): # DATA
			if (randint(0,100) < threshold):
				command = command + " " + self.randomString(5) # DATA syntax error
				code = 501
			else:
				code = 354 # valid command
		elif (commandType == 4): # "", message
			command = command + self.randomString(5) + " " + self.randomString(5) + " End\r\n."
			code = 250
		else: # OTHER
			code = 502 # command not recognized

		# randomly include the end mark
		if (randint(0,100) > threshold):
			command += '\r\n'
		else:

			code = 421 # time out

		return (code, commandType, command)

	def identify_error(self, reply, state, code, commandType):
		if (reply is not None):
			replyCode = int(reply.split()[0])
			if (code == 421):
				return ((replyCode == 421), replyCode)
			elif commandType > 4:
				return ((replyCode == 502), replyCode)
			elif commandType == 4 and state != 4:
				return ((replyCode == 502), replyCode)
			elif (state == commandType):
				return ((replyCode == code), replyCode)
			else:
				return ((replyCode == 503), replyCode)

	def run(self):
		self.connectSocket()

		""" 0 : HELO
			1: MAIL FROM
			2: RCPT TO
			3: DATA
			4: (MESSAGE)
			5: (OTHER COMMAND)
		"""
		while time.time() - self.starTime < 60:
			try:
				# get command
				(code, commandType, command) = self.getCommand()
				self.socket.send(command)
				self.totalMessage += 1
				# get the reply from server and identity reply
				reply = self.socket.recv(500)
				(verify, info) = self.identify_error(reply, self.state, code, commandType)	
				if verify:
					if ((info == 250 and commandType != 2) or (commandType == 3 and info == 354) or 
					(self.state != 4 and commandType != 2)):
						self.state += 1
						if (self.state > 4):
							self.state = 1
			except Exception as e:
				self.connectSocket()

		self.socket.close()
		self.counter.addCounts(self.totalMessage)

counter = Counter()
clients = [RandomizedClient(i,counter) for i in range(threadNumber)]
for i in range(threadNumber):
	clients[i].start()
time.sleep(66)
print "In 60 seconds, {} clients sent {} total message.".format(threadNumber, counter.getCount())