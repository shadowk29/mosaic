from __future__ import with_statement

import numpy as np
import sys
import os
import csv
import glob
import sqlite3

from PyQt4 import QtCore, QtGui, uic

import pyeventanalysis.sqlite3MDIO as sqlite

import matplotlib.ticker as ticker
# from qtgui.trajview.trajviewui import Ui_Dialog

css = """QLabel {
      color: red;
}"""


class BlockDepthWindow(QtGui.QDialog):
	def __init__(self, parent = None):
		self.v=[]

		super(BlockDepthWindow, self).__init__(parent)

		uic.loadUi(os.path.join(os.path.dirname(os.path.abspath(__file__)),"blockdepthview.ui"), self)
		self._positionWindow()

		self.idleTimer=QtCore.QTimer()
		self.idleTimer.start(5000)

		# Set error line edit color to red
		self.errorLabel.setStyleSheet(css)

		self.queryString="select BlockDepth from metadata where ProcessingStatus='normal' and BlockDepth > 0 and BlockDepth < 0.8 and ResTime > 0.1"
		self.queryData=[]
		self.queryError=False
		self.lastGoodQueryString=""

		self.nBins=200
		self.binsSpinBox.setValue(self.nBins)

		QtCore.QObject.connect(self.updateButton, QtCore.SIGNAL('clicked()'), self.OnUpdateButton)
		QtCore.QObject.connect(self.sqlQueryLineEdit, QtCore.SIGNAL('textChanged ( const QString & )'), self.OnQueryTextChange)
		QtCore.QObject.connect(self.binsSpinBox, QtCore.SIGNAL('valueChanged ( int )'), self.OnBinsChange)
		

	def openDB(self, dbpath):
		self.queryDatabase=sqlite.sqlite3MDIO()
		self.queryDatabase.openDB(glob.glob(dbpath+"/*sqlite")[-1])

		# Idle processing
		QtCore.QObject.connect(self.idleTimer, QtCore.SIGNAL('timeout()'), self.OnAppIdle)

	def _positionWindow(self):
		"""
			Position settings window at the top left corner
		"""
		screen = QtGui.QDesktopWidget().screenGeometry()
		self.setGeometry(405, 0, 500, 350)
		# self.move( (-screen.width()/2)+200, -screen.height()/2 )


	def refreshPlot(self):
		try:
			self.dataLoaded=True

			# self.mpl_hist.canvas.ax.set_autoscale_on(True)
			self.update_graph()
		except AttributeError:
			QtGui.QMessageBox.warning(self, "Path Error","Data path not set")
			raise
		except FileNotFoundError:
			QtGui.QMessageBox.warning(self, "Data Error","Files not found")
		except:
			raise

	def update_graph(self):
		try:
			# c='#%02x%02x%02x' % (72,91,144)
			n, bins, patches = self.mpl_hist.canvas.ax.hist( 
						self.queryData, 
						bins=self.nBins, 
						normed=1, 
						facecolor='green', 
						alpha=0.5
					)
			self.mpl_hist.canvas.ax.set_xlabel('<i>/<i0>', fontsize=10)
			self.mpl_hist.canvas.ax.set_ylabel('density', fontsize=10)
			
			self.mpl_hist.canvas.draw()
		except:
			raise

	def _ticks(self, nticks):
		axes=self.mpl_hist.canvas.ax

		start, end = axes.get_xlim()
		dx=(end-start)/(nticks-1)
		axes.xaxis.set_ticks( np.arange( start, end+dx, dx ) )
		axes.xaxis.set_major_formatter(ticker.FormatStrFormatter('%0.2f'))

		start, end = axes.get_ylim()
		dy=(end-start)/(nticks-1)
		axes.yaxis.set_ticks( np.arange( start, end+dy, dy ) ) 
		axes.yaxis.set_major_formatter(ticker.FormatStrFormatter('%d'))

	def _updatequery(self):
		try:
			self.queryData=np.array(self.queryDatabase.queryDB(self.queryString)).flatten()
	
			if not self.queryError:
				self.errorLabel.setText("")

			self.lastGoodQueryString=self.queryString

			self.update_graph()
		except sqlite3.OperationalError, err:
			self.errorLabel.setText(str(err))
			self.queryString=self.lastGoodQueryString
			self.queryError=True

	def OnQueryTextChange(self, text):
		qtext=str(text)
		if qtext:
			self.updateButton.setEnabled(True)			
		else:
			self.updateButton.setEnabled(False)

	def OnUpdateButton(self):
		qtext=str(self.sqlQueryLineEdit.text())
		if qtext:
			self.queryString="select BlockDepth from metadata where ProcessingStatus='normal' and BlockDepth > 0 and " + qtext
			self.queryError=False

			self._updatequery()

	def OnBinsChange(self, value):
		self.nBins=int(value)

	def OnAppIdle(self):
		self._updatequery()

if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)
	dmw = BlockDepthWindow()
	dmw.openDB('/Users/arvind/Desktop/POM ph5.45 m120_6')
	dmw.show()
	dmw.raise_()
	sys.exit(app.exec_())
