#!/usr/bin/env python
# -*- coding: utf-8 -*-

class LineParser(object):
    def parse(self, line):
        """Parse a line and returns result.

        Args:
          line: the message data.

        Returns:
          A tuple of (month, day, timestring, host, message).
          the message is also a tuple of words.
        """
        assert(False)
