import sys
import time
import glob
import csv
import cv2

from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QComboBox, QFormLayout, QSpinBox, QGridLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap

from picamera2 import Picamera2
from libcamera import Transform
from DFRobot_LTR390UV import *

ADDRESS = 0x1c 
I2C_screen = 0x05
I2C_back = 0x04

screenUV = DFRobot_LTR390UV_I2C(I2C_screen, ADDRESS)
backUV = DFRobot_LTR390UV_I2C(I2C_back, ADDRESS)

class ImageCollectorApp(QMainWindow):

    def __init__(self):
        super().__init__()
        
        # Globals 
        self.camera = Picamera2()
        self.camera.configure(self.camera.create_preview_configuration(main={"format": 'BGR888', "size": (640, 480)}, transform=Transform(180)))
        self.timer = QTimer(self)

        self.saving = False
        self.initialised = None
        self.state = "setup"

        self.participantNumber = 0
        self.runNumber = 0
        self.sampleNumber = None
        self.newRun = None

        self.path = ""
        
        maxParticipantNumber = len(glob.glob("/home/pi/Data_Collection/data/P*"))

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
        self.topText.setStyleSheet("font-size: 18px;")  # Set bold and larger font

        # Image Preview
        self.imagePreview = QLabel(self)
        self.imagePreview.setAlignment(Qt.AlignmentFlag.AlignCenter)


        # Bottom Dropdowns
        self.bodyPartLabel = QLabel("Body Part:", self)
        self.bodyPart = QComboBox(self)
        self.bodyPart.addItems(["Face", "Chest", "Back", "Left_Arm", "Right_Arm", "Left_Leg", "Right_Leg", "Background"])
        self.bodyPart.view().parentWidget().setStyleSheet("background-color: #3498db")

        self.applicationTypeLabel = QLabel("Expected Application:", self)
        self.applicationType = QComboBox(self)
        self.applicationType.addItems(["Unknown", "None", "Partial", "Full", "Degraded_(WET)", "Degraded_(DRY)"])
        self.applicationType.view().parentWidget().setStyleSheet("background-color: #3498db")
        

        # Sensor Values Group
        self.skinSensorLabel = QLabel(self)
        self.skinSensorLabel.setAlignment(Qt.AlignmentFlag.AlignJustify)

        self.screenSensorLabel = QLabel(self)
        self.screenSensorLabel.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.sensorValues = QGridLayout()
        self.sensorValues.addWidget(self.skinSensorLabel, 0, 0)
        self.sensorValues.addWidget(self.screenSensorLabel, 0, 1)
        
        # Capture Button
        self.startStopButton = QPushButton("Start Capture", self)
        self.startStopButton.setObjectName("startButton")  
        self.startStopButton.clicked.connect(self.toggle_capture)

        
        # Top Spin Boxes
        self.participantNumberInputLabel = QLabel("Participant Number:", self)
        self.participantNumberInput = QSpinBox(self)  # New QSpinBox
        self.participantNumberInput.setRange(0, maxParticipantNumber)  # Set the range of the spin box
        self.participantNumberInput.valueChanged.connect(self.setRunNumber)

        self.runNumberInputLabel = QLabel("Run Number:", self)
        self.runNumberInput = QSpinBox(self)  # New QSpinBox
        self.setRunNumber()
        self.runNumberInput.setRange(self.runNumber, self.runNumber+1)  # Set the range of the spin box
        
        # Button Groups
        self.topButtons = QFormLayout()
        self.topButtons.addRow(self.participantNumberInputLabel, self.participantNumberInput)
        self.topButtons.addRow(self.runNumberInputLabel, self.runNumberInput)

        self.bottomButtons = QFormLayout()
        self.bottomButtons.addRow(self.bodyPartLabel, self.bodyPart)
        self.bottomButtons.addRow(self.applicationTypeLabel, self.applicationType)
        

        self.cancelButton = QPushButton("Cancel Capture", self) 
        self.cancelButton.setObjectName("cancelButton")  
        self.cancelButton.clicked.connect(self.setupCapture)
        self.cancelButton.hide()


        # UI Layout
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.addLayout(self.topButtons)
        self.layout.addWidget(self.topText)
        self.layout.addWidget(self.imagePreview)
        self.layout.addLayout(self.sensorValues)
        self.layout.addWidget(self.startStopButton)
        self.layout.addWidget(self.cancelButton)
        self.layout.addLayout(self.bottomButtons)


    def toggle_capture(self):
        # move from setup state to preview state
        if self.state == "setup":
            self.previewCapture()
            
        # move from preview state to capture state
        elif self.state == "preview" and self.initialised == True:
            self.startCapture()
        
        # move from capture state to setup state
        else:
            self.setupCapture()


    def setRunNumber(self):
        self.runNumber = len(glob.glob("/home/pi/Data_Collection/data/P" + str(self.participantNumberInput.value()) + "/R*"))-1# number of files which name starts with 'R'
        if self.runNumber == -1:
            self.runNumber = 0
            self.runNumberInput.setRange(self.runNumber, self.runNumber)
        else:
            self.runNumberInput.setRange(self.runNumber, self.runNumber+1)


    def startCapture(self):
        self.startStopButton.setText("Stop Capture")
        self.startStopButton.setObjectName("stopButton")
        self.startStopButton.setStyleSheet('')

        self.state = "capture"
        self.saving = True
        
        
        # Hide the dropdowns and spin box when capturing
        self.applicationType.hide()
        self.applicationTypeLabel.hide()
        self.bodyPart.hide()
        self.bodyPartLabel.hide()
        self.participantNumberInput.hide()
        self.participantNumberInputLabel.hide()
        self.runNumberInput.hide()
        self.runNumberInputLabel.hide()

        self.cancelButton.hide()


    def previewCapture(self):
        
        # Start Camera
        self.camera.start()
        self.timer.start(100)  # Update every 30 milliseconds
        
        # Set Participant, Run Number and Sample Number
        self.participantNumber = str(self.participantNumberInput.value())
        self.runNumber = str(self.runNumberInput.value())
        
        self.startStopButton.setText("Start Capture")
        self.startStopButton.setObjectName("startButton")
        self.startStopButton.setStyleSheet('')

        self.topText.show()
        self.cancelButton.show()
        self.state = "preview"

        self.timer.timeout.connect(self.capture)

        # Hide the dropdowns and spin box when capturing
        self.applicationType.hide()
        self.applicationTypeLabel.hide()
        self.bodyPart.hide()
        self.bodyPartLabel.hide()
        self.participantNumberInput.hide()
        self.participantNumberInputLabel.hide()
        self.runNumberInput.hide()
        self.runNumberInputLabel.hide()

        # Create folders
        self.path = "/home/pi/Data_Collection/data/P" + self.participantNumber + "/R" + self.runNumber + "/" 
    
        if not os.path.exists(self.path):
            os.makedirs(self.path)
            os.makedirs(self.path + "images/")
            
            self.newRun = True
            with open(self.path + "P" + self.participantNumber + "_R" + self.runNumber + "_data.csv", "w") as file:
                writer = csv.writer(file)
                writer.writerow(["Sample_Number", "Sample_Timestamp", "Image_Name", "Image_Timestamp", "Screen_Visible_Data", "Screen_Visible_Timestamp", "Back_Visible_Data", "Back_Visible_Timestamp", "Screen_UV_Data", "Screen_UV_Timestamp", "Back_UV_Data", "Back_UV_Timestamp", "Participant_Number", "Run_Number", "Body_Part", "Application_Condition"])
                file.close()
        else:
            self.newRun = False
            self.sampleNumber = len(glob.glob(self.path + "images/*")) - 1 # number of files in images dir
            print(self.sampleNumber)
        

        # Initialise sensors
        while (self.initialised != True):
            if(screenUV.begin() == True and backUV.begin() == True):
                screenUV.set_ALS_or_UVS_meas_rate(e17bit,e50ms)#Set resolution and sampling time of module
                screenUV.set_ALS_or_UVS_gain(eGain1)#Set gain
                screenUV.set_mode(ALSMode)#Set as ambient light mode, UVSMode (UV light mode)
                
                backUV.set_ALS_or_UVS_meas_rate(e17bit,e50ms)#Set resolution and sampling time of module
                backUV.set_ALS_or_UVS_gain(eGain1)#Set gain
                backUV.set_mode(ALSMode)#Set as ambient light mode, UVSMode (UV light mode)
                    
                self.initialised = True
                print("UV Sensor initialise success!!")
            time.sleep(1)
        

    def setupCapture(self):
        
        self.timer.stop()
        self.camera.stop()
        self.imagePreview.clear()
        self.topText.clear()
        self.skinSensorLabel.clear()
        self.screenSensorLabel.clear()
        self.startStopButton.setText("Start Capture")
        self.startStopButton.setObjectName("startButton")
        self.startStopButton.setStyleSheet('')

        self.initialised = False
        self.state = "setup"
        self.saving = False

        # Show the dropdowns and spin box when capturing is stopped
        self.applicationType.show()
        self.applicationTypeLabel.show()
        self.bodyPart.show()
        self.bodyPartLabel.show()
        self.participantNumberInput.show()
        self.participantNumberInputLabel.show()
        self.runNumberInput.show()
        self.runNumberInputLabel.show()

        self.cancelButton.hide()

    def capture(self):
        sampleTime = time.time_ns()

        #IMG Data
        img = self.camera.capture_array()
        imageTime = time.time_ns()

        # VIS Data
        screenUV.set_mode(ALSMode)
        backUV.set_mode(ALSMode)
        time.sleep(0.03)

        screenUV_visData = screenUV.read_original_data()
        screenUV_visTime = time.time_ns()
        backUV_visData = backUV.read_original_data()
        backUV_visTime = time.time_ns()
        
        # UV Data
        screenUV.set_mode(UVSMode)
        backUV.set_mode(UVSMode)
        time.sleep(0.03)

        screenUV_uvData = screenUV.read_original_data()
        screenUV_uvTime = time.time_ns()
        backUV_uvData = backUV.read_original_data()
        backUV_uvTime = time.time_ns()

        # Display the image
        height, width, channel = img.shape
        bytes_per_line = 3 * width
        q_image = QImage(img.data, width, height, bytes_per_line, QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(q_image)
        pixmap = pixmap.scaledToWidth(400)  # Adjust the size as needed
        self.imagePreview.setPixmap(pixmap)

        # Display the sensor values below image when capturing
        self.skinSensorLabel.setText(f"Skin Sensor Values:\nVisible: {str(backUV_visData)}\nUV: {str(backUV_uvData)}")
        self.screenSensorLabel.setText(f"Screen Sensor Values:\nVisible: {str(screenUV_visData)}\nUV: {str(screenUV_uvData)}")
            
        # Display the value of the option dropdown below the timestamp when capturing
        self.topText.setText(f"Participant Number: {str(self.participantNumber)}\nRun Number: {str(self.runNumber)}\nNew Run: {str(self.newRun)}\nBody Part: {self.bodyPart.currentText()}\nExpected Application: {self.applicationType.currentText()}")

        # Saving Img Data
        if self.saving:
            imageName = "P" + self.participantNumber + "_R" + self.runNumber + "_" + "I" + str(self.sampleNumber)
            cv2.imwrite(self.path + "images/" + imageName + ".jpeg", img)
            
            # Saving Sensor Data
            with open(self.path + "P" + self.participantNumber + "_R" + self.runNumber + "_data.csv", "a") as file:
                writer = csv.writer(file)
                writer.writerow([self.sampleNumber, sampleTime, imageName, imageTime, screenUV_visData, screenUV_visTime, backUV_visData, backUV_visTime, screenUV_uvData, screenUV_uvTime, backUV_uvData, backUV_uvTime, self.participantNumber, self.runNumber, self.bodyPart.currentText(), self.applicationType.currentText()])

            self.sampleNumber = self.sampleNumber + 1

    def closeEvent(self, event):
        if self.initialised:
            self.setupCapture()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageCollectorApp()
    window.show()
    sys.exit(app.exec_())
