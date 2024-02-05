################################################################################
##
# Utpal Kumar
# @Earth Inversion
################################################################################

import sys
import platform
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import (QCoreApplication, QPropertyAnimation, QDate, QDateTime,
                          QMetaObject, QObject, QPoint, QRect, QSize, QTime, QUrl, Qt, QEvent)
from PyQt5.QtGui import (QBrush, QColor, QConicalGradient, QCursor, QFont, QFontDatabase,
                         QIcon, QKeySequence, QLinearGradient, QPalette, QPainter, QPixmap, QRadialGradient)
from PyQt5.QtWidgets import *
from PyQt5 import uic
import psutil
from pyqtgraph import PlotWidget
import pyqtgraph as pg
from pathlib import Path
import numpy as np
from collections import deque
import threading

import time
import ast
import signal
# application specific imports
import simply_can
from simply_can import Message


# GLOBALS
counter = 0
jumper = 10
PVoltage, PCurrent, BVoltage, BCurrent = 0, 0, 0, 0
Status = 'Unknown'
CurrentMonitored = "Panneaux"
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True) #enable highdpi scaling
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True) #use highdpi icons

class MainWindow(QMainWindow): # Main Window Class for the GUI
    def __init__(self): # Constructor
        QMainWindow.__init__(self) # Call the super class constructor
        # self.ui = Ui_MainWindow()
        # self.ui.setupUi(self)
        self.ui = uic.loadUi("main.ui", self) # Load the UI file
        self.cpu_percent = 0 # CPU percentage variable initialization (= Courant)
        self.ram_percent = 0 # RAM percentage variable initialization (= Tension)
        self.traces = dict() # Dictionary to store the traces
        self.timestamp = 0 # Timestamp initialization
        self.timeaxis = [] # Time axis initialization
        self.cpuaxis = [] # Current axis initialization
        self.ramaxis = [] # Voltage axis initialization
        # self.csv_file = open(datafile, 'w')
        # self.csv_writer = csv.writer(self.csv_file, delimiter=',')
        self.current_timer_graph = None
        self.graph_lim = 15
        self.deque_timestamp = deque([], maxlen=self.graph_lim+20) # Panneaux
        self.deque_timestamp2 = deque([], maxlen=self.graph_lim+20) # Batterie

        self.deque_cpu = deque([], maxlen=self.graph_lim+20) # Panneaux
        self.deque_ram = deque([], maxlen=self.graph_lim+20) # Panneaux

        self.deque_cpu2 = deque([], maxlen=self.graph_lim+20) # Batterie
        self.deque_ram2 = deque([], maxlen=self.graph_lim+20) # Batterie

        self.graphwidget1 = PlotWidget(title="Evolution du Courant") #Panneaux Courant
        x1_axis = self.graphwidget1.getAxis('bottom') # x axis
        x1_axis.setLabel(text='Temps écoulé depuis le début (s)') # Label for the x axis
        y1_axis = self.graphwidget1.getAxis('left') # y axis
        y1_axis.setLabel(text='Ampere (A)') # Label for the y axis

        self.graphwidget2 = PlotWidget(title="Evolution de la Tension") # Panneaux Tension
        x2_axis = self.graphwidget2.getAxis('bottom') # x axis
        x2_axis.setLabel(text='Temps écoulé depuis le début (s)') # Label for the x axis
        y2_axis = self.graphwidget2.getAxis('left') # y axis
        y2_axis.setLabel(text='Tension (V)') # Label for the y axis

        self.graphwidget3 = PlotWidget(title="Evolution du Courant") # Batterie Courant
        x1_axis = self.graphwidget3.getAxis('bottom') # x axis
        x1_axis.setLabel(text='Temps écoulé depuis le début (s)') # Label for the x axis
        y1_axis = self.graphwidget3.getAxis('left') # y axis 
        y1_axis.setLabel(text='Ampere (A)') # Label for the y axis

        self.graphwidget4 = PlotWidget(title="Evolution de la Tension") # Batterie Tension
        x2_axis = self.graphwidget4.getAxis('bottom') # x axis
        x2_axis.setLabel(text='Temps écoulé depuis le début (s)') # Label for the x axis
        y2_axis = self.graphwidget4.getAxis('left') # y axis
        y2_axis.setLabel(text='Tension (V)') # Label for the y axis

        self.pushButton.clicked.connect(self.show_cpu_graph) # Connect the button to switch graph to the current to the function
        self.pushButton_2.clicked.connect(self.show_ram_graph) # Connect the button to switch graph to voltage to the function
        self.pushButton_3.clicked.connect(self.changeSource) # Connect the button to change source (solar panel or battery) to the function
        self.ui.gridLayout.addWidget(self.graphwidget1, 0, 0, 1, 3) # Add the graph to the grid layout
        self.ui.gridLayout.addWidget(self.graphwidget2, 0, 0, 1, 3)
        self.ui.gridLayout.addWidget(self.graphwidget3, 0, 0, 1, 3)
        self.ui.gridLayout.addWidget(self.graphwidget4, 0, 0, 1, 3)

        self.current_timer_systemStat = QtCore.QTimer() # Timer to update the CPU and RAM percentage
        self.current_timer_systemStat.timeout.connect( 
            self.getsystemStatpercent) # Connect the timer to the function
        self.current_timer_systemStat.start(1000) # Start the timer w ith an interval of 1 second
        self.show_cpu_graph() # Show the CPU (Current) graph by default

    def getsystemStatpercent(self):  # Function to get the CPU and RAM percentage
        # gives a single float value
        global CurrentMonitored # Global variable to retrieve the source (solar panel or battery)
        if (CurrentMonitored == "Panneaux"): # If the source is the solar panel
            self.cpu_percent = PCurrent # Courant
            self.ram_percent = PVoltage # Tension
        else:
            self.cpu_percent = BCurrent
            self.ram_percent = BVoltage
        self.ui.label_2.setText(
            f"Status: {Status}")
        if (CurrentMonitored == "Panneaux"):
            self.ui.label.setText(
                f"Cible : Panneaux solaires")
        else:    
            self.ui.label.setText(
                f"Cible : Batterie")
        self.setValue(self.cpu_percent, self.ui.labelPercentageCPU,
                      self.ui.circularProgressCPU, "rgba(85, 170, 255, 255)")
        self.setValue(self.ram_percent, self.ui.labelPercentageRAM,
                      self.ui.circularProgressRAM, "rgba(255, 0, 127, 255)")

    def start_cpu_graph(self): # Start the timer to update the CPU graph
        # self.timeaxis = []
        # self.cpuaxis = []
        if self.current_timer_graph:
            self.current_timer_graph.stop()
            self.current_timer_graph.deleteLater()
            self.current_timer_graph = None
        self.current_timer_graph = QtCore.QTimer()
        self.current_timer_graph.timeout.connect(self.update_cpu)
        self.current_timer_graph.start(1000)

    def update_cpu(self): # Courant
        global CurrentMonitored # Global variable to retrieve the source (solar panel or battery)
        if (CurrentMonitored == "Panneaux"): # If the source is the solar panel
            self.timestamp += 1

            self.deque_timestamp.append(self.timestamp) # Add the timestamp to the deque
            self.deque_cpu.append(self.cpu_percent) # Add the CPU percentage to the deque
            self.deque_ram.append(self.ram_percent) # Add the RAM percentage to the deque 
            timeaxis_list = list(self.deque_timestamp)  # Convert the deque to a list
            cpu_list = list(self.deque_cpu) # Convert the deque to a list

            if self.timestamp > self.graph_lim: # If the timestamp is greater than the graph limit
                self.graphwidget1.setRange(xRange=[self.timestamp-self.graph_lim+1, self.timestamp], yRange=[
                                        min(cpu_list[-self.graph_lim:]), max(cpu_list[-self.graph_lim:])]) # Set the range of the graph
            self.set_plotdata(name="cpu", data_x=timeaxis_list,
                            data_y=cpu_list) # Set the plot data
        else: 
            self.timestamp += 1 # Add 1 to the timestamp

            self.deque_timestamp2.append(self.timestamp) # Add the timestamp to the deque
            self.deque_cpu2.append(self.cpu_percent) # Add the CPU percentage to the deque
            self.deque_ram2.append(self.ram_percent) # Add the RAM percentage to the deque
            timeaxis_list = list(self.deque_timestamp2) # Convert the deque to a list
            cpu_list = list(self.deque_cpu2) # Convert the deque to a list
 
            if self.timestamp > self.graph_lim: 
                self.graphwidget3.setRange(xRange=[self.timestamp-self.graph_lim+1, self.timestamp], yRange=[
                                        min(cpu_list[-self.graph_lim:]), max(cpu_list[-self.graph_lim:])])
            self.set_plotdata(name="cpu2", data_x=timeaxis_list,
                            data_y=cpu_list)

    def start_ram_graph(self): # Start the timer to update the RAM graph

        if self.current_timer_graph:
            self.current_timer_graph.stop()
            self.current_timer_graph.deleteLater()
            self.current_timer_graph = None
        self.current_timer_graph = QtCore.QTimer()
        self.current_timer_graph.timeout.connect(self.update_ram)
        self.current_timer_graph.start(1000)

    def update_ram(self): # Same as update_cpu but for the voltage
        global CurrentMonitored # Global variable to retrieve the source (solar panel or battery)
        if (CurrentMonitored == "Panneaux"): 
            self.timestamp += 1

            self.deque_timestamp.append(self.timestamp) # Add the timestamp to the deque
            self.deque_cpu.append(self.cpu_percent)
            self.deque_ram.append(self.ram_percent)
            timeaxis_list = list(self.deque_timestamp)
            ram_list = list(self.deque_ram)

            if self.timestamp > self.graph_lim: 
                self.graphwidget2.setRange(xRange=[self.timestamp-self.graph_lim+1, self.timestamp], yRange=[
                                        min(ram_list[-self.graph_lim:]), max(ram_list[-self.graph_lim:])])
            self.set_plotdata(name="ram", data_x=timeaxis_list,
                            data_y=ram_list)
        else:
            self.timestamp += 1

            self.deque_timestamp2.append(self.timestamp)
            self.deque_cpu2.append(self.cpu_percent)
            self.deque_ram2.append(self.ram_percent)
            timeaxis_list = list(self.deque_timestamp2)
            ram_list = list(self.deque_ram2)

            if self.timestamp > self.graph_lim:
                self.graphwidget4.setRange(xRange=[self.timestamp-self.graph_lim+1, self.timestamp], yRange=[
                                        min(ram_list[-self.graph_lim:]), max(ram_list[-self.graph_lim:])])
            self.set_plotdata(name="ram2", data_x=timeaxis_list,
                            data_y=ram_list)

    def show_cpu_graph(self): # Show the CPU graph
        global CurrentMonitored
        if (CurrentMonitored == "Panneaux"):
            self.graphwidget2.hide()
            self.graphwidget1.show()
        else:
            self.graphwidget4.hide()
            self.graphwidget3.show()
        self.start_cpu_graph()
        self.pushButton.setEnabled(False)
        self.pushButton_2.setEnabled(True)
        self.pushButton.setStyleSheet(
            "QPushButton" "{" "background-color : lightblue;" "}"
        )
        self.pushButton_2.setStyleSheet(
            "QPushButton"
            "{"
            "background-color : rgb(255, 44, 174);"
            "}"
            "QPushButton"
            "{"
            "color : white;"
            "}"
        )

    def show_ram_graph(self):
        global CurrentMonitored
        if (CurrentMonitored == "Panneaux"):
            self.graphwidget1.hide()
            self.graphwidget2.show()
        else:
            self.graphwidget3.hide()
            self.graphwidget4.show()
        # self.graphwidget2.autoRange()
        self.start_ram_graph()
        self.pushButton_2.setEnabled(False)
        self.pushButton.setEnabled(True)
        self.pushButton_2.setStyleSheet(
            "QPushButton" "{" "background-color : lightblue;" "}"
        )
        self.pushButton.setStyleSheet(
            "QPushButton"
            "{"
            "background-color : rgba(85, 170, 255, 255);"
            "}"
            "QPushButton"
            "{"
            "color : white;"
            "}"
        )

    def changeSource(self): # Change the source of the graph (solar panel or battery)
        global CurrentMonitored
        if (CurrentMonitored == "Panneaux"):
            self.graphwidget1.hide()
            self.graphwidget2.hide()
            self.graphwidget3.show()
            self.graphwidget4.hide()
            CurrentMonitored = "Batterie"
            self.ui.label.setText(
                f"Cible : Batterie")
        else:
            self.graphwidget1.show()
            self.graphwidget2.hide()
            self.graphwidget3.hide()
            self.graphwidget4.hide()    
            CurrentMonitored = "Panneaux"
            self.ui.label.setText(
                f"Cible : Panneaux solaires")

    def set_plotdata(self, name, data_x, data_y): # Set the data of the graph
        # print('set_data')
        if name in self.traces: # If the graph already exists, update it
            #print(data_x, data_y)
            self.traces[name].setData(data_x, data_y)
        else:
            if name == "cpu": # If the graph doesn't exist, create it
                self.traces[name] = self.graphwidget1.getPlotItem().plot(
                    pen=pg.mkPen((85, 170, 255), width=3))

            elif name == "ram":
                self.traces[name] = self.graphwidget2.getPlotItem().plot(
                    pen=pg.mkPen((255, 0, 127), width=3))
                
            if name == "cpu2":
                self.traces[name] = self.graphwidget3.getPlotItem().plot(
                    pen=pg.mkPen((85, 170, 255), width=3))

            elif name == "ram2":
                self.traces[name] = self.graphwidget4.getPlotItem().plot(
                    pen=pg.mkPen((255, 0, 127), width=3))

    # ==> SET VALUES TO DEF progressBarValue

    def setValue(self, value, labelPercentage, progressBarName, color): # Set the value of the progress bar (arround the voltage and current)

        sliderValue = value

        # HTML TEXT PERCENTAGE
        if (color == "rgba(255, 0, 127, 255)"): # Tension
            htmlText = """<p align="center"><span style=" font-size:40pt;">{VALUE}</span><span style=" font-size:40pt; vertical-align:super;">V</span></p>"""
        else: # Intensité
            htmlText = """<p align="center"><span style=" font-size:40pt;">{VALUE}</span><span style=" font-size:40pt; vertical-align:super;">A</span></p>"""
        labelPercentage.setText(htmlText.replace(
            "{VALUE}", f"{sliderValue:.1f}"))

        if (CurrentMonitored == "Panneaux"):
            # CALL DEF progressBarValue
            if (color == "rgba(255, 0, 127, 255)"): # Tension
                sliderValue = sliderValue / 12
            else:
                sliderValue = sliderValue * 10
        else: # Batterie
            if (color == "rgba(255, 0, 127, 255)"):
                sliderValue = sliderValue * 3.44
            else:
                sliderValue = sliderValue
        self.progressBarValue(sliderValue, progressBarName, color)

    # DEF PROGRESS BAR VALUE
    ########################################################################

    def progressBarValue(self, value, widget, color): # Set the value of the progress bar (arround the voltage and current)

        # PROGRESSBAR STYLESHEET BASE
        styleSheet = """
        QFrame{
        	border-radius: 110px;
        	background-color: qconicalgradient(cx:0.5, cy:0.5, angle:90, stop:{STOP_1} rgba(255, 0, 127, 0), stop:{STOP_2} {COLOR});
        }
        """

        # GET PROGRESS BAR VALUE, CONVERT TO FLOAT AND INVERT VALUES
        # stop works of 1.000 to 0.000
        progress = (100 - value) / 100.0

        # GET NEW VALUES
        stop_1 = str(progress - 0.001)
        stop_2 = str(progress)

        # FIX MAX VALUE
        if value == 100:
            stop_1 = "1.000"
            stop_2 = "1.000"

        # SET VALUES TO NEW STYLESHEET
        newStylesheet = styleSheet.replace("{STOP_1}", stop_1).replace(
            "{STOP_2}", stop_2).replace("{COLOR}", color)

        # APPLY STYLESHEET WITH NEW VALUES
        widget.setStyleSheet(newStylesheet)


