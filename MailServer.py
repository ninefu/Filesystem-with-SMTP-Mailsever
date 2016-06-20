import getopt
import socket
import sys

from threading import Thread, Condition, Lock
import time
import shutil

# Don't change 'host' and 'port' values below.  If you do, we will not be able to
# find your server when grading.
host = "127.0.0.1"
port = 8765
# Instead, you can pass command-line arguments
# -h/--host [IP] -p/--port [PORT]
# to put your server on a different IP/port.

threadNumber = 32
netID = "yf263"

class ConnectionHandler:
    """Handles a single client request"""

    def __init__(self, socket, WriteMonitor):
        self.socket = socket
        self.writer = WriteMonitor
        self.incomingMessage = ""
        self.expectedCommand = "CLOSED"
        self.email = {}
        self.email['to'] = []

    def handle(self):
        # update the expected command so that it's ready to handle msg
        self.expectedCommand = "HELO"
        self.sendAndReset("220 " + netID + " SMTP CS4410MP3\r\n")
        while (self.expectedCommand != "CLOSED"):
            if (self.expectedCommand == "HELO"):
                self.HELO()
            elif (self.expectedCommand == "MAIL"):
                self.MAIL()
            elif (self.expectedCommand == "RCPT"):
                self.RCPT()
            elif (self.expectedCommand == "DATA"):
                self.DATA()
            elif (self.expectedCommand == "WRITE"):
                self.WRITE()
        self.socket.close()
    
    def getSocketMessage(self, token):
        while self.incomingMessage.find(token) == -1:            
            try:
                self.incomingMessage = self.incomingMessage + self.socket.recv(500)
            except:
                self.expectedCommand = "CLOSED"
                self.sendMessage("421 4.4.2 "+ netID +" Error: timeout exceeded\r\n")
                return
        
        index = self.incomingMessage.find(token);
        msg = self.incomingMessage[0:index]
        self.incomingMessage = self.incomingMessage[(index + len(token)):]
        return msg
                
    def HELO(self):
        message = self.getSocketMessage("\r\n")
        if (message != None):
            tokens = message.split()
            if (len(tokens) == 0):
                # empty command
                self.sendMessage("502 5.5.2 Error: command not recognized\r\n")
            else:
                if (tokens[0].upper() == "HELO"):
                    if (len(tokens) == 2):
                        # correct command syntax, update accordingly
                        self.email["clientHostName"] = tokens[1]
                        self.expectedCommand = "MAIL"
                        self.sendAndReset("250 " + netID + "\r\n")
                    else:
                        # command starts with HELO but wrong agurments
                        self.sendMessage("501 Syntax: HELO clientHostName\r\n")
                elif (tokens[0].upper() == "MAIL" or tokens[0].upper() == "RCPT" 
                      or tokens[0].upper() == "DATA"):
                    # command not in the right order
                    self.sendMessage("503 Error: need HELO command\r\n")
                else:
                    # un-recognized command
                    self.sendMessage("502 5.5.2 Error: command not recognized\r\n")
     
    def MAIL(self):
        message = self.getSocketMessage("\r\n")
        if (message != None):
            tokens = message.split()
            if (len(tokens) == 0):
                # empty command
                self.sendMessage("502 5.5.2 Error: command not recognized\r\n")
            else:
                if (tokens[0].upper() == "HELO"):
                    self.sendMessage("503 Error: duplicate HELO\r\n")
                elif (tokens[0].upper() == "MAIL"):
                    if (len(tokens) == 1):
                        # only contain MAIL, no following command/argument
                        self.sendMessage("501 Syntax: MAIL FROM:email@host\r\n")
                    elif (tokens[1].upper().find("FROM") == -1):
                        self.sendMessage("501 Syntax: MAIL FROM:email@host\r\n")
                    else:
                        # at least found "MAIL FROM"
                        if ("from" in self.email):
                            # duplicate MAIL command
                            self.sendMessage("503 5.5.1 Error: nested MAIL command\r\n")
                        else:
                            colonIdx = message.find(":")
                            address = message[colonIdx + 1 : ].strip()
                            if (address.find(" ") == -1 and address.find("@") > 0 and address.find("@") < len(address) - 1):
                                # no whitespace, and there are content before @ and after @
                                self.email['from'] = address
                                self.expectedCommand = "RCPT"
                                self.sendAndReset("250 2.1.0 OK\r\n")
                            else:
                                self.sendMessage("504 5.5.2 <" + address +">: Sender address rejected\r\n")
                elif (tokens[0].upper() == "RCPT" or tokens[0].upper() == "DATA"):
                    # command not in the right order
                    self.sendMessage("503 Error: need MAIL command\r\n")
                else:
                    # un-recognized command
                    self.sendMessage("502 5.5.2 Error: command not recognized\r\n")
    
    def RCPT(self):
        message = self.getSocketMessage("\r\n")
        if (message != None):
            tokens = message.split()
            if (len(tokens) == 0):
                # empty command
                self.sendMessage("502 5.5.2 Error: command not recognized\r\n")
            else:
                if (tokens[0].upper() == "HELO"):
                    self.sendMessage("503 Error: duplicate HELO\r\n")
                elif (tokens[0].upper() == "MAIL"):
                    self.sendMessage("503 5.5.1 Error: nested MAIL command\r\n")
                elif (tokens[0].upper() == "RCPT"):
                    if (len(tokens) == 1):
                        # only contain RCPT, no following command/argument
                        self.sendMessage("501 Syntax: RCPT TO:email@host\r\n")
                    elif (tokens[1].upper().find("TO") == -1):
                        self.sendMessage("501 Syntax: RCPT TO:email@host\r\n")
                    else:
                        # at least found "RCPT TO"
                        colonIdx = message.find(":")
                        address = message[colonIdx + 1 : ].strip()
                        if (address.find(" ") == -1 and address.find("@") > 0 and address.find("@") < len(address) - 1):
                            # no whitespace, and there are content before @ and after @
                            self.email['to'].append(address)
                            self.sendAndReset("250 2.1.5 OK\r\n")
                        else:
                            self.sendMessage("504 5.5.2 <" + address +">: Recipient address invalid\r\n")
                elif (tokens[0].upper() == "DATA"):
                    if (len(self.email['to']) == 0):
                        self.sendMessage("503 Error: need RCPT TO command\r\n")
                    else:
                        if (len(tokens) > 1):
                            self.sendMessage("501 Syntax: DATA\r\n")
                        else:
                            self.expectedCommand = "DATA"
                            self.sendMessage("354 End data with <CR><LF>.<CR><LF>\r\n")
                else:
                    self.sendMessage("502 5.5.2 Error: command not recognized\r\n")


    def DATA(self):
        message = self.getSocketMessage("\r\n.\r\n")
        if (message is not None):
            self.email['content'] = message
            self.expectedCommand = "WRITE"
        else:
            self.expectedCommand = "CLOSED"
    
    def WRITE(self):
        msgNum = self.writer.writeToFile(self.email)
        self.sendAndReset("250 OK: delivered message " + str(msgNum) + "\r\n")
        self.expectedCommand = "MAIL"
        self.email['to'] = []
        self.email.pop("from")
        self.email.pop("content")

    def sendAndReset(self, content):
        self.sendMessage(content)
        self.socket.settimeout(10.0)

    def sendMessage(self, msg):
        try:
            self.socket.send(msg.encode('utf-8'))
        except socket.error:
            self.expectedCommand == "CLOSED"
            # self.socket.close()        

