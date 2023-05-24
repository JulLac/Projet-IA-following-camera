import argparse
import os
import sys
import time

import blobconverter
import cv2
import depthai
import numpy as np
from PyQt5 import uic
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QMainWindow, QLabel, QPushButton, QMessageBox
import depthai as dai
from textHelper import TextHelper
from faceRecognition import FaceRecognition
from MultiMsgSync import TwoStageHostSeqSync
from Mouvement import Mouvement_camera


class InterfaceQT(QMainWindow):
    def __init__(self):
        super(InterfaceQT, self).__init__()
        try:
            uic.loadUi("assets/Interface_ProjetIA.ui", self)
        except FileNotFoundError:
            print("Could not find the UI file.")
            sys.exit(1)

        self.check = 0
        self.object_camera = Mouvement_camera(1, 1, 0.45, 0.55, 0.45, 0.55)
        self.object_camera.centrer()


        # tiny yolo v4 label texts
        self.labelMap = [
            "person",         "bicycle",    "car",           "motorbike",     "aeroplane",   "bus",           "train",
            "truck",          "boat",       "traffic light", "fire hydrant",  "stop sign",   "parking meter", "bench",
            "bird",           "cat",        "dog",           "horse",         "sheep",       "cow",           "elephant",
            "bear",           "zebra",      "giraffe",       "backpack",      "umbrella",    "handbag",       "tie",
            "suitcase",       "frisbee",    "skis",          "snowboard",     "sports ball", "kite",          "baseball bat",
            "baseball glove", "skateboard", "surfboard",     "tennis racket", "bottle",      "wine glass",    "cup",
            "fork",           "knife",      "spoon",         "bowl",          "banana",      "apple",         "sandwich",
            "orange",         "broccoli",   "carrot",        "hot dog",       "pizza",       "donut",         "cake",
            "chair",          "sofa",       "pottedplant",   "bed",           "diningtable", "toilet",        "tvmonitor",
            "laptop",         "mouse",      "remote",        "keyboard",      "cell phone",  "microwave",     "oven",
            "toaster",        "sink",       "refrigerator",  "book",          "clock",       "vase",          "scissors",
            "teddy bear",     "hair drier", "toothbrush"
        ]

        self.syncNN = True

        # Create pipeline
        self.pipeline = dai.Pipeline()

        # Define sources and outputs
        self.camRgb = self.pipeline.create(dai.node.ColorCamera)
        self.detectionNetwork = self.pipeline.create(dai.node.YoloDetectionNetwork)
        self.xoutRgb = self.pipeline.create(dai.node.XLinkOut)
        self.nnOut = self.pipeline.create(dai.node.XLinkOut)

        self.xoutRgb.setStreamName("rgb")
        self.nnOut.setStreamName("nn")

        # Properties
        self.camRgb.setPreviewSize(416, 416)
        self.VIDEO_SIZE = (1072, 1072)
        self.camRgb.setVideoSize(self.VIDEO_SIZE)
        self.camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        self.camRgb.setInterleaved(False)
        self.camRgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
        self.camRgb.setFps(40)

        # Network specific settings
        self.detectionNetwork.setConfidenceThreshold(0.5)
        self.detectionNetwork.setNumClasses(len(self.labelMap))
        self.detectionNetwork.setCoordinateSize(4)
        self.detectionNetwork.setAnchors([10, 14, 23, 27, 37, 58, 81, 82, 135, 169, 344, 319])
        self.detectionNetwork.setAnchorMasks({"side26": [1, 2, 3], "side13": [3, 4, 5]})
        # detectionNetwork.setAnchorMasks({"side26": [1], "side13": [1]})

        self.detectionNetwork.setIouThreshold(0.5)
        self.detectionNetwork.setBlobPath(self.nnPath)
        self.detectionNetwork.setNumInferenceThreads(2)
        self.detectionNetwork.input.setBlocking(False)

        # Linking
        self.camRgb.preview.link(self.detectionNetwork.input)
        if self.syncNN:
            self.detectionNetwork.passthrough.link(self.xoutRgb.input)
        else:
            self.camRgb.preview.link(self.xoutRgb.input)

        self.detectionNetwork.out.link(self.nnOut.input)


        # Connect to device and start pipeline
        self.device = depthai.Device(self.pipeline)

        # Output queues will be used to get the rgb frames and nn data from the outputs defined above
        self.qRgb = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
        self.qDet = self.device.getOutputQueue(name="nn", maxSize=4, blocking=False)

        self.frame = None
        self.detections = []
        self.startTime = time.monotonic()
        self.counter = 0
        self.color2 = (255, 255, 255)

        self.facerec = FaceRecognition(self.databases, "Mathieu") #self.args.name)
        self.sync = TwoStageHostSeqSync()
        self.text = TextHelper()

        self.queues = {}

        # Connect to device and start pipeline
        self.device = depthai.Device(self.pipeline)

        # Output queues will be used to get the rgb frames and nn data from the outputs defined above
        self.qRgb = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
        self.qDet = self.device.getOutputQueue(name="nn", maxSize=4, blocking=False)

        self.frame = None
        self.detections = []
        self.startTime = time.monotonic()
        self.counter = 0
        self.color2 = (255, 255, 255)

        self.last_exec_time = time.time()  # initialize the last execution time to 0


        #self.stream = self.device.getOutputQueue('preview', maxSize=1, blocking=False)

        self.label = self.findChild(QLabel, "label_2")
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(1)
        # self.cap = cv2.VideoCapture(0)

        BoutonDetection = self.findChild(QPushButton, "DetectionBouton")
        BoutonDetection.clicked.connect(self.BoutonDetection_clicked)

        LancerBouton = self.findChild(QPushButton, "LancerBouton")
        LancerBouton.clicked.connect(self.LancerBouton_clicked)

        QuitterBouton = self.findChild(QPushButton, "QuitterBouton")
        QuitterBouton.clicked.connect(self.QuitterBouton_clicked)

    def tourner_camera(self, object_camera, xmin, xmax, ymin, ymax):
        # servo 1 horizontal
        # servo 2 vertical

        # print("Position caméra:")
        # print('Horizontal:',object_camera.get_position_horizontal())
        # print('Vertical:',object_camera.get_position_vertical())
        # Donner les coordonnées
        object_camera.setxmax(xmax)
        object_camera.setxmin(xmin)
        object_camera.setymax(ymax)
        object_camera.setymin(ymin)
        object_camera.bouger_camera()
        # print("\n")
        # time.sleep(1)

    def frame_norm(self, frame, bbox):
        normVals = np.full(len(bbox), frame.shape[0])
        normVals[::2] = frame.shape[1]
        return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)

    def displayFrame(self, name, frame):
        color = (255, 0, 0)
        for detection in self.detections:
            if self.labelMap[detection.label] == 'person':
                bbox = self.frameNorm(frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))
                cv2.putText(frame, self.labelMap[detection.label], (bbox[0] + 10, bbox[1] + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                cv2.putText(frame, f"{int(detection.confidence * 100)}%", (bbox[0] + 10, bbox[1] + 40), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
        # Show the frame

        # self.check if frame is valid
        if frame is not None:
            # Convert frame to QImage
            frame = cv2.resize(frame, (741,511))
            h, w, ch = frame.shape
            bytesPerLine = ch * w
            qImg = QImage(frame.data, w, h, bytesPerLine, QImage.Format_RGB888)
            qImg = qImg.rgbSwapped()

            # Display frame
            self.label.setPixmap(QPixmap.fromImage(qImg))


    def update_frame(self):
        if self.syncNN:
            inRgb = self.qRgb.get()
            inDet = self.qDet.get()
        else:
            inRgb = self.qRgb.tryGet()
            inDet = self.qDet.tryGet()

        if inRgb is not None:
            frame = inRgb.getCvFrame()
            cv2.putText(frame, "NN fps: {:.2f}".format(self.counter / (time.monotonic() - self.startTime)),
                        (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, self.color2)

        if inDet is not None:
            detections = inDet.detections
            self.counter += 1

        if frame is not None:
            self.displayFrame("rgb", frame)

        if cv2.waitKey(1) == ord('q'):
            exit(1)

    def BoutonDetection_clicked(self):
        #self.check = 1
        pass
    def LancerBouton_clicked(self):
        #if self.check == 0:
        #    msg = QMessageBox()
        #    msg.setWindowTitle("Face Tracking")
        #    msg.setText("Veuillez vous enregistrer avant de lancer le suivi de caméra")
        #    msg.setIcon(QMessageBox.Information)
        #    msg.setStandardButtons(QMessageBox.Ok)
        #    msg.exec_()
        #else:
        #    self.check = 0
        pass

    def QuitterBouton_clicked(self):
        self.close()

    def stop(self):
        self.timer.stop()
        self.device.close()
        self.pipeline.reset()
