import tkinter as tk
from tkinter.filedialog import askdirectory
import os
import cv2
import PIL.Image, PIL.ImageTk
import pandas as pd
from tkinter import messagebox


class FeedingLabeler:
    """ The Feeding Labeler is a GUI to help tag video samples for the Larvae Feeding project. It is meant to be used
    to label videos cut by the Movie Cutter GUI.
    The user selects a directory using the 'Load Movies' button, the movies are then presented in the Movie Player
    portion of the GUI. Existing labels will be loaded along with the videos and displayed. New labels can be assigned
     by selecting the appropriate label on the left hand side of the screen ('Feeding', 'Non-Feeding' or 'Other'
     for blurry items or non-fish items). Labels are retained even when navigating to another video,
     however the labels will only be saved to file when pressing the 'Save Labels' button.
     Labels are saved to the 'log.csv' file which was created by the Movie Cutter GUI. For more detail on this file,
     please see the 'MovieCutterGUI.py' file in this repository.
     For more infomation about the Movie Player functionality, please see the Movie Player class DocString."""
    def __init__(self):
        """ Intialize a new instance of the FeedingLabeler application."""
        # This is a tkinter based GUI
        # Main consideration was that it should function well cross-platform, as it was developed in a Mac environment
        # and designated to run in a Windows environment.
        self.window = tk.Tk()
        # setup the general layout of the window using the grid geometry manager:
        self.window.rowconfigure(0, weight=1, minsize=500)
        self.window.rowconfigure(1, weight=1, minsize=75)
        self.window.columnconfigure(1, weight=1, minsize=500)
        # Define the widgets containing the labels for the videos:
        self.define_label_frm()
        self.btn_save = tk.Button(master=self.window,text='Save Labels', command=self.save_labels)
        # Set the layout of the labeling window:
        self.set_layout()
        # Define the movie player that will handle video display and navigation:
        self.player = MoviePlayer(self.window,self.label)
        self.log_saved = True  # Track changes to the label log

        self.window.wm_title("Fish Labeler")
        # define what happens when the GUI window is closed by user:
        self.window.wm_protocol("WM_DELETE_WINDOW", self.on_close)
        self.window.mainloop()  # Start the main event loop of the GUI

    def define_label_frm(self):
        """ Define the labeling widgets in the app. A button to select movies to load and three Radio Buttons with the
        three different labels the user can assign to the data."""
        self.frm_label = tk.Frame(master=self.window)
        self.label = tk.StringVar()  # this variable will hold the label for the current video
        self.label.set(None)  # No default value
        self.btn_load = tk.Button(master=self.frm_label, text='Load Movies', command=self.get_dir) # load movies
        # Label options depicted as radio buttons, "Feeding","Not Feeding", "Other" -
        # Not feeding is when the fish is visible, in focus and is not feeding:
        self.btn_not_feed = tk.Radiobutton(master=self.frm_label, text='Not Feeding', variable=self.label,
                                           value='Not feeding', command=self.set_label)
        # Feeding is when the fish can been seen swallowing a rotifer (small, round object) successfully:
        self.btn_feed = tk.Radiobutton(master=self.frm_label, text='Feeding', variable=self.label,
                                       value='Feeding', command=self.set_label)
        # Other is when the main part of the frame doesn't contain a fish or the fish is blurry and out-of-focus:
        self.btn_other = tk.Radiobutton(master=self.frm_label, text='Other', variable=self.label,
                                        value='Other', command=self.set_label)

    def set_layout(self):
        """ Layout all the GUI widgets"""
        # Place the widgets within the label frame:
        self.btn_load.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.btn_feed.grid(row=2, column=0, sticky="ew", padx=5, pady=10)
        self.btn_not_feed.grid(row=3, column=0, sticky="ew", padx=5, pady=10)
        self.btn_other.grid(row=4, column=0, sticky='ew', padx=5, pady=10)
        # Place the Save button:
        self.btn_save.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        # Place the frame label within the window:
        self.frm_label.grid(row=0, column=0, sticky="ns")
        # Note: the Movie Player's layout is configured internally within that class

    def on_close(self):
        """ Define the behavior of the GUI upon window close."""
        # If a video file is currently open, release it:
        if self.player.curr_vid:
            self.player.curr_vid.release()
            if not self.log_saved:
                # If the log has been change without saving, open a window prompt:
                result = messagebox.askquestion('Save log','Do you want to save changes?')
                if result == 'yes':
                    # Save labels if requested to by the user:
                    self.save_labels()
        self.window.quit() # Close the window

    def save_labels(self):
        """ Save video labels to log file"""
        try:
            # Save changes to the log DataFrame to the log.csv file:
            self.player.log.to_csv(self.player.log_filepath,index=False)
            # Open a prompt displaying the file path:
            messagebox.showinfo('Labels Saved', f'Log saved to: {self.player.log_filepath} ')
            self.log_saved = True # Change the track saved changes marker to True
        except:
            # If save fails alert user:
            messagebox.showinfo('Error', f'Error saving log file')

    def get_dir(self):
        """ Get the desired directory from user and load videos to GUI for analysis.
        """
        self.player.load_directory(askdirectory())  # See the Movie Player class for details

    def set_label(self):
        """Commit changes made in to the video label from the GUI to the log dataframe"""
        self.player.log.loc[self.player.log.movie_name == self.player.curr_movie_name, ['label']] \
            = self.label.get()
        self.log_saved = False  # Track changes that are not saved to .csv file

