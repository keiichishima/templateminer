#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""A very basic line spliter.

White space characters are defined as the trans_table variable and
configurable.
"""

import re

import line_parser

trans_table = str.maketrans("[]()='\"", '       ')
separator_regex = '\s+'

class BasicLineParser(line_parser.LineParser):
    def __init__(self,
                 trans_table=trans_table,
                 separator_regex=separator_regex):
        self.trans_table = trans_table
        self.separator_regex = separator_regex

    def parse(self, line):
        (month, day, timestr, host, message) = line.split(maxsplit=4)
        message = message.translate(self.trans_table).rstrip()
        return (month, day, timestr, host,
                re.split(self.separator_regex, message))

if __name__ == '__main__':
    import sys

    parser = BasicLineParser()
    line = sys.stdin.readline()
    while line:
        print(parser.parse(line))
        line = sys.stdin.readline()
