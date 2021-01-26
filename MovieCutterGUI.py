from MovieCutter import MovieCutter
import tkinter as tk
from tkinter.filedialog import askopenfilenames, askdirectory
from tkinter.ttk import Progressbar
from tkinter import messagebox
import os
from AdvanceMovieCutterGUI import AdvanceMovieCutterGUI

class CutterApp():
    """ An application for cutting videos of fish larvae into smaller (in frame size) and shorter (frame length)
    segments with individual fish.
    To do this the app uses the MovieCutter class to detect the fish and cut movie segments, see the MovieCutter class
    documentation for more details.
    The user chooses a file to cut and a directory into which the files will be saved. When cutting starts progress
    will be displayed on a progress bar."""
    # Define some class variables of messages with user instruction:
    INIT_MSG = 'Choose a video file first'
    SAVE_MSG = 'Choose where to save the videos'
    CUT_MSG = "You're all good, start cutting!"

    def __init__(self):
        """ Initialize the main GUI window."""
        self.window=tk.Tk()
        self.frm_btn = tk.Frame(self.window) # Create a parent frame for the GUI buttons
        # Button to get the desired video from the user:
        self.btn_open = tk.Button(self.frm_btn, text="Open", command=self.open_vid)
        # Button to get the directory for saving the files (another subdirectory will be created in this directory):
        self.btn_save = tk.Button(self.frm_btn,text='Save to', command=self.save_dir)
        self.btn_advance= tk.Button(self.frm_btn,text='Advance Options', command=self.open_advance)
        self.write_movies = tk.BooleanVar()
        self.btn_write_movies = tk.Radiobutton(self.frm_btn,text='Just Log',variable=self.write_movies, value=False)
        # Button to start the video cutting proccess
        self.btn_start = tk.Button(self.frm_btn, text="Start Cutting", command=self.cut_movies)
        # This label shows some info to direct user actions:
        self.lbl_training = tk.Label(self.window, text=self.INIT_MSG)
        self.lbl_movie_counter = tk.Label(self.window, text='')
        # Progress bar to show the progression of the cutting process:
        self.bar = Progressbar(self.window, length=300, orient="horizontal",
                                    style='black.Horizontal.TProgressbar', mode="determinate")
        self.vidpaths = []  # File paths for videos to be cut will be stored here
        self.savepath = None  # will contain a path selected by user where cut videos will be saved
        self.movie_cutters = []  # Movie cutter objects will be stored here
        self.num_vids_selected=None
        self.define_layout()
        self.window.wm_title("Fish Movie Cutter")
        # Set a closing procedure for the GUI window and start the mainloop:
        self.window.mainloop()

    def define_layout(self):
        """Set the layout using the grid geometry manager:"""
        self.window.rowconfigure([0,1],weight=1,minsize=100)
        self.btn_open.grid(row=0,column=0, sticky="ew",padx=5,pady=2)
        self.btn_save.grid(row=0,column=1,sticky="ew",padx=5,pady=2)
        self.btn_advance.grid(row=0, column=2, sticky="ew", padx=5, pady=2)
        self.btn_write_movies.grid(row=0,column=3,sticky="ew", padx=5, pady=2)
        self.btn_start.grid(row=0,column=4, sticky="ew",padx=5,pady=2)
        self.frm_btn.grid(row=0)
        self.lbl_movie_counter.grid(row=2,column=0,sticky="nsew")
        self.lbl_training.grid(row=1,column=0,sticky="nsew")
        self.bar.grid(row=3,sticky="e",pady=5,padx=5)



    def open_vid(self):
        """Get the video file for cutting from the user."""
        # Open a system dialog to get the file path, multiple file selection enabled:
        self.vidpaths += list(askopenfilenames(filetypes=[("Video Files", ["*.mp4", "*.avi"]),
                                                         ("All Files", "*.*")]))
        if not self.vidpaths:
            # if no file was chosen, stop the method:
            return
        self.window.title(f"Movie Cutter - {self.vidpaths[0]}")  # Set the title of the GUI to match the first file path
        self.num_vids_selected = len(self.vidpaths)
        # Display the next set of user instructions on the GUI:
        self.lbl_training.configure(text=self.SAVE_MSG)
        self.lbl_training.update()
        # Inform the user how many videos are currently selected for cutting:
        self.lbl_movie_counter.configure(text=f'{self.num_vids_selected} videos were selected for cutting')
        self.lbl_movie_counter.update()
        self.bar["value"] = 0   # Set the progress bar value to 0

    def save_dir(self):
        """Get the directory to save the file."""
        # Ask where to save segments - in the same folder as the video being cut or in a new place?
        default_path = messagebox.askquestion('Use Default Path',
                                              "Would like to save the segments in "
                                              "the same directory as the parent video?")
        if default_path=='yes':
            # We will handle this in the for loop below
            multiple_save_paths = True
        else:
            # Get the new directory desired by the user, please note it will be one directory for all videos being cut:
            multiple_save_paths = False
            self.savepath = askdirectory()
            # However there will be subdirectories within this for each video separately.

        if self.vidpaths:
            # If a video file was already chosen with the open_vid method, create a new list of MovieCutter objects:
            for i in range(self.num_vids_selected):
                if multiple_save_paths:
                    # If we're saving in the same directory as the parent vid, get the directory path:
                    self.savepath = os.path.dirname(self.vidpaths[i])
                # Define a new movie cutter object:
                self.movie_cutters.append(MovieCutter(self.vidpaths[i], self.savepath,
                                                      trainlabel=self.lbl_training, progressbar=self.bar,
                                                      save_movies=self.write_movies.get()))
            # Display the next set of user instructions on the GUI:
            self.lbl_training.configure(text=self.CUT_MSG)
            self.lbl_training.update()

    def open_advance(self):
        if self.movie_cutters:
            AdvanceMovieCutterGUI(self.movie_cutters)
        else:
            messagebox.showinfo(title="Oops!", message="You need to choose a saving directory first")

    def cut_movies(self):
        """Start the movie cutting operation."""
        for i in self.movie_cutters:
            print(i)
        if self.movie_cutters:
            for i in range(self.num_vids_selected):
                # Keep track of which movie we're cutting
                self.lbl_movie_counter.configure(text=f'Video {i+1} / {self.num_vids_selected}')
                # Cut movies one after the other:
                self.movie_cutters[i].cut()  # see the MovieCutter class for more details
                self.bar['value'] = 0
            # Note: the progress bar is updated inside the cut method of the MovieCutter class
            # Prompt user when done, show where the video segments were saved:
            messagebox.showinfo('Done Cutting', f'Videos saved to subdirectories at: {self.savepath} ')
        else:
            messagebox.showinfo('Oops!', 'An Error occurred. Did you forget to choose files for cutting?')


if __name__ == '__main__':
    CutterApp()

