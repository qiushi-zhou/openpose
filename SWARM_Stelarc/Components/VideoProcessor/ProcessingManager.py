from ..SwarmComponentMeta import SwarmComponentMeta
import threading
import cv2
import time
from collections import deque
from ..Utils.utils import Point
from ..Utils.FPSCounter import FPSCounter


class FrameData:
    def __init__(self, tracks=None, keypoints=None, frame=None):
        self.tracks = [] if tracks is None else tracks
        self.keypoints = [] if keypoints is None else keypoints
        self.frame = None if frame is None else frame
        self.processed = False

class ProcessingManager(SwarmComponentMeta):
    def __init__(self, tag, app_logger, ui_drawer, tasks_manager, camera_manager=None, cont_color=(0, 255, 0)):
        self.app_logger = app_logger
        self.processing_type = "simple"
        self.input = None
        super(ProcessingManager, self).__init__(ui_drawer, tasks_manager, "ProcessingManager")
        self.cameras = camera_manager.cameras if camera_manager is not None else []
        self.processed_frame_data = None
        self.multi_threaded = False
        self.background_task = self.tasks_manager.add_task(f"OP_{tag}", None, self.processing_loop, None)
        self.processing_lock = threading.Lock()
        self.processed_lock = threading.Lock()
        self.buffer_size = 2
        self.frames_to_process = deque([])
        self.frames_processed = deque([])
        self.fps_counter = FPSCounter()
        self.cont_color = cont_color
        self.avg_processing_time = 0
        self.total_processing_time = 0
        self.proc_time_count = 0
        self.op_lock = threading.Lock()

    def init(self):
        if not self.multi_threaded:
            if self.background_task.is_running():
                print(f"Stopping {self.background_task.name} background task")
                self.background_task.stop()
        else:
            if not self.background_task.is_running():
                print(f"Starting {self.background_task.name} background task")
                self.background_task.start()

    def update_config(self):
        if self.processing_type == "op" and self.input is None:
            from . import Input
            print(f"Initializing input for OP")
            self.input = Input.Input()

    def update_config_data(self, data, last_modified_time):
        pass

    def processing_loop(self, task_manager=None, async_loop=None):
        if len(self.frames_to_process) <= 0:
            time.sleep(0.001)
            return True
        with self.processing_lock:
            to_process = self.frames_to_process.popleft()
        processed = to_process
        try:
            start = time.time()
            processed = self.process_frame(to_process)
            self.total_processing_time += time.time() - start
            self.proc_time_count += 1
        except Exception as e:
            pass
        with self.processed_lock:
            self.avg_processing_time = self.total_processing_time / self.proc_time_count
            if self.proc_time_count > 10:
                self.proc_time_count = 0
                self.total_processing_time = 0
            self.frames_processed.append(processed)
        return True

    def process_frame(self, to_process):
        if to_process is None:
            return FrameData()
        try:
            if self.processing_type == "op":
                with self.op_lock:
                    tracks, keypoints, updated_frame = self.input.update_trackers(to_process.frame)
                    to_process.processed = True
            elif self.processing_type == "simple":
                with self.op_lock:
                    tracks, keypoints, updated_frame = self.simple_processing(to_process.frame)
                    to_process.processed = True
            elif self.processing_type == "dancing":
                with self.op_lock:
                    tracks, keypoints, updated_frame = self.input.dancing_processing(to_process.frame)
                    to_process.processed = True
            else:
                tracks, keypoints, updated_frame = (None, None, to_process.frame)
                to_process.processed = False
            self.fps_counter.update(1)
            to_process.tracks = tracks
            to_process.keypoints = keypoints
            if updated_frame is not None:
                to_process.frame = updated_frame
            return to_process
        except Exception as e:
            print(f"Error processing frame: {e}")
        return to_process

    def simple_processing(self, frame):
        if frame is None:
            return None, None, None
        imgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ret, thresh = cv2.threshold(imgray, 127, 255, 0)
        contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        frame = cv2.blur(frame, (51,51), borderType=cv2.BORDER_DEFAULT)
        frame = cv2.drawContours(frame, contours, -1, self.cont_color, 1)
        return None, None, frame

    def get_processed_frame(self, camera_frame, return_last=True):
        if camera_frame is not None:
            # camera_frame = camera_frame.copy()
            if self.multi_threaded:
                if len(self.frames_to_process) < self.buffer_size:
                    self.frames_to_process.append(FrameData(frame=camera_frame))
                if len(self.frames_processed) > 0:
                    self.processed_frame_data = self.frames_processed.popleft()
                    return self.processed_frame_data.frame
            else:
                self.processed_frame_data = self.process_frame(FrameData(frame=camera_frame))
                return self.processed_frame_data.frame
        if return_last:
            return None if self.processed_frame_data is None else self.processed_frame_data.frame
        return None


    def update(self, debug=False, surfaces=None):
        if debug:
            print(f"Updating Openpose Manager")
        # Reset graphs to get new points

        for camera in self.cameras:
            camera.p_graph.init_graph()

        if self.processed_frame_data is None or self.processed_frame_data.tracks is None:
            return

        for track in self.processed_frame_data.tracks:
            color = (255, 255, 255)
            if not track.is_confirmed():
                color = (0, 0, 255)
            bbox = track.to_tlbr()
            p1 = Point(int(bbox[0]), int(bbox[1]))
            p2 = Point(int(bbox[2]), int(bbox[3]))
            min_p = Point(min(p1.x, p2.x), min(p1.y, p2.y))
            chest_offset = Point(0, 0)
            # ((x1+x2)/2, (y1+y2)/2).
            center_x, center_y = (min_p.x + ((p2.x-p1.x)/2) + chest_offset.x,min_p.y + ((p2.y-p1.y)/2) + chest_offset.y)
            center_p = Point(center_x, center_y)
            color = (0, 255, 0)
            thickness = 1
            if track.is_confirmed():
                for pair in self.input.POSE_PAIRS:
                    idFrom = self.input.BODY_PARTS[pair[0]]
                    idTo = self.input.BODY_PARTS[pair[1]]
                    points = track.last_seen_detection.pose
                    if points[idFrom] is not None and points[idTo] is not None:
                        kp1 = points[idFrom]
                        kp2 = points[idTo]
                        p1 = Point(kp1[0], kp1[1])
                        p2 = Point(kp2[0], kp2[1])
                        if p1.x > 1 and p1.y > 1 and p2.x > 1 and p2.y > 1:
                            self.ui_drawer.draw_line(p1, p2, color, thickness, surfaces)

            for camera in self.cameras:
                # camera.check_track([p1,p2], center_p)
                camera.check_track([center_p], center_p)
            if debug:
                print(f"Center: ({center_x:.2f}, {center_y:.2f})")

    def draw(self, text_pos, debug=False, surfaces=None):
        text_pos = self.ui_drawer.add_text_line(f"{self.tag} - Time: {self.avg_processing_time:.3f} FPS: {self.fps_counter.fps}, To process: {len(self.frames_to_process)}, Processed: {len(self.frames_processed)}", (255, 255, 0), text_pos, surfaces)
        text_pos.y -= self.ui_drawer.line_height
