import sys

import cv2
import depthai
from PyQt5 import uic
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QMainWindow, QLabel, QPushButton, QMessageBox

global check
check = 0
class InterfaceQT(QMainWindow):
    def __init__(self):
        super(InterfaceQT, self).__init__()
        try:
            uic.loadUi("assets/Interface_ProjetIA.ui", self)
        except FileNotFoundError:
            print("Could not find the UI file.")
            sys.exit(1)

        self.label = self.findChild(QLabel, "label_2")
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(1)
        self.cap = cv2.VideoCapture(0)
        """
        # Create DepthAI pipeline
        self.pipeline = depthai.Pipeline()

        # Create ColorCamera node
        self.cam = self.pipeline.createColorCamera()
        self.cam.setPreviewSize(640, 480)

        # Create XLinkOut nodes
        self.xout_preview = self.pipeline.createXLinkOut()
        self.xout_preview.setStreamName('preview')
        self.xout_preview.input.setQueueSize(1)

        # Link nodes
        self.cam.preview.link(self.xout_preview.input)

        with depthai.Device(self.pipeline) as device:
            # Create video stream object for OAK-1 camera
            self.stream = device.getOutputQueue('preview', maxSize=1, blocking=False)
        """
        BoutonDetection = self.findChild(QPushButton, "DetectionBouton")
        BoutonDetection.clicked.connect(self.BoutonDetection_clicked)

        LancerBouton = self.findChild(QPushButton, "LancerBouton")
        LancerBouton.clicked.connect(self.LancerBouton_clicked)

        QuitterBouton = self.findChild(QPushButton, "QuitterBouton")
        QuitterBouton.clicked.connect(self.QuitterBouton_clicked)

    def BoutonDetection_clicked(self):
        print("Button clicked")

    def LancerBouton_clicked(self):
        if check == 0:
            msg = QMessageBox()
            msg.setWindowTitle("Face Tracking")
            msg.setText("Veuillez vous enregistrer avant de lancer le suivi de caméra")
            msg.setIcon(QMessageBox.Information)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

    def QuitterBouton_clicked(self):
        self.close()

    def update_frame(self):

        ret, frame = self.cap.read()
        if ret:
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = image.shape
            bytes_per_line = ch * w
            q_image = QImage(image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.label.setPixmap(QPixmap.fromImage(q_image))
