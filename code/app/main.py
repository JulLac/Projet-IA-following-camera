# coding=utf-8
import os
import argparse
import time
from Mouvement import Mouvement_camera
import random

import blobconverter
import cv2
import depthai as dai
import numpy as np
from MultiMsgSync import TwoStageHostSeqSync
from textHelper import TextHelper
from faceRecognition import FaceRecognition


def tourner_camera(object_camera, xmin, xmax, ymin, ymax):
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


def frame_norm(frame, bbox):
    normVals = np.full(len(bbox), frame.shape[0])
    normVals[::2] = frame.shape[1]
    return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)

parser = argparse.ArgumentParser()
parser.add_argument("-name", "--name", type=str, help="Name of the person for database saving")

args = parser.parse_args()

object_camera = Mouvement_camera(1, 1, 0.45, 0.55, 0.45, 0.55)
object_camera.centrer()

VIDEO_SIZE = (1072, 1072)
databases = "databases"
if not os.path.exists(databases):
    os.mkdir(databases)

print("Creating pipeline...")
pipeline = dai.Pipeline()

print("Creating Color Camera...")
cam = pipeline.create(dai.node.ColorCamera)
# For ImageManip rotate you need input frame of multiple of 16
cam.setPreviewSize(1072, 1072)
cam.setVideoSize(VIDEO_SIZE)
cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
cam.setInterleaved(False)
cam.setBoardSocket(dai.CameraBoardSocket.RGB)

host_face_out = pipeline.create(dai.node.XLinkOut)
host_face_out.setStreamName('rgb')
cam.video.link(host_face_out.input)

# ImageManip as a workaround to have more frames in the pool.
# cam.preview can only have 4 frames in the pool before it will
# wait (freeze). Copying frames and setting ImageManip pool size to
# higher number will fix this issue.
copy_manip = pipeline.create(dai.node.ImageManip)
cam.preview.link(copy_manip.inputImage)
copy_manip.setNumFramesPool(20)
copy_manip.setMaxOutputFrameSize(1072 * 1072 * 3)

# ImageManip that will crop the frame before sending it to the Face detection NN node
face_det_manip = pipeline.create(dai.node.ImageManip)
face_det_manip.initialConfig.setResize(300, 300)
copy_manip.out.link(face_det_manip.inputImage)

# NeuralNetwork
print("Creating Face Detection Neural Network...")
face_det_nn = pipeline.create(dai.node.MobileNetDetectionNetwork)
face_det_nn.setConfidenceThreshold(0.5)
face_det_nn.setBlobPath(blobconverter.from_zoo(name="face-detection-retail-0004", shaves=6))
# Link Face ImageManip -> Face detection NN node
face_det_manip.out.link(face_det_nn.input)

face_det_xout = pipeline.create(dai.node.XLinkOut)
face_det_xout.setStreamName("detection")
face_det_nn.out.link(face_det_xout.input)

# Script node  allows users to run custom Python scripts on the device
# It will take the output from the face detection NN as an input and set ImageManipConfig
# to the 'age_gender_manip' to crop the initial frame
script = pipeline.create(dai.node.Script)
script.setProcessor(dai.ProcessorType.LEON_CSS)

face_det_nn.out.link(script.inputs['face_det_in'])
# We also interested in sequence number for syncing
face_det_nn.passthrough.link(script.inputs['face_pass'])

copy_manip.out.link(script.inputs['preview'])

with open("script.py", "r") as f:
    script.setScript(f.read())

print("Creating Head pose estimation NN")

headpose_manip = pipeline.create(dai.node.ImageManip)
headpose_manip.initialConfig.setResize(60, 60)
headpose_manip.setWaitForConfigInput(True)
script.outputs['manip_cfg'].link(headpose_manip.inputConfig)
script.outputs['manip_img'].link(headpose_manip.inputImage)

headpose_nn = pipeline.create(dai.node.NeuralNetwork)
headpose_nn.setBlobPath(blobconverter.from_zoo(name="head-pose-estimation-adas-0001", shaves=6))
headpose_manip.out.link(headpose_nn.input)

headpose_nn.out.link(script.inputs['headpose_in'])
headpose_nn.passthrough.link(script.inputs['headpose_pass'])

print("Creating face recognition ImageManip/NN")

face_rec_manip = pipeline.create(dai.node.ImageManip)
face_rec_manip.initialConfig.setResize(112, 112)
face_rec_manip.inputConfig.setWaitForMessage(True)

script.outputs['manip2_cfg'].link(face_rec_manip.inputConfig)
script.outputs['manip2_img'].link(face_rec_manip.inputImage)

face_rec_nn = pipeline.create(dai.node.NeuralNetwork)
face_rec_nn.setBlobPath(blobconverter.from_zoo(name="face-recognition-arcface-112x112", zoo_type="depthai", shaves=6))
face_rec_manip.out.link(face_rec_nn.input)

arc_xout = pipeline.create(dai.node.XLinkOut)
arc_xout.setStreamName('recognition')
face_rec_nn.out.link(arc_xout.input)

with dai.Device(pipeline) as device:
    facerec = FaceRecognition(databases, args.name)
    sync = TwoStageHostSeqSync()
    text = TextHelper()

    queues = {}
    # Create output queues
    for name in ["rgb", "detection", "recognition"]:
        queues[name] = device.getOutputQueue(name)

    last_exec_time = time.time()  # initialize the last execution time to 0
    while True:
        for name, q in queues.items():
            # Add all msgs (color frames, object detections and face recognitions) to the Sync class.
            if q.has():
                sync.add_msg(q.get(), name)

        msgs = sync.get_msgs()
        if msgs is not None:
            frame = msgs["rgb"].getCvFrame()
            dets = msgs["detection"].detections

            if args.name:
                for i, detection in enumerate(dets):
                    bbox = frame_norm(frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))
                    cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (10, 245, 10), 2)

                    features = np.array(msgs["recognition"][i].getFirstLayerFp16())
                    conf, name = facerec.new_recognition(features)
                    text.putText(frame, f"{name} {(100 * conf):.0f}%", (bbox[0] + 10, bbox[1] + 35))

            else:
                # Only execute the for loop if 5 seconds have passed since the last execution
                if len(dets) > 0:
                    object_camera.reset()
                    if time.time() - last_exec_time >= 0.35:
                        best_detection = None
                        is_unknown = 1
                        best_index = None
                        for i, detection in enumerate(dets):
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
                            bbox = frame_norm(frame, (
                            best_detection.xmin, best_detection.ymin, best_detection.xmax, best_detection.ymax))
                            # print(detection.xmin, detection.ymin, detection.xmax, detection.ymax)
                            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (10, 245, 10), 2)

                            features = np.array(msgs["recognition"][best_index].getFirstLayerFp16())
                            conf, name = facerec.new_recognition(features)
                            text.putText(frame, f"{name} {(100 * conf):.0f}%", (bbox[0] + 10, bbox[1] + 35))

                            tourner_camera(object_camera, best_detection.xmin, best_detection.xmax, best_detection.ymin,
                                           best_detection.ymax)

                        last_exec_time = time.time()  # update the last execution time
                else:
                    if time.time() - last_exec_time >= 8:
                        object_camera.balayage()
                        last_exec_time = time.time()  # update the last execution time

            cv2.imshow("rgb", cv2.resize(frame, (800, 800)))

        if cv2.waitKey(1) == ord('q'):
            break
