# import qgis libs so that ve set the correct sip api version
import os, sys, qgis   # pylint: disable=W0611  # NOQA
from qgis.testing import unittest

def run_all(): 
    loader = unittest.TestLoader()
    
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir)
      
    runner = unittest.TextTestRunner(verbosity = 3, stream=sys.stdout)
    runner.run(suite)
    
class CoordinatorTestCase(unittest.TestCase):
  def __init__(self):
    super(CoordinatorTestCase, self).__init__()

