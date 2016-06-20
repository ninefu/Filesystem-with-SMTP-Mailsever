#!/usr/bin/python
import sys, struct
import Segment
import InodeMap

from threading import Thread, Lock, Condition, Semaphore
from Segment import SegmentManagerClass
from Disk import DiskClass
from Inode import Inode, getmaxinode, setmaxinode
from InodeMap import InodeMapClass
from FileDescriptor import FileDescriptor
from DirectoryDescriptor import DirectoryDescriptor
from Constants import FILENAMELEN
from FSE import FileSystemException
import Disk

DEBUG = False

# find the directory one level up
def find_parent_name(path):
    parent, sep, element = path.rpartition("/")
    if parent == '':
        parent = '/'
    return parent

def find_filename(path):
    parent, sep, element = path.rpartition("/")
    return element

#takes an absolute path, iterates through the components in the name
def get_path_components(path):
    for component in path[1:].strip().split("/"):
        yield component

class LFSClass:
    def __init__(self, initdisk=True):
        pass

    # open an existing file or directory
    def open(self, path, isdir=False):
        inodenumber = self.searchfiledir(path)
        if inodenumber is None:
            raise FileSystemException("Path Does Not Exist")
        # create and return a Descriptor of the right kind
        if isdir:
            if DEBUG:
                print "LFS.open opened a directory {}".format(path)
            return DirectoryDescriptor(inodenumber)
        else:
            if DEBUG:
                print "LFS.open opened a file {}".format(path)
            return FileDescriptor(inodenumber)

    def create(self, filename, isdir=False):
        fileinodenumber = self.searchfiledir(filename)
        if fileinodenumber is not None:
            raise FileSystemException("File/Directory Already Exists")

        # create an Inode for the file
        # Inode constructor writes the inode to disk and implicitly updates the inode map
        newinode = Inode(isdirectory=isdir)
        if DEBUG:
            print "LFS.create new inode {} isDir={} size={}".format(newinode.id, newinode.isDirectory, newinode.filesize)
        # now append the <filename, inode> entry to the parent directory
        parentdirname = find_parent_name(filename)
        parentdirinodenumber = self.searchfiledir(parentdirname)
        if parentdirinodenumber is None:
            raise FileSystemException("Parent Directory Does Not Exist")
        parentdirblockloc = InodeMap.inodemap.lookup(parentdirinodenumber)
        parentdirinode = Inode(str=Segment.segmentmanager.blockread(parentdirblockloc))
        self.append_directory_entry(parentdirinode, find_filename(filename), newinode)

        if isdir:
            return DirectoryDescriptor(newinode.id)
        else:
            return FileDescriptor(newinode.id)

    # return metadata about the given file
    def stat(self, pathname):
        if DEBUG:
            print "LFS.stat for path {}".format(pathname)
        inodenumber = self.searchfiledir(pathname)
        if inodenumber is None:
            raise FileSystemException("File or Directory Does Not Exist")

        inodeblocknumber = InodeMap.inodemap.lookup(inodenumber)
        if inodeblocknumber is None:
            return None, None
        inodeobject = Inode(str=Segment.segmentmanager.blockread(inodeblocknumber))
        return inodeobject.filesize, inodeobject.isDirectory

    # delete the given file
    def unlink(self, pathname, isDir=False):
        # XXX - do this tomorrow! after the meteor shower!
        # find the file inode and block location
        filename = find_filename(pathname)
        fileinodenumber = self.searchfiledir(pathname)
        if fileinodenumber is None:
            raise FileSystemException("File/Path {} Already Deleted".format(pathname))
        if DEBUG:
            print "LFS.unlink found the inode {} for {}".format(fileinodenumber, pathname)

        if isDir:
            dd = DirectoryDescriptor(fileinodenumber)
            for name, inode in dd.enumerate():
                if inode is not None:
                    dd.close()
                    raise FileSystemException("Directory Not Empty")
            dd.close()
            
        # find the file's parent
        parentdirname = find_parent_name(pathname)
        if DEBUG:
            print "LFS.unlink parentdirname {} for file {}".format(parentdirname, filename)
        parentdirinodenumber = self.searchfiledir(parentdirname)
        if parentdirinodenumber is None:
            raise FileSystemException("File/Path {} Parent Directory Does Not Exist".format(pathname))
        parentdirblockloc = InodeMap.inodemap.lookup(parentdirinodenumber)
        parentdirinode = Inode(str=Segment.segmentmanager.blockread(parentdirblockloc))
        if DEBUG:
            print "LFS.unlink found the parent inode {} for parent dir {}".format(parentdirinodenumber, parentdirname)

        dd = DirectoryDescriptor(parentdirinodenumber)
        # remove this file from parent inode
        # compact the directory and trim down size
        content = ""
        position = 0
        for name, inode in dd.enumerate():
            if name != filename:
                content += parentdirinode.read(position, FILENAMELEN + 4)
            position += (FILENAMELEN + 4)
        parentdirinode.filesize -= (FILENAMELEN + 4)
        try:
            parentdirinode.write(0, content, False)
            # remove this file's inode from the inodemap
            InodeMap.inodemap.remove_inode(fileinodenumber)
        except:
            dd.close()

    # write all in memory data structures to disk
    # It has to make sure that the inode map is updated properly 
    # and then flush the segment to the disk.
    def sync(self):
        # XXX - do this tomorrow! after the meteor shower!
        inode = Inode()
        maxinodenumber = getmaxinode()
        inodemapcontent, generationcount = InodeMap.inodemap.save_inode_map(maxinodenumber)
        inode.write(0, inodemapcontent, True)
        inodeloc = Segment.segmentmanager.write_to_newblock(inode.serialize())
        Segment.segmentmanager.update_inodemap_position(inodeloc, generationcount)
        Segment.segmentmanager.flush()

    # restore in memory data structures (e.g. inode map) from disk
    def restore(self):
        imlocation = Segment.segmentmanager.locate_latest_inodemap()
        if DEBUG:
            print "LFS.restore latest inodemap is at location {}".format(imlocation)
        iminode = Inode(str=Disk.disk.blockread(imlocation))
        if DEBUG:
            print "LFS.restore reconstruct the inodemap inode {}".format(iminode.serialize())
        imdata = iminode.read(0, 10000000)
        # restore the latest inodemap from wherever it may be on disk
        setmaxinode(InodeMap.inodemap.restore_inode_map(imdata))

    # for a given file or directory named by path,
    # return its inode number if the file or directory exists,
    # else return None
    def searchfiledir(self, path):
        # XXX - do this tomorrow! after the meteor shower!
        if DEBUG:
            print "LFS.searchfiledir for a whole path {}".format(path)
        
        pathComponents = get_path_components(path)
        inodeNumber = 1 # starting from the super node
        for component in pathComponents:
            if component == "":
                continue
            
            inodeblocknumber = InodeMap.inodemap.lookup(inodeNumber)
            inodeobject = Inode(str=Segment.segmentmanager.blockread(inodeblocknumber))
            # get the generator for the current directory
            if inodeobject.isDirectory:
                lookupDir = DirectoryDescriptor(inodeNumber)
                inodeNumber = -1
                # iterate through every file/dir in the current directory and try to find a match
                # if not, return None
                for name, inode in lookupDir.enumerate():
                    if DEBUG:
                            print "LFS.searchfiledir name in enumerate is {}".format(name)
                    if component == name:
                        inodeNumber = inode
                        break
                lookupDir.close()
                if inodeNumber == -1:
                    if DEBUG:
                        print "LFS.searchfiledir couldn't find a matching name for component {}".format(component)
                    return None
        if DEBUG:
            print "LFS.searchfiledir found the path for {}, returning inodenumber {}".format(path, inodeNumber)
        return inodeNumber

    # add the new directory entry to the data blocks,
    # write the modified inode to the disk,
    # and update the inode map
    def append_directory_entry(self, dirinode, filename, newinode):
        dirinode.write(dirinode.filesize, struct.pack("%dsI" % FILENAMELEN, filename, newinode.id))

filesystem = None
