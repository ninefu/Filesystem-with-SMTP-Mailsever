import Shell
from Shell import Shell
from FSE import FileSystemException
import string, math
import time

shell = Shell()


def runCommand(inputCommand):
    inputCommands = inputCommand.strip().split(" ")
    func = getattr(shell, inputCommands[0])
    res = func(inputCommands)
    return res


def test():
    # /
    runCommand("mkfs")  # test mkfs brandnew
    # /a
    runCommand("mkdir /a")  # test mkdir absolute path
    try:
        runCommand("mkdir a")  # test mkdir relative path, should raise a FSE exception
    except FileSystemException, fse:
        assert fse.parameter == 'File/Directory Already Exists'
    # /
    runCommand("rmdir /a")  # test rmdir absolute path
    try:
        runCommand("rmdir a")  # test rmdir relative path, should raise a FSE exception
    except FileSystemException, fse:
        assert fse.parameter == 'File or Directory Does Not Exist'
    # /a
    runCommand("mkdir /a")  # test mkdir absolute path
    runCommand("cd /a")  # test cd dir absolute path
    # /a >
    try:
        runCommand("cd a")  # test cd dir relative path
    except FileSystemException, fse:
        assert fse.parameter == 'File or Directory Does Not Exist'
    # runCommand("ls") # test ls, expect nothing
    # /a/b.txt 10
    runCommand("create b.txt 10")  # test create with relative path
    try:
        runCommand("create /a/b.txt 10")  # test create with absolute path
    except FileSystemException, fse:
        assert fse.parameter == 'File/Directory Already Exists'
    content = runCommand("cat b.txt")  # test cat with relative path
    assert content == "abcdefghij"
    content = runCommand("cat /a/b.txt")  # test cat with absolut path
    assert content == "abcdefghij"

    runCommand("write b.txt HelloWorld")  # test write with relative path
    content = runCommand("cat b.txt")
    assert content == 'HelloWorld'
    runCommand("write /a/b.txt WorldHello")  # test write with absolute path
    assert runCommand("cat b.txt") == 'WorldHello'

    # /a >
    runCommand("rm b.txt")  # test remove with aboslute path
    try:
        runCommand("rm b.txt")
    except FileSystemException, fse:
        assert fse.parameter == 'File or Directory Does Not Exist'

    # /a/c
    runCommand("mkdir /a/c")
    # /a/c
    # /a/b.txt
    runCommand("create /a/b.txt 10")
    runCommand("write /a/b.txt WorldHello")  # test write with absolute path
    runCommand("mkdir /a/c/d")
    runCommand("mkdir /a/c/d/e")
    runCommand("mkdir /a/c/d/e/f")
    runCommand("mkdir /a/c/d/e/f/g")
    runCommand("mkdir /a/c/d/e/f/g/h")
    # /a/c
    # /a/b.txt
    # /a/c/d/e/f/g/h
    runCommand("cd /a")
    runCommand("cd c")
    runCommand("cd d")
    runCommand("cd e")
    runCommand("create test1.txt 5")
    assert runCommand("cat /a/c/d/e/test1.txt") == 'abcde'
    runCommand("create test2.txt 6")
    assert runCommand("cat /a/c/d/e/test2.txt") == 'abcdef'
    runCommand("cd f")
    runCommand("cd g")
    runCommand("cd h")
    runCommand("create test3.txt 7")
    assert runCommand("cat test3.txt") == 'abcdefg'
    runCommand("mkdir /a/i")
    runCommand("cd /a/i")
    runCommand("create test4.txt 8")
    assert runCommand("cat /a/i/test4.txt") == 'abcdefgh'
    # /a/c
    # /a/b.txt
    # /a/c/d/e/f/g/h
    # /a/c/d/e/test1.txt 5
    # /a/c/d/e/test2.txt 6
    # /a/c/d/e/f/g/h/test3.txt 7
    # /a/i/test4.txt 8
    try:
        runCommand("rmdir /a/c/d")  # test removing a intermediate directory
    except FileSystemException, fse:
        assert fse.parameter == 'Directory Not Empty'
    print "waiting for the first cleaner"
    time.sleep(15)
    # make sure the files are still there after cleaning
    assert runCommand("cat /a/c/d/e/test1.txt") == 'abcde'
    assert runCommand("cat /a/b.txt") == 'WorldHello'

    runCommand("sync")  # test sync
    runCommand("mkfs -reuse")
    runCommand("cd /")
    content = runCommand("cat /a/b.txt")
    assert content == 'WorldHello'

    runCommand("mkfs")
    runCommand("create large.txt 114000")  # a file larger than 100 data blocks, with indirect blocks
    stringPool = string.ascii_letters + string.digits
    toWriteContent = stringPool * int(math.ceil(114000.0 / len(stringPool)))
    newWriteContent = toWriteContent[0:114000]
    runCommand("write large.txt {}".format(newWriteContent))
    assert runCommand("cat large.txt") == newWriteContent
    runCommand("ls")
    runCommand("mkfs")
    try:
        runCommand(("create supersuperlarge.txt 1048576"))
    except FileSystemException, fse:
        assert fse.parameter == 'Exceeded single file limit'

    runCommand("mkfs")
    try:
        runCommand(("create supersuperlarge.txt 364550")) # maximum file size 364544 bytes
    except FileSystemException, fse:
        assert fse.parameter == 'Exceeded single file limit'
    
    runCommand("mkfs")
    runCommand("create superlarge1.txt 256000")
    runCommand("create superlarge2.txt 256000")
    runCommand("create superlarge3.txt 256000")
    try:
        runCommand("create superlarge4.txt 256000")
    except FileSystemException, fse:
        print fse
    print "waiting for the second and third cleaner"
    time.sleep(15)
    runCommand("create superlarge5.txt 256000")
    runCommand("create extra.txt 10")

    # runCommand("sync")

    runCommand("exit")


if __name__ == "__main__":
    test()