# ==> SPLASHSCREEN WINDOW
class SplashScreen(QMainWindow): # Loading screen
    def __init__(self):
        QMainWindow.__init__(self)
        # self.ui = Ui_SplashScreen()
        # self.ui.setupUi(self)
        self.ui = uic.loadUi("splash_screen.ui", self)
        # ==> SET INITIAL PROGRESS BAR TO (0) ZERO
        self.progressBarValue(0)

        # ==> REMOVE STANDARD TITLE BAR
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)  # Remove title bar
        # Set background to transparent
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # ==> APPLY DROP SHADOW EFFECT
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(0)
        self.shadow.setColor(QColor(0, 0, 0, 120))
        self.ui.circularBg.setGraphicsEffect(self.shadow)

        # QTIMER ==> START
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.progress)
        # TIMER IN MILLISECONDS
        self.timer.start(15)

        # SHOW ==> MAIN WINDOW
        ########################################################################
        self.show()
        ## ==> END ##

    # DEF TO LOANDING
    ########################################################################
    def progress(self):
        global counter
        global jumper
        value = counter

        # HTML TEXT PERCENTAGE
        htmlText = """<p><span style=" font-size:68pt;">{VALUE}</span><span style=" font-size:58pt; vertical-align:super;">%</span></p>"""

        # REPLACE VALUE
        newHtml = htmlText.replace("{VALUE}", str(jumper))

        if(value > jumper):
            # APPLY NEW PERCENTAGE TEXT
            self.ui.labelPercentage.setText(newHtml)
            jumper += 10

        # SET VALUE TO PROGRESS BAR
        # fix max value error if > than 100
        if value >= 100:
            value = 1.000
        self.progressBarValue(value)
        if counter == 10:
            self.main = MainWindow()

        # CLOSE SPLASH SCREE AND OPEN APP
        if counter > 100:
            # STOP TIMER
            self.timer.stop()

            # SHOW MAIN WINDOW
            # self.main = MainWindow()
            self.main.show()

            # CLOSE SPLASH SCREEN
            self.close()

        # INCREASE COUNTER
        counter += 0.5

    # DEF PROGRESS BAR VALUE
    ########################################################################
    def progressBarValue(self, value):

        # PROGRESSBAR STYLESHEET BASE
        styleSheet = """
        QFrame{
        	border-radius: 150px;
        	background-color: qconicalgradient(cx:0.5, cy:0.5, angle:90, stop:{STOP_1} rgba(255, 0, 127, 0), stop:{STOP_2} rgba(85, 170, 255, 255));
        }
        """

        # GET PROGRESS BAR VALUE, CONVERT TO FLOAT AND INVERT VALUES
        # stop works of 1.000 to 0.000
        progress = (100 - value) / 100.0

        # GET NEW VALUES
        stop_1 = str(progress - 0.001)
        stop_2 = str(progress)

        # SET VALUES TO NEW STYLESHEET
        newStylesheet = styleSheet.replace(
            "{STOP_1}", stop_1).replace("{STOP_2}", stop_2)

        # APPLY STYLESHEET WITH NEW VALUES
        self.ui.circularProgress.setStyleSheet(newStylesheet)




