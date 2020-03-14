# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# 
# Trace Digitize Action - Sets up a Qgis action with/for the vertex tracer tool
#
# Copyright (C) 2010  Cédric Möri, with stuff from Stefan Ziegler
#
# EMAIL: cmoe (at) geoing (dot) ch
# WEB  : www.geoing.ch
#
# ---------------------------------------------------------------------
# 
# licensed under the terms of GNU GPL 2
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
# 
# ---------------------------------------------------------------------
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import QgsFeature, QgsMapLayer
# from qgis.gui import *

# import pydevd

# initialize Qt resources from file resources.py
from .resources import *

# Import own tools
from .vertexTracerTool import VertexTracerTool


# Our main class for the plugin
class TraceDigitize:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.rubberBand = 0
        self.action = None
        self.actionShowTip = None
        self.tool = None

    def initGui(self):
        mc = self.canvas
        layer = mc.currentLayer()

        self.rubberBand = 0

        # Create action that will start plugin configuration
        self.action = QAction(QIcon(":/plugins/traceEdit/vector-create-trace.png"),
                              "Trace Edit", self.iface.mainWindow())
        self.action.setEnabled(False)
        self.action.setCheckable(True)
        self.action.setChecked(False)

        # Connect to signals for button behaviour
        self.action.triggered.connect(self.run)
        self.canvas.currentLayerChanged.connect(self.toggle)
        self.canvas.mapToolSet.connect(self.deactivate)

        # Add toolbar button
        self.iface.digitizeToolBar().addAction(self.action)

        # Get the Tool
        self.tool = VertexTracerTool(self.canvas)
        # Connect to the VTtool
        self.tool.traceFound.connect(self.createFeature)

        # Add help in plugin menu
        self.actionShowTip = QAction(u"Help", self.iface.mainWindow())
        self.iface.addPluginToMenu("&TraceDigitize", self.actionShowTip)
        self.action.triggered.connect(self.actionShowTip)

        # Get the Tool
        self.tool = VertexTracerTool(self.canvas)

    def unload(self):
        self.iface.digitizeToolBar().removeAction(self.action)
        self.iface.removePluginMenu("&TraceDigitize", self.actionShowTip)

    def toggle(self):
        mc = self.canvas
        layer = mc.currentLayer()

        # Decide whether the plugin button/menu is enabled or disabled
        if layer is not None:
            if layer.type() == QgsMapLayer.VectorLayer:

                if layer.isEditable():
                    self.action.setEnabled(True)
                    layer.editingStopped.connect(self.toggle)
                    try:
                        layer.editingStarted.disconnect(self.toggle)
                    except Exception:
                        pass
                else:
                    self.action.setEnabled(False)
                    layer.editingStarted.connect(self.toggle)
                    try:
                        layer.editingStopped.disconnect(self.toggle)
                    except Exception:
                        pass

    def deactivate(self):
        # uncheck the button/menu and get rid off the VTTool signal
        self.action.setChecked(False)
        # QObject.disconnect(self.tool, SIGNAL("traceFound(PyQt_PyObject)"), self.createFeature)

    def showTip(self):
        reply = QMessageBox.information(self.iface.mainWindow(), 'Tip',
                                        "Use <ctrl>-Key to trace, <backspace> to delete, left mouse click to set a normal vertex and right mouse click to finish.\nUses the snapping options, which may be changed during digitizing (Consider opening the snapping option as dock widget). ",
                                        QMessageBox.Ok)

    def run(self):
        # Here we go...
        mc = self.canvas
        layer = mc.currentLayer()

        # bring our tool into action
        mc.setMapTool(self.tool)
        self.action.setChecked(True)


    def createFeature(self, geom):
        # pydevd.settrace()
        layer = self.canvas.currentLayer()
        provider = layer.dataProvider()
        f = QgsFeature()

        # if (geom.validateGeometry()):
        if (geom.isGeosValid()):
            f.setGeometry(geom)
        else:
            reply = QMessageBox.question(self.iface.mainWindow(), 'Feature not valid',
                                         "The geometry of the feature you just added isn't valid. Do you want to use it anyway?",
                                         QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                f.setGeometry(geom)
            else:
                return False

        ## Add attributefields to feature.
        fields = layer.pendingFields()

        try:  # API-Break 1.8 vs. 2.0 handling
            attr = f.initAttributes(len(fields))
            for i in range(len(fields)):
                f.setAttribute(i, provider.defaultValue(i))

        except AttributeError:  # <=1.8
            ## Add attributefields to feature.
            for i in fields:
                f.addAttribute(i, provider.defaultValue(i))

        layer.beginEditCommand("Feature added")
        layer.addFeature(f)
        layer.endEditCommand()

        self.canvas.refresh()
