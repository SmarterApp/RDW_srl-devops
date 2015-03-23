#!/usr/bin/python

import yaml
import sys

#import pdb; pdb.set_trace()

def main():
    yaml.load(open(sys.argv[1], 'r'))
    exit(0)

    
