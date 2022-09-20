from .WebSocketVideoStream import WebSocketVideoStream
from .WebSocketInteraction import WebSocketInteraction
from .WebSocketMeta import WebSocketMeta
from ..SwarmComponentMeta import SwarmComponentMeta
import pygame
import socketio


class WebSocketsManager(SwarmComponentMeta):
    def __init__(self, logger, tasks_manager, frame_w, frame_h):
        super(WebSocketsManager, self).__init__(logger, tasks_manager, "WebSocketManager", r'./Config/WebSocketConfig.yaml', self.update_config_data)
        self.tasks_manager = tasks_manager
        self.multi_threaded = True
        self.sockets = {}

        self.frame_w = frame_w
        self.frame_h = frame_h
        self.surface = pygame.Surface((frame_w, frame_h))
        self.logger.add_surface(self.surface, self.tag)

    def update_config(self):
        super().update_config_from_file(self.tag, self.config_filename, self.last_modified_time)
        sockets_config = self.config_data.get("sockets", self.sockets)
        for s_config in sockets_config:
            namespace = s_config.get("namespace", None)
            # print(f"Namespace {namespace}")
            if namespace is not None and namespace not in self.sockets:
                url = s_config.get("url", "")
                if "gallery" in namespace:
                    self.sockets[namespace] = WebSocketVideoStream.create_ws(self.tasks_manager, url, namespace, self.frame_w, self.frame_h)
                elif "inter" in namespace:
                    self.sockets[namespace] = WebSocketInteraction.create_ws(self.tasks_manager, url, namespace, self.frame_w, self.frame_h)
                self.sockets[namespace].update_config(s_config)

    def enqueue_frame(self, namespace, cv2_frame, cameras_data, draw=False):
        self.sockets[namespace].enqueue_frame(cv2_frame, cameras_data)
        if draw:
            self.logger.draw_frame((0, 0, 0), cv2_frame, self.tag)

    def get_stream_frame(self, namespace):
        if "inter" in namespace and namespace in self.sockets:
            return self.sockets[namespace].get_latest_received_frame()
        return None

    def update_config_data(self, data, last_modified_time):
        self.config_data = data
        # self.frame_scaling = data.get("frame_scaling", False)
        # self.adaptive_scaling = data.get("frame_adaptive", False)
        # self.min_frame_scaling = data.get("min_frame_scaling", 1)
        # self.fixed_frame_scaling = data.get("fixed_frame_scaling", 1)
        # self.max_frame_scaling = self.fixed_frame_scaling
        # self.send_frames = data.get("send_frames", self.send_frames)
        # self.target_framerate = data.get("target_framerate", 30)
        # self.frame_skipping = data.get("frame_skip", False)
        self.last_modified_time = last_modified_time
    #
    # def get_frame(self, surface):
    #     scaling_factor = self.update_scaling()
    #     image_bytes = io.BytesIO()
    #     subsurface = pygame.transform.scale(surface, (self.frame_w * scaling_factor, self.frame_h * scaling_factor))
    #     pygame.image.save(subsurface, image_bytes, "JPEG")
    #     return image_bytes

    def draw(self, start_pos, debug=False, surfaces=None):
        if debug:
            print(f"Drawing WebSocket Manager")
        dbg_str = "WebSocket "
        if not self.enabled:
            dbg_str += "Disabled"
            start_pos = self.logger.add_text_line(dbg_str, (255, 50, 0), start_pos, surfaces)
        else:
            for key in self.sockets:
                s = self.sockets[key]
                status_dbg_str = f"{s.tag} {s.status_manager.get_status_info()}"
                data_str = f"OUT FPS: {int(s.out_buffer.fps())}, Buff Out: {s.out_buffer.count()}/{s.out_buffer.size()}          "
                data_str += f"IN FPS: {int(s.in_buffer.fps())}, Buff In: {s.in_buffer.count()}/{s.in_buffer.size()}"
                # dbg_str = f"{s.tag} FPS: {int(s.fps_counter.fps)}, Scale: {s.scaling_factor:0.2f},{mt_data} Size: {s.last_file_size}"
                start_pos = self.logger.add_text_line(status_dbg_str, (255, 50, 0), start_pos, surfaces)
                start_pos.y -= self.logger.line_height
                start_pos = self.logger.add_text_line(data_str, (255, 50, 0), start_pos, surfaces)
                # start_pos.y -= self.logger.line_height
                # start_pos = self.logger.add_text_line(in_data, (255, 50, 0), start_pos, surfaces)
