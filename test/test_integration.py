import unittest
import qgis

from coordinator.test.utilities import get_qgis_app, helperFormatCoordinates
from coordinator.coordinator import Coordinator
from qgis._core import QgsCoordinateReferenceSystem
from PyQt5.QtTest import QTest
from PyQt5 import QtCore
from PyQt5.Qt import QLocale

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()

class CoordinatorIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.coordinator = Coordinator(IFACE)
        self.coordinator.run()
        self.dw = self.coordinator.dockwidget

        self.initialCanvasCrsAuthid = CANVAS.mapSettings().destinationCrs().authid()

    def tearDown(self):
        self.dw.close()
            
        self.coordinator = None
        self.dw = None

    def test_openPlugin(self):
        self.assertTrue(self.coordinator.dockwidget.isVisible())
        
    def testInitialValues(self):
        
        expectedOutputCrsAuthid = "" if self.initialCanvasCrsAuthid == None else self.initialCanvasCrsAuthid
        
        self.assertEqual("EPSG:4326", self.coordinator._inputCrs.authid())
        self.assertEqual(expectedOutputCrsAuthid, self.coordinator._outputCrs.authid() )
        self.assertEqual("EPSG:4326", self.coordinator._transform.sourceCrs().authid())
        self.assertEqual(expectedOutputCrsAuthid, self.coordinator._transform.destinationCrs().authid())
        self.assertEqual(self.initialCanvasCrsAuthid, self.coordinator._canvasTransform.destinationCrs().authid())
        self.assertEqual("EPSG:4326", self.coordinator._canvasTransform.sourceCrs().authid())
        
        self.assertEqual("EPSG:4326", self.coordinator.dockwidget.selectCrsButton.text())
    
    def testCanvasTransformation(self):
        
        currentCanvasCrs = CANVAS.mapSettings().destinationCrs()
        self.assertEqual(currentCanvasCrs, self.coordinator._canvasTransform.destinationCrs())
        
        CANVAS.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:32615"))
        self.assertEqual("EPSG:32615", self.coordinator._canvasTransform.destinationCrs().authid())
        
        CANVAS.setDestinationCrs(QgsCoordinateReferenceSystem(currentCanvasCrs))
        self.assertEqual(currentCanvasCrs, self.coordinator._canvasTransform.destinationCrs())
        
    
    def testLayerLock(self):
        outputCrs = self.coordinator._outputCrs
        
        newCrs = QgsCoordinateReferenceSystem("EPSG:32615")
        CANVAS.setDestinationCrs(newCrs)
        
        self.dw.outputCrsConn.setEnabled(True)
        QTest.mouseClick(self.dw.outputCrsConn, QtCore.Qt.LeftButton)
        QTest.qWait(100)
        QTest.mouseClick(self.dw.outputCrsConn, QtCore.Qt.LeftButton)
        
        self.assertEqual(self.coordinator._outputCrs, newCrs)
        
        QTest.qWait(100)
        # Simulate a click, but nothing should happen
        QTest.mouseClick(self.dw.outputCrs, QtCore.Qt.LeftButton)
         
        
    def testTransformIdentity(self):
        
        crsIn = QgsCoordinateReferenceSystem("EPSG:4326")
        crsOut = QgsCoordinateReferenceSystem("EPSG:4326")
        
        self.coordinator.setInputCrs(crsIn)
        self.dw.outputCrsConn.setEnabled(False)
        self.coordinator.setOutputCrs(crsOut)
        
        QTest.keyPress(self.dw.inLeft, "2")
        self.assertEqual(helperFormatCoordinates("2°0′0.000″E"), self.dw.resultLeft.text())
        self.assertEqual(helperFormatCoordinates("0°0′0.000″"), self.dw.resultRight.text())

        QTest.keyPress(self.dw.inLeft, "3")
        self.assertEqual(helperFormatCoordinates("23°0′0.000″E"), self.dw.resultLeft.text())
        self.assertEqual(helperFormatCoordinates("0°0′0.000″"), self.dw.resultRight.text())

        
        QTest.keyPress(self.dw.inRightMin, "2")
        self.assertEqual(helperFormatCoordinates("23°0′0.000″E"), self.dw.resultLeft.text())
        self.assertEqual(helperFormatCoordinates("0°2′0.000″N"), self.dw.resultRight.text())
        
        
        

    def testSwitchHemispheres(self):
        crsIn = QgsCoordinateReferenceSystem("EPSG:4326")
        crsOut = QgsCoordinateReferenceSystem("EPSG:4326")
        
        self.coordinator.setInputCrs(crsIn)
        self.dw.outputCrsConn.setEnabled(False)
        self.coordinator.setOutputCrs(crsOut)
        
        self.assertEqual("E", self.dw.leftDirButton.text())
        self.assertEqual("N", self.dw.rightDirButton.text())
        
        self.dw.inLeft.insert("10")
        self.dw.inLeftMin.insert("5")
        self.dw.inLeftSec.insert("1")
        
        self.dw.inRight.insert("5")
        self.dw.inRightMin.insert("10")
        self.dw.inRightSec.insert("45")
        
        self.assertEqual(helperFormatCoordinates("10°5′1.000″E"), self.dw.resultLeft.text())
        self.assertEqual(helperFormatCoordinates("5°10′45.000″N"), self.dw.resultRight.text())
        
        QTest.mouseClick(self.dw.leftDirButton, QtCore.Qt.LeftButton)
        self.assertEqual("W", self.dw.leftDirButton.text())
        self.assertEqual("N", self.dw.rightDirButton.text())
        self.assertEqual(helperFormatCoordinates("10°5′1.000″W"), self.dw.resultLeft.text())
        self.assertEqual(helperFormatCoordinates("5°10′45.000″N"), self.dw.resultRight.text())
        
        QTest.mouseClick(self.dw.rightDirButton, QtCore.Qt.LeftButton)
        self.assertEqual("W", self.dw.leftDirButton.text())
        self.assertEqual("S", self.dw.rightDirButton.text())
        self.assertEqual(helperFormatCoordinates("10°5′1.000″W"), self.dw.resultLeft.text())
        self.assertEqual(helperFormatCoordinates("5°10′45.000″S"), self.dw.resultRight.text())

        QTest.mouseClick(self.dw.rightDirButton, QtCore.Qt.LeftButton)
        self.assertEqual("W", self.dw.leftDirButton.text())
        self.assertEqual("N", self.dw.rightDirButton.text())
        self.assertEqual(helperFormatCoordinates("10°5′1.000″W"), self.dw.resultLeft.text())
        self.assertEqual(helperFormatCoordinates("5°10′45.000″N"), self.dw.resultRight.text())
        
    
    def testGeographicInputDisplay(self):
        crsIn = QgsCoordinateReferenceSystem("EPSG:4326")
        
        QTest.mouseClick(self.dw.inputAsDec, QtCore.Qt.LeftButton)
        self.assertFalse(self.dw.inputAsDMS.isChecked())
        self.assertTrue(self.dw.inputAsDec.isChecked())
        
        QTest.qSleep(3000)
        
        self.assertFalse(self.dw.inLeft.isVisible())
        self.assertFalse(self.dw.inLeftMin.isVisible())
        self.assertFalse(self.dw.inLeftSec.isVisible())
        
        self.assertFalse(self.dw.inRight.isVisible())
        self.assertFalse(self.dw.inRightMin.isVisible())
        self.assertFalse(self.dw.inRightSec.isVisible())
        
        self.assertTrue(self.dw.inLeftDec.isVisible())
        self.assertTrue(self.dw.inRightDec.isVisible())
        
        QTest.mouseClick(self.dw.inputAsDMS, QtCore.Qt.LeftButton)
        self.assertTrue(self.dw.inputAsDMS.isChecked())
        self.assertFalse(self.dw.inputAsDec.isChecked())
        
        self.dw.inLeft.insert("10")
        self.dw.inLeftMin.insert("5")
        self.dw.inLeftSec.insert("1")
        
        self.dw.inRight.insert("5")
        self.dw.inRightMin.insert("10")
        self.dw.inRightSec.insert("45")
        
        QTest.mouseClick(self.dw.inputAsDec, QtCore.Qt.LeftButton)
        self.assertEqual(helperFormatCoordinates("10.083611111"),self.dw.inLeftDec.text())
        self.assertEqual(helperFormatCoordinates("5.179166667"),self.dw.inRightDec.text())
        
if __name__ == "__main__":
    suite = unittest.makeSuite(CoordinatorIntegrationTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
        
        
    