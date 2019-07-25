# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Yacub
                                 A QGIS plugin
 makes coordinate discovery and editing easier
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-05-04
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Jonas Küpper
        email                : qgis@ag99.de
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from functools import partial
import os.path

from PyQt5.Qt import Qt, QSettings, QTranslator, qVersion, QApplication, QCoreApplication, QIcon, QColor,\
    QMouseEvent, QEvent, QLocale
from PyQt5.QtWidgets import QAction, QMainWindow
from PyQt5 import QtCore

from qgis.gui import QgsProjectionSelectionDialog, QgsVertexMarker, QgsMapToolEmitPoint, QgsMapTool, \
    QgsMapToolCapture, QgsMapMouseEvent, QgsMapToolCapture
from qgis.core import QgsProject, QgsMessageLog, QgsCoordinateReferenceSystem, QgsCoordinateTransform, \
    QgsPointXY, QgsGeometry, QgsFeature, QgsVectorLayer, QgsRasterLayer
from qgis.PyQt import sip

from .coordinator_dockwidget import CoordinatorDockWidget
from .resources import *
from .funcs import coordinatorLog, CoordinatorTranslator as CT

class Coordinator():
    """YACUP plugin"""

    def __init__(self, iface, mainWindow = None):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # store references to important stuff from QGIS
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self._project = QgsProject.instance()
        
        self._observingLayer = None
            
        self._uiHook = mainWindow if isinstance(mainWindow, QMainWindow) else iface
        
        # region: LOCALE - UNUSED
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        #
        #initialize locale
        localeString = QSettings().value('locale/userLocale')
        if(localeString):
            locale = localeString[0:2]
        else:
            locale = QLocale().language()
        
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Coordinator_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)
        # endregion

        # plugin housekeeping:
        self.openPanelAction = None
        self.pluginIsActive = False
        self.dockwidget = None


        # Init CRS Transformation:
        self._inputCrs = None
        self._outputCrs = None

        # self._transform : input -> output transformation
        # self._canvasTransform: input -> canvas transformation
        self.__initTransformers()

        # initialize canvas marker icon:
        self.marker = QgsVertexMarker(self.canvas)
        self.marker.hide()
        self.marker.setColor(QColor(255, 0, 0))
        self.marker.setIconSize(14)
        self.marker.setIconType(QgsVertexMarker.ICON_CIRCLE)  # See the enum IconType from http://www.qgis.org/api/classQgsVertexMarker.html
        self.marker.setPenWidth(3)

        # init point picker:
        self.mapTool = QgsMapToolEmitPoint(self.canvas)

    # LIFECYCLE :
    def initGui(self):
        """Create the menu entry inside the QGIS GUI."""
        icon = QIcon(':/plugins/coordinator/icons/marker.svg')
        menuTitle = CT.tr("Open Coordinator")
        self.openPanelAction =  QAction(icon, menuTitle)
        self.openPanelAction.triggered.connect(self.run)
        self.iface.pluginMenu().addAction( self.openPanelAction )

    #--------------------------------------------------------------------------

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        # remove the marker from the canvas:
        self.marker.hide()

        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
        # disconnect from the GUI-signals
        self._disconnectExternalSignals()

        self.pluginIsActive = False

    def unload(self):
        """Removes the plugin menu item from QGIS GUI."""
        self.iface.pluginMenu().removeAction( self.openPanelAction )
        self.marker.hide()

        self._disconnectExternalSignals()
    #--------------------------------------------------------------------------


    # PRIVATE HELPERS:
    def __initTransformers(self):
        """Initializes both coordinate transform object needed: the transformation from the
        input CRS to the output CRS (self._transform) and a tranformer from the input CRS to
        the current canvas CRS."""
        inputCrs = self._inputCrs if self._inputCrs != None else QgsCoordinateReferenceSystem("EPSG:4326")
        outputCrs = self._outputCrs if self._outputCrs != None else QgsCoordinateReferenceSystem("EPSG:4326")

        self._transform = QgsCoordinateTransform(
            inputCrs,
            outputCrs,
            self._project)


        canvasCrs = self.canvas.mapSettings().destinationCrs()