class MoviePlayer:
    """"""
    def __init__(self,window,label_var):
        self.window = window
        self.new_vid_idx = tk.IntVar()
        self.label_var=label_var
        self.curr_vid_idx = 0
        self.num_vids = 0
        self.panel = tk.Canvas(master=self.window, width=500, height=500)
        self.directory = None
        self.curr_vid = None
        self.log_filepath = ''
        self.curr_movie_name = ''
        self.file_paths = []
        self.snap_idx = 0
        self.log = pd.DataFrame()
        self.pause = True
        self.define_vid_btn_frm()
        self.set_layout()

    def define_vid_btn_frm(self):
        self.frm_vid_btns = tk.Frame(master=self.window)
        self.ent_vid_idx = tk.Entry(master=self.frm_vid_btns,text=str(self.curr_vid_idx), width=3)
        self.ent_vid_idx.bind("<Return>", self.set_new_vid)
        self.lbl_numvids = tk.Label(master=self.frm_vid_btns,text='/ '+str(self.num_vids))
        self.btn_back = tk.Button(master=self.frm_vid_btns, text="\N{LEFTWARDS ARROW}",command=self.prev_vid)
        self.btn_play = tk.Button(master=self.frm_vid_btns, text='Play/Pause', command=self.play_vid)
        self.btn_play.bind('<Button-1>', self.handle_play)
        self.btn_next = tk.Button(master=self.frm_vid_btns, text="\N{RIGHTWARDS ARROW}", command=self.next_vid)
        self.btn_snapshot = tk.Button(master=self.frm_vid_btns, text='Snapshot', command=self.get_snapshot)
        self.lbl_frame_centroid = tk.Label(master=self.frm_vid_btns, text='')

    def set_layout(self):
        self.ent_vid_idx.grid(row=0, column=0,sticky="e")
        self.lbl_numvids.grid(row=0, column=1, sticky="w", padx=2)
        self.btn_back.grid(row=0, column=2, sticky="e", padx=10)
        self.btn_play.grid(row=0, column=3, sticky="e", padx=10)
        self.btn_next.grid(row=0, column=4, sticky="e", padx=10)
        self.btn_snapshot.grid(row=0, column=5, sticky="e", padx=10)
        self.lbl_frame_centroid.grid(row=0, column=6, sticky="e", padx=10)
        self.panel.grid(row=0, column=1, sticky='nsew')
        self.frm_vid_btns.grid(row=1, column=1)

    def load_directory(self,directory):
        self.directory=directory
        for root, directories, files in os.walk(self.directory):
            for filename in files:
                # Join the two strings in order to form the full filepath.
                if filename.endswith('.avi'):
                    filepath = os.path.join(root, filename)
                    self.file_paths.append(filepath)  # Add it to the list.
                elif filename.endswith('.csv'):
                    self.log_filepath = os.path.join(root, filename)
                    self.log = pd.read_csv(self.log_filepath)
        self.num_vids = len(self.file_paths)-1
        self.lbl_numvids.configure(text='/ '+str(self.num_vids))
        self.lbl_numvids.update()
        self.curr_vid_idx = 0
        self.ent_vid_idx.insert(0, str(self.curr_vid_idx))
        try:
            self.set_vid()
        except:
            self.panel.create_text(0, 0, text='No video in directory')



    def handle_play(self, event):
        self.pause = not self.pause

    def set_new_vid(self,event):
        user_selection = int(self.ent_vid_idx.get())
        if user_selection>self.num_vids:
            user_selection=self.num_vids-1
            self.ent_vid_idx.delete(0,tk.END)
            self.ent_vid_idx.insert(0, str(user_selection))
        self.curr_vid_idx = user_selection
        self.curr_vid.release()
        self.curr_vid = cv2.VideoCapture(self.file_paths[self.curr_vid_idx])
        self.set_vid()
        self.btn_play.focus_set()

    def get_snapshot(self):
        path = self.directory + os.path.sep + 'snapshots'
        if self.snap_idx == 0:
            try:
                os.mkdir(path)
            except:
                print('Snap directory already exists!')
        filepath = path + os.path.sep + self.curr_movie_name[0:-4] + '_snap' + str(self.snap_idx) + '.jpg'
        cv2.imwrite(filepath, self.frame)
        self.snap_idx += 1
        tk.messagebox.showinfo('Save Snapshot', f'Snapshot saved at {filepath}')

    def display_frame(self):
        ret, frame = self.curr_vid.read()
        self.frame = frame
        self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
        self.panel.create_image(0, 0, image=self.photo, anchor=tk.NW)

    def set_vid(self):
        self.ent_vid_idx.delete(0,tk.END)
        self.ent_vid_idx.insert(0,self.curr_vid_idx)
        self.curr_movie_name = os.path.basename(self.file_paths[self.curr_vid_idx])
        self.label_var.set(self.log.loc[self.log.movie_name == self.curr_movie_name].label.values[0])
        txt=self.log.loc[self.log.movie_name == self.curr_movie_name,['frame','coordinates']].to_string(index=False)
        self.lbl_frame_centroid.configure(text=txt)
        self.curr_vid = cv2.VideoCapture(self.file_paths[self.curr_vid_idx])
        self.display_frame()
        self.window.title(self.curr_movie_name)

    def play_vid(self):
        try:
            if not self.pause:
                self.display_frame()
                self.window.after(15, self.play_vid)
        except:
            self.curr_vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.display_frame()
            self.pause = not self.pause

    def next_vid(self):
        self.curr_vid.release()
        self.curr_vid_idx += 1
        if self.curr_vid_idx > self.num_vids:
            self.curr_vid_idx = self.num_vids
            self.panel.create_text(250, 250, text='Done!')
        self.set_vid()

    def prev_vid(self):
        self.curr_vid.release()
        self.curr_vid_idx -= 1
        if self.curr_vid_idx < 0:
            self.curr_vid_idx = 0
        self.set_vid()


if __name__ == '__main__':
    FeedingLabeler()
