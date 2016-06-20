from threading import Thread
import time


"""
A segment cleaner run every 10 seconds to clean stale blocks in LFS
as new free blocks
"""
class SegmentCleaner(Thread):
    def __init__(self, monitor):
        Thread.__init__(self)
        self.cleanOp = monitor

    def run(self):
        while True:
            time.sleep(10)
            self.cleanOp.clean_segments()