class ThreadPool:
    
    def __init__(self):
        # self.queue = []
        self.lock = Lock()
        self.waitForTask = Condition(self.lock)
        self.waitForThread = Condition(self.lock)
        self.task = None
    
    def enqueue(self, clientsocket):
        with self.lock:
            while (self.task is not None):
                self.waitForThread.wait()
            self.task = clientsocket
            self.waitForTask.notify()
    
    def dequeue(self):
        with self.lock:
            while (self.task is None):
                self.waitForTask.wait()
            item = self.task
            self.task = None
            self.waitForThread.notify()
            return item

class Consumer(Thread):
    
    def __init__(self, threadPool, writePool):
        Thread.__init__(self)
        self.threadPool = threadPool
        self.writePool = writePool
        
    def run(self):
        while True:
            handler = ConnectionHandler(self.threadPool.dequeue(), self.writePool)
            handler.handle()

class WriteMonitor():
    
    def __init__(self):
        self.lock = Lock()
        self.toWrite = Condition(self.lock)
        self.toBackup = Condition(self.lock)
        self.isWriting = False
        self.isBackup = False
        self.emailNum = 1
        
    def writeToFile(self, email):
        """Return the message number"""
        # wait while back up or other thread is writing
        with self.lock:
            while (self.isWriting or self.isBackup):
                self.toWrite.wait()
            self.isWriting = True

            mailbox = 0
            if self.emailNum == 1:
                mailbox = open("mailbox","w")
            else:
                mailbox = open("mailbox","a")

            mailbox.write("Received: from " + email['clientHostName'] + " by " + netID + " (CS4410MP3)\n")
            mailbox.write("Number: " + str(self.emailNum) + "\n")
            mailbox.write("From: " + email['from'] + "\n")
            for recipient in email['to']:
                mailbox.write("To: " + recipient + "\n")
            mailbox.write("\n")
            mailbox.write(email['content'] + "\n")
            mailbox.write("\n")

            mailbox.close()

            self.emailNum += 1
            # self.isWriting = False
            if (self.emailNum > 1 and self.emailNum % 32 == 1):
                self.isBackup = True
                self.isWriting = False
                self.toBackup.notify()
            else:
                self.isWriting = False
                self.toWrite.notify()

        return self.emailNum - 1
                
    def writeToBackUp(self):
        # wait while writing or less than 32 emails
        with self.lock:
            while (self.isWriting or self.emailNum % 32 != 1 or self.isBackup == False):
                self.toBackup.wait()
            
            shutil.copyfile("mailbox", "mailbox." + str(self.emailNum - 32) + "-" + str(self.emailNum - 1))
            with open("mailbox","w") as mailbox:
                mailbox.write("")
            
            self.isBackup = False
            self.toWrite.notify()

class BackupWriter(Thread):
    def __init__(self, writeMonitor):
        Thread.__init__(self)
        self.writer = writeMonitor
    
    def run(self):
        while True:
            self.writer.writeToBackUp()
        
def serverloop():
    """The main server loop"""

    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # mark the socket so we can rebind quickly to this port number
    # after the socket is closed
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # bind the socket to the local loopback IP address and special port
    serversocket.bind((host, port))
    # start listening with a backlog of 5 connections
    serversocket.listen(5)
    
    threadPool = ThreadPool()
    writePool = WriteMonitor()
    BackupWriter(writePool).start()
    for i in range(threadNumber):
        Consumer(threadPool, writePool).start()


    while True:
        # accept a connection
        (clientsocket, address) = serversocket.accept()
        #ct = ConnectionHandler(clientsocket)
        #ct.handle()
        threadPool.enqueue(clientsocket)

# DO NOT CHANGE BELOW THIS LINE

opts, args = getopt.getopt(sys.argv[1:], 'h:p:', ['host=', 'port='])

for k, v in opts:
    if k in ('-h', '--host'):
        host = v
    if k in ('-p', '--port'):
        port = int(v)

print("Server coming up on %s:%i" % (host, port))
serverloop()