#         coordinatorLog("init canvas transform with %s -> %s"
#                        % (inputCrs.authid(), canvasCrs.authid() if canvasCrs else "NONE!!")
#                        )

        self._canvasTransform = QgsCoordinateTransform(
            inputCrs,
            canvasCrs,
            self._project)


    def __checkEnableAddFeatureButton(self):
        shouldEnable = bool(self.dockwidget.hasInput() and self.__compatibleMapTool())
        return shouldEnable

    def __compatibleMapTool(self):
        newTool = self.canvas.mapTool()
        if( newTool != None and (newTool.flags() & QgsMapTool.EditTool) ) :

            newTool = sip.cast(newTool, QgsMapToolCapture)

            if(newTool.mode() == QgsMapToolCapture.CaptureMode.CapturePoint
                or newTool.mode() == QgsMapToolCapture.CaptureMode.CapturePolygon
                or newTool.mode() == QgsMapToolCapture.CaptureMode.CaptureLine
                ):
               return newTool

        return False

    def _disconnectExternalSignals(self):
        try: self.iface.mapCanvas().destinationCrsChanged.disconnect(self.mapCanvasCrsChanged)
        except TypeError: pass
        try: self.canvas.mapToolSet.disconnect(self.mapToolChanged)
        except TypeError: pass
        try: self.iface.currentLayerChanged.disconnect(self.currentLayerChanged)
        except TypeError: pass
        try: self.iface.projectRead.disconnect(self.projectRead)
        except TypeError: pass
        
        if (self._observingLayer != None) and sip.isdeleted(self._observingLayer):
            self._observingLayer = None
            
        if self._observingLayer:
            self._observingLayer.crsChanged.disconnect(self.layerChangedCrs)

    def _currentEffectiveCrsInMap(self):
        activeLayer = self.iface.activeLayer()

        if(activeLayer):
            if type(activeLayer) == QgsVectorLayer:
                return activeLayer.sourceCrs()
            elif type(activeLayer) == QgsRasterLayer:
                return activeLayer.crs()
        else:
            return self.canvas.mapSettings().destinationCrs()

    def _warnIfPointOutsideCanvas(self):
        if(self.dockwidget.hasInput() and not self.canvas.extent().contains(self.inputCoordinatesInCanvasCrs())):
            self.setWarningMessage(CT.tr("outside of map extent"))
        else:
            self.setWarningMessage(None)

    #--------------------------------------------------------------------------


    # GETTERS/SETTERS
    def setInputCrs(self, crs):
        oldCrs = self._inputCrs

        if (oldCrs == None) or ( crs.authid() != oldCrs.authid() ) :
            #coordinatorLog("setting input CRS to %s" % crs.authid())
            currentCoordinates = self.dockwidget.inputCoordinates()
            self._inputCrs = crs
            self.dockwidget.setSectionCrs(CoordinatorDockWidget.SectionInput, crs)
            self._transform.setSourceCrs(crs)
            self._canvasTransform.setSourceCrs(crs)

            if(oldCrs != None and self.dockwidget.hasInput()):
                # make sure we transform the currently set coordinate
                # to the new Coordinate System :
                t = QgsCoordinateTransform(oldCrs, crs, QgsProject.instance())
                transformedPoint = t.transform(QgsPointXY(currentCoordinates[0], currentCoordinates[1]))
                self.dockwidget.setInputPoint(transformedPoint)
            else:
                self.dockwidget.clearSection(CoordinatorDockWidget.SectionBoth)

    def inputCrs(self) :
        return self._inputCrs

    def setOutputCrs(self, crs):
        #coordinatorLog("changing output CRS %s -> %s" % (self._outputCrs.authid() if self._outputCrs else "NONE!", crs.authid()) )
        oldCrs = self._outputCrs
        if ( oldCrs == None ) or (oldCrs.authid() != crs.authid()) :
            self._outputCrs = crs
            self.dockwidget.setSectionCrs(CoordinatorDockWidget.SectionOutput, crs)
            self._transform.setDestinationCrs(crs)
            self.process()

    def outputCrs(self):
        return self._outputCrs

    def setWarningMessage(self, message):
        self.dockwidget.setWarningMessage(message)

    # ACTIONS :
    def openCrsSelectionDialogForSection(self, section):
        projSelector = QgsProjectionSelectionDialog()
        if(projSelector.exec()):
            if section == CoordinatorDockWidget.SectionInput:
                self.setInputCrs(projSelector.crs())
            elif section == CoordinatorDockWidget.SectionOutput:
                self.setOutputCrs(projSelector.crs())

    def setOutputCrsToCanvasCrs(self):
        crs = self.canvas.mapSettings().destinationCrs()
        self.setOutputCrs(crs)

    def connectCrsToCanvas(self, section, connect) :
        #coordinatorLog("%s %s" % (section, connect))

        if section == CoordinatorDockWidget.SectionOutput:

            if(connect): # connect to map
                # disable dialog for selecting output CRS:
                self.dockwidget.outputCrs.clicked.disconnect()
                # set CRS to be canvas' CRS and follow it
                self.setOutputCrsToCanvasCrs()
            else:
                # enable dialog selection
                self.dockwidget.outputCrs.clicked.connect(partial(self.openCrsSelectionDialogForSection, CoordinatorDockWidget.SectionOutput))

    def addCurrentCoordinatesToDigitizeSession(self):
        editTool = self.__compatibleMapTool()
        if(not editTool):
            return False

        result = False

        point = self.inputCoordinatesInCanvasCrs()
        if( editTool.mode() == QgsMapToolCapture.CaptureMode.CapturePoint):
            #coordinatorLog("Point Capture!")
            layer = self.iface.activeLayer()
            geometry = QgsGeometry.fromPointXY(point)
            feature = QgsFeature(layer.fields())
            feature.setGeometry(geometry)
            if( (len(layer.fields()) < 1) or self.iface.openFeatureForm(layer, feature)):
                result = layer.addFeature(feature)
                #coordinatorLog("Point written to layer")
                layer.triggerRepaint()

        elif (
            (editTool.mode() == QgsMapToolCapture.CaptureMode.CapturePolygon)
            or (editTool.mode() == QgsMapToolCapture.CaptureMode.CaptureLine)
        ):
            #coordinatorLog("Rubberband Capture!")
            result = (editTool.addVertex(point) == 0)
        else:
            return False

        if(result):
            self.dockwidget.showInfoMessage(CT.tr("coordinate added"),1500)
        else:
            self.setWarningMessage(CT.tr("adding coordinate failed"))

        return result

    def switchInputOutputCrs(self):
        inputCrs = self._inputCrs
        self.setInputCrs(self._outputCrs)
        self.setOutputCrs(inputCrs)

        if self.dockwidget.outputCrsConn.isChecked() and (self._outputCrs.authid() != self._inputCrs.authid()) :
            self.dockwidget.outputCrsConn.setChecked(False)

    def _showMarker(self, show):
        if show and self.dockwidget.hasInput():
            self.marker.show()
        else:
            self.marker.hide()

    # API :
    def enableMarker(self, show):
        self._showMarker(show)
        self.dockwidget.showMarker.setChecked(show)

    # PIPELINE :
    def ensureValidInputGui(self):
        self.dockwidget.addFeatureButton.setEnabled(self.__checkEnableAddFeatureButton())
        self._warnIfPointOutsideCanvas()

        # make sure we show the marker now:
        if self.dockwidget.hasInput():
            if self.dockwidget.showMarker.isChecked():
                self.marker.show()
        else:
            self.marker.hide()

        self.dockwidget.setInputToDMS(
            self.dockwidget.inputAsDMS.isChecked()
            & self._inputCrs.isGeographic()
        )

    def process(self):
        #coordinatorLog("about to process input")
        if(self.dockwidget.hasInput()):
            (x, y) = self.dockwidget.inputCoordinates()
            # coordinatorLog("Input: %f %f " %  (x, y)  )
            transformedPoint = self._transform.transform(QgsPointXY(x, y))
            # coordinatorLog("Transformed point: %f %f " %  (transformedPoint.x(), transformedPoint.y())  )
            self.dockwidget.setResultPoint(transformedPoint)
            self.marker.setCenter(self.inputCoordinatesInCanvasCrs())
        else:
            self.dockwidget.clearFieldsInSection(CoordinatorDockWidget.SectionOutput)

    def inputCoordinatesInCanvasCrs(self):
        (x, y) = self.dockwidget.inputCoordinates()
        result = self._canvasTransform.transform(QgsPointXY(x, y))
        #coordinatorLog("transformation: (%s,%s) are (%s,%s)" % (x,y, result.x(), result.y()))
        #coordinatorLog(" %s -> %s" % (self._canvasTransform.sourceCrs().authid(), self._canvasTransform.destinationCrs().authid()) )
        return result

    # SLOTS :
    def mapCanvasCrsChanged(self):
        self._canvasTransform.setDestinationCrs(self.canvas.mapSettings().destinationCrs())
        #if(self.dockwidget.outputCrsConn.isChecked()):
        #    self.setOutputCrs(self.canvas.mapSettings().destinationCrs())

    def inputCoordinatesChanged(self):
        #Coordinator.log("Input changed")
        self.process()
        self.ensureValidInputGui()

    def inputFormatChanged(self):
        self.ensureValidInputGui()

    def outputFormatChanged(self):
        self.process()

    def moveCanvasButtonClicked(self):
        self.canvas.setCenter(self.inputCoordinatesInCanvasCrs())

    def mapCrsConnectionButtonToggled(self, forSection, enabled):
        self.connectCrsToCanvas(forSection, enabled)

    def showMarkerButtonToggled(self, show):
        self._showMarker(show)

    def captureCoordsButtonToggled(self, enabled):
        #coordinatorLog( "enable Capture Coords: %s" % enabled)
        if(enabled):
            self.canvas.setMapTool(self.mapTool)
            self.mapTool.canvasClicked.connect(self.canvasClickedWithPicker)
        else:
            self.mapTool.canvasClicked.disconnect(self.canvasClickedWithPicker)
            self.canvas.unsetMapTool(self.mapTool)

    def canvasClickedWithPicker(self, point, button):
        # button is the MouseButton
        #coordinatorLog(type(button).__name__)

        if QApplication.keyboardModifiers() and Qt.ControlModifier:
            self.setInputCrs(self.canvas.mapSettings().destinationCrs())

