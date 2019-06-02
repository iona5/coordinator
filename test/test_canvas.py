import unittest
import qgis

from coordinator.coordinator import Coordinator
from coordinator.test.utilities import get_qgis_app, IFACE
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QDialog, QMainWindow, QDockWidget, QWidget
from PyQt5.Qt import Qt, QSize
import os
from qgis.core import QgsProject, QgsVectorLayer, QgsCoordinateReferenceSystem, QgsRectangle, QgsPointXY
from PyQt5 import QtCore


class CoordinatorCanvasTest(unittest.TestCase):
    def setUp(self):
        
        global CANVAS, IFACE
        QGIS_APP, IFACE, CANVAS = get_qgis_app()
        
        if isinstance(IFACE, QgisStubInterface):
            self.window = QMainWindow()
            self.window.resize(QSize(800,400))
            self.window.setCentralWidget(CANVAS)
        else:
            self.window = None
        
        
        self.coordinator = Coordinator(IFACE, self.window)
        self.coordinator.run()
        self.dw = self.coordinator.dockwidget
        
        if self.window:
            self.window.show()

    def tearDown(self):
        QTest.qWait(200)
        try:
            self.window.close()
        except:
            pass
        
    def testMarkerGeographicOnGeodesic(self):
        CANVAS.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:32632"))
        project = QgsProject.instance()
        project.addMapLayer(QgsVectorLayer(os.path.join(os.path.dirname(__file__), "data/europe.geojson" ), "europe", "ogr"), True)
        #
        CANVAS.zoomToFeatureExtent(QgsRectangle(150000, 4800000, 850000, 5500000 ))
        
        QTest.mouseClick(self.dw.inputAsDec, Qt.LeftButton)
        
        marker = self.coordinator.marker
        mapToPixel = CANVAS.getCoordinateTransform()
        
        # set point to 8°E but 0°N
        QTest.keyClicks(self.dw.inLeftDec, "8" )
        QTest.qWait(1000)
        # check non visible 
        self.assertFalse(CANVAS.sceneRect().contains(marker.scenePos()))
        self.assertTrue(self.dw.messageIcon.isVisible())
        
        # add 45°N
        QTest.keyClicks(self.dw.inRightDec, "45" )
        QTest.qWait(200)
        # now point should be visible
        self.assertTrue(CANVAS.sceneRect().contains(marker.scenePos()))
        self.assertFalse(self.dw.messageIcon.isVisible())
        
        # check the actual position on the map
        coords = mapToPixel.toMapCoordinates(marker.pos().x(), marker.pos().y())
        expectedPixelPos = mapToPixel.transform(QgsPointXY(421184, 4983436))
        self.assertAlmostEqual(expectedPixelPos.x(), marker.pos().x(), 0)
        self.assertAlmostEqual(expectedPixelPos.y(), marker.pos().y(), 0)
        
        # remove latitude coordinates
        QTest.mouseDClick(self.dw.inRightDec, Qt.LeftButton)
        QTest.keyClick(self.dw.inRightDec, Qt.Key_Delete)
        QTest.qWait(200)
        self.assertFalse(CANVAS.sceneRect().contains(marker.scenePos()))
        self.assertTrue(self.dw.messageIcon.isVisible())
        
        # set 80°N
        QTest.keyClicks(self.dw.inRightDec, "80" )
        QTest.qWait(200)
        # check non visible 
        self.assertFalse(CANVAS.sceneRect().contains(marker.scenePos()))
        self.assertTrue(self.dw.messageIcon.isVisible())
        
        # clear input and set coordinates on western hemisphere but with correct Latitude
        QTest.mouseClick(self.dw.clearInput, Qt.LeftButton)
        QTest.mouseClick(self.dw.leftDirButton, Qt.LeftButton)
        QTest.keyClicks(self.dw.inLeftDec, "8" )
        QTest.keyClicks(self.dw.inRightDec, "45" )
         # check non visible 
        self.assertFalse(CANVAS.sceneRect().contains(marker.scenePos()))
        self.assertTrue(self.dw.messageIcon.isVisible())
        

if __name__ == "__main__":
    suite = unittest.makeSuite(CoordinatorCanvasTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
