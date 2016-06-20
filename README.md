# Log Structured File System with SMTP Mail Server
This is a course project from CS 4410 Operation Systems. It includes a log structured filesystem (LFS) and an mail server that supports mail delivery under SMTP protocol and using socket-oriented network programming.

* Implementation for the LFS:
	- Sync inode map to the segment
	- Add file descriptor Write
	- Add file search
	- Write block to segment
	- Delete a file or remove a directory
	- Indirect Blocks in inode
	- Background segment cleaner
	- Multithread support
	- Mailserver Integration

* Implementation for the SMTP mail server:
	- SMTP to handle incoming delivery requests
	- Multi-threading to support paralell processing
	- A multiclient to test the mail server and the total counts of operations perform within a minute

## Detailed Implementation for LFS

### Change to the code base:

- In Shell.mkfs(), reset the max inode number to 1 when making a brand new file system
- Modified the argument passed in fd.write() in Shell.write() so that it now supports writing content with spaces.
- Inode.write() will check the data size first to ensure that it does not exceed the maximum single file size which is (NUMDIRECTBLOCKS * BLOCKSIZE + BLOCKSIZE / 4 * BLOCKSIZE)

### Implementation Details

- Fix Sync
	An inode is created as to hold the content of the latest generation of inode map. When writing the content to the inode data blocks, skip_inodemap_update is set to true so that the inode map will not be updated again. This inode is written as an invisible file to the current segment by calling update_inodemap_position then flush. To execute syn(), there should be at least one free block in the disk.

	To make sure the data on the disk is consistent, the user must call sync() to save any in-memory data to disk.

- Fix File Descriptor Write
	The file descriptor will first get its inode, then call inode's write() to write the file content. I added a parameter so that it allows overwriting content in a file, which is useful since some random content will be written in shell's create(). 

	If the user tries to write a file that exceeds the single file limit or disk's free space, a FileSystemException will be thrown and the size of the file will be zero. The user should manually delete the file from the file system.

- Fix file search
	It iteratively search each level of the directory, and return the inode number when it finds a matching subdirectory/file with the same name, or return None. Here, a file and a directory with the same name cannot coexist in the same level in the same directory, which is consistent with the current implmentation as Linux.

- Write block to segment
	Since the segment cleaner is implemented as threaded-log, the write_to_newblock() will walk through all the segments in a circle to find a free block. If not found, it will raise a FileSystemException.

- Deletion
	Upon deleting a file or removing a directory, it will find the file inode and the parent directory, then compact the parent directory without the deleted file. My implementation will raise a FileSystemException if we are deleting a non-empty directory.

- Indirect Blocks
	Implemented in Inode _adddatatoblock(), _datablockexists(), and _getdatablockcontents(). Particularly, every time the content of the indirect block is modified, the updated indirect block will be written back to the original place. Otherwise, whenever we add a datablock as an indirect block, we will need a new block which will be too space consuming.

- Segment Cleaner
	The segmentManagerClass now includes a clean_segments function, which upon called, will block the whole segment manager, iterate through the inode map to find the blocks actually are in use, mark them accordingly, then update the supernode for each block. There is a seperate Cleaner class in Cleaner.py. A cleaner thread is initialized only when Shell.mkfs() is called and currently there is no cleaner instance in Shell yet. Two locks are included in InodeMap and SegmentManager to ensure synchronization.

	The cleaner will run every 10 seconds. To change the waiting time, change the parameter of time.sleep() in the 16th line in Cleaner.py.

- Multithread support
	Apart from the two locks used to implement cleaner, I added a lock in Shell to ensure that only one thread can enter the critical section for mkfs(). Another lock is added to DiskClass since it involves reading and writing content from a block.

	I intended to implement monitor and condition variable for cleaner and mutithread supporting, but was running out of time.

- Mailserver Integration
	In the previous implementation of MP3, I have a write monitor which controls the behaviors of writing an email to the mail box and backing up the mailbox. This time, the write monitor is connected to a file system, and every time an email is written to a seperate file (and sync) to save the overhead for stale blocks when overwriting an existing mailbox file. The write monitor will try to call "mkfs -reuse" first, trying to reusing the existing file system. If not found, it will format a new file system.
	
## Detailed Implementation for SMTP Mail Server

### Server Implementation
There is a thread pool assigning tasks to consumers to handle sockets. Incoming sockets are backlogged in the OS as instructed. There is also a write monitor which controls writing and backing up the mailbox. A back up thread starts before handling the socket connections and works as described in the instruction. When 32 messages have been written into mailbox, a flag for isBackup will be set true to block future message delivery and wake up the waiting backup thread. When finished backing up, the isBackup flag is set false and one waiting thread will be waken up to deliver message.

ConnectionHandler handles the socket. A getSocketMessage() method helps collect input from the client until '\r\n'  or '\r\n.\r\n' is received within 10 seconds, otherwise, it will raise a socket timeout exception. The ConnectionHandler has HELO(), MAIL(), RCPT(), and DATA() methods which handle "HELO", "MAIL FROM", "RCPT TO","DATA" commands respectively. Receiving a valid command and sending back 250/354 status codes will reset the timeout to 10 seconds.

The priority of generating error codes is the same as the MP3 FAQ post suggested: "Your server should read the command incrementally: first it should parse the command instruction, then the data that follows it.  Thus, any error related to the command instruction has precedence over syntax errors or errors with the command body.  For example, if the first command that a user sends is "MAIL FROM ~~~~~" then the error should be "needs HELO", not "syntax error". " Whitespace is not allowed in client host name or email address. Additionally, the email address must include '@' and have at least one character before and after '@'.

### Multi-client Implementation
In the multiclient file, a Counter monitor serves the purpose to count the total number of operations for all 32 threads. It will be updated when a thread has been run for 60 seconds. 32 RandomizedClient will be created and run for 60 seconds each. It has a global variable threshold which is used to compare with a randomly generated integer from random.randint(a,b) and determine whether or not the thread should generate invalid host names, emails, or commands. It will also detect the responses from the server to see if it's appropriate.

As for the stress test, in the last experiment, the server was able to deliver 35 messages (with 1-32 backed up) and the multiclient performed 4038 send operations in one minute (tested on Vagrant). In previous experiments, the number of total operations was usually about 3300 ops/minute, but the number of delivered messages sometimes were below 32.

## Test and play

### Basic Funtionalities for LFS
The test cases are included in test.py. It tests the following shell scenarios:
- mkfs
- mkfs -resue
- mkdir
- rmdir
- cd
- create
- write 
- cat
- rm
- ls
- sync
- cleaner

In test.py, there are two places where the main thread will wait for 15 seconds so that the cleaner is able to clean stale blocks and a following large file can be created in a disk which was full before cleaning. 

To run, type "python test.py" and it will take 30 seconds to finish. You should be able to see to the program exit with "So long and thank you for all the fish on the terminal".
	
### Multithread Support for LFS
To test multithread support, first run "python testMultithread.py" included in the submission. It includes two assertions that checks if a file is actually created and written with intended content. You may also run "python Shell.py" after this, then type "mkfs -reuse" followed by "ls" to see the files and directories created in the testing script, with the intended hierarchy:

	/a1/b1
    /a1/c1.txt
    /a1/d1
	/a2/b2
    /a2/c2.txt
    /a2/d2
    /test.txt


### Integration with Mail Server
To test this, run "python server.py" first then run "python client.py". The latter is the simple client given for demo, but it is able to show that the integration is successful. Multiclient is included as well.
