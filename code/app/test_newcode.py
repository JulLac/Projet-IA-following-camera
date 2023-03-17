import numpy as np  # numpy - manipulate the packet data returned by depthai
import cv2  # opencv - display the video stream
import depthai  # depthai - access the camera and its data packets
import blobconverter  # blobconverter - compile and download MyriadX neural network blobs
import time
from Mouvement import Mouvement_camera

# Create DepthAI pipeline
pipeline = depthai.Pipeline()

VIDEO_SIZE = (1072, 1072)

object_camera=Mouvement_camera(1,1,0.45,0.55,0.45,0.55)
object_camera.centrer()

def tourner_camera(object_camera,xmin,xmax,ymin,ymax):
    #servo 1 horizontal
    #servo 2 vertical
    
    #Donner les coordonnées
    object_camera.setxmax(xmax)
    object_camera.setxmin(xmin)
    object_camera.setymax(ymax)
    object_camera.setymin(ymin)
    object_camera.bouger_camera()
    print("Position caméra après mouvement:")
    print('Horizontal:',object_camera.get_position_horizontal())
    print('Vertical:',object_camera.get_position_vertical())
    print("\n")

    
    
    
# Create ColorCamera node
cam_rgb = pipeline.create(depthai.node.ColorCamera)
cam_rgb.setPreviewSize(300, 300)
# ?
cam_rgb.setInterleaved(False)

# MODEL
detection_nn = pipeline.create(depthai.node.MobileNetDetectionNetwork)
# Set path of the blob (NN model). We will use blobconverter to convert&download the model
# detection_nn.setBlobPath("/path/to/model.blob")
detection_nn.setBlobPath(blobconverter.from_zoo(name='mobilenet-ssd', shaves=6))
#detection_nn.setBlobPath(blobconverter.from_zoo(name='face-recognition-resnet100-arcface-onnx', shaves=6))
detection_nn.setConfidenceThreshold(0.5)

cam_rgb.preview.link(detection_nn.input)

xout_rgb = pipeline.create(depthai.node.XLinkOut)
xout_rgb.setStreamName("rgb")
cam_rgb.preview.link(xout_rgb.input)

xout_nn = pipeline.create(depthai.node.XLinkOut)
xout_nn.setStreamName("nn")
detection_nn.out.link(xout_nn.input)

def frameNorm(frame, bbox):
    normVals = np.full(len(bbox), frame.shape[0])
    normVals[::2] = frame.shape[1]
    return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)


with depthai.Device(pipeline) as device:
    q_rgb = device.getOutputQueue("rgb")
    q_nn = device.getOutputQueue("nn")

    frame = None
    detections = []
    last_exec_time = 0  # initialize the last execution time to 0
    while True:

        in_rgb = q_rgb.tryGet()
        in_nn = q_nn.tryGet()

        if in_rgb is not None:
            frame = in_rgb.getCvFrame()

        if in_nn is not None:
            detections = in_nn.detections
            
        if frame is not None:
            
            # Only execute the for loop if 2.5 seconds have passed since the last execution
            if time.time() - last_exec_time >= 2.5:
                
                detections = sorted(detections, key=lambda detection: detection.confidence, reverse=True)
                
                if len(detections) > 0: 
                    best_detection = detections[0]
                    bbox = frameNorm(frame, (best_detection.xmin, best_detection.ymin, best_detection.xmax, best_detection.ymax))
                    print(best_detection.xmin, best_detection.ymin, best_detection.xmax, best_detection.ymax)
                    cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 0, 0), 2)
                    
                    tourner_camera(object_camera,best_detection.xmin,best_detection.xmax,best_detection.ymin,best_detection.ymax)
                    
                last_exec_time = time.time()  # update the last execution time
                
            cv2.imshow("preview", cv2.resize(frame, (800,800)))

        if cv2.waitKey(1) == ord('q'):
            break
