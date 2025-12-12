#!/usr/bin/env python

# adding one dir up to path
import sys

import options
from Database import Database

# get command line arguments, log to screen
args = options.get_args()
print(args)


# build SConfiguration from Steering Card (SCard) text file
#database = Database(args.scardFile)
#submitConfiguration.show()