#### ------------------ END OF GUI CODE ------------------ ####
# The following code focuses on retrieving information from the CAN BUS to update our GUI. 

SimplyObj = None

def error(simply):
    err = simply.get_last_error()
    print("Error:", simply.get_error_string(err))
    simply.close()
    sys.exit(-1)
    
def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    if SimplyObj:
    	SimplyObj.close()
    sys.exit(0)
    
def receive_messages(simply): # Function to receive messages from the CAN bus
    global PCurrent, PVoltage, BCurrent, BVoltage, Status
    res, msg = simply.receive() 
    if res == 1:
        # separate msg into a list seperated by spaces
        #print(msg)
        msg_list = str(msg).split(" ")
        #print(msg_list)
        id = msg_list[1]
        if id == '0x19F21224': # Battery informations, unused here but could be implemeted so the code is kept
            return
            Sequence_ID = msg_list[3][0]
            DC_Instance = msg_list[3][1]

            #print(msg_list)
            print("Battery informations : ", end='')
            # Convert the data from 
            data = 16^3 * ast.literal_eval('0x' + msg_list[4][0]) + 16^2* ast.literal_eval('0x' + msg_list[4][1]) + ast.literal_eval('0x' + msg_list[3][0]) * 16^1 + ast.literal_eval('0x' + msg_list[3][1]) * 16^0
            print(msg_list)
        elif id == '0x19F21424':
            #print(msg_list)
            voltage = 16**3 * ast.literal_eval('0x' + msg_list[5][0]) + 16**2 * ast.literal_eval('0x' + msg_list[5][1]) + ast.literal_eval('0x' + msg_list[4][0]) * 16**1 + ast.literal_eval('0x' + msg_list[4][1]) * 16**0
            voltage = voltage / 100
            current = 16**3 * ast.literal_eval('0x' + msg_list[7][0]) + 16**2 * ast.literal_eval('0x' + msg_list[7][1]) + ast.literal_eval('0x' + msg_list[6][0]) * 16**1 + ast.literal_eval('0x' + msg_list[6][1]) * 16**0
            current = current / 10
            if (msg_list[3][1] == '1'): # Solar cell
                print("Stats Panneau : ", end='')
                PVoltage = voltage
                PCurrent = current
            elif (msg_list[3][1] == '0'): # Battery
                print("Stats Batterie : ", end='')
                BVoltage = voltage
                BCurrent = current
            print("Tension : ", round(voltage,2), "V", end=' ')
            print("Courant : ", round(current,2), "A", end = ' ')
            print("Puissance : ", round(voltage * current,2), "W")
        elif id == '0x19F30624':
            #print(msg_list)
            print("Phase de charge : ", end='')
            match msg_list[5][1]:
                case '3':
                    Status = "Bulk"
                case '4':
                    Status = "Absorption"
                case '5':
                    Status = "Floating"
                case '6':
                    Status = "Storage"
                case '7':
                    Status = "Equalization"
                case '8':
                    Status = "Pass-through"
                case '9':
                    Status = "Inverter"
                case 'A':
                    Status = "Assistance"
                case _:
                    Status = "Unknown"
            print(Status)
        return True
    
    elif res == -1:
        error()
    return False
    
