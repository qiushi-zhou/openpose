from .Camera import Camera
from ..SwarmComponentMeta import SwarmComponentMeta

class CamerasManager(SwarmComponentMeta):
    def __init__(self, logger, screen_w=500, screen_h=500):
        self.screen_w = screen_w
        self.screen_h = screen_h
        super(CamerasManager, self).__init__(logger, "CamerasManager", r'./Config/CamerasConfig.yaml', self.update_config_data)
        self.cameras = []
    
    def update_config(self):
      super().update_config_from_file(self.tag, self.config_filename, self.last_modified_time)
        
    def update_config_data(self, data, last_modified_time):
        self.config_data = data
        cameras_data = self.config_data.get("cameras", [])
        for i in range(0, len(cameras_data)):
            if len(self.cameras) <= i:
                self.cameras.append(Camera(i, self.screen_w, self.screen_h, cameras_data[i]))
            else:
                self.cameras[i].update_config(self.screen_w, self.screen_h, cameras_data[i])
        self.last_modified_time = last_modified_time      
    
    def update(self, *args, **kwargs):
        debug = kwargs.get('debug', True)
        if debug:
            print(f"Updating Cameras data")
        for camera in self.cameras:
            if camera.enabled:
                camera.update_graph()
                
    def draw(self, *args, **kwargs):
        draw_graph_data = kwargs.get('draw_graph_data', True)
        for i in range(0, len(self.cameras)):
            camera = self.cameras[i]
            camera.draw_debug(self.logger, draw_graph_data=draw_graph_data)