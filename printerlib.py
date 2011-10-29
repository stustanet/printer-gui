# -*- coding: UTF-8 -*-

import sys
import re
from datetime import datetime

class PrinterLib:
    #constructor
    def __init__(self, loghandle, logstring = ""):
        self.logstring = logstring
        self.out = loghandle

    #destructor
    def __del__(self):
        try:
            self.out.close()
        except:
            pass

    def setlogstring(self, logstring):
        self.logstring = logstring

    #central log function
    def logit(self, msg):
        self.out.write("%s %s: %s\n" % (datetime.now().strftime("%b %e %T"),
                                        self.logstring, msg))

