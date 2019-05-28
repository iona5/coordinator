import os, sys
# from . import Coordinator
#
from qgis.testing import unittest

def run_all(): 
    loader = unittest.TestLoader()
    
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir)
      
    runner = unittest.TextTestRunner(verbosity = 3, stream=sys.stdout)
    runner.run(suite)