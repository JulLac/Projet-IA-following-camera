import blobconverter
import cv2
import numpy as np
from PyQt5 import uic, QtCore
from PyQt5.QtGui import QFont, QImage, QPixmap
from PyQt5.QtWidgets import QLabel, QPushButton, QDialog, QVBoxLayout, QLineEdit, QCheckBox, QMainWindow, QMessageBox

import depthai as dai
import sys
import argparse
import os
import time
import glob

# tell interpreter where to look
sys.path.insert(0, "..")
from app.textHelper import TextHelper
from app.faceRecognition import FaceRecognition
from app.MultiMsgSync import TwoStageHostSeqSync
from app.Mouvement import Mouvement_camera


class InterfaceQT(QMainWindow):
    def __init__(self):
        super(InterfaceQT, self).__init__()
        
        try:
            uic.loadUi("../gui/assets/Interface_ProjetIA.ui", self)
        except FileNotFoundError:
            print("Could not find the UI file.")
            sys.exit(1)
        
        self.face_detection = False
        self.body_detection = True
        self.frame = None
        
        ## Init face
        self.init_body()
        
        self.show_bounding_box = False
        self.lancer = False
        
        self.label = self.findChild(QLabel, "label_2")

        self.BoutonAuto = self.findChild(QPushButton, "Auto")
        self.BoutonAuto.clicked.connect(self.BoutonAuto_clicked)

        self.BoutonBrider = self.findChild(QPushButton, "Brider")
        self.BoutonBrider.clicked.connect(self.BoutonBrider_clicked)

        self.LancerBouton = self.findChild(QPushButton, "LancerBouton")
        self.LancerBouton.clicked.connect(self.LancerBouton_clicked)

        self.QuitterBouton = self.findChild(QPushButton, "QuitterBouton")
        self.QuitterBouton.clicked.connect(self.QuitterBouton_clicked)

        self.Text_mode = self.findChild(QLabel, "label_3")
        self.Text_mode.setFont(QFont('Times', 15))

        self.CheckBox = self.findChild(QCheckBox, "checkBox")
        self.CheckBox.stateChanged.connect(self.clickBox)
        self.CheckBox.setFont(QFont('Times', 11))

        self.ToggleButonFaceBody = self.findChild(QPushButton, "ToggleFaceBody")
        self.ToggleButonFaceBody.clicked.connect(self.ToggleButonFaceBody_clicked)
        
        self.object_camera = Mouvement_camera(1, 1, 0.45, 0.55, 0.45, 0.55)
        self.object_camera.centrer()

    def init_face(self):
        
        #try:
        #    uic.loadUi("../gui/assets/Interface_ProjetIA.ui", self)
        #except FileNotFoundError:
        #    print("Could not find the UI file.")
        #    sys.exit(1)

        self.person_to_detect = "user"
        self.save_new_face = False
        
        # Create database folder if necessary. Clear if it already exists
        self.databases = "databases"
        if not os.path.exists(self.databases):
            os.mkdir(self.databases)
        else:
            npz_files = glob.glob(os.path.join(self.databases, "*.npz"))
            for file in npz_files:
                os.remove(file)

        # Create DepthAI pipeline
        self.pipeline = dai.Pipeline()
        self.cam = self.pipeline.createColorCamera()
        self.cam.setPreviewSize(1072, 1072)
        self.VIDEO_SIZE = (1072, 1072)
        self.cam.setVideoSize(self.VIDEO_SIZE)
        self.cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        self.cam.setInterleaved(False)
        self.cam.setBoardSocket(dai.CameraBoardSocket.RGB)

        # Create XLinkOut nodes
        self.host_face_out = self.pipeline.create(dai.node.XLinkOut)
        self.host_face_out.setStreamName('rgb')

        # Link nodes
        self.cam.video.link(self.host_face_out.input)

        # ImageManip as a workaround to have more frames in the pool.
        # cam.preview can only have 4 frames in the pool before it will
        # wait (freeze). Copying frames and setting ImageManip pool size to
        # higher number will fix this issue.
        self.copy_manip = self.pipeline.create(dai.node.ImageManip)
        self.cam.preview.link(self.copy_manip.inputImage)
        self.copy_manip.setNumFramesPool(20)
        self.copy_manip.setMaxOutputFrameSize(1072 * 1072 * 3)

        # ImageManip that will crop the frame before sending it to the Face detection NN node
        self.face_det_manip = self.pipeline.create(dai.node.ImageManip)
        self.face_det_manip.initialConfig.setResize(300, 300)
        self.copy_manip.out.link(self.face_det_manip.inputImage)

        # NeuralNetwork
        print("Creating Face Detection Neural Network...")
        self.face_det_nn = self.pipeline.create(dai.node.MobileNetDetectionNetwork)
        self.face_det_nn.setConfidenceThreshold(0.5)
        self.face_det_nn.setBlobPath(blobconverter.from_zoo(name="face-detection-retail-0004", shaves=6))
        # Link Face ImageManip -> Face detection NN node
        self.face_det_manip.out.link(self.face_det_nn.input)

        self.face_det_xout = self.pipeline.create(dai.node.XLinkOut)
        self.face_det_xout.setStreamName("detection")
        self.face_det_nn.out.link(self.face_det_xout.input)

        # Script node  allows users to run custom Python scripts on the device
        # It will take the output from the face detection NN as an input and set ImageManipConfig
        # to the 'age_gender_manip' to crop the initial frame
        self.script = self.pipeline.create(dai.node.Script)
        self.script.setProcessor(dai.ProcessorType.LEON_CSS)

        self.face_det_nn.out.link(self.script.inputs['face_det_in'])
        # We also interested in sequence number for syncing
        self.face_det_nn.passthrough.link(self.script.inputs['face_pass'])

        self.copy_manip.out.link(self.script.inputs['preview'])

        with open("../app/script.py", "r") as f:
            self.script.setScript(f.read())

        print("Creating Head pose estimation NN")

        self.headpose_manip = self.pipeline.create(dai.node.ImageManip)
        self.headpose_manip.initialConfig.setResize(60, 60)
        self.headpose_manip.setWaitForConfigInput(True)
        self.script.outputs['manip_cfg'].link(self.headpose_manip.inputConfig)
        self.script.outputs['manip_img'].link(self.headpose_manip.inputImage)

        self.headpose_nn = self.pipeline.create(dai.node.NeuralNetwork)
        self.headpose_nn.setBlobPath(blobconverter.from_zoo(name="head-pose-estimation-adas-0001", shaves=6))
        self.headpose_manip.out.link(self.headpose_nn.input)

        self.headpose_nn.out.link(self.script.inputs['headpose_in'])
        self.headpose_nn.passthrough.link(self.script.inputs['headpose_pass'])

        print("Creating face recognition ImageManip/NN")

        self.face_rec_manip = self.pipeline.create(dai.node.ImageManip)
        self.face_rec_manip.initialConfig.setResize(112, 112)
        self.face_rec_manip.inputConfig.setWaitForMessage(True)

        self.script.outputs['manip2_cfg'].link(self.face_rec_manip.inputConfig)
        self.script.outputs['manip2_img'].link(self.face_rec_manip.inputImage)

        self.face_rec_nn = self.pipeline.create(dai.node.NeuralNetwork)
        self.face_rec_nn.setBlobPath(
            blobconverter.from_zoo(name="face-recognition-arcface-112x112", zoo_type="depthai", shaves=6))
        self.face_rec_manip.out.link(self.face_rec_nn.input)

        self.arc_xout = self.pipeline.create(dai.node.XLinkOut)
        self.arc_xout.setStreamName('recognition')
        self.face_rec_nn.out.link(self.arc_xout.input)

        #self.parser = argparse.ArgumentParser()
        #self.parser.add_argument("-name", "--name", type=str, help="Name of the person for database saving")

        #self.args = self.parser.parse_args()
        #print(self.args)

        

        self.facerec = FaceRecognition(self.databases, self.person_to_detect)
        self.sync = TwoStageHostSeqSync()
        self.text = TextHelper()
        
        self.queues = {}

        # Connect to device and start pipeline
        self.device = dai.Device(self.pipeline)

        # Create output queues
        for name in ["rgb", "detection", "recognition"]:
            self.queues[name] = self.device.getOutputQueue(name)
        
        self.last_exec_time = time.time()  # initialize the last execution time to 0

        # self.stream = self.device.getOutputQueue('preview', maxSize=1, blocking=False)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame_face)
        self.timer.start(1)
    
    def init_body(self):        
        # try:
        #    uic.loadUi("../gui/assets/Interface_ProjetIA.ui", self)
        # except FileNotFoundError:
        #     print("Could not find the UI file.")
        #    sys.exit(1)
        
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
        self.bounding_box = True

        # Create pipeline
        self.pipeline = dai.Pipeline()
        
        #SUPR
        #self.pipeline.setDevice("03e7:2485")
        
        #modelname
        self.nnPath = blobconverter.from_zoo(name="yolo-v4-tiny-tf")
        #self.nnPath = blobconverter.from_zoo(name="person-detection-0200") 

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
        self.camRgb.setFps(30)

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
        self.device = dai.Device(self.pipeline)

        # Output queues will be used to get the rgb frames and nn data from the outputs defined above
        self.qRgb = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
        self.qDet = self.device.getOutputQueue(name="nn", maxSize=4, blocking=False)

        self.frame = None
        self.detections = []
        self.startTime = time.monotonic()
        self.counter = 0
        self.color = (255, 0, 0)
        self.color2 = (255, 255, 255)

        self.last_exec_time = time.time()  # initialize the last execution time to 0


        #self.stream = self.device.getOutputQueue('preview', maxSize=1, blocking=False)

        #self.label = self.findChild(QLabel, "label_2")
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame_body)
        self.timer.start(1)
        # self.cap = cv2.VideoCapture(0)


    def clickBox(self, state):
        if state == QtCore.Qt.Checked:
            self.show_bounding_box = True
        else:
            self.show_bounding_box = False

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

    def frame_norm(self, bbox):
        normVals = np.full(len(bbox), self.frame.shape[0])
        normVals[::2] = self.frame.shape[1]
        return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)


    def displayFrame(self, name):
        # Show the frame
        # Convert frame to QImage
        self.frame = cv2.resize(self.frame, (741,511))
        h, w, ch = self.frame.shape
        bytesPerLine = ch * w
        qImg = QImage(self.frame.data, w, h, bytesPerLine, QImage.Format_RGB888)
        qImg = qImg.rgbSwapped()

        # Display frame
        self.label.setPixmap(QPixmap.fromImage(qImg))

    def update_frame_face(self):
        for name, q in self.queues.items():
            # Add all msgs (color frames, object detections and face recognitions) to the Sync class.
            if q.has():
                self.sync.add_msg(q.get(), name)

        self.msgs = self.sync.get_msgs()
        if self.msgs is not None:
            self.frame = self.msgs["rgb"].getCvFrame()
            self.dets = self.msgs["detection"].detections

            # print(self.check)
            #print("args.name:", args.name)
            
            #if args.name:
            #if self.check == 2:

            if self.save_new_face:
                print("Visage en cours d'enregistrement")
                for i, detection in enumerate(self.dets):
                    
                    bbox = self.frame_norm((detection.xmin, detection.ymin, detection.xmax, detection.ymax))
                    
                    features = np.array(self.msgs["recognition"][i].getFirstLayerFp16())
                    conf, name = self.facerec.new_recognition(features)
                    
                    if self.show_bounding_box: 
                        cv2.rectangle(self.frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (240, 10, 10), 2)
                        self.text.putText(self.frame, f"{name} {(100 * conf):.0f}%", (bbox[0] + 10, bbox[1] + 35))

            else:
                if self.lancer == True:
                    # print("detection")
                    # Only execute the for loop if 5 seconds have passed since the last execution
                    if len(self.dets) > 0:
                        self.object_camera.reset()
                        if time.time() - self.last_exec_time >= 0.35:
                            best_detection = None
                            is_unknown = 1
                            best_index = None
                            for i, detection in enumerate(self.dets):
                                if best_detection is None or detection.confidence > best_detection.confidence:
                                    if detection.label == "Unknown":
                                        if is_unknown == 1:
                                            best_detection = detection
                                            best_index = i
                                        else:
                                            pass
                                    else:
                                        best_detection = detection
                                        is_unknown = 0
                                        best_index = i

                            if best_detection is not None:
                                # print("move")
                                bbox = self.frame_norm((best_detection.xmin, best_detection.ymin, best_detection.xmax, best_detection.ymax))
                                # print(detection.xmin, detection.ymin, detection.xmax, detection.ymax)
                                
                                features = np.array(self.msgs["recognition"][best_index].getFirstLayerFp16())
                                conf, name = self.facerec.new_recognition(features)
                                
                                if self.show_bounding_box: 
                                    cv2.rectangle(self.frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (10, 245, 10), 2)
                                    self.text.putText(self.frame, f"{name} {(100 * conf):.0f}%", (bbox[0] + 10, bbox[1] + 35))
                                    
                                
                                self.tourner_camera(self.object_camera, best_detection.xmin, best_detection.xmax,
                                                    best_detection.ymin, best_detection.ymax)

                            self.last_exec_time = time.time()  # update the last execution time
                    else:
                        if time.time() - self.last_exec_time >= 8:
                            # print("balayage")
                            self.object_camera.balayage()
                
        #self.check if frame is valid
        if self.frame is not None:
            # Convert frame to QImage
            self.frame = cv2.resize(self.frame, (741, 511))
            h, w, ch = self.frame.shape
            bytesPerLine = ch * w
            qImg = QImage(self.frame.data, w, h, bytesPerLine, QImage.Format_RGB888)
            qImg = qImg.rgbSwapped()

            # Display frame
            self.label.setPixmap(QPixmap.fromImage(qImg))
      
    def update_frame_body(self):
        if self.syncNN:
            inRgb = self.qRgb.get()
            inDet = self.qDet.get()
        else:
            inRgb = self.qRgb.tryGet()
            inDet = self.qDet.tryGet()

        if inRgb is not None:
            self.frame = inRgb.getCvFrame()
            #cv2.putText(frame, "NN fps: {:.2f}".format(self.counter / (time.monotonic() - self.startTime)),
            #            (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, self.color2)

        if self.lancer == True:    
            if inDet is not None:
                self.detections = inDet.detections
                self.counter += 1
                
                # Only execute the for loop if 5 seconds have passed since the last execution
                if len(self.detections) > 0:
                    self.object_camera.reset()
                    if time.time() - self.last_exec_time >= 0.35:
                        best_detection = None
                        best_index = None
                        for i, detection in enumerate(self.detections):
                            if self.labelMap[detection.label] == 'person':
                                if best_detection is None or detection.confidence > best_detection.confidence:
                                    best_detection = detection
                                    best_index = i
                       
                        if best_detection is not None:
                            #print("move")
                            bbox = self.frame_norm((best_detection.xmin, best_detection.ymin, best_detection.xmax, best_detection.ymax))
                            
                            if self.show_bounding_box:
                                cv2.putText(self.frame, self.labelMap[detection.label], (bbox[0] + 10, bbox[1] + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                                cv2.putText(self.frame, f"{int(detection.confidence * 100)}%", (bbox[0] + 10, bbox[1] + 40), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                                cv2.rectangle(self.frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), self.color, 2)
                            
                                
                            self.tourner_camera(self.object_camera, best_detection.xmin, best_detection.xmax, best_detection.ymin, best_detection.ymax)
     
                        self.last_exec_time = time.time()  # update the last execution time
                else:
                    if time.time() - self.last_exec_time >= 8:
                        #print("balayage")
                        self.object_camera.balayage()

        # Check if frame is valid
        if self.frame is not None:
            self.displayFrame("rgb")

    def BoutonAuto_clicked(self):
        self.object_camera.set_max_degre_x_gauche(-90)
        self.object_camera.set_max_degre_x_droite(90)
        self.object_camera.set_max_degre_y_haut(-90)
        self.object_camera.set_max_degre_y_bas(90)
        self.object_camera.centrer()

    def get_line_edit_value(self, line_edit):
        return line_edit.text()

    def BoutonBrider_clicked(self):
        print("BoutonBrider push")
        #self.check = 2
        self.dialog = QDialog()
        layout = QVBoxLayout()

        label = QLabel("Valeur par défaut du bridage de la caméra :\n")
        layout.addWidget(label)

        #gauche
        label_gauche = QLabel("Valeur bridage gauche (-90>valeur>90)")
        layout.addWidget(label_gauche)
        self.line_edit_xmin = QLineEdit("-90")
        layout.addWidget(self.line_edit_xmin)

        #droit
        label_droit = QLabel("Valeur bridage droit (-90>valeur>90)")
        layout.addWidget(label_droit)
        self.line_edit_xmax = QLineEdit("90")
        layout.addWidget(self.line_edit_xmax)

        #haut
        label_haut = QLabel("Valeur bridage haut (-90>valeur>90)")
        layout.addWidget(label_haut)
        self.line_edit_ymin = QLineEdit("-90")
        layout.addWidget(self.line_edit_ymin)

        #bas
        label_bas = QLabel("Valeur bridage bas (-90>valeur>90)")
        layout.addWidget(label_bas)
        self.line_edit_ymax = QLineEdit("90")
        layout.addWidget(self.line_edit_ymax)

        button_valider = QPushButton("Valider")
        button_valider.clicked.connect(self.Bouton_valider_clicked)
        layout.addWidget(button_valider)

        button = QPushButton("Fermer")
        button.clicked.connect(self.dialog.close)
        layout.addWidget(button)

        self.dialog.setLayout(layout)
        self.dialog.exec_()

    def Bouton_valider_clicked(self):

        try:
            self.BoutonBrider.clicked.disconnect()
            xmin = self.is_numeric(self.line_edit_xmin.text())
            xmax = self.is_numeric(self.line_edit_xmax.text())
            ymin = self.is_numeric(self.line_edit_ymin.text())
            ymax = self.is_numeric(self.line_edit_ymax.text())

            if -90 <= xmin <= xmax <= 90 and -90 <= ymin <= ymax <= 90:
                print("Mise à jour du bridage haut à la valeur :", ymin)
                print("Mise à jour du bridage bas à la valeur :", ymax)
                print("Mise à jour du bridage droit à la valeur :", xmax)
                print("Mise à jour du bridage gauche à la valeur :", xmin)

                self.object_camera.set_max_degre_x_gauche(xmin)
                self.object_camera.set_max_degre_x_droite(xmax)
                self.object_camera.set_max_degre_y_haut(ymin)
                self.object_camera.set_max_degre_y_bas(ymax)
                self.object_camera.centrer_bridage(xmin,xmax,ymin,ymax)

            else:
                self.popUp()

        except TypeError:
            pass
        self.BoutonBrider.clicked.connect(self.BoutonBrider_clicked)

    def popUp(self):
        dialog = QDialog()
        layout = QVBoxLayout()
        label = QLabel("Les valeurs reseignées ne sont pas correctes !")
        label.setFont(QFont('Times', 15))
        label.setStyleSheet("color: red;")
        layout.addWidget(label)
        dialog.setLayout(layout)
        dialog.exec_()

    def LancerBouton_clicked(self):

        if not self.lancer:
            self.lancer = True
            self.LancerBouton.setStyleSheet("""
                QPushButton{
        	        border-radius:10px;
        	        background-image: url(../gui/Images/IMG_arreter.png);
                }
                QPushButton:hover{
                    background-image: url(../gui/Images/IMG_arreter_hover.png);
                }""")
            
            if self.face_detection and len(os.listdir(self.databases))==0:
                msg = QMessageBox()
                msg.setWindowTitle("Face Tracking")
                msg.setText("Veuillez vous positionner devant la caméra, face visible, pendant l'enregistrement de votre tête. Une fois terminé, cliquez sur arrêter.")
                msg.setIcon(QMessageBox.Information)
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
                self.save_new_face = True
                
        else:
            self.lancer = False
            self.LancerBouton.setStyleSheet("""
                QPushButton{
                    border-radius:10px;
                    background-image: url(../gui/Images/IMG_lancer.png);
                }
                QPushButton:hover{
                    background-image: url(../gui/Images/IMG_lancer_hover.png);
                }""")

            self.save_new_face = False
            
            # Rerun read db so new npz file can be detected
            self.facerec.read_db(self.databases)



    """
    def button_valider_clicked(self):
        user_input = x_min.text()
        # Traitez l'entrée de l'utilisateur ici
        print("Entrée de l'utilisateur :", user_input)
        dialog.accept()
    return x_min, x_max, y_min, y_max
    """
    
    
    def ToggleButonFaceBody_clicked(self):
        if self.body_detection:
            self.ToggleButonFaceBody.setStyleSheet("""
                    QPushButton{
                        border-radius:10px;
                        background-image: url(../gui/Images/IMG_bouton_visage.png);
                    }
                    QPushButton:hover{
                        background-image: url(../gui/Images/IMG_bouton_visage_hover.png);
                    }""")
            
            self.stop()
            
            # switch to face
            self.init_face()

            self.body_detection = False
            self.face_detection = True
            
        else:
            self.ToggleButonFaceBody.setStyleSheet("""
                    QPushButton{
                        border-radius:10px;
                        background-image: url(../gui/Images/IMG_bouton_corps.png);
                    }
                    QPushButton:hover{
                        background-image: url(../gui/Images/IMG_bouton_corps_hover.png);
                    }""")
            
            self.stop()
            
            # switch to body
            self.init_body()
            
            self.body_detection = True
            self.face_detection = False
            
        print('changement de mode')


    def QuitterBouton_clicked(self):
        self.close()

    def is_numeric(self, nombre):
        try:
            return int(nombre)

        except ValueError:
            return False

    def stop(self):
        #self.timer.stop()
        self.device.close()
        #self.pipeline.reset()
        self.frame = None
        
