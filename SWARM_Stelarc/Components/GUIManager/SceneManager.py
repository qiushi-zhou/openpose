# -*- coding: utf-8 -*-
from ..SwarmComponentMeta import SwarmComponentMeta
import threading

class SceneDrawerType:
    PYGAME = 'pygame'
    OPENCV = 'opencv'
    NONE = 'None'
    
class SceneManager(SwarmComponentMeta):
    def __init__(self, app_logger, ui_drawer, tasks_manager, drawer_type, screen_w=500, screen_h=500, font_size=16):
        super(SceneManager, self).__init__(ui_drawer, tasks_manager, "SceneManager")
        self.app_logger = app_logger
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.drawer_type = drawer_type
        self.read_lock = threading.Lock()
        if self.drawer_type == SceneDrawerType.PYGAME:
            import pygame
            self.pygame = pygame
            self.pygame.init()
            self.pygame.display.set_mode((int(self.screen_w + self.screen_w*0.24), self.screen_h))
            self.pygame.display.set_caption("SWARM")
            self.screen = self.pygame.display.get_surface()
            self.sceneClock = self.pygame.time.Clock()
            self.font = self.pygame.font.SysFont('Cascadia', font_size)
            self.ui_drawer.set_drawer(self.pygame)
            self.ui_drawer.add_surface(self.screen, self.tag)
            self.ui_drawer.set_font(self.font, font_size)
            # self.ui_drawer.set_font(self.font, font_size, line_height=font_size*0.7)
            # log.add_widget(PyGameLogWidget(pygame=pygame, font=self.font, font_size=Constants.font_size, canvas=self.scene.screen))
        elif self.drawer_type == SceneDrawerType.OPENCV:
            import cv2
            self.cv2 = cv2
            self.ui_drawer.set_drawer(self.cv2, self.screen)
            self.ui_drawer.set_font(None, 0.4)

        self.screen_delay = 0
        self.backgroundColor = (0, 0, 0)
    
    def update_config(self):
        pass
            
    def update_config_data(self, data, last_modified_time):
        pass

    def draw_rect_alpha(self, color, rect):
        shape_surf = self.pygame.Surface(self.pygame.Rect(rect).size, self.pygame.SRCALPHA)
        self.pygame.draw.rect(shape_surf, color, shape_surf.get_rect())
        self.screen.blit(shape_surf, rect)

    def update(self, frame, debug=False, surfaces=None):
        if debug:
            print(f"Updating Scene Manager!")
            if frame is None:
                print(f"Frame in update is None!")
        if self.drawer_type == SceneDrawerType.PYGAME:
            self.screen_delay = self.sceneClock.tick()
            self.ui_drawer.draw_frame(self.backgroundColor, frame, self.tag)
            rect = (self.screen_w/2, self.screen_h/2, self.screen_w/2, self.screen_h/2)
            self.draw_rect_alpha((0,0,0,220), rect)
            rect = (self.screen_w, 0, self.screen_w/2, self.screen_h)
            self.draw_rect_alpha((0,0,0,220), rect)
    
    def draw(self, debug=True, surfaces=None):
        if debug:
            print(f"Draw Scene Manager!")
        self.ui_drawer.flush_text_lines(debug=False, draw=True, s_names=surfaces)
        if self.drawer_type == SceneDrawerType.PYGAME:
            self.pygame.display.flip()
