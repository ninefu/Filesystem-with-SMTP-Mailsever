import sys, struct
import Segment

from threading import Thread, Lock, Condition, Semaphore
from Inode import Inode
import InodeMap
from FSE import FileSystemException

DEBUG = False


class FileDescriptor(object):
    def __init__(self, inodenumber):
        object.__init__(self)
        self.inodenumber = inodenumber
        self.position = 0
        self.isopen = True

    def close(self):
        if not self.isopen:
            raise FileSystemException("The File is Already Closed!")
        self.isopen = False

    def _getinode(self):
        # find the inode's position on disk
        inodeblocknumber = InodeMap.inodemap.lookup(self.inodenumber)
        # get the inode
        inodeobject = Inode(str=Segment.segmentmanager.blockread(inodeblocknumber))
        return inodeobject

    def getlength(self):
        inodeobject = self._getinode()
        return inodeobject.filesize

    def read(self, readlength):
        if not self.isopen:
            raise FileSystemException("The File is Already Closed!")

        inodeobject = self._getinode()
        data = inodeobject.read(self.position, readlength)
        self.position += len(data)
        return data

    # The write function in the file descriptor is supposed to handle 
    # the write to a file or directory. It just makes the necessary calls
    #  to the inode of the file or directory, and handles essential 
    #  changes to the file descriptor.
    def write(self, data, overwrite=False):
        # XXX - do this tomorrow! after the meteor shower!
        if not self.isopen:
            raise FileSystemException("The File is Already Closed!")

        inodeobject = self._getinode()
        if DEBUG:
            print "FileDescriptor.write inode {} writes data length {}".format(self.inodenumber, len(data))

        if overwrite:
            inodeobject.write(0, data)
        else:
            inodeobject.write(inodeobject.filesize, data)
        self.position += len(data)
