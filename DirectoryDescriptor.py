import pickle
import sys, struct, os, random, math, pickle
from threading import Thread, Lock, Condition, Semaphore

from Disk import *
from Constants import FILENAMELEN
from FileDescriptor import FileDescriptor
from FSE import FileSystemException


class DirectoryDescriptor(FileDescriptor):
    def __init__(self, inodenumber):
        super(DirectoryDescriptor, self).__init__(inodenumber)
        inodeobject = self._getinode()
        if not inodeobject.isDirectory:
            raise FileSystemException("Not a directory - inode %d" % inodenumber)

    def enumerate(self):
        length = self.getlength()
        numentries = length / (FILENAMELEN + 4)  # a directory entry is a filename and an integer for the inode number
        for i in range(0, numentries):
            data = self.read(FILENAMELEN + 4)
            name, inode = struct.unpack("%dsI" % (FILENAMELEN,), data[0:(FILENAMELEN + 4)])
            name = name.strip('\x00')
            yield name, inode
