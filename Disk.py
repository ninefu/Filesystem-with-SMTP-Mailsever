import struct, os

from Constants import DISKSIZE, BLOCKSIZE
from threading import Thread, Lock, Condition
# Disk provides no synchronization; all synch operations should
# take place at a higher level in the software stack inside the
# file system!

DEBUG = False

class DiskException(Exception):
    def __init__(self, errortype):
        self.parameter = errortype

    def __str__(self):
        return repr(self.parameter)

class DiskClass:
    def __init__(self, brandnew=True):
        self.lock = Lock()
        if brandnew:
            if os.path.isfile('filesystem.bin'):
                print "Deleting Old Disk..."
                os.remove('filesystem.bin')
            # Create the disk
            self.formatdisk()
        # Open the disk for updating
        self.disk = open('filesystem.bin', 'rb+')

    def formatdisk(self):
        print "Formatting The Disk..."
        self.disk = open('filesystem.bin', 'wb')
        self.disk.write(struct.pack('B', 0) * DISKSIZE)
        self.disk.close()

    def blockwrite(self, blocknumber, data):
        with self.lock:
            if DEBUG:
                print "Writing block #%d to the disk" % blocknumber
            if blocknumber > self.getnumberofblocks():
                raise DiskException("Block Out Of Bound")
            if len(data) > BLOCKSIZE:
                raise DiskException("Data Exceeds Size Of Block")
            # we need to modify this item on disk
            self.disk.seek(blocknumber * BLOCKSIZE, 0)
            self.disk.write(data)
            self.disk.flush()
            return 0

    def blockread(self, blocknumber):
        with self.lock:
            if DEBUG:
                print "Reading block #%d from the disk" % int(blocknumber)
            if blocknumber > self.getnumberofblocks():
                raise DiskException("Block Out Of Bound")
            self.disk.seek(blocknumber * BLOCKSIZE, 0)
            return self.disk.read(BLOCKSIZE)

    def getblocksize(self):
        return BLOCKSIZE

    def getcapacity(self):
        return DISKSIZE

    def getnumberofblocks(self):
        # = 1024
        return DISKSIZE/BLOCKSIZE

    def closedisk(self):
        with self.lock:
            self.disk.close()

# with diskMutex:
disk = None
