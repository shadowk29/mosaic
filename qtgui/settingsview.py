import sys
import os
import glob
import json
import types
import multiprocessing

from PyQt4 import QtCore, QtGui, uic
from qtgui.redirectSTDOUT import redirectSTDOUT
import qtgui.EBSStateFileDict
import pyeventanalysis.settings
# import AnalysisSettings
# from qtgui.SettingsWindow import Ui_SettingsWindow
import qtgui.trajview.trajview
import qtgui.advancedsettings.advancedsettings
import qtgui.blockdepthview.blockdepthview
import qtgui.consolelog.consolelog
import qtgui.datamodel

class settingsview(QtGui.QMainWindow):
	def __init__(self, parent = None):
		super(settingsview, self).__init__(parent)

		uic.loadUi(os.path.join(os.path.dirname(os.path.abspath(__file__)),"SettingsWindow.ui"), self)
		# self.setupUi(self)

		self.setMenuBar(self.menubar)
		self._positionWindow()

		self.updateDialogs=False
		self.analysisRunning=False

		# setup handles and data structs for other application windows
		self.trajViewerWindow = qtgui.trajview.trajview.TrajectoryWindow(parent=self)
		self.advancedSettingsDialog = qtgui.advancedsettings.advancedsettings.AdvancedSettingsDialog(parent=self)
		self.consoleLog = qtgui.consolelog.consolelog.AnalysisLogDialog(parent=self)
		self.blockDepthWindow = qtgui.blockdepthview.blockdepthview.BlockDepthWindow(parent=self)
		
		self.showBlockDepthWindow=False
		# redirect stdout and stderr
		# sys.stdout = redirectSTDOUT( edit=self.consoleLog.consoleLogTextEdit, out=sys.stdout, color=QtGui.QColor(0,0,0) )
		# sys.stderr = redirectSTDOUT( edit=self.consoleLog.consoleLogTextEdit, out=sys.stderr, color=QtGui.QColor(255,0,0) )
		# # Always show the console log
		# self.consoleLog.show()
		# self.consoleLog.raise_()

		# Setup and initialize the data model for the settings view
		self.analysisDataModel=qtgui.datamodel.guiDataModel()

		# default settings
		self._updateControls()

		# Connect signals and slots

		# Data settings signals
		QtCore.QObject.connect(self.datPathToolButton, QtCore.SIGNAL('clicked()'), self.OnSelectPath)
		QtCore.QObject.connect(self.datPathLineEdit, QtCore.SIGNAL('textChanged ( const QString & )'), self.OnDataPathChange)
		QtCore.QObject.connect(self.datTypeComboBox, QtCore.SIGNAL('currentIndexChanged(const QString &)'), self.OnDataTypeChange)
		QtCore.QObject.connect(self.dcOffsetDoubleSpinBox, QtCore.SIGNAL('valueChanged ( double )'), self.OnDataOffsetChange)
		QtCore.QObject.connect(self.startIndexLineEdit, QtCore.SIGNAL('textChanged ( const QString & )'), self.OnDataStartIndexChange)

		# Baseline detection signals
		QtCore.QObject.connect(self.baselineAutoCheckBox, QtCore.SIGNAL('clicked(bool)'), self.OnBaselineAutoCheckbox)
		QtCore.QObject.connect(self.baselineBlockSizeDoubleSpinBox, QtCore.SIGNAL('valueChanged ( double )'), self.OnBlockSizeChangeSpinbox)
		QtCore.QObject.connect(self.baselineMeanLineEdit, QtCore.SIGNAL('textChanged ( const QString & )'), self.OnBaselineMeanChange)
		QtCore.QObject.connect(self.baselineSDLineEdit, QtCore.SIGNAL('textChanged ( const QString & )'), self.OnBaselineSDChange)

		# Event partition signals
		QtCore.QObject.connect(self.ThresholdDoubleSpinBox, QtCore.SIGNAL('valueChanged ( double )'), self.OnThresholdChange)
		QtCore.QObject.connect(self.partitionThresholdHorizontalSlider, QtCore.SIGNAL('valueChanged ( int )'), self.OnThresholdChange)

		# Misc signals
		QtCore.QObject.connect(self.advancedModeCheckBox, QtCore.SIGNAL('clicked(bool)'), self.OnAdvancedMode)
		QtCore.QObject.connect(self.writeEventsCheckBox, QtCore.SIGNAL('clicked(bool)'), self.OnWriteEvents)
		QtCore.QObject.connect(self.parallelCheckBox, QtCore.SIGNAL('clicked(bool)'), self.OnParallelProcessing)
		QtCore.QObject.connect(self.parallelCoresSpinBox, QtCore.SIGNAL('valueChanged ( int )'), self.OnParallelProcessing)
		QtCore.QObject.connect(self.processingAlgorithmComboBox, QtCore.SIGNAL('currentIndexChanged(const QString &)'), self.OnProcessingAlgoChange)
		
		# Plots signals
		QtCore.QObject.connect(self.plotBlockDepthHistCheckBox, QtCore.SIGNAL('clicked(bool)'), self.OnPlotBlockDepth)

		# View Menu signals
		QtCore.QObject.connect(self.actionAdvanced_Settings_Mode, QtCore.SIGNAL('triggered()'), self.OnAdvancedModeMenuAction)
		QtCore.QObject.connect(self.actionTrajectory_Viewer, QtCore.SIGNAL('triggered()'), self.OnShowTrajectoryViewer)
		QtCore.QObject.connect(self.actionBlockade_Depth_Histogram, QtCore.SIGNAL('triggered()'), self.OnShowBlockDepthViewer)
		
		
		# Dialog signals and slots
		QtCore.QObject.connect(self.advancedSettingsDialog, QtCore.SIGNAL('rejected()'), self.OnAdvancedModeCancel)
		QtCore.QObject.connect(self.advancedSettingsDialog, QtCore.SIGNAL('accepted()'), self.OnAdvancedModeSave)		


	def _positionWindow(self):
		"""
			Position settings window at the top left corner
		"""
		screen = QtGui.QDesktopWidget().screenGeometry()
		self.move( -screen.width()/2, -screen.height()/2 )

	def _updateControls(self):
		self.updateDialogs=False

		model=self.analysisDataModel

		datidx= { 
					"QDF" : self.datTypeComboBox.findText("QDF"), 
					"ABF" : self.datTypeComboBox.findText("ABF")
				}
		path=model["DataFilesPath"] 
		if len(glob.glob(str(path)+'/*qdf')) > 0:
			self.datTypeComboBox.setCurrentIndex( datidx["QDF"] )
		elif len(glob.glob(str(path)+'/*abf')) > 0:
			self.datTypeComboBox.setCurrentIndex( datidx["ABF"] )

		# store the  data type in the trajviewer data struct
		model["DataFilesType"] = str(self.datTypeComboBox.currentText())

		self.startIndexLineEdit.setText(str(model["start"]))
		self.dcOffsetDoubleSpinBox.setValue(model["dcOffset"])

		if float(model["meanOpenCurr"]) == -1 or float(model["sdOpenCurr"]) == -1:
			self.baselineAutoCheckBox.setChecked(True)
			self.OnBaselineAutoCheckbox(True)			
		else:
			# Populate baseline parameters
			self.baselineAutoCheckBox.setChecked(False)
			self.OnBaselineAutoCheckbox(False)

			self.baselineMeanLineEdit.setText(str(model["meanOpenCurr"]))
			self.baselineSDLineEdit.setText(str(model["sdOpenCurr"]))
			self.baselineBlockSizeDoubleSpinBox.setValue(float(model["blockSizeSec"]))
	
		# Populate EventSegment parameters
		self._setThreshold(float(model["meanOpenCurr"]), float(model["sdOpenCurr"]), float(model["eventThreshold"]))
		
		# Populate misc parameters
		self.writeEventsCheckBox.setChecked(int(model["writeEventTS"]))
		self.parallelCheckBox.setChecked(int(model["parallelProc"]))				
		self.parallelCoresSpinBox.setValue(multiprocessing.cpu_count()-int(model["reserveNCPU"]))

		procidx= {}
		for v in self.analysisDataModel.eventProcessingAlgoKeys.values():
			procidx[v]=self.processingAlgorithmComboBox.findText(v)
		
		self.processingAlgorithmComboBox.setCurrentIndex( procidx[self.analysisDataModel["ProcessingAlgorithm"]] )

		# If an advanced mode dialog exists, update its settings
		if self.advancedSettingsDialog:
			self.advancedSettingsDialog.updateSettingsString(
					model.GenerateSettingsView(
							eventPartitionAlgo=str(self.partitionAlgorithmComboBox.currentText()), 
							eventProcessingAlgo=str(self.processingAlgorithmComboBox.currentText())
						)
				)

		self.updateDialogs=True

	def _loadEBSState(self):
		path=self.analysisDataModel["DataFilesPath"] 

		if path:
			ebsFile=glob.glob(str(path)+'/*_?tate.txt')

			if len(ebsFile) > 0:
				ebsState=qtgui.EBSStateFileDict.EBSStateFileDict(ebsFile[0])
				
				rfb=ebsState.pop('FB Resistance',1.0)
				cfb=ebsState.pop('FB Capacitance',1.0)

				self.qdfRfbLineEdit.setText( str(float(rfb)/1E9) )
				self.qdfCfbLineEdit.setText( str(float(cfb)/1E-12) )

				# More Traj viewer settings
				self.analysisDataModel["Rfb"]=rfb
				self.analysisDataModel["Cfb"]=cfb

	def _setThreshold(self, mean, sd, threshold):
		self.ThresholdDoubleSpinBox.setValue(threshold)

		# [min,max]=[self.ThresholdDoubleSpinBox.minimum(), self.ThresholdDoubleSpinBox.maximum()]
		# [smin,smax]=[self.partitionThresholdHorizontalSlider.minimum(),self.partitionThresholdHorizontalSlider.maximum()]

		# self.ThresholdDoubleSpinBox.setValue( (int((max-min))*threshold/float(smax-smin)) )

		# self.OnThresholdChangeSpinbox(threshold)

	def _setEnableSettingsWidgets(self, state):
		self.baselineGroupBox.setEnabled(state)
		self.eventPartitionGroupBox.setEnabled(state)
		self.writeEventsCheckBox.setEnabled(state)
		self.parallelCheckBox.setEnabled(state)
		self.parallelCoresSpinBox.setEnabled(state)
		self.processingAlgorithmComboBox.setEnabled(state)
		self.advancedModeCheckBox.setEnabled(state)

	def _setEnableDataSettingsWidgets(self, state):
		self.processingAlgorithmComboBox.setEnabled(state)
		self.dataSettingsGroupBox.setEnabled(state)

	def _baselineupdate(self, value):
		if not self.baselineAutoCheckBox.isChecked():
			if value=="meanOpenCurr":
				control=self.baselineMeanLineEdit
			else:
				control=self.baselineSDLineEdit

			try:
				self.analysisDataModel[value] = float(control.text())
				self.analysisDataModel["slopeOpenCurr"]=0.0
			except:
				self.analysisDataModel[value]=-1
				self.analysisDataModel["slopeOpenCurr"]=-1

			self.analysisDataModel["blockSizeSec"]=float(self.baselineBlockSizeDoubleSpinBox.value())
			self.trajViewerWindow.setTrajdata(self.analysisDataModel.GenerateTrajView())

	# SLOTS

	# Data settings SLOTS
	def OnSelectPath(self):
		"""
			Select the data directory. Once a folder is selected, 
			call additional functions to read in settings if they exist.
		"""
		fd=QtGui.QFileDialog()
		
		if self.datPathLineEdit.text() != "":
			fd.setDirectory( self.datPathLineEdit.text() )

		path=fd.getExistingDirectory()
		if path:
			self.datPathLineEdit.setText(path)
			self.OnDataPathChange(path)

	def OnDataPathChange(self, value):
		if self.updateDialogs:
			self.analysisDataModel["DataFilesPath"]=str(value)
			self.analysisDataModel.UpdateDataModelFromSettings()

			self._loadEBSState()
			self._updateControls()

			self.trajViewerWindow.setTrajdata(self.analysisDataModel.GenerateTrajView())
			self.trajViewerWindow.refreshPlot()
			self.blockDepthWindow.hide()
			self.trajViewerWindow.show()

	def OnDataTypeChange(self, item):
		if self.updateDialogs:
			if str(item) == "QDF":
				self.qdfRfbLineEdit.setEnabled(True)
				self.qdfCfbLineEdit.setEnabled(True)

				# If the data type was changed reload the EBS state
				self._loadEBSState()
			else:
				self.qdfRfbLineEdit.setEnabled(False)
				self.qdfCfbLineEdit.setEnabled(False)

			self.analysisDataModel["DataFilesType"]=str(item)

			self.trajViewerWindow.setTrajdata(self.analysisDataModel.GenerateTrajView())
			self.trajViewerWindow.refreshPlot()


	def OnDataOffsetChange(self, item):
		if self.updateDialogs:
			self.analysisDataModel["dcOffset"]=float(item)

			# print self.analysisDataModel["dcOffset"]
			# self.trajViewerWindow.updatePlot(self.analysisDataModel.GenerateTrajView())
			self.trajViewerWindow.setTrajdata(self.analysisDataModel.GenerateTrajView())
			self.trajViewerWindow.refreshPlot()

	def OnDataStartIndexChange(self, item):
		if self.updateDialogs:
			self.analysisDataModel["start"]=int(item)
			
			self.trajViewerWindow.setTrajdata(self.analysisDataModel.GenerateTrajView())
			self.trajViewerWindow.refreshPlot()

	# Baseline detection SLOTS
	def OnBaselineAutoCheckbox(self, value):
		if self.updateDialogs:
			# print value
			if value:
				self.baselineMeanLineEdit.setText("")
				self.baselineSDLineEdit.setText("")

				self.baselineMeanLineEdit.setPlaceholderText("<auto>")
				self.baselineSDLineEdit.setPlaceholderText("<auto>")

				self.analysisDataModel["meanOpenCurr"]=-1
				self.analysisDataModel["sdOpenCurr"]=-1
				self.analysisDataModel["slopeOpenCurr"]=-1

				self.baselineMeanLineEdit.setEnabled(False)
				self.baselineSDLineEdit.setEnabled(False)

				self.analysisDataModel["blockSizeSec"]=float(self.baselineBlockSizeDoubleSpinBox.value())
				self.trajViewerWindow.updatePlot(self.analysisDataModel.GenerateTrajView())
			else:
				self.baselineMeanLineEdit.setPlaceholderText("")
				self.baselineSDLineEdit.setPlaceholderText("")

				self.baselineMeanLineEdit.setEnabled(True)
				self.baselineSDLineEdit.setEnabled(True)

	def OnBlockSizeChangeSpinbox(self, value):
		if self.updateDialogs:
			self.analysisDataModel["blockSizeSec"]=float(value)
			self.trajViewerWindow.setTrajdata(self.analysisDataModel.GenerateTrajView())
			self.trajViewerWindow.refreshPlot()

	def OnBaselineMeanChange(self, value):
		if self.updateDialogs:
			self._baselineupdate("meanOpenCurr")

			self.trajViewerWindow.updatePlot(self.analysisDataModel.GenerateTrajView())

	def OnBaselineSDChange(self, value):
		if self.updateDialogs:
			self._baselineupdate("sdOpenCurr")

			self.trajViewerWindow.updatePlot(self.analysisDataModel.GenerateTrajView())

	# Event partition SLOTS
	def OnThresholdChange(self, value):
		if self.updateDialogs:
			[min,max]=[self.ThresholdDoubleSpinBox.minimum(), self.ThresholdDoubleSpinBox.maximum()]
			[smin,smax]=[self.partitionThresholdHorizontalSlider.minimum(),self.partitionThresholdHorizontalSlider.maximum()]

			# The trajectory window needs the update threshold
			self.analysisDataModel["blockSizeSec"]=self.baselineBlockSizeDoubleSpinBox.value()

			if type(value)==types.FloatType:
				self.analysisDataModel["eventThreshold"]=value
				self.partitionThresholdHorizontalSlider.setValue( (int(smax-smin)*value/float(max-min)) )
			else:
				self.analysisDataModel["eventThreshold"]=float((int((max-min))*value/float(smax-smin)))
				self.ThresholdDoubleSpinBox.setValue( (int((max-min))*value/float(smax-smin)) )

			self.trajViewerWindow.updatePlot(self.analysisDataModel.GenerateTrajView())

	# Misc SLOTS
	def OnWriteEvents(self, value):
		self.analysisDataModel["writeEventTS"]=int(value)

	def OnParallelProcessing(self, value):
		if self.parallelCheckBox.isChecked():
			self.analysisDataModel["parallelProc"]=1
		else:
			self.analysisDataModel["parallelProc"]=0

		self.analysisDataModel["reserveNCPU"]=multiprocessing.cpu_count()-int(self.parallelCoresSpinBox.value())

	def OnAdvancedMode(self, value):
		if value:
			self.advancedSettingsDialog.updateSettingsString(
					self.analysisDataModel.GenerateSettingsView(
						eventPartitionAlgo=str(self.partitionAlgorithmComboBox.currentText()), 
						eventProcessingAlgo=str(self.processingAlgorithmComboBox.currentText())
					)
				)
			self.advancedSettingsDialog.show()
			self._setEnableSettingsWidgets(False)
		else:
			self.advancedSettingsDialog.hide()
			self._setEnableSettingsWidgets(True)

	def OnProcessingAlgoChange(self, value):
		self.analysisDataModel["ProcessingAlgorithm"]=value

	# Plot SLOTS
	def OnPlotBlockDepth(self, value):
		self.showBlockDepthWindow=bool(value)
		if value:
			if self.analysisRunning:
				self.blockDepthWindow.show()
		else:
			self.blockDepthWindow.hide()

	# Menu SLOTs
	def OnAdvancedModeMenuAction(self):
		if self.advancedModeCheckBox.isChecked():
			self.advancedSettingsDialog.show()
		 	self.advancedSettingsDialog.raise_()

	# Dialog SLOTS
	def OnShowTrajectoryViewer(self):
		self.trajViewerWindow.show()

	def OnShowBlockDepthViewer(self):
		self.blockDepthWindow.show()

	def OnAdvancedModeCancel(self):
		self.advancedModeCheckBox.setChecked(False)
		self._setEnableSettingsWidgets(True)

	def OnAdvancedModeSave(self):
		updatesettings=self.analysisDataModel.UpdateDataModelFromSettingsString

		updatesettings(str(self.advancedSettingsDialog.advancedSettingsTextEdit.toPlainText()))
		self._updateControls()
		
		# update trajviewer
		self.trajViewerWindow.setTrajdata(self.analysisDataModel.GenerateTrajView())
		self.trajViewerWindow.refreshPlot()

		self.advancedModeCheckBox.setChecked(False)
		self._setEnableSettingsWidgets(True)

if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)
	dmw = settingsview()
	dmw.show()
	dmw.raise_()
	sys.exit(app.exec_())

