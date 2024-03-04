import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QComboBox, QFormLayout, QSpinBox, QGridLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap

# from ultralytics import YOLO

# menu state

import time

import cv2

# from picamera2 import Picamera2
# from libcamera import Transform
# from DFRobot_LTR390UV import *

ADDRESS = 0x1c 
I2C_screen = 0x05
I2C_back = 0x04

# screenUV = DFRobot_LTR390UV_New(I2C_screen, ADDRESS)
# backUV = DFRobot_LTR390UV_New(I2C_back, ADDRESS)

class DetectorApp(QMainWindow):

    def __init__(self):
        super().__init__()
        
        # Globals 
        # self.camera = Picamera2()
        # self.camera.configure(self.camera.create_preview_configuration(main={"format": 'BGR888', "size": (640, 480)}, transform=Transform(180)))
        
        # model
        # model = YOLO("yolov8n.pt")

        # object classes
        classNames = ["sunscreen", "no sunscreen"]
        
        self.timer = QTimer(self)
        self.timerConnected = None


        self.state = "setup"

        self.uvi = 0
        self.screenUV_uvData_max = 0
        self.backUV_uvData_max = 0

        self.skinType = 0

        self.setWindowTitle("Image Collector")
        self.setFixedSize(480, 750)

        # Set a high-contrast color scheme using stylesheets
        self.setStyleSheet("""
            QMainWindow {
                background-color: black;
                color: white;
                font-size: 18px;
            }
            QPushButton {
                border-radius: 5px;
                padding: 20px;
                margin: 5px;
                margin-bottom: 15px;
                font-size: 18px;
            }
            QPushButton#startButton {
                background-color: #2ecc71; /* Green color for start */
                color: white;
                border: 1px solid #2ecc71;
                font-size: 18px;
            }
            QPushButton#stopButton {
                background-color: #e74c3c; /* Red color for stop */
                color: white;
                border: 1px solid #e74c3c;
                font-size: 18px;
            }
            QPushButton#cancelButton {
                background-color: #e74c3c; /* Red color for stop */
                color: white;
                border: 1px solid #e74c3c;
                font-size: 18px;
            }
            QPushButton#UVIButton {
                background-color: #fcba03; /* Red color for stop */
                color: white;
                border: 1px solid #fcba03;
                font-size: 18px;
            }
            QPushButton#skinTypeButton {
                background-color: #e709eb; /* Red color for stop */
                color: white;
                border: 1px solid #e709eb;
                font-size: 18px;
            }
            QPushButton#burnTimeButton {
                background-color: #e74c3c; /* Red color for stop */
                color: white;
                border: 1px solid #e74c3c;
                font-size: 18px;
            }
            QPushButton#sunscreenAssessmentButton {
                background-color: #67e04f; /* Red color for stop */
                color: white;
                border: 1px solid #67e04f;
                font-size: 18px;
            }
            QLabel {
                color: white;
                font-size: 18px;
            }
            QSpinBox, QComboBox {
                background-color: #3498db; /* Blue color */
                color: white;
                padding: 10px;
                margin: 5px;
                border-radius: 5px;
                font-size: 18px;
            }
            QSpinBox:up-button, QSpinBox:down-button{
                width: 40;
            }
            QComboBox QAbstractItemView {
                background-color: #3498db; /* Blue color */
                selection-background-color: #2980b9;
            }
        """)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Preview Text
        self.topText = QLabel(self)
        self.topText.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.topText.setStyleSheet("font-size: 18px;")

        # Image Preview
        self.imagePreview = QLabel(self)
        self.imagePreview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Sensor Values Group
        self.skinSensorLabel = QLabel(self)
        self.skinSensorLabel.setAlignment(Qt.AlignmentFlag.AlignJustify)

        self.screenSensorLabel = QLabel(self)
        self.screenSensorLabel.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.sensorValues = QGridLayout()
        self.sensorValues.addWidget(self.skinSensorLabel, 0, 0)
        self.sensorValues.addWidget(self.screenSensorLabel, 0, 1)

        # UVI Inputs
        self.uviLabel = QLabel("UV Index:", self)
        self.uviBox = QSpinBox(self)
        self.uviBox.setRange(0, 12)

        self.uviButton = QPushButton("Measure UVI", self)
        self.uviButton.setObjectName("UVIButton")  
        self.uviButton.clicked.connect(self.setUVI)

        self.uviButtonGroup = QFormLayout()
        self.uviButtonGroup.addRow(self.uviLabel, self.uviBox)
        self.uviButtonGroup.addRow(self.uviButton)

        # Skin Type Inputs
        self.skinTypeLabel = QLabel("Skin Type:", self)
        self.skinTypeBox = QSpinBox(self) 
        self.skinTypeBox.setRange(0, 6)

        self.skinTypeButton = QPushButton("Measure Skin Type", self)
        self.skinTypeButton.setObjectName("skinTypeButton")  
        self.skinTypeButton.clicked.connect(self.setSkinType)
        
        self.skinTypeButtonGroup = QFormLayout()
        self.skinTypeButtonGroup.addRow(self.skinTypeLabel, self.skinTypeBox)
        self.skinTypeButtonGroup.addRow(self.skinTypeButton)

        # Erythema Time Calculation
        self.spfLabel = QLabel("Sunscreen SPF:", self)
        self.spfBox = QSpinBox(self) 
        self.spfBox.setRange(0, 6)

        self.spfButtonGroup = QFormLayout()
        self.spfButtonGroup.addRow(self.spfLabel, self.spfBox)
        self.spfButtonGroup.addRow(self.spfBox)

        self.burnTimeText = QLabel(self)
        self.burnTimeText.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.burnTimeText.setStyleSheet("font-size: 18px;")
        self.burnTimeText.setText("Estimated Burn Time:\nNA")

        self.burnTimeButton = QPushButton("Estimate Burn Time", self)
        self.burnTimeButton.setObjectName("burnTimeButton")  
        self.burnTimeButton.clicked.connect(self.estimateErythemaTime)

        # Sunscreen Assessment
        self.sunscreenAssessmentButton = QPushButton("Sunscreen Assessment", self)
        self.sunscreenAssessmentButton.setObjectName("sunscreenAssessmentButton")  
        self.sunscreenAssessmentButton.clicked.connect(self.setSunscreenAssessment)

        # Capture Button
        self.startStopButton = QPushButton("Start Capture", self)
        self.startStopButton.setObjectName("startButton")  
        self.startStopButton.clicked.connect(self.startCapture)
        self.startStopButton.hide()

        # Cancel Button
        self.cancelButton = QPushButton("Cancel Capture", self) 
        self.cancelButton.setObjectName("cancelButton")  
        self.cancelButton.clicked.connect(self.initialiseSetup)
        self.cancelButton.hide()

        # UI Layout
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.addLayout(self.uviButtonGroup)
        self.layout.addLayout(self.skinTypeButtonGroup)
        self.layout.addLayout(self.sButtonGroup)
        self.layout.addWidget(self.burnTimeText)
        self.layout.addWidget(self.burnTimeButton)
        self.layout.addWidget(self.sunscreenAssessmentButton)
        self.layout.addWidget(self.topText)
        self.layout.addWidget(self.imagePreview)
        self.layout.addLayout(self.sensorValues)
        self.layout.addWidget(self.startStopButton)
        self.layout.addWidget(self.cancelButton)


    def setUVI(self):
        self.state = "uvi"
        self.topText.setText("UV Index Measurement")

        self.setPreview()

        # Initialise Sensors
        self.initialiseSensors()
        # screenUV.set_mode(UVSMode)
        # backUV.set_mode(UVSMode)

    def setSkinType(self):
        self.state = "skinType"
        self.topText.setText("Skin Type Measurement")

        self.setPreview()
        
        # Initialise Sensors
        self.initialiseSensors()
        # screenUV.set_mode(ALSMode)
        # backUV.set_mode(ALSMode)

        # Start Camera
        # self.camera.start()
        

    def setSunscreenAssessment(self):
        self.state = "sunscreenAssessment"
        self.topText.setText("Sunscreen Application Assessment")

        self.setPreview()

        # Start Camera
        # self.camera.start()

    def estimateErythemaTime(self):
        self.uvi = self.uviBox.value()
        self.skinType = self.skinTypeBox.value()

        if(self.uvi != 0 and self.skinType !=0):
            self.burnTimeText.setText("Estimated Burn Time:\nTEST")
        else:
            self.burnTimeText.setText("Estimated Burn Time:\nNA")

    def startCapture(self):
        if self.state == "uvi":
            self.setCapture()
            self.timer.start(50)  # Update every 50 milliseconds
            self.timer.timeout.connect(self.uviCapture)
        
        elif self.state == "skinType":
            self.setCapture()
            self.timer.start(50)
            self.timer.timeout.connect(self.skinTypeCapture)

        elif self.state == "sunscreenAssessment":
            self.setCapture()   
            self.timer.start(50)
            self.timer.timeout.connect(self.sunscreenCapture)


    def setCapture(self):
        # Reconfigure UI Elements
        self.cancelButton.setText("Stop Capture")
        self.cancelButton.setObjectName("stopButton")
        self.cancelButton.setStyleSheet('')

        self.uviBox.hide()
        self.uviLabel.hide()
        self.skinTypeBox.hide()
        self.skinTypeLabel.hide()
        self.startStopButton.hide()

        self.cancelButton.show()

    def setPreview(self):
        # Reconfigure UI Elements
        self.topText.show()
        self.startStopButton.show()
        self.cancelButton.show()

        self.uviBox.hide()
        self.uviLabel.hide()
        self.uviButton.hide()
        self.skinTypeBox.hide()
        self.skinTypeLabel.hide()
        self.skinTypeButton.hide()
        self.burnTimeText.hide()
        self.burnTimeButton.hide()
        self.sunscreenAssessmentButton.hide()

    def initialiseSetup(self):
        self.state = "setup"

        self.timer.stop()
        if self.timerConnected == True:
            self.timer.disconnect()
            self.timerConnected = False

            self.uviBox.setValue(round(self.uvi))
            self.skinTypeBox.setValue(round(self.skinType))

        # self.camera.stop()
            
        self.estimateErythemaTime()

        # Reconfigure UI Elements
        self.imagePreview.clear()
        self.topText.clear()
        self.skinSensorLabel.clear()
        self.screenSensorLabel.clear()

        self.uviBox.show()
        self.uviLabel.show()
        self.uviButton.show()
        self.skinTypeBox.show()
        self.skinTypeLabel.show()
        self.skinTypeButton.show()
        self.burnTimeText.show()
        self.burnTimeButton.show()
        self.sunscreenAssessmentButton.show()

        self.startStopButton.hide()
        self.cancelButton.hide()

    def initialiseSensors(self):
        # Initialise sensors
        # while (self.initialised != True):
        #     if(screenUV.begin() == True and backUV.begin() == True):
        #         screenUV.set_ALS_or_UVS_meas_rate(e16bit,e50ms)#Set resolution and sampling time of module
        #         screenUV.set_ALS_or_UVS_gain(eGain9)#Set gain
        #         screenUV.set_mode(ALSMode)#Set as ambient light mode, UVSMode (UV light mode)
                
        #         backUV.set_ALS_or_UVS_meas_rate(e16bit,e50ms)#Set resolution and sampling time of module
        #         backUV.set_ALS_or_UVS_gain(eGain9)#Set gain
        #         backUV.set_mode(ALSMode)#Set as ambient light mode, UVSMode (UV light mode)
                    
        #         self.initialised = True
        #         print("Sensor initialise success!!")
            time.sleep(1)
        
    def uviCapture(self):
        # UV Data
        time.sleep(0.03)
        # screenUV_uvData = screenUV.read_original_data()
        # backUV_uvData = backUV.read_original_data()

        # Display the sensor values below image when capturing
        # self.skinSensorLabel.setText(f"Skin Sensor Values:\nUV: {str(self.backUV_uvData)}")
        # self.screenSensorLabel.setText(f"Screen Sensor Values:\nUV: {str(self.screenUV_uvData)}")

        # UVI Calculation
        if self.screenUV_uvData > 250:
            self.uvi = "0"
            self.initialiseSensors()

        elif self.screenUV_uvData > self.screenUV_uvData_max and self.screenUV_uvData < 200:
            self.screenUV_uvData_max = self.screenUV_uvData
            self.uvi = 0.0000000154*self.screenUV_uvData_max^4 - 0.0000037453*self.screenUV_uvData_max^3 + 0.0003615149*self.screenUV_uvData_max^2 + 0.0068468111*self.screenUV_uvData_max + 0.0056487941

        elif self.screenUV_uvData > 200:
            self.uvi = 12

        self.uvi = round(self.uvi, 1)
        self.topText.setText(f"UV Index Measurement\nCalculated UV Index: {str(self.uvi)}")

    def skinTypeCapture(self):
        #IMG Data
        # img = self.camera.capture_array()
        
        # UV Data
        time.sleep(0.03)
        # screenUV_visData = screenUV.read_original_data()
        # backUV_visData = backUV.read_original_data()

        # # Display the image
        # height, width, channel = img.shape
        # bytes_per_line = 3 * width
        # q_image = QImage(img.data, width, height, bytes_per_line, QImage.Format.Format_BGR888)
        # pixmap = QPixmap.fromImage(q_image)
        # pixmap = pixmap.scaledToWidth(400)  # Adjust the size as needed
        # self.imagePreview.setPixmap(pixmap)

        # Display the sensor values below image when capturing
        # self.skinSensorLabel.setText(f"Skin Sensor Values:\nUV: {str(self.backUV_visData)}")
        # self.screenSensorLabel.setText(f"Screen Sensor Values:\nUV: {str(self.screenUV_visData)}")
        
        # Skin Type Calculation
        self.skinType = 1
        self.skinType = round(self.skinType, 0)
        self.topText.setText(f"Skin Type Measurement\nCalculated Skin Type: {str(self.skinType)}")

    def sunscreenCapture(self):
        #IMG Data
        # img = self.camera.capture_array()
        
        # UV Data
        time.sleep(0.03)
        # screenUV_visData = screenUV.read_original_data()
        # backUV_visData = backUV.read_original_data()

        # results = self.model(img, stream=True)

        # coordinates
        # for r in results:
            # boxes = r.boxes

            # # for box in boxes:
            #     # bounding box
            #     x1, y1, x2, y2 = box.xyxy[0]
            #     x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2) # convert to int values

            #     # put box in cam
            #     cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 3)

            #     # confidence
            #     confidence = math.ceil((box.conf[0]*100))/100

            #     # class name
            #     cls = int(box.cls[0])

            #     # object details
            #     org = [x1, y1]
            #     font = cv2.FONT_HERSHEY_SIMPLEX
            #     fontScale = 1
            #     color = (255, 0, 0)
            #     thickness = 2

            #     cv2.putText(img, classNames[cls], org, font, fontScale, color, thickness)

        # # Display the image
        # height, width, channel = img.shape
        # bytes_per_line = 3 * width
        # q_image = QImage(img.data, width, height, bytes_per_line, QImage.Format.Format_BGR888)
        # pixmap = QPixmap.fromImage(q_image)
        # pixmap = pixmap.scaledToWidth(400)  # Adjust the size as needed
        # self.imagePreview.setPixmap(pixmap)

        print("s")
        self.topText.setText(f"Sunscreen Application Assessment:")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DetectorApp()
    window.show()
    sys.exit(app.exec_())

