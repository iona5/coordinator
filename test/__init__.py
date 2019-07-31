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


  def assertTextFieldCloseTo(self, expected, textField, tolerance = 1, msg = None):
      textFieldValue = float(textField.text())
      
      result = ( (expected - tolerance) <= textFieldValue <= (expected + tolerance) )
      
      if msg == None:
          msg = "value '%f' of QTextField is not close to %f±%f)" % (textFieldValue, expected, tolerance)
      
      self.assertTrue(result, msg)
      
      
  def assertTextFieldBetween(self, lower, upper, textField, msg = None):
      textFieldValue = float(textField.text())
      
      result = (lower < textFieldValue < upper)
      
      if msg == None:
          msg = "value '%f' of QTextField is not between %f and %f)" % (textFieldValue, lower, upper)
      
      self.assertTrue(result, msg)
