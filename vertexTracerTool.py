# -*- coding: latin1 -*-
#---------------------------------------------------------------------
# 
# Vertex Trace Tool - A QGIS tool to get a geometry by moving the cursor over vertices. Draws rubberband.
#
# Copyright (C) 2010-2012 Cédric Möri
#
# EMAIL: cmoe (at) geoing (dot) ch
# WEB  : www.geoing.ch
#
#---------------------------------------------------------------------
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
#---------------------------------------------------------------------

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *

import math

#import pydevd

# Vertex Finder Tool class
class VertexTracerTool(QgsMapTool):
  def __init__(self, canvas):
    #some stuff we need from qgis
    QgsMapTool.__init__(self,canvas)
    self.canvas=canvas
    self.snapper = QgsMapCanvasSnapper(self.canvas)
    #some stuff to control our state
    self.mCtrl = False
    self.started = False
    self.firstTimeOnSegment = True
    self.lastPointMustStay = False
    #some stuff to put our temp output
    self.lastPoint = None
    
   #our own fancy cursor
    self.cursor = QCursor(QPixmap(["16 16 3 1",
                                  "      c None",
                                  ".     c #00FF00",
                                  "+     c #FFFFFF",
                                  "                ",
                                  "       +.+      ",
                                  "      ++.++     ",
                                  "     +.....+    ",
                                  "    +.     .+   ",
                                  "   +.   .   .+  ",
                                  "  +.    .    .+ ",
                                  " ++.    .    .++",
                                  " ... ...+... ...",
                                  " ++.    .    .++",
                                  "  +.    .    .+ ",
                                  "   +.   .   .+  ",
                                  "   ++.     .+   ",
                                  "    ++.....+    ",
                                  "      ++.++     ",
                                  "       +.+      "]))
                                  
 
 
  #we need to know, if ctrl-key is pressed
  def keyPressEvent(self,  event):
    if event.key() == Qt.Key_Control:
      self.mCtrl = True


  #and also if ctrl-key is released
  def keyReleaseEvent(self,  event):
    if event.key() == Qt.Key_Control:
     self.mCtrl = False
    #remove the last added point when the delete key is pressed
    if event.key() == Qt.Key_Backspace:
      self.rb.removeLastPoint()



  def canvasPressEvent(self,event):
    #on left click, we add a point
    if event.button()  ==  1:
      layer = self.canvas.currentLayer()
      #if it is the start of a new trace, set the rubberband up
      if self.started == False:
        if layer.geometryType() == 1:
          self.isPolygon = False
        if layer.geometryType() == 2:
          self.isPolygon = True
        self.rb = QgsRubberBand (self.canvas, layer.geometryType())
        self.rb. setColor(QColor(255, 0, 0)) 
      #declare, that are we going to work, now!
      self.started = True
      if layer <> None:
          x = event.pos().x()
          y = event.pos().y()
          selPoint = QPoint(x,y)
          #try to get something snapped
          (retval,result) = self.snapper.snapToBackgroundLayers(selPoint)
          
          #the point we want to have, is either from snapping result
          if result  <> []:
            point = result[0].snappedVertex
            #if we snapped something, it's either a vertex 
            if result[0].snappedVertexNr <> -1:
                self.firstTimeOnSegment = True
            #or a point on a segment, so we have to declare, that a point on segment is found
            else:
                self.firstTimeOnSegment = False
          #or its some point from out in the wild
          else:
            point =  QgsMapToPixel.toMapCoordinates(self.canvas.	getCoordinateTransform (), x, y)
            self.firstTimeOnSegment = True

          #bring the rubberband to the cursor i.e. the clicked point
          self.rb.movePoint(point)
          #and set a new point to go on with
          self.appendPoint(point)
          #try to remember that this point was on purpose i.e. clicked by the user
          self.lastPointMustStay = True
          self.firstTimeOnSegment = True
          
     
     
  def canvasMoveEvent(self,event):
    #QgsMessageLog.logMessage('fts: '+str(self.firstTimeOnSegment), 'state', 0)
    #QgsMessageLog.logMessage('lpc: '+str(self.lastPointMustStay), 'state', 0)
    if self.started:
      #Get the click
      x = event.pos().x()
      y = event.pos().y()
      eventPoint = QPoint(x,y)
      #only if the ctrl key is pressed
      if self.mCtrl == True:
        layer = self.canvas.currentLayer()
        if layer <> None:
         (retval,result) = self.snapper.snapToBackgroundLayers(eventPoint)
         
        #so if we have found a snapping
        if result <> []:
          #pydevd.settrace()
          #that's the snapped point
          point =QgsPoint(result[0].snappedVertex)
          #if it is a vertex, not a point on a segment
          if result[0].snappedVertexNr <> -1: 
            self.rb.movePoint(point) 
            self.appendPoint(point)
            self.lastPointMustStay = True
            #the next point found, may  be on a segment
            self.firstTimeOnSegment = True
          #we are on a segment
          else:
            self.rb.movePoint(point)
            #if we are on a new segment, we add the point in any case
            if self.firstTimeOnSegment:
                self.appendPoint(point)
                self.lastPointMustStay = True
                self.firstTimeOnSegment = False
            #if we are not on a new segemnt, we have to test, if this point is realy needed
            else:
                #but only if we have already enough points
                #TODO: check if this is correct for lines also (they only need two points, to be vaild)
                if self.rb.numberOfVertices() >=3:
                    max = self.rb.numberOfVertices()
                    lastRbP = self.rb.getPoint(0, max-2)
                    #QgsMessageLog.logMessage(str(self.rb.getPoint(0, max-1)), 'rb', 0)
                    nextToLastRbP = self.rb.getPoint(0, max-3)
                    #QgsMessageLog.logMessage(str(self.rb.getPoint(0, max-2)), 'rb', 0)
                    #QgsMessageLog.logMessage(str(point), 'rb', 0)
                    if not self.pointOnLine(lastRbP, nextToLastRbP, QgsPoint(point)):
                      self.appendPoint(point)
                      self.lastPointMustStay = False
                    else:
                        #TODO: schauen, ob der letzte punkt ein klick war, dann nicht löschen. entsrpechend auch die "punkt auf linie" neu berechenen.
                        if not self.lastPointMustStay:
                          self.rb.removeLastPoint()
                          self.rb.movePoint(point)
                          #QgsMessageLog.logMessage('point removed', 'click', 0)
                    #else:
                      #QgsMessageLog.logMessage('sleep', 'rb', 0)
                else:
                    self.appendPoint(point)
                    self.lastPointMustStay = False
                    self.firstTimeOnSegment = False
  
        else:
           #if nothing specials happens, just update the rubberband to the cursor position
           point =  QgsMapToPixel.toMapCoordinates(self.canvas.getCoordinateTransform (), x, y)
           self.rb.movePoint(point)
  
      else:
        #in "not-tracing" state, just update the rubberband to the cursor position
        #but we have still to snap to act like the "normal" digitize tool
        (retval,result) = self.snapper.snapToBackgroundLayers(eventPoint)
        if result <> []:
            point =QgsPoint(result[0].snappedVertex)
        else:
            point =  QgsMapToPixel.toMapCoordinates(self.canvas.getCoordinateTransform(),  x, y)
        self.rb.movePoint(point)    



  def canvasReleaseEvent(self,event):
    #with right click the digitizing is finished
    if event.button()  == 2:
      
      layer = self.canvas.currentLayer()
      x = event.pos().x()
      y = event.pos().y()
      if layer <> None and self.started == True: 
        selPoint = QPoint(x,y)
        (retval,result) = self.snapper.snapToBackgroundLayers(selPoint)
        
        if result  <> []:
          point = result[0].snappedVertex
        else:
          point =  QgsMapToPixel.toMapCoordinates(self.canvas.getCoordinateTransform(), x, y)
        
        #add this last point
        self.appendPoint(QgsPoint(point))
        self.sendGeometry()
  
   

  def appendPoint(self, point):
    #don't add the point if it is identical to the last point we added
    if not (self.lastPoint ==  point) :      
      self.rb.addPoint(point)
      self.lastPoint = QgsPoint(point)
    else:
      pass
      
      
      
  # see: double QgsGeometryValidator::distLine2Point( QgsPoint p, QgsVector v, QgsPoint q )
  #distance of point q from line through p in direction v
  def pointOnLine(self, pntAft,  pntBef, pntTest):
        p = QgsPoint(pntAft)
        vx = pntBef.x() - pntAft.x()
        vy = pntBef.y() - pntAft.y()
        vlength = math.sqrt(vy*vy+vx*vx)
        if vlength == 0:
            return False
        q = QgsPoint(pntTest)
 
        res =  (vx*( q.y() - p.y() ) - vy*( q.x() - p.x() ) ) / vlength
        #res = 0 means point is on line, but we are not in a perfect world, so a tolerance is needed
        #to get rid of some numerical problems. Tolerance estimated by solid engenieering work (rule of thumb...)
        if res < 1E-10:
            return True
        else:
            return False



  def sendGeometry(self):
    layer = self.canvas.currentLayer() 
    coords = []

    #backward compatiblity for a bug in qgsRubberband, that was fixed in 1.7
    if QGis.QGIS_VERSION_INT >= 10700:
      [coords.append(self.rb.getPoint(0, i)) for i in range(self.rb.numberOfVertices())]
    else:
      [coords.append(self.rb.getPoint(0,i)) for i in range(1,self.rb.numberOfVertices())]
    
    # On the Fly reprojection, not necessary any more, mapToLayerCoordinates is clever enough on its own
    #layerEPSG = layer.srs().epsg()
    #projectEPSG = self.canvas.mapRenderer().destinationSrs().epsg()
    #if layerEPSG != projectEPSG:
    coords_tmp = coords[:]
    coords = []
    for point in coords_tmp:
      transformedPoint = self.canvas.mapRenderer().mapToLayerCoordinates( layer, point );
      coords.append(transformedPoint)
       
    coords_tmp = coords[:]
    coords = []
    lastPt = None
    for pt in coords_tmp:
      if (lastPt <> pt) :
        coords.append(pt)
        lastPt = pt
             
    # Add geometry to feature.
    if self.isPolygon == True:
        g = QgsGeometry().fromPolygon([coords])
    else:
        g = QgsGeometry().fromPolyline(coords)
    
    self.emit(SIGNAL("traceFound(PyQt_PyObject)"),g) 
    self.rb.reset(self.isPolygon)
    self.started = False


  def activate(self):
    self.canvas.setCursor(self.cursor)
  
  def deactivate(self):
    try:
      self.rb.reset()
    except AttributeError:
      pass

  def isZoomTool(self):
    return False
  
  def isTransient(self):
    return False
    
  def isEditTool(self):
    return True
