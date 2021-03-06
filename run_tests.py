#!/usr/bin/env python

import unittest
import sys

if sys.version_info[0] < 3:
    try:
        from lib3to2 import main as three2two
    except ImportError:
        print('If this keeps happening please install'
              '3to2 yourself with `pip install 3to2 --user`.')
        from pip import main as mainpip
        mainpip(['install', '3to2', 'mock', '--user'])
        from lib3to2 import main as three2two
    three2two.main('lib3to2.fixes', '-n --no-diffs -w paperworks'.split(' '))
    three2two.main('lib3to2.fixes', '-n --no-diffs -w test'.split(' '))

if __name__ == '__main__':
    testsuite = unittest.TestLoader().discover('./test/')
    unittest.TextTestRunner(verbosity=1).run(testsuite)
