# import qgis libs so that ve set the correct sip api version
import os, sys, qgis   # pylint: disable=W0611  # NOQA
from qgis.testing import unittest
from qgis.core import QgsProject, QgsVectorLayer

def run_all(): 
    loader = unittest.TestLoader()
    
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir)
      
    runner = unittest.TextTestRunner(verbosity = 3, stream=sys.stdout)
    runner.run(suite)
    
class CoordinatorTestCase(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    super(CoordinatorTestCase, cls).setUpClass()
    cls.project = QgsProject.instance()

  def addMapLayer(self, mapLayer):
    self.project.addMapLayer(mapLayer, True)
    
  def addVectorLayerFile(self, vectorLayerFile, vectorLayerName):
    vectorLayer = QgsVectorLayer(vectorLayerFile, vectorLayerName, "ogr")
    self.addMapLayer(vectorLayer)
    return vectorLayer

  def addEuropeLayer(self):
    return self.addVectorLayerFile(os.path.join(os.path.dirname(__file__), "data/europe.geojson" ), "europe")
