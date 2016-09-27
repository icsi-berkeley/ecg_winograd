"""
Author: seantrott <seantrott@icsi.berkeley.edu>
Similar to a regular UserAgent, but it uses a WinogradSpecializer instead.
"""

from nluas.language.user_agent import *
from starcraft.winograd_specializer import *
import sys
import subprocess


class WinogradUserAgent(UserAgent):

    def __init__(self, args):
        UserAgent.__init__(self, args)

    def initialize_specializer(self):
        self.specializer = WinogradSpecializer(self.analyzer)

    def output_stream(self, tag, message):
        print("{}: {}".format(tag, message))
        # MAC only
        #subprocess.Popen(["say", message])


if __name__ == "__main__":
    ui = WinogradUserAgent(sys.argv[1:])
    ui.prompt()
