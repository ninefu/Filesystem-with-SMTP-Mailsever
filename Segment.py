#!/usr/bin/python
import sys, struct, os, random, time
import Disk
from FSE import FileSystemException

from Constants import BLOCKSIZE, DISKSIZE, SEGMENTSIZE, NUMSEGMENTS
from threading import Lock
from InodeMap import InodeMapClass
import InodeMap
from Inode import Inode, getmaxinode


NUMBLOCKS = SEGMENTSIZE - 1 # number of blocks in a segment (one less than SEGMENTSIZE because of the superblock)

DEBUG = False

# the segmentmanager manages the current segment, flushing it
# to disk as necessary and picking up another segment to work on
class SegmentManagerClass:
    def __init__(self):
        self.lock = Lock()
        self.segcounter = 0
        self.currentseg = SegmentClass(self.segcounter)
        self.blocks = [False] * (DISKSIZE / BLOCKSIZE)

    # write the given data to a free block in the current segment.
    # if no free block exists, find another segment with a free block in it
    # return the location of the block where the data is written
    def write_to_newblock(self, data):
        # XXX - do this tomorrow! after the meteor shower!
        with self.lock:
            startingCounter = self.segcounter
            blockLoc = self.currentseg.write_to_newblock(data)
            # couldn't find a free block in the current segment
            while blockLoc == -1:
                # flush the current segment to disk
                self.currentseg.flush()
                # get a new segment
                if DEBUG:
                    print "SegmentManager.write_to_newblock current segment {} is full, ready to read in next segment {}".format(self.segcounter, (self.segcounter + 1)%NUMSEGMENTS)
                self.segcounter = (self.segcounter + 1) % NUMSEGMENTS
                if self.segcounter == startingCounter:
                    raise FileSystemException("Disk is full, waiting for cleaner")
                self.currentseg = SegmentClass(self.segcounter)
                # try to find a free block again
                blockLoc = self.currentseg.write_to_newblock(data)

            return self.segcounter * SEGMENTSIZE + blockLoc

    # read the requested block if it is in memory, if not, read it from disk
    def blockread(self, blockno):
        with self.lock:
            if self.is_in_memory(blockno):
                return self.read_in_place(blockno)
            else:
                return Disk.disk.blockread(blockno)

    # write the requested block, to the disk, or else to memory if
    # this block is part of the current segment
    def blockwrite(self, blockno, data):
        with self.lock:
            if self.is_in_memory(blockno):
                self.update_in_place(blockno, data)
            else:
                Disk.disk.blockwrite(blockno, data)

    # returns true if the given block disk address is currently in memory
    def is_in_memory(self, blockno):
        return blockno >= self.currentseg.segmentbase and blockno < (self.currentseg.segmentbase + SEGMENTSIZE)

    def update_in_place(self, blockno, data):
        # if DEBUG:
        #     print "Writing block #%d to the segment" % blockno
        blockoffset = blockno - 1 - self.currentseg.segmentbase
        if len(data) != len(self.currentseg.blocks[blockoffset]):
            print "Assertion error 1: data being written to segment is not the right size (%d != %d)" % (len(data), len(self.currentseg.blocks[blockoffset]))
        else:
            self.currentseg.blocks[blockoffset] = data
    
    def read_in_place(self, blockno):
        # if DEBUG:
            # print "Reading block #%d from the segment" % blockno
        blockoffset = blockno - 1 - self.currentseg.segmentbase
        return self.currentseg.blocks[blockoffset]

    # update the current segment's superblock with the latest position & gen number of the inodemap
    def update_inodemap_position(self, imloc, imgen):
        with self.lock:
            self.currentseg.superblock.update_inodemap_position(imloc, imgen)

    # flush the current segment to the disk
    def flush(self):
        with self.lock:
            self.currentseg.flush()

    def locate_latest_inodemap(self):
        # go through all segments, read all superblocks,
        # find the inodemap with the highest generation count
        with self.lock:
            maxgen = -1
            imlocation = -1
            for segno in range(0, NUMSEGMENTS):
                superblock = SuperBlock(data=Disk.disk.blockread(segno * SEGMENTSIZE))
                if superblock.inodemapgeneration > 0 and superblock.inodemapgeneration > maxgen:
                    maxgen = superblock.inodemapgeneration
                    imlocation = superblock.inodemaplocation
            return imlocation

    def clean_segments(self):
        with self.lock:
            if DEBUG:
                print "Start cleaning"

            self.currentseg.flush()
            # reset the in-use bitmap
            self.blocks = [False] * (DISKSIZE / BLOCKSIZE)
            # for each inode in the inode map, iterate through and find the blocks that are in use
            self.iterateInodeMap()
            # add blocks for supernode
            for i in range(0, NUMSEGMENTS):
                self.blocks[i * SEGMENTSIZE] = True

            capacity = DISKSIZE / BLOCKSIZE
            if sum(self.blocks) == capacity:
                self.currentseg = SegmentClass(self.segcounter)
                raise FileSystemException("The disk is completely full. Cleaner cannot find any free blocks")
            else:
                # copy each segment's bitmap to a new superblock
                if DEBUG:
                    print "{} blocks are in use".format(sum(self.blocks))
                for i in range(0, NUMSEGMENTS):
                    count = 0
                    superblock = SuperBlock(data=Disk.disk.blockread(i * SEGMENTSIZE))
                    self.blocks[superblock.inodemaplocation] = True

                    for j in range(0, NUMBLOCKS):
                        if superblock.blockinuse[j] != self.blocks[i * SEGMENTSIZE + j + 1]:
                            count += 1
                        superblock.blockinuse[j] = self.blocks[i * SEGMENTSIZE + j + 1]

                    # flush the new superblock to disk
                    Disk.disk.blockwrite(i * SEGMENTSIZE, superblock.serialize())
                    if DEBUG:
                        print "Cleaned {} blocks in segment {}".format(count, i)
                self.currentseg = SegmentClass(self.segcounter)

    def iterateInodeMap(self):
        if DEBUG:
            print "Segment.iterateInodeMap"
        for inodeNumber, blockLoc in InodeMap.inodemap.mapping.items():
            # the block for this inode is in use
            # self.blocks[blockLoc] = True
            self.markBlockInUse(blockLoc)
            # get the inode object
            inode = Inode(str=Disk.disk.blockread(blockLoc))
            # mark the direct data blocks in use
            for loc in inode.fileblocks:
                # if loc != 0:
                    # self.blocks[loc] = True
                self.markBlockInUse(loc)
            # mark the indirect data blocks in use
            if inode.indirectblock != 0:
                # self.blocks[inode.indirectblock] = True
                self.markBlockInUse(inode.indirectblock)
                indirectBlock = Disk.disk.blockread(inode.indirectblock)

                for j in range(0, len(indirectBlock)/4):
                    blockLocation = struct.unpack("I", indirectBlock[(j * 4):(j * 4 + 4)])[0]
                    self.markBlockInUse(blockLocation)
                    # if blockLocation != 0:
                    #     self.blocks[blockLocation] = True

    def markBlockInUse(self, blockLoc):
        if blockLoc > 0 and blockLoc < len(self.blocks):
            self.blocks[blockLoc] = True
            return True
        else:
            return False

