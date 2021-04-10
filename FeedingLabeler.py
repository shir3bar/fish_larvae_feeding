import tkinter as tk
from tkinter.filedialog import askopenfilenames, askdirectory
import os
import cv2
import PIL.Image, PIL.ImageTk
import pandas as pd
from tkinter import messagebox
import numpy as np
from SEQReader import SEQReader


class FeedingLabeler:
    def __init__(self):
        """ Initialize a new instance of the FeedingLabeler application."""
         # This is a tkinter based GUI
         # Main consideration was that it should function well cross-platform, as it was developed in a Mac environment
        # and designated to run in a Windows environment.
        self.window = tk.Tk()
        # Define the widgets containing the labels for the videos:
        self.define_btns()
        self.pause = True  # Play/pause marker, to make the play button function as a pause as well
        # Set the layout of the labeling window:
        self.set_layout()
        # This will be our video player once we load some movies, see the get_dir method:
        self.player = []
        self.window.wm_title("Fish Labeler")
        # define what happens when the GUI window is closed by user:
        self.window.wm_protocol("WM_DELETE_WINDOW", self.on_close)
        self.window.mainloop()  # Start the main event loop of the GUI

    def define_btns(self):
        self.video_panel = tk.Canvas(master=self.window, width=800, height=500)
        self.frm_admin_btns = tk.Frame(master=self.window)
        self.btn_load = tk.Button(master=self.frm_admin_btns, text = 'load video',command=self.load_vid)
        self.btn_save_seg = tk.Button(master=self.frm_admin_btns, text='save segment', command=self.save_segment)
        self.frm_vid_btns = tk.Frame(master=self.window)
        self.btn_back = tk.Button(master=self.frm_vid_btns, text="\N{LEFTWARDS ARROW}",command=self.prev_frame)
        self.btn_next = tk.Button(master=self.frm_vid_btns, text="\N{RIGHTWARDS ARROW}", command=self.next_frame)
        # Play button:
        self.btn_play = tk.Button(master=self.frm_vid_btns, text='Play/Pause', command=self.play_vid)
        self.btn_play.bind('<Button-1>', self.handle_play)  # Set the play/pause marker
        self.lbl_frame_centroid = tk.Label(master=self.frm_vid_btns, text='')

    def set_layout(self):
        """ Layout all the GUI widgets"""
        self.btn_load.grid(row=0, column=0, sticky='e', pady=10)
        self.btn_save_seg.grid(row=1, column=0, sticky='e', pady=10)
        self.frm_admin_btns.grid(row=0,column=0, sticky='nsew')
        self.btn_back.grid(row=0, column=2, sticky="e", padx=10)
        self.btn_play.grid(row=0, column=3, sticky="e", padx=10)
        self.btn_next.grid(row=0, column=4, sticky="e", padx=10)
        self.lbl_frame_centroid.grid(row=0, column=6, sticky="e", padx=10)
        self.video_panel.grid(row=0, column=1, sticky='nsew')
        self.frm_vid_btns.grid(row=1, column=1, sticky='nsew')

    def load_vid(self):
        self.vidpath = list(askopenfilenames(filetypes=[("Video Files", ["*.mp4", "*.avi", "*.seq"])]))
        print(self.vidpath)
        if not self.vidpath:
            # if no file was chosen, stop the method:
            return
        self.window.title(f"Feeding Analyzer - {self.vidpath[0]}")
        self.vid = SEQReader(self.vidpath[0])

    def on_close(self):
        self.window.quit()

    def display_frame(self, event=None):
        """Read a single frame from the current video and display it onto the GUI."""
        ret, frame = self.vid.read()  # Read a single frame
        self.frame = frame  # Save that frame
        self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))  # Convert frame to display it on GUI
        self.video_panel.create_image(0, 0, image=self.photo, anchor=tk.NW)  # Draw the image in the Panel widget

    def save_segment(self):
        pass

    def prev_frame(self):
        self.vid.frame_pointer -= 2
        self.display_frame()

    def next_frame(self):
        self.display_frame()

    def handle_play(self, event=None):
        """ Handle play button click, if it is clicked once turn it into a pause button."""
        self.pause = not self.pause  # Now when the "Play" button will be clicked again it will pause the video

    def play_vid(self,event=None,play_speed=15):
        """ This method plays the video file currently loaded to the GUI.
        The video is played by recursively calling this method using the window.after() tkinter method.
        The method will stop when the video is paused or reaches its end.
        This method is invoked either by pressing the play button, or by pressing the 0 key.

        """
        if event:
            # if the method was invoked via key stroke, then call the method that handles the play/pause functionality:
            self.handle_play()

        try:
            # Now, as long as pause isn't pressed, and the video doesn't end, sequentially display frames:
            if not self.pause:
                # pause hasn't been pressed
                self.display_frame()  # display a single frame
                # The main driving force behind the method, recursively calling the method again after 15 milliseconds:
                self.window.after(play_speed, self.play_vid)
        except AttributeError:
            # If the video reached its end tkinter will raise an AttributeError, we'll catch it and reset the video:
            self.vid.frame_pointer = -1  # Rewind the video capture object to frame
            self.display_frame()  # display the first frame
            self.pause = not self.pause  # Change the status of the play/pause button from "Pause" to "Play"

if __name__ == '__main__':
    FeedingLabeler()