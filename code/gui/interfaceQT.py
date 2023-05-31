#import blobconverter
import cv2
import numpy as np
from PyQt5 import uic, QtCore
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel, QPushButton, QDialog, QVBoxLayout, QLineEdit, QCheckBox, QMainWindow
#import depthai as dai
import sys

# tell interpreter where to look
sys.path.insert(0, "..")
#from app.textHelper import TextHelper
#from app.faceRecognition import FaceRecognition
#from app.MultiMsgSync import TwoStageHostSeqSync
from app.Mouvement import Mouvement_camera


class InterfaceQT(QMainWindow):
    def __init__(self):
        super(InterfaceQT, self).__init__()
        try:
            uic.loadUi("../gui/assets/Interface_ProjetIA.ui", self)
        except FileNotFoundError:
            print("Could not find the UI file.")
            sys.exit(1)


        #self.check = 0
        self.object_camera = Mouvement_camera(1, 1, 0.45, 0.55, 0.45, 0.55)
        """
        self.object_camera.centrer()

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

        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("-name", "--name", type=str, help="Name of the person for database saving")

        self.args = self.parser.parse_args()

        self.databases = "databases"
        if not os.path.exists(self.databases):
            os.mkdir(self.databases)

        self.facerec = FaceRecognition(self.databases, "Mathieu")  # self.args.name)
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

        self.label = self.findChild(QLabel, "label_2")
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(1)
        """
        self.cap = cv2.VideoCapture(0)

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


    def clickBox(self, state):
        if state == QtCore.Qt.Checked:
            print('Checked')
        else:
            print('Unchecked')

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

    def update_frame(self):
        # Get frame from video stream
        ret, self.frame = self.cap.read()

        # Display the resulting frame
        #¶cv2.imshow('frame', self.frame)

        # the 'q' button is set as the
        # quitting button you may use any
        # desired button of your choice


        """ 
        for name, q in self.queues.items():
            # Add all msgs (color frames, object detections and face recognitions) to the Sync class.
            if q.has():
                self.sync.add_msg(q.get(), name)

        self.msgs = self.sync.get_msgs()
        if self.msgs is not None:
            self.frame = self.msgs["rgb"].getCvFrame()
            self.dets = self.msgs["detection"].detections

            # print(self.check)

            # if args.name:
            if self.check == 2:
                # print("enregistrement face")
                for i, detection in enumerate(self.dets):
                    bbox = self.frame_norm(self.frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))
                    cv2.rectangle(self.frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (240, 10, 10), 2)

                    features = np.array(self.msgs["recognition"][i].getFirstLayerFp16())
                    conf, name = self.facerec.new_recognition(features)
                    self.text.putText(self.frame, f"{name} {(100 * conf):.0f}%", (bbox[0] + 10, bbox[1] + 35))

            else:
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
                            bbox = self.frame_norm(self.frame, (
                            best_detection.xmin, best_detection.ymin, best_detection.xmax, best_detection.ymax))
                            # print(detection.xmin, detection.ymin, detection.xmax, detection.ymax)
                            cv2.rectangle(self.frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (10, 245, 10), 2)

                            features = np.array(self.msgs["recognition"][best_index].getFirstLayerFp16())
                            conf, name = self.facerec.new_recognition(features)
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
            """

    def BoutonAuto_clicked(self):
        self.check = 1
        print(self.check)
        self.object_camera.set_max_degre_x_gauche(-90)
        self.object_camera.set_max_degre_x_droite(90)
        self.object_camera.set_max_degre_y_haut(-90)
        self.object_camera.set_max_degre_y_bas(90)

    def get_line_edit_value(self, line_edit):
        return line_edit.text()

    def BoutonBrider_clicked(self):
        print("BoutonBrider push")
        self.check = 2
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
        a = 2
        # if self.check == 0:
        #    msg = QMessageBox()
        #    msg.setWindowTitle("Face Tracking")
        #    msg.setText("Veuillez vous enregistrer avant de lancer le suivi de caméra")
        #    msg.setIcon(QMessageBox.Information)
        #    msg.setStandardButtons(QMessageBox.Ok)
        #    msg.exec_()
        # else:
        #    self.check = 0


    """
    def button_valider_clicked(self):
        user_input = x_min.text()
        # Traitez l'entrée de l'utilisateur ici
        print("Entrée de l'utilisateur :", user_input)
        dialog.accept()
    return x_min, x_max, y_min, y_max
    """

    def QuitterBouton_clicked(self):
        self.close()

    def is_numeric(self, nombre):
        try:
            return int(nombre)

        except ValueError:
            return False

    def stop(self):
        self.timer.stop()
        self.device.close()
        self.pipeline.reset()
