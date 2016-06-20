from threading import Thread
from Shell import Shell
import time


class MultiThreadTester(Thread):
    def __init__(self, id):
        Thread.__init__(self)
        self.id = id
        self.shell = Shell()
        runCommand("mkfs -reuse",self.shell)
        print "Thread {} initialized".format(self.id)

    def run(self):
        print "running thread {}".format(self.id)
        runCommand("mkdir a{}".format(self.id), self.shell)
        runCommand("cd a{}".format(self.id), self.shell)
        runCommand("mkdir b{}".format(self.id), self.shell)
        runCommand("create c{}.txt 11".format(self.id), self.shell)
        runCommand("write c{}.txt HelloWorld{}".format(self.id, self.id), self.shell)
        runCommand("cat c{}.txt".format(self.id), self.shell)
        runCommand("mkdir /a{}/d{}".format(self.id, self.id), self.shell)
        runCommand("cd /a{}/d{}".format(self.id, self.id), self.shell)
        # /a1/b1
        # /a1/c1.txt
        # /a1/d1
        runCommand("sync", self.shell)
        print "Thread {} finishes".format(self.id)


def runCommand(inputCommand, shell):
    inputCommands = inputCommand.strip().split(" ")
    func = getattr(shell, inputCommands[0])
    res = func(inputCommands)
    return res


def setUp():
    testShellSetUp = Shell()
    runCommand("mkfs", testShellSetUp)
    runCommand("create test.txt 10", testShellSetUp)
    runCommand("sync", testShellSetUp)


def assertTest():
    testShellTest = Shell()
    runCommand("mkfs -reuse", testShellTest)
    assert runCommand("cat /a1/c1.txt", testShellTest) == "HelloWorld1"
    assert runCommand("cat /a2/c2.txt", testShellTest) == "HelloWorld2"
    runCommand("exit", testShellTest)

def test():
    setUp()
    print "finished setting up"

    test1 = MultiThreadTester(1)
    test2 = MultiThreadTester(2)

    test1.start()
    test2.start()

    time.sleep(3)

    print "starting testing"
    assertTest()

if __name__ == "__main__":
    test()