class SuperBlock:
    def __init__(self, data=None):
        if data is None:
            # the first block is the superblock and is handled specially
            self.blockinuse = [False] * NUMBLOCKS
            self.inodemapgeneration = -1
            self.inodemaplocation = -1
        else:
            # recover a superblock that was previously written to disk
            self.blockinuse = [False] * NUMBLOCKS
            for i in range(0, NUMBLOCKS):
                self.blockinuse[i] = struct.unpack('?', data[i])[0]
            self.inodemapgeneration = struct.unpack('I', data[NUMBLOCKS:NUMBLOCKS+4])[0]
            self.inodemaplocation = struct.unpack('I', data[NUMBLOCKS+4:NUMBLOCKS+8])[0]

    def serialize(self):
        str = ""
        for i in range(0, NUMBLOCKS):
            str += struct.pack('?', self.blockinuse[i])
        str += struct.pack('II', self.inodemapgeneration, self.inodemaplocation)
        return str

    # the inodemap is written to a specially created inode. the generation
    # count of that inode and its flushed location on disk is written to the
    # superblock
    def update_inodemap_position(self, imlocation, imgeneration):
        self.inodemapgeneration = imgeneration
        self.inodemaplocation = imlocation


class SegmentClass:
    def __init__(self, segmentnumber):
        self.segmentbase = segmentnumber * SEGMENTSIZE
        # read the superblock, it's the first block in the segment
        self.superblock = SuperBlock(data=Disk.disk.blockread(self.segmentbase))
        self.blocks= []
        # read the segment blocks from disk, they follow the superblock
        for i in range(self.segmentbase + 1, self.segmentbase + 1 + NUMBLOCKS):
            self.blocks.append(Disk.disk.blockread(i))

    # write data to a free block within the segment. Since the
    # segment is in memory, the write only updates the blocks in
    # memory and does not have to touch the disk
    def write_to_newblock(self, data):
        for i in range(0, NUMBLOCKS):
            if not self.superblock.blockinuse[i]:
                if len(data) > BLOCKSIZE:
                    print "Assertion error 2: data being written to segment is not the right size (%d != %d)" % (len(data), len(self.blocks[i]))
                    print data
                    os._exit(1)
                # update the block data
                self.blocks[i] = data + self.blocks[i][len(data):]
                self.superblock.blockinuse[i] = True
                # return the physical location of the block
                return i + 1
        return -1

    def flush(self):
        #write the superblock to disk
        Disk.disk.blockwrite(self.segmentbase, self.superblock.serialize())
        #write all blocks in the segment to disk
        for i in range(0, NUMBLOCKS):
            Disk.disk.blockwrite(self.segmentbase + 1 + i, self.blocks[i])

segmentmanager = None
