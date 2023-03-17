import time
sync = {}  # Dict of messages -  keys are sequence numbers and the values are lists of messages that correspond to that sequence number.

# So the correct frame will be the first in the list
# For this experiment this function is redundant, since everything
# runs in blocking mode, so no frames will get lost
def get_sync(target_seq):
    """
    returns a list of messages that have been synchronized with the target_seq sequence number.
    """
    seq_remove = [] # Arr of sequence numbers to get deleted
    for seq, msgs in sync.items():
        if seq == str(target_seq):
            # We have synced msgs, remove previous msgs (memory cleaning)
            for rm in seq_remove:
                del sync[rm]
            return msgs
        seq_remove.append(seq) # Will get removed from dict if we find synced sync pair
    return None

def find_frame(target_seq):
    """
    returns the frame (image) that corresponds to the target_seq sequence number.
    """
    if str(target_seq) in sync and "frame" in sync[str(target_seq)]:
        return sync[str(target_seq)]["frame"]


def add_detections(det, seq):
    """
    :param det: list of detections
    :param seq: sequence number
    If the list of detections is empty (i.e., len(det) == 0), it deletes the corresponding sequence number from
    the sync dictionary.
    If the list of detections is not empty, it adds the detections to the sync dictionary under the corresponding
    sequence number, so they can be used later for face recognition.
    """
    # No detections, we can remove saved frame
    if len(det) == 0:
        del sync[str(seq)]
    else:
        # Save detections, as we will need them for face recognition model
        sync[str(seq)]["detections"] = det

def correct_bb(bb):
    """
    Check and adapt the place of a bounding box bb to ensure that its coordinates are valid
    """
    if bb.xmin < 0: bb.xmin = 0.001
    if bb.ymin < 0: bb.ymin = 0.001
    if bb.xmax > 1: bb.xmax = 0.999
    if bb.ymax > 1: bb.ymax = 0.999

while True:
    """
    Check for new data on different input streams using the tryGet() function, until the program is interrupted

    The 1st section waits for new data on the 'rgb' input stream. When new data arrives, it is stored in the sync dictionary along with a sequence number. The sequence number is used to keep track of which frames are associated with which data.

    The 2nd section waits for new data on the 'face_det_in' input stream. When new data arrives, the function add_detections is called to store the face detections in the sync dictionary, along with the associated sequence number.

    The 3rd section waits for new data on the 'headpose_in' input stream. When new data arrives, the function get_sync is called to retrieve the previously stored face detections and frame using the associated sequence number. The face detection bounding box is extracted from the list of detections and passed to correct_bb to ensure that it falls within the image boundaries. The bounding box is then used to create a RotatedRect object that is rotated by the head pose angle. An ImageManipConfig object is then created with the rotated bounding box and sent to the 'manip2_cfg' output stream. The original image is also sent to the 'manip2_img' output stream.
"""
    time.sleep(0.001)
    preview = node.io['preview'].tryGet()
    if preview is not None:
        sync[str(preview.getSequenceNum())] = {}
        sync[str(preview.getSequenceNum())]["frame"] = preview

    face_dets = node.io['face_det_in'].tryGet()
    if face_dets is not None:
        # node.warn(f"New detection start")
        passthrough = node.io['face_pass'].get()
        seq = passthrough.getSequenceNum()
        # node.warn(f"New detection {seq}")
        if len(sync) == 0: continue
        img = find_frame(seq) # Matching frame is the first in the list
        if img is None: continue

        add_detections(face_dets.detections, seq)

        for det in face_dets.detections:
            cfg = ImageManipConfig()
            correct_bb(det)
            cfg.setCropRect(det.xmin, det.ymin, det.xmax, det.ymax)
            cfg.setResize(60, 60)
            cfg.setKeepAspectRatio(False)
            node.io['manip_cfg'].send(cfg)
            node.io['manip_img'].send(img)

    headpose = node.io['headpose_in'].tryGet()
    if headpose is not None:
        # node.warn(f"New headpose")
        passthrough = node.io['headpose_pass'].get()
        seq = passthrough.getSequenceNum()
        # node.warn(f"New headpose seq {seq}")
        # Face rotation in degrees
        r = headpose.getLayerFp16('angle_r_fc')[0] # Only 1 float in there

        msgs = get_sync(seq)
        bb = msgs["detections"].pop(0)
        correct_bb(bb)

        # remove_prev_frame(seq)
        img = msgs["frame"]
        # node.warn('HP' + str(img))
        # node.warn('bb' + str(bb))
        cfg = ImageManipConfig()
        rr = RotatedRect()
        rr.center.x = (bb.xmin + bb.xmax) / 2
        rr.center.y = (bb.ymin + bb.ymax) / 2
        rr.size.width = bb.xmax - bb.xmin
        rr.size.height = bb.ymax - bb.ymin
        rr.angle = r # Rotate the rect in opposite direction
        # True = coordinates are normalized (0..1)
        cfg.setCropRotatedRect(rr, True)
        cfg.setResize(112, 112)
        cfg.setKeepAspectRatio(True)

        node.io['manip2_cfg'].send(cfg)
        node.io['manip2_img'].send(img)