#         coordinatorLog("Current Canvas Transform is %s -> %s (we do the reverse to get input)"
#                        % (self._canvasTransform.sourceCrs().authid(), self._canvasTransform.destinationCrs().authid())
#                        )

        point = self._canvasTransform.transform(point, QgsCoordinateTransform.ReverseTransform)
        self.dockwidget.setInputPoint(point)

    def canvasMoved(self):
        self._warnIfPointOutsideCanvas()

    def mapToolChanged(self):
        #coordinatorLog("map tools changed")
        self.dockwidget.addFeatureButton.setEnabled(self.__checkEnableAddFeatureButton())

    def addFeatureClicked(self):
        self.addCurrentCoordinatesToDigitizeSession()

    def projectRead(self):
        #coordinatorLog("new project")
        self._project = QgsProject.instance()
        self.__initTransformers()
        self.dockwidget.resetInterface()

    def currentLayerChanged(self, layer):        
        
        if self._observingLayer:
            self._observingLayer.crsChanged.disconnect(self.layerChangedCrs)
        
        if layer:
            self._observingLayer = layer
            self._observingLayer.crsChanged.connect(self.layerChangedCrs)
        
        #coordinatorLog("%s" % type(layer).__name__)
        if self.dockwidget.outputCrsConn.isChecked():
            self.setOutputCrs(self._currentEffectiveCrsInMap())
    
    def layerChangedCrs(self):
        #coordinatorLog("%s" % type(layer).__name__)
        if self.dockwidget.outputCrsConn.isChecked():
            self.setOutputCrs(self._currentEffectiveCrsInMap())
        

    def run(self):
        """Run method that loads and starts the plugin"""
        #coordinatorLog("run", "Coordinator")
        if not self.pluginIsActive:
            self.pluginIsActive = True

            #QgsMessageLog.logMessage("Starting", "Coordinator")

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            if self.dockwidget == None:
                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = CoordinatorDockWidget()

            #for child in self.dockwidget.children():
            #    self.log("Child: %s" % child.objectName())

            # MA LOGIC:

            # EXTERNAL connections
            self.canvas.destinationCrsChanged.connect(self.mapCanvasCrsChanged)
            self.canvas.mapToolSet.connect(self.mapToolChanged)
            self.canvas.extentsChanged.connect(self.canvasMoved)
            self.iface.projectRead.connect(self.projectRead)
            self.iface.currentLayerChanged.connect(self.currentLayerChanged)

            # CONNECT the initially active buttons from the GUI:
            self.dockwidget.selectCrsButton.clicked.connect(partial(self.openCrsSelectionDialogForSection, CoordinatorDockWidget.SectionInput) )
            self.dockwidget.mapConnectionChanged.connect(self.mapCrsConnectionButtonToggled)

            # set the inital CRS:
            self.setInputCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
            self.setOutputCrs(self.canvas.mapSettings().destinationCrs())

            # connect the marker button :
            self.dockwidget.showMarker.clicked.connect(self.showMarkerButtonToggled)
            self.dockwidget.moveCanvas.clicked.connect(self.moveCanvasButtonClicked)
            self.dockwidget.captureCoordButton.clicked.connect(self.captureCoordsButtonToggled)

            self.dockwidget.addFeatureButton.clicked.connect(self.addFeatureClicked)

            self.dockwidget.inputFormatButtonGroup.buttonClicked.connect(self.inputFormatChanged)
            self.dockwidget.resultFormatButtonGroup.buttonClicked.connect(self.outputFormatChanged)

            self.dockwidget.inputChanged.connect(self.inputCoordinatesChanged)

            # connect to provide cleanup on closing of dockwidget
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)


            # SETUP:
            self.enableMarker(True)
            self._canvasTransform.setDestinationCrs(self.canvas.mapSettings().destinationCrs())

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self._uiHook.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
            self.dockwidget.show()
