# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CoordinatorDockWidget
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

import os

from functools import partial

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import Qt
from PyQt5.Qt import pyqtSignal, QLocale, QApplication, QDoubleValidator, QIntValidator,\
    QKeyEvent, QScrollEvent, QWheelEvent, QPixmap, QIcon, QSize, QTimer, QEvent,\
    QObject, QWebView, QUrl

from qgis.core import QgsMessageLog, QgsCoordinateFormatter

from .funcs import coordinatorDecimalToDms, coordinatorDmsStringsToDecimal,\
    coordinatorLog
from PyQt5.QtWidgets import QLineEdit
import pathlib

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'coordinator_dockwidget_base.ui'))

class CoordinatorDockWidget(QtWidgets.QDockWidget, FORM_CLASS):

    SectionInput = 1
    SectionOutput = 2
    SectionBoth = 3

    SideRight = 1
    SideLeft = 2
    SideBoth = 3

    closingPlugin = pyqtSignal()

    inputChanged = pyqtSignal()
    mapConnectionChanged = pyqtSignal(int, bool)

    def __init__(self, parent=None):
        """Constructor."""
        super(CoordinatorDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect


        self.decDegreeValidator = QDoubleValidator(0.0, 180.0, 8, parent = self)
        self.decDegreeValidator.setNotation(QDoubleValidator.StandardNotation)

        self.projectedValidator = QDoubleValidator(-999999999.0, 999999999.0, 4, parent = self)

        self._eastingLeftNorthingRight = True

        self._eastingInverted = False
        self._northingInverted = False

        self.sectionIsGeographic = {
            CoordinatorDockWidget.SectionInput : True,
            CoordinatorDockWidget.SectionOutput : True
        }
        
        self.setupUi(self)
        
        # setup some lists of the input for easier access later
        self._widgetlistInputDms = [
            self.inLeft,
            self.inRight,
            self.inLeftSec,
            self.inRightSec,
            self.inLeftMin,
            self.inRightMin
        ]
        self._widgetlistInput = self._widgetlistInputDms + [
            self.inLeftDec,
            self.inRightDec
        ]
        
        self.resetInterface()
        self.setupInternal()

        # need to init that after setupUi because of message icon label size
        messageIconWidgetSize = self.messageIcon.size()
        messageIconSize = QSize(messageIconWidgetSize.width()-2, messageIconWidgetSize.height()-2)
        self.warningPixmap = QIcon(':/plugins/coordinator/icons/warning.svg').pixmap(messageIconSize)

        self.messageHideTimer = QTimer(parent = self)
        self.messageHideTimer.setSingleShot(True)
        self.messageHideTimer.timeout.connect(self.hideMessages)
        

    def setupInternal(self ):
        self.leftDecimal.hide()
        self.rightDecimal.hide()

        
        self.leftDmsDisplay = DmsHandler(self.inLeft, self.inLeftMin, self.inLeftSec, 180)
        self.leftDmsDisplay.inputDidChange.connect(self.__inputFieldsChangedInternal)
        self.rightDmsDisplay = DmsHandler(self.inRight, self.inRightMin, self.inRightSec, 90)
        self.rightDmsDisplay.inputDidChange.connect(self.__inputFieldsChangedInternal)

        for dirButton in [
            self.leftDirButton,
            self.rightDirButton
        ]:
            # see https://stackoverflow.com/questions/4578861/connecting-slots-and-signals-in-pyqt4-in-a-loop
            dirButton.clicked.connect( partial(self.toggleCardinalDirectionButton, dirButton) )

        for inputField in self._widgetlistInputDms:
            inputField.installEventFilter(self)

        for inputField in [
            self.inLeftDec,
            self.inRightDec
        ]:
            inputField.textEdited.connect(self.__inputFieldsChangedInternal)
            inputField.setValidator(self.decDegreeValidator)
            inputField.installEventFilter(self)
            
        self.leftDecIncrementor = ValueIncrementor(self.inLeftDec, 180, -180)
        self.rightDecIncrementor = ValueIncrementor(self.inLeftDec, 90, -90)

        self.outputCrsConn.clicked.connect(partial(self.toggledMapConnection, CoordinatorDockWidget.SectionOutput))

        self.copyLeft.clicked.connect(partial(self.copyResultToClipBoard, CoordinatorDockWidget.SideLeft))
        self.copyRight.clicked.connect(partial(self.copyResultToClipBoard,  CoordinatorDockWidget.SideRight))
        self.copyResultComplete.clicked.connect(partial(self.copyResultToClipBoard,  CoordinatorDockWidget.SideBoth))
        self.clearInput.clicked.connect(partial(self.resetInterface, self.SectionBoth))
        self.showHelp.clicked.connect(self.showHelpButtonClicked)

    def _setToolsEnabled(self, enabled, section = None):
        if(section == None): section = self.SectionBoth

        if(section & self.SectionInput):
            self.moveCanvas.setEnabled(enabled)

        if(section & self.SectionOutput):
            for widget in [
                self.copyResultComplete,
                self.copyLeft,
                self.copyRight
            ]:
                widget.setEnabled(enabled)

    def resetInterface(self, section = None):
        if section == None: section = self.SectionBoth
        self.clearSection(section)
        self._setToolsEnabled(False, section)

    def eventFilter(self, obj, event):
        if(type(event) == QKeyEvent and event.type() == QEvent.KeyRelease):
            key = event.key()
            if(self.sectionIsGeographic[self.SectionInput] and event.text() == "-"):
                # maybe we should switch the hemisphere?
                if(obj in [self.inLeft, self.inLeftDec, self.inLeftMin, self.inLeftSec]):
                    self.toggleCardinalDirectionButton(self.leftDirButton)
                else:
                    self.toggleCardinalDirectionButton(self.rightDirButton)
            elif(key in [Qt.Key_Return, Qt.Key_Enter]):
                if(self.addFeatureButton.isEnabled()):
                    #coordinatorLog("Clicking add Feature Button")
                    self.addFeatureButton.click()

            #coordinatorLog("Yakub Key Event (Filter): %s (%s)" % (event.key(), event.text()) )

        return super(CoordinatorDockWidget, self).eventFilter(obj, event)

    def __styleInputStyleSelectorForGeographicCrs(self, isGeographic):

        for widget in [
            self.geoLabel,
            self.inputAsDMS,
            self.inputAsDec
        ]:
            widget.setEnabled(isGeographic)

    def setSectionIsGeographic(self, section, isGeographic):
        if(section & self.SectionInput):
            # switch validators for the decimal field, as we may support different ranges
            # switch to DMS view accordingly
            if isGeographic:
                self.inLeftDec.setValidator(self.decDegreeValidator)
                self.inRightDec.setValidator(self.decDegreeValidator)
                # switch to DMS view if it is selected
                self.setInputToDMS(self.inputAsDMS.isChecked())
            else:
                self.inLeftDec.setValidator(self.projectedValidator)
                self.inRightDec.setValidator(self.projectedValidator)

                self.setInputToDMS(False)

            for widget in [
                self.labelDecDegreeLeft,
                self.labelDecDegreeRight,
                self.leftDirButton,
                self.rightDirButton
            ]:
                widget.show() if isGeographic else widget.hide()

            self.__styleInputStyleSelectorForGeographicCrs(isGeographic)


        if(section & self.SectionOutput):
            for widget in [
                self.resultAsDMS,
                self.resultAsDec
            ]:
                widget.setEnabled(isGeographic)

        self.sectionIsGeographic[section] = isGeographic

    def setSectionCrs(self, section, crs):
        #QgsMessageLog.logMessage("set SectionCrs, is Geographic: %s" % crs.isGeographic(), "Coordinator")

        self.setSectionIsGeographic(section, crs.isGeographic())

        if(section == self.SectionInput):
            self.selectCrsButton.setText(crs.authid())
        elif(section == self.SectionOutput):
            self.outputCrs.setText(crs.authid())

    def setInputToDMS(self, isDms):
        if isDms :
            self.leftDMS.show()
            self.rightDMS.show()
            self.leftDecimal.hide()
            self.rightDecimal.hide()
        else:
            self.leftDMS.hide()
            self.rightDMS.hide()
            self.leftDecimal.show()
            self.rightDecimal.show()

    def setInputPoint(self, point):
        #QgsMessageLog.logMessage("%s/%s" % (point.x(), point.y()))

        precision = 9 if self.sectionIsGeographic[self.SectionInput] else 3

        # remove leading minus when setting decimal fields. The correct state for
        # the hemisphere buttons is applied in setDmsInputFromDecimal() later.
        xDec = abs(point.x())
        yDec = abs(point.y())

        self.inLeftDec.setText(QLocale().toString(xDec if self._eastingLeftNorthingRight else yDec, "f", precision))
        self.inRightDec.setText(QLocale().toString(yDec if self._eastingLeftNorthingRight else xDec,"f", precision))

        self.setDmsInputFromDecimal(point.x(), point.y())

        self.__inputFieldsChangedInternal()

    def setDmsInputFromDecimal(self, x, y, setEastingNorthingInversion=True):
        xDMS = coordinatorDecimalToDms(x)
        yDMS = coordinatorDecimalToDms(y)

        #QgsMessageLog.logMessage(str(xDMS))

        if(setEastingNorthingInversion):
            self.setEastingInverted(xDMS[0])
            self.setNorthingInverted(yDMS[0])

        leftDMS = xDMS if self._eastingLeftNorthingRight else yDMS
        rightDMS = yDMS if self._eastingLeftNorthingRight else xDMS

        self.inLeft.setText(QLocale().toString(leftDMS[1]))
        self.inLeftMin.setText(QLocale().toString(leftDMS[2]))
        self.inLeftSec.setText(QLocale().toString(leftDMS[3], "f", 2))

        self.inRight.setText(QLocale().toString(rightDMS[1]))
        self.inRightMin.setText(QLocale().toString(rightDMS[2]))
        self.inRightSec.setText(QLocale().toString(rightDMS[3], "f", 2))

    def setResultPoint(self, point):
        if self.sectionIsGeographic[CoordinatorDockWidget.SectionOutput]:
            if(self.resultAsDec.isChecked()):
                f = QgsCoordinateFormatter.FormatDecimalDegrees
                precision = 9
            else:
                f = QgsCoordinateFormatter.FormatDegreesMinutesSeconds
                precision = 3

            transformedX = QgsCoordinateFormatter.formatX(point.x(), f, precision )
            transformedY = QgsCoordinateFormatter.formatY(point.y(), f, precision )
            # if we use FormatDecimalDegrees QgsCoordinateFormatter produces
            # a string just with a QString::number(). Therefore the string is NOT
            # localized. But QgsCoordinateFormatter provides coordinate wrapping already
            # so we just hack the correct decimal sign into the string and should be
            # fine... juuust fine!
            decPoint = QLocale().decimalPoint()
            #coordinatorLog("Decimal Point: %s" % decPoint)
            if(decPoint != "."):
                #coordinatorLog("replace!!")
                transformedX = transformedX.replace(".", decPoint)
                transformedY = transformedY.replace(".", decPoint)

        else:
            #self.log(" -> using decimal output")
            transformedX = QLocale().toString(point.x(), 'f', 2 )
            transformedY = QLocale().toString(point.y(), 'f', 2 )



        self.setResult(transformedX, transformedY)

    def setResult(self, x, y):
        if(self._eastingLeftNorthingRight):
            self.resultLeft.setText(x)
            self.resultRight.setText(y)
        else:
            self.resultLeft.setText(y)
            self.resultRight.setText(x)

    def setWarningMessage(self, message):
        if(message and len(message) > 0):
            self.messageIcon.setPixmap(self.warningPixmap)
            self.messageIcon.show()
            self.messageText.setText(message)
        else:
            self.hideMessages()

    def showInfoMessage(self, message, hideAfterMilliseconds = None):
        self.messageIcon.clear()
        self.messageText.setText(message)
        if(hideAfterMilliseconds):
            self.messageHideTimer.setInterval(hideAfterMilliseconds)
            self.messageHideTimer.start()

    def hideMessages(self):
        self.messageIcon.clear()
        self.messageIcon.hide()
        self.messageText.clear()

    def clearFieldsInSection(self, section):
        if(section & self.SectionInput):
            for inputField in self._widgetlistInput:
                inputField.setText("")
        if(section & self.SectionOutput):
            for inputField in [
                self.resultRight,
                self.resultLeft,
            ]:
                inputField.setText("")

    def clearSection(self, section):
        self.clearFieldsInSection(section)

        # the following code will also reset
        # the buttons designating the hemisphere:
        #if (section & self.SectionInput ) :
        #    self.setEastingInverted(False)
        #    self.setNorthingInverted(False)

        self.addFeatureButton.setEnabled(False)

        self.inputChanged.emit()


    def calculateDecimalDegreesFromDMS(self):
        #QgsMessageLog.logMessage("calc DMS", "Coordinator")
        valueLeft = coordinatorDmsStringsToDecimal(
            self.inLeft.text(),
            self.inLeftMin.text(),
            self.inLeftSec.text()
        )
        valueRight = coordinatorDmsStringsToDecimal(
            self.inRight.text(),
            self.inRightMin.text(),
            self.inRightSec.text()
        )
        return (valueLeft, valueRight)

    def hasInput(self):
        if self.leftDMS.isVisible():
            hasInput = False
            for field in self._widgetlistInputDms:
                if len(field.text()) > 0:
                    hasInput = True
                    break
        else:
            hasInput = (
                len(self.inLeftDec.text()) > 0 or
                len(self.inRightDec.text()) > 0
            )
        return hasInput

    def __rawInputCoordinates(self):
        if (self.leftDMS.isVisible()):
            return(self.calculateDecimalDegreesFromDMS())
        else:
            valueLeft = 0.0
            valueRight = 0.0
            if(len(self.inLeftDec.text())):
                valueLeft = QLocale().toFloat(self.inLeftDec.text())[0]
            if(len(self.inRightDec.text())):
                valueRight = QLocale().toFloat(self.inRightDec.text())[0]

            return (valueLeft, valueRight)

    def inputCoordinates(self):
        (valueLeft, valueRight) = self.__rawInputCoordinates()

        if(self._eastingLeftNorthingRight):
            inX = valueLeft
            inY = valueRight
        else:
            inX = valueRight
            inY = valueLeft

        if(self.sectionIsGeographic[self.SectionInput] and self._eastingInverted):
            inX *= -1
        if(self.sectionIsGeographic[self.SectionInput] and self._northingInverted):
            inY *= -1

        return (inX, inY)

    def setNorthingInverted(self, northingInverted):
        self._northingInverted = northingInverted
        label = self.tr("S", "lblSouth") if northingInverted else self.tr("N", "lblNorth")
        if(self._eastingLeftNorthingRight):
            self.rightDirButton.setText(label)
        else:
            self.leftDirButton.setText(label)

    def setEastingInverted(self, eastingInverted):
        self._eastingInverted = eastingInverted
        label = self.tr("W", "lblWest") if eastingInverted else self.tr("E", "lblEast")
        if(self._eastingLeftNorthingRight):
            self.leftDirButton.setText(label)
        else:
            self.rightDirButton.setText(label)

    def toggleCardinalDirectionButton(self, button) :
        if(self._eastingLeftNorthingRight):
            toggleEasting = (button == self.leftDirButton)
        else:
            toggleEasting = (button == self.rightDirButton)

        if(toggleEasting):
            self.setEastingInverted(not self._eastingInverted)
        else:
            self.setNorthingInverted(not self._northingInverted)

        self.inputChanged.emit()

    def toggledMapConnection(self, section, isConnected):
        if section == CoordinatorDockWidget.SectionOutput:
            self.outputCrs.setEnabled(not isConnected)

        self.mapConnectionChanged.emit(section, isConnected)

    def __inputFieldsChangedInternal(self):
        #coordinatorLog("fields changed internal triggered")

        self._setToolsEnabled(self.hasInput())

        if(self.hasInput()):

            if (self.leftDMS.isVisible()):
                (leftValue, rightValue) = self.calculateDecimalDegreesFromDMS()
                self.inLeftDec.setText(QLocale().toString(leftValue,  "f", 9) )
                self.inRightDec.setText(QLocale().toString(rightValue, "f", 9) )
            else:
                # calculate DMS Values

                leftValue = QLocale().toFloat(self.inLeftDec.text())[0]
                rightValue = QLocale().toFloat(self.inRightDec.text())[0]

                x = leftValue if self._eastingLeftNorthingRight else rightValue
                y = rightValue if self._eastingLeftNorthingRight else leftValue

                self.setDmsInputFromDecimal(x, y, False)
        else:
            if (self.leftDMS.isVisible()):
                self.inLeftDec.setText(None)
                self.inRightDec.setText(None)
            else:
                for f in self._widgetlistInputDms: f.setText(None)

        self.inputChanged.emit()

    def copyResultToClipBoard(self, which) :
        cb = QApplication.clipboard()
        cb.clear(mode=cb.Clipboard )
        if which == CoordinatorDockWidget.SideLeft:
            content = self.resultLeft.text()
        elif which == CoordinatorDockWidget.SideRight:
            content = self.resultRight.text()
        else:
            content = "%s\t%s" % (self.resultLeft.text(), self.resultRight.text())

        cb.setText(content, mode=cb.Clipboard)

    def showHelpButtonClicked(self):
        
        if not hasattr(self, "helpview"):
            helpBasepath = "%s/help" % os.path.normpath(os.path.dirname(__file__))
            helpUrl = QUrl(pathlib.Path("%s/index.html" % helpBasepath).as_uri())
            cssUrl = QUrl(pathlib.Path("%s/help.css" % helpBasepath).as_uri())
            self.helpview = QWebView()
            self.helpview.settings().setUserStyleSheetUrl(cssUrl)
            
            self.helpview.load(helpUrl)

        self.helpview.show()

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

class DmsHandler(QObject):
    
    inputDidChange = pyqtSignal()
    
    def __init__(self, degField, minField, secField, maxDegrees):
        super(DmsHandler, self).__init__()
        
        # init validators:
        self.intDegValidator = QIntValidator(0,maxDegrees, parent = self)
        self.minValidator = QIntValidator(0,59, parent = self)
        
        self.secValidator = QDoubleValidator(0.0,59.999, 3, parent = self)
        self.secValidator.setNotation(QDoubleValidator.StandardNotation)
        
        self._degField = degField
        self._minField = minField
        self._secField = secField
        
        self._maxDegrees = maxDegrees
        
        self._degFieldIncrementor = ValueIncrementor(self._degField, maxDegrees, doOverflow = False )
        self._degFieldIncrementor.fieldDidOverflow.connect(self.fieldDidOverflow)
        self._degField.setValidator(self.intDegValidator)
        self._degField.textEdited.connect(self.inputDidChange.emit)

        self._minFieldIncrementor = ValueIncrementor(self._minField, 59, wrapCallback = self.isWrapAllowedFor)
        self._minFieldIncrementor.fieldDidOverflow.connect(self.fieldDidOverflow)
        self._minField.setValidator(self.minValidator)
        self._minField.textChanged.connect( partial(self.minorFieldDidChange, self._minField))

        self._secFieldIncrementor = ValueIncrementor(self._secField, 59, wrapCallback = self.isWrapAllowedFor)
        self._secFieldIncrementor.fieldDidOverflow.connect(self.fieldDidOverflow)
        self._secField.setValidator(self.secValidator)
        self._secField.textChanged.connect( partial(self.minorFieldDidChange, self._secField))
    
    def fieldDidOverflow(self, field, overflow):
        if field == self._minField:
            self._degFieldIncrementor.doStepwiseIncrement(overflow)
        elif field == self._secField:
            self._minFieldIncrementor.doStepwiseIncrement(overflow)
            
    def minorFieldDidChange(self, field):
        degrees = QLocale().toInt(self._degField.text())[0]
        if degrees == self._maxDegrees:
            field.setText("0")
            
        self.inputDidChange.emit()
    
    def isWrapAllowedFor(self, field, direction):
        if(field == self._minField):
            degrees = QLocale().toInt(self._degField.text())[0]
            res = degrees + direction
            return 0 <= res <= self._maxDegrees
        elif(field == self._secField):
            minutes = QLocale().toInt(self._minField.text())[0]
            res = minutes + direction
            if not (0 <= res < 60):
                return self.isWrapAllowedFor(self._minField, direction)
            else:
                return True
        elif(field == self._degField):
            degrees = QLocale().toInt(self._degField.text())[0]
            res = degrees + direction
            return 0 <= res <= self._maxDegrees
        
        return True
        
    
        

class ValueIncrementor(QObject):
    
    IS_OVERFLOW = 1
    IS_UNDERFLOW = -1
    
    fieldDidOverflow = pyqtSignal(QLineEdit, int)
    
    def __init__(self, lineEditField, max, min = 0, doOverflow = True, wrapCallback = None):
        super(QObject, self).__init__()
        b = lineEditField.installEventFilter(self)
        self._leField = lineEditField
        self._max = float(max)
        self._min = float(min)
        self._doOverflow = doOverflow
        self._wrapCallback = wrapCallback
        
    
    def doStepwiseIncrement(self, direction):
        value = QLocale().toFloat(self._leField.text())[0]
        overflow = 0

        if(direction < 0):
            newValue = value - 1
        elif(direction > 0):
            newValue = value + 1
        else:
            return False
        #coordinatorLog("new value : %s" % newValue)
        
        if self._doOverflow:
            if newValue < self._min:
                newValue = self._max
                overflow = ValueIncrementor.IS_UNDERFLOW
            elif newValue > self._max:
                newValue = self._min
                overflow = ValueIncrementor.IS_OVERFLOW
        else:
            if newValue < self._min:
                newValue = self._min
                overflow = ValueIncrementor.IS_UNDERFLOW
            elif newValue > self._max:
                newValue = self._max
                overflow = ValueIncrementor.IS_OVERFLOW

    
        # important to call the overflow before we edit the minor
        # field because subsequent validators (like DmsHandler.minorFieldDidChange)
        # may depend on an already correct DegreeField
        if(overflow != 0):
            # we do overflow. check if we are allowed to overflow:  
            if(self._wrapCallback):
                if not self._wrapCallback(self._leField, direction):
                    return True
            
            self.fieldDidOverflow.emit(self._leField, overflow)
    
   
        textValidator = self._leField.validator()
    
        if isinstance(textValidator, QIntValidator):
            newValueString = QLocale().toString(newValue, "f", 0)
        else:
            precision = textValidator.decimals()
            newValueString = QLocale().toString(newValue, "f", precision)

        self._leField.clear()
        self._leField.insert(newValueString )
        
        return True
    
    def eventFilter(self, obj, event):
        if(type(event) == QKeyEvent and event.type() == QEvent.KeyPress):
            key = event.key()
            if(key == Qt.Key_Up):
                return self.doStepwiseIncrement(1)
            elif(key == Qt.Key_Down):
                return self.doStepwiseIncrement(-1)
        elif (type(event) == QWheelEvent):
            delta = event.angleDelta().y()
            if delta != 0:
                return self.doStepwiseIncrement(delta)
        
        return super(ValueIncrementor, self).eventFilter(obj, event)
    
    