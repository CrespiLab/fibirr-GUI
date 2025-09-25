# -*- coding: utf-8 -*-

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import globals

class Plot(QWidget):
    points = QPolygonF(4096)
    def __init__(self, parent=None):
        super(Plot, self).__init__(parent)
        self.setBackgroundRole(QPalette.Base)
        self.setAutoFillBackground(True)
        return

    def paintEvent(self, event):
        painter = QPainter(self)
        self.points.clear()
        x = 0
        while (x < globals.pixels):   # 0 through 2047
           self.points.append(QPointF(float(x), float(67000.0 - globals.spectraldata[x]))) 
           x += 1
        painter.scale(self.width()/globals.pixels, self.height()/67000.0)
        # height is a little over 65536, to show saturation in top of screen
        pen = QPen(Qt.blue, 2)
        pen.setCosmetic(True) # line width must be independent of scale
        painter.setPen(pen)
        painter.drawPolyline(self.points)
        pen = QPen(Qt.black, 1)
        pen.setCosmetic(True) # line width must be independent of scale
        painter.setPen(pen)
        painter.drawRect(0, 0, globals.pixels - 1, 66999) 
        return

    def update_plot(self):
        self.update()
