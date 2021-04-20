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
    KEYS_TO_LABELS = {'2': 'Feeding I&O', '3': 'Spitting', '5': 'Feeding Success',
                      '7': 'Delete Video', '8': 'Other', '9': 'Feeding Fail', '-': 'Swimming'}

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
        self.pause = True  # Play/pause marker, to make the play button function as a pause as well
        self.centroid = (0,0)
        self.fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        self.fps = fps
        self.padding = padding
        self.last_frame_written = 0
        self.vid_loaded = False
        self.label = tk.StringVar()  # this variable will hold the label for the current video
        self.define_btns()
        self.log = pd.DataFrame(columns=['source_vid','start_frame','coords','num_frames','label','comments'])
        # Set the layout of the labeling window:
        self.set_layout()
        # This will be our video player once we load some movies, see the get_dir method:
        self.window.wm_title("Feeding Labeler")
        # define what happens when the GUI window is closed by user:
        self.window.wm_protocol("WM_DELETE_WINDOW", self.on_close)
        self.window.mainloop()  # Start the main event loop of the GUI

    def define_btns(self):
        self.video_panel = tk.Canvas(master=self.window, width=700, height=500)
        self.video_panel.bind('<Configure>', self._resize_image)
        self.video_panel.bind('<Button-1>', self.displayclick)
        self.video_panel.bind('<Button-2>', self.removeclick)
        self.frm_admin_btns = tk.Frame(master=self.window)
        self.btn_load = tk.Button(master=self.frm_admin_btns, text = 'load video',command=self.load_vid)
        self.btn_save_seg = tk.Button(master=self.frm_admin_btns, text='save segment', command=self.removeclick)
        self.define_label_frm()
        self.lbl_frame_centroid = tk.Label(master=self.frm_admin_btns, text='', fg='red')
        self.define_vid_frm()
        self.window.bind('<Key>', self.handle_keystroke)

    def define_vid_frm(self):
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

    def define_label_frm(self):
        self.comment=''
        self.frm_label = tk.Frame(master=self.frm_admin_btns)
        self.btn_labels = []
        label_list = ['Feeding Success','Feeding Fail','Feeding I&O','Spitting','Other']
        for label_name in label_list:
            self.btn_labels.append(tk.Radiobutton(master=self.frm_label, text=label_name, variable=self.label,
                                                  value=label_name, command=self.set_label))
        self.label.set(None)  # No default value
        self.lbl_comment = tk.Label(master=self.frm_label, text='Comments:')
        self.ent_comment = tk.Entry(master=self.frm_label)
        self.ent_comment.bind("<Return>", self.insert_comment)

    def set_layout(self):
        """ Layout all the GUI widgets"""
        #self.window.columnconfigure(0, weight=1)
        #self.window.rowconfigure(0, weight=1)
        self.btn_load.pack(expand=0,pady=10)#.grid(row=0, column=0, sticky='e', pady=10)
        self.btn_save_seg.pack(expand=0)#.grid(row=1, column=0, sticky='e', pady=10)
        self.set_label_frm()
        self.frm_label.pack(expand=1)
        self.lbl_frame_centroid.pack(expand=1,side=tk.BOTTOM,pady=100)
        self.frm_admin_btns.pack(expand=0,side=tk.LEFT)#.grid(row=0,column=0, sticky='nsew')
        self.set_vid_frm()
        self.video_panel.pack(expand=1, fill=tk.BOTH,side=tk.TOP)#.grid(row=0, column=1, sticky='nsew')
        self.frm_vid_btns.pack(expand=0, fill=tk.BOTH,side=tk.BOTTOM)#,anchor='center')#.grid(row=1, column=1, sticky='nsew')

    def set_vid_frm(self):
        self.frm_vid_btns.grid_columnconfigure(4, weight=1, uniform='middle')
        self.frm_vid_btns.grid_columnconfigure(11, weight=3, uniform='middle')
        self.frm_vid_btns.grid_columnconfigure(15, weight=1, uniform='middle')
        self.frm_vid_btns.grid_columnconfigure(24, weight=1, uniform='middle')
        self.btn_back.grid(row=0, column=4, sticky="nsew",pady=25, padx=10,columnspan=3)
        self.btn_play.grid(row=0, column=11, sticky="nsew",pady=25, padx=10)
        self.btn_rewind.grid(row=0, column=15, sticky='nsew',pady=25, padx=10,columnspan=3)
        self.btn_next.grid(row=0, column=24, sticky="nsew",pady=25, padx=10,columnspan=3)

    def set_label_frm(self):
        for i in range(len(self.btn_labels)):
            self.btn_labels[i].grid(row=i+2, column=0, sticky='w',padx=5,pady=10)
        new_row_num = i+4
        # Place the comments field:
        self.lbl_comment.grid(row=new_row_num, column=0, sticky='w', padx=5, pady=10)
        self.ent_comment.grid(row=new_row_num+1, column=0, sticky='w', padx=5, pady=10)

    def set_label(self,event=None):
        """Commit changes made in to the video label from the GUI to the log dataframe.
        Handles changes made by either button click (trackpad or mouse) or keystroke (specified keyboard key)."""
        # If label change was initiated by keystroke:
        if event:
            # If the keystroke is coming from an entry widget, ignore it:
            if isinstance(event.widget, tk.Entry):
                return
            # Set the label to the appropriate value:
            self.label.set(self.KEYS_TO_LABELS[event.char])
        # Whether click or key, label variable value is retrieved and saved to the log dataframe:
        #self.log.loc[self.player.log.movie_name == self.player.curr_movie_name, ['label']] \
        #    = self.label.get()
       # self.log_saved = False  # Track changes that are not saved to .csv file

    def insert_comment(self,event):
        """Commits changes made to the comments entry field from the GUI to the log dataframe."""
        self.comment=self.ent_comment.get()
        self.window.focus_set()

    def handle_keystroke(self,event):
        """ Use specific keystrokes to navigate between videos.
        Meant to improve the workflow for the end user."""
        # When typing into an entry, don't activate hot-keys
        if isinstance(event.widget, tk.Entry):
            return
        # Define pairs of keystrokes and actions in a dictionary:
        key_dict = { "0": self.play_vid, "4": self.prev_frame, "6": self.next_frame}
        if event.char in key_dict.keys():
            key_dict[event.char](event)

    def _resize_image(self,event):
        if self.vid_loaded:
            self.width = event.width
            self.height = event.height
            self.frame = self.photo_copy.resize((self.width, self.height))
            self.photo = PIL.ImageTk.PhotoImage(image=self.frame)
            self.video_panel.create_image(0, 0, image=self.photo, anchor=tk.NW)

    def load_vid(self):
        if self.vid_loaded:
            self.log.to_csv(self.log_path)
        self.vidpath = list(askopenfilenames(filetypes=[("Video Files", ["*.mp4", "*.avi", "*.seq"])]))
        print(self.vidpath)
        if not self.vidpath:
            # if no file was chosen, stop the method:
            return
        else:
            self.vidpath = self.vidpath[0]
        self.vid_loaded = True
        self.window.title(f"Feeding Analyzer - {self.vidpath}")
        if self.vidpath.endswith('.seq'):
            self.vid = SEQReader(self.vidpath)
        elif self.vidpath.endswith('.avi'):
            self.vid = VidReader(self.vidpath)
        else:
            messagebox.showerror(title='Not a movie!', message='Pick either a .seq or .avi file')
        self.centroids_by_frm = np.zeros((len(self.vid),2))
        self.save_dir = os.path.join(os.path.dirname(self.vidpath), 'feeding_events')
        if not os.path.exists(self.save_dir):
            os.mkdir(self.save_dir)
        else:
            self.log_path = os.path.join(self.save_dir,'feeding_log.csv')
            if os.path.exists(self.log_path):
                self.log = pd.read_csv(self.log_path)
        self.display_frame()

    def on_close(self):
        if self.vid_loaded:
            self.log.to_csv(self.log_pathpath)
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
        self.lbl_frame_centroid.configure(text=f'{event.x:.3f}, {event.y:.3f} \n {self.width},{self.height}')
        self.lbl_frame_centroid.update()
        self.video_panel.create_image(0, 0, image=self.photo, anchor=tk.NW)  # Draw the image in the Panel widget
        self.centroid = (event.x/self.width, event.y/self.height)
        # x is cols y is rows, it is the other way around when cut from a matrix, so we'll store it backwards:
        self.centroids_by_frm[self.vid.frame_pointer,:] = self.centroid[1], self.centroid[0]
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
                self.centroid = tuple(self.centroids_by_frm[self.vid.frame_pointer,::-1])
            else:
                self.centroids_by_frm[self.vid.frame_pointer,:] = self.centroid[1],self.centroid[0]
            self.draw_centroid()
        else:
            self.centroid = tuple(self.centroids_by_frm[self.vid.frame_pointer, ::-1])
            self.draw_centroid()

    def translate_centroid(self,centroid):
        row, col = centroid
        col = int(col * self.ORIGINAL_WIDTH)
        row = int(row * self.ORIGINAL_HEIGHT)
        return row,col

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
                # this is a row,col centroid
                centroid = self.centroids_by_frm[frame_num,::-1]
                row, col = self.translate_centroid(centroid)
                frm_tmp = frame_num+1
                parent_vidname = os.path.basename(self.vidpath).split('.')[0]
                movie_name = f'{parent_vidname}_frame_{frm_tmp}_coords_{row}-{col}.avi'
                entry = {'source_vid': self.vidpath, 'start_frame': frm_tmp,'coords':(row,col)}
                movie_path = os.path.join(self.save_dir,movie_name)
                video_writer = cv2.VideoWriter(movie_path, self.fourcc, self.fps,
                                                   (self.padding * 2, self.padding * 2), False)
                for i in range(frame_num,self.centroids_by_frm.shape[0]):
                    frame = self.vid[i]['frame']
                    # again a row,col centroid:
                    centroid = self.centroids_by_frm[i,:]
                    if centroid[0] == -1:
                        print(centroid)
                        break
                    row,col = self.translate_centroid(centroid)
                    upper_row, bottom_row, left_col, right_col = self.get_bounds(row,col)
                    subframe = frame[upper_row:bottom_row, left_col:right_col]
                    video_writer.write(subframe)
                print(i)
                entry['num_frames'] =i-frame_num
                entry['label'] = self.label.get()
                entry['comments'] = self.comment
                frame_num = i+1
                video_writer.release()
                self.log = self.log.append(entry,ignore_index=True)
                self.zero_vars()
                self.last_frame_written = i
            else:
                frame_num += 1
        messagebox.showinfo('segment saved!', f'finished saving at {movie_path}')


    def zero_vars(self):
        self.comment =''
        self.ent_comment.delete(0, 'end')
        self.label.set(None)

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

class VidReader():
    """ Helper class for avi compatibility, as well as seq. It uses cv2.VideoCapture"""
    def __init__(self,vidpath):
        self.cap = cv2.VideoCapture(vidpath)
        self.frame_pointer = 0
        self.num_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def read(self):
        if self.frame_pointer < self.num_frames-1:
            frame = self.__getitem__(self.frame_pointer+1)['frame']
            ret = True
        else:
            frame = None
            ret = False
        return ret, frame

    def __getitem__(self, idx):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx-1)
        ret,frame = self.cap.read()
        frame = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        self.frame_pointer = idx
        return {'frame' : frame}

    def __len__(self):
        return self.num_frames


if __name__ == '__main__':
    FeedingLabeler()