def send_message(simply, msg):
    simply.send(msg)
    simply.flush_tx_fifo()
    msg.ident = (msg.ident + 1) % 0x3FF

def main2(ser_port, baudrate):
    global SimplyObj
    print("\n#### simplyCAN Demo 2.0 (c) 2018-2022 HMS ####\n")

    # abort with Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    simply = simply_can.SimplyCAN()
    SimplyObj = simply
    if not simply.open(ser_port): error(simply)
    
    id = simply.identify()
    if not id: error(simply)
        
    print("Firmware version:", id.fw_version.decode("utf-8"))
    print("Hardware version:", id.hw_version.decode("utf-8"))
    print("Product version: ", id.product_version.decode("utf-8"))
    print("Product string:  ", id.product_string.decode("utf-8"))
    print("Serial number:   ", id.serial_number.decode("utf-8"))

    res = simply.stop_can()  # to be on the safer side
    res &= simply.initialize_can(baudrate)
    res &= simply.start_can()
    if not res: error(simply)

    lastSent = 0
    TxMsg = Message(0x100, [1,2,3,4,5,6,7,8])
    print("Run application...")
    while True:
        if time.time() - lastSent > 1.0:  # one message every second
            lastSent = time.time()
            send_message(simply, TxMsg)
            #print("CAN Status:", simply.can_status())
        if not receive_messages(simply):
            time.sleep(0.01)

# main("/dev/ttyACM0", 250)    # for Linux


def main1():
    app = QApplication(sys.argv)
    window = SplashScreen()
    sys.exit(app.exec_())

main11 = threading.Thread(target=main1)
main11.start()

main2("COM4", 250)  # for Windows