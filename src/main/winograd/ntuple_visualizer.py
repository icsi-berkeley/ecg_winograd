"""
@author: <seantrott@icsi.berkeley.edu>
A simple program to output n-tuples using Analyzer+Specializer. Not reliant on any packages other than Jython.
"""

from winograd_specializer import *
from nluas.ntuple_decoder import *
import traceback

decoder = NtupleDecoder()

analyzer = Analyzer("http://localhost:8090")
rs = WinogradSpecializer(analyzer)

while True:
    text = input("> ")
    if text == "q":
        quit()
    elif text == "d":
        rs.debug_mode = True
    else:
        try:
            semspecs = analyzer.parse(text)
            for fs in semspecs:
                try:
                    ntuple = rs.specialize(fs)
                    pprint(ntuple)
                    decoder.pprint_ntuple(ntuple)
                    break
                except Exception as e:
                    traceback.print_exc()
                    print(e)
        except Exception as e:
            traceback.print_exc()
            print(e)
