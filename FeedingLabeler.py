import tkinter as tk
from tkinter.filedialog import askopenfilenames, askdirectory
import os
import cv2
import PIL.Image, PIL.ImageTk
import pandas as pd
from tkinter import messagebox
import numpy as np
from SEQReader import SEQReader
import tkinter.ttk as ttk


class FeedingLabeler:
    ORIGINAL_WIDTH = 1920
    ORIGINAL_HEIGHT = 1080
    MOVIE_PREFIX = 'cutout'  # movie file name prefix

    def __init__(self,fps=30,padding=325):
        """ Initialize a new instance of the FeedingLabeler application."""
         # This is a tkinter based GUI
         # Main consideration was that it should function well cross-platform, as it was developed in a Mac environment
        # and designated to run in a Windows environment.
        self.window = tk.Tk()
        self.height = int(2*self.ORIGINAL_HEIGHT/3)
        self.width = int(2*self.ORIGINAL_WIDTH/3)
        self.window.geometry(f"{self.width:d}x{self.height:d}")
        # Define the widgets containing the labels for the videos:
        self.define_btns()
        self.pause = True  # Play/pause marker, to make the play button function as a pause as well
        self.centroid = (0,0)
        self.fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        self.fps = fps
        self.padding = padding
        self.last_frame_written = 0
        self.vid_loaded = False
        self.log = pd.DataFrame(columns=['source_vid','start_frame','coords','num_frames'])
        # Set the layout of the labeling window:
        self.set_layout()
        # This will be our video player once we load some movies, see the get_dir method:
        self.player = []
        self.window.wm_title("Feeding Labeler")
        # define what happens when the GUI window is closed by user:
        self.window.wm_protocol("WM_DELETE_WINDOW", self.on_close)
        self.window.mainloop()  # Start the main event loop of the GUI

    def define_btns(self):
        self.video_panel = tk.Canvas(master=self.window, width=700, height=500)
        self.video_panel.bind('<Button-1>', self.displayclick)
        self.video_panel.bind('<Button-2>', self.removeclick)
        self.frm_admin_btns = tk.Frame(master=self.window)
        self.btn_load = tk.Button(master=self.frm_admin_btns, text = 'load video',command=self.load_vid)
        self.btn_save_seg = tk.Button(master=self.frm_admin_btns, text='save segment', command=self.save_segment)
        self.frm_vid_btns = tk.Frame(master=self.window)
        self.btn_back = tk.Button(master=self.frm_vid_btns, relief= 'raised',
                                  text="\N{LEFTWARDS ARROW}",width=3,height=3,
                                   command=self.prev_frame)
        self.btn_next = tk.Button(master=self.frm_vid_btns, relief= 'raised',
                                  text="\N{RIGHTWARDS ARROW}",width=3,height=3,
                                   command=self.next_frame)
        # Play button:
        self.btn_play = tk.Button(master=self.frm_vid_btns,bg='blue',relief= 'raised',
                                  text='Play/Pause',width=10,height=3,
                                  command=self.play_vid)
        self.btn_rewind = tk.Button(master=self.frm_vid_btns,bg='pink',relief='raised', text= 'Rewind',
                                    width=3, height=3, command=self.rewind)
        self.btn_play.bind('<Button-1>', self.handle_play)  # Set the play/pause marker
        self.lbl_frame_centroid = tk.Label(master=self.frm_admin_btns, text='',fg='red')

    def set_layout(self):
        """ Layout all the GUI widgets"""
        #self.window.columnconfigure(0, weight=1)
        #self.window.rowconfigure(0, weight=1)
        self.btn_load.pack(expand=0,pady=10)#.grid(row=0, column=0, sticky='e', pady=10)
        self.btn_save_seg.pack(expand=0)#.grid(row=1, column=0, sticky='e', pady=10)
        self.lbl_frame_centroid.pack(expand=1,side=tk.BOTTOM,pady=200)
        self.frm_admin_btns.pack(expand=0,side=tk.LEFT)#.grid(row=0,column=0, sticky='nsew')
        self.frm_vid_btns.grid_columnconfigure(4, weight=1, uniform='middle')
        self.frm_vid_btns.grid_columnconfigure(11, weight=3, uniform='middle')
        self.frm_vid_btns.grid_columnconfigure(15, weight=1, uniform='middle')
        self.frm_vid_btns.grid_columnconfigure(24, weight=1, uniform='middle')
        self.btn_back.grid(row=0, column=4, sticky="nsew",pady=25, padx=10,columnspan=3)
        self.btn_play.grid(row=0, column=11, sticky="nsew",pady=25, padx=10)
        self.btn_rewind.grid(row=0, column=15, sticky='nsew',pady=25, padx=10,columnspan=3)
        self.btn_next.grid(row=0, column=24, sticky="nsew",pady=25, padx=10,columnspan=3)
        self.video_panel.pack(expand=1, fill=tk.BOTH,side=tk.TOP)#.grid(row=0, column=1, sticky='nsew')
        self.frm_vid_btns.pack(expand=0, fill=tk.BOTH,side=tk.BOTTOM)#,anchor='center')#.grid(row=1, column=1, sticky='nsew')
        self.video_panel.bind('<Configure>', self._resize_image)

    def _resize_image(self,event):
        if self.vid_loaded:
            self.width = event.width
            self.height = event.height
            self.frame = self.photo_copy.resize((self.width, self.height))
            self.photo = PIL.ImageTk.PhotoImage(image=self.frame)
            self.video_panel.create_image(0, 0, image=self.photo, anchor=tk.NW)

    def load_vid(self):
        self.vidpath = list(askopenfilenames(filetypes=[("Video Files", ["*.mp4", "*.avi", "*.seq"])]))[0]
        print(self.vidpath)
        if not self.vidpath:
            # if no file was chosen, stop the method:
            return
        self.vid_loaded = True
        self.window.title(f"Feeding Analyzer - {self.vidpath}")
        self.vid = SEQReader(self.vidpath)
        self.centroids_by_frm = np.zeros((len(self.vid),2))
        self.save_dir = os.path.join(os.path.dirname(self.vidpath), 'feeding_events')
        if not os.path.exists(self.save_dir):
            os.mkdir(self.save_dir)
        self.display_frame()


    def on_close(self):
        if self.vid_loaded:
            path = os.path.join(os.path.dirname(self.save_dir),'feeding_log.csv')
            self.log.to_csv(path)
        self.window.quit()

    def rewind(self):
        if self.centroids_by_frm[self.vid.frame_pointer,:].sum()>0:
            self.removeclick()
        self.vid.frame_pointer=-1
        self.display_frame()

    def draw_centroid(self):
        if self.centroid!=(0,0) and self.centroid!=(-1,-1) :
            x,y = self.centroid
            x = int(x * self.width)
            y = int(y * self.height)
            self.video_panel.create_oval(x,y,
                                     5+x,5+y,
                                     outline="#f11", width=2)

    def displayclick(self,event):
        self.lbl_frame_centroid.configure(text=f'{event.y/self.height:.3f}, {event.x/self.width:.3f}')
        self.lbl_frame_centroid.update()
        self.video_panel.create_image(0, 0, image=self.photo, anchor=tk.NW)  # Draw the image in the Panel widget
        self.centroid = (event.x/self.width, event.y/self.height)
        self.centroids_by_frm[self.vid.frame_pointer,:] = self.centroid
        self.draw_centroid()

    def removeclick(self, even=False):
        self.centroid = (-1,-1)
        self.video_panel.create_image(0, 0, image=self.photo, anchor=tk.NW)  # Draw the image in the Panel widget
        self.centroids_by_frm[self.vid.frame_pointer, :] = self.centroid
        result = messagebox.askquestion('segment save', 'do you want to save segment?')
        if result=='yes':
            self.save_segment()

    def display_frame(self, event=None,back=False):
        """Read a single frame from the current video and display it onto the GUI."""
        ret, frame = self.vid.read()  # Read a single frame
        self.frame = PIL.Image.fromarray(frame)  # Save that frame
        self.frame_array = frame
        self.frame = self.frame.resize((self.width,self.height))
        self.photo = PIL.ImageTk.PhotoImage(image=self.frame)  # Convert frame to display it on GUI
        self.photo_copy = PIL.Image.fromarray(frame)
        self.video_panel.create_image(0, 0, image=self.photo, anchor=tk.NW)  # Draw the image in the Panel widget
        if not back:
            if self.centroids_by_frm[self.vid.frame_pointer,:].sum() != 0:
                self.centroid = tuple(self.centroids_by_frm[self.vid.frame_pointer,:])
            else:
                self.centroids_by_frm[self.vid.frame_pointer,:] = self.centroid
            self.draw_centroid()
        else:
            self.centroid = tuple(self.centroids_by_frm[self.vid.frame_pointer, :])
            self.draw_centroid()

    def translate_centroid(self,centroid):
        x, y = centroid
        x = int(x * self.ORIGINAL_WIDTH)
        y = int(y * self.ORIGINAL_HEIGHT)
        return x,y

    def get_bounds(self,row,col):
        upper_row = row-self.padding
        bottom_row = row+self.padding
        left_col = col-self.padding
        right_col = col+self.padding
        if upper_row<0:
            bottom_row += abs(upper_row)
            upper_row = 0
        if bottom_row>self.ORIGINAL_HEIGHT:
            upper_row -= (bottom_row-self.ORIGINAL_HEIGHT)
            bottom_row = self.ORIGINAL_HEIGHT
        if left_col<0:
            right_col += abs(left_col)
            left_col = 0
        if right_col>self.ORIGINAL_WIDTH:
            left_col -= (right_col-self.ORIGINAL_WIDTH)
            right_col = self.ORIGINAL_WIDTH
        return upper_row, bottom_row, left_col, right_col

    def save_segment(self,event=False):
        frame_num = self.last_frame_written
        while frame_num < len(self.vid):
            if self.centroids_by_frm[frame_num,:].sum()>0:
                centroid = self.centroids_by_frm[frame_num,:]
                row, col = self.translate_centroid(centroid)
                frm_tmp = frame_num+1
                movie_name = f'frame_{frm_tmp}_coords_{row}-{col}.avi'
                entry = {'source_vid': self.vidpath, 'frame': frm_tmp,'coords':(row,col)}
                movie_path = os.path.join(self.save_dir,movie_name)
                video_writer = cv2.VideoWriter(movie_path, self.fourcc, self.fps,
                                                   (self.padding * 2, self.padding * 2), False)
                for i in range(frame_num,self.centroids_by_frm.shape[0]):
                    centroid = self.centroids_by_frm[i,:]
                    if centroid[0] == -1:
                        print(centroid)
                        break
                    row,col = self.translate_centroid(centroid)
                    upper_row, bottom_row, left_col, right_col = self.get_bounds(row,col)
                    subframe = self.frame_array[upper_row:bottom_row, left_col:right_col]
                    video_writer.write(subframe)
                print(i)
                entry['num_frames'] =i-frame_num
                frame_num = i+1
                video_writer.release()
                self.log = self.log.append(entry,ignore_index=True)
            else:
                frame_num += 1
        self.last_frame_written = i



    def prev_frame(self):
        self.vid.frame_pointer -= 2
        if self.vid.frame_pointer < -1:
            self.vid.frame_pointer = -1
        self.display_frame(back=True)

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