from MovieCutter import MovieCutter
import tkinter as tk
from tkinter.filedialog import askopenfilename, askdirectory
from tkinter.ttk import Progressbar
from tkinter import messagebox

class CutterApp():
    """ An application for cutting a video of fish larvae into smaller and shorter segments with individual fish.
     To do this the app uses the MovieCutter class to detect the fish and cut movie segments, see the MovieCutter class
      documentation for more details.
      The user chooses a file to cut and a directory into which the files will be saved. When cutting starts progress
      will be displayed on a progress bar."""
    def __init__(self):
        """ Initialize the main GUI window."""
        self.window=tk.Tk()
        self.frm_btn = tk.Frame(self.window) # Create a parent frame for the GUI buttons
        # Button to get the desired video from the user:
        self.btn_open = tk.Button(self.frm_btn, text="Open", command=self.open_vid)
        # Button to get the directory for saving the files (another subdirectory will be created in this directory):
        self.btn_save = tk.Button(self.frm_btn,text='Save to', command=self.save_dir)
        # Button to start the video cutting proccess
        self.btn_start = tk.Button(self.frm_btn, text="Start Cutting", command=self.cut_movies)
        # This label shows some info to direct user actions:
        self.lbl_training = tk.Label(self.window, text='Choose a video file first')
        # Progress bar to show the progression of the cutting process:
        self.bar = Progressbar(self.window, length=300, orient="horizontal",
                                    style='black.Horizontal.TProgressbar', mode="determinate")
        # Set the layout using the grid geometry manager:
        self.window.rowconfigure([0,1],weight=1,minsize=100)
        self.btn_open.grid(row=0,column=0, sticky="ew",padx=5,pady=2)
        self.btn_save.grid(row=0,column=1,sticky="ew",padx=5,pady=2)
        self.btn_start.grid(row=0,column=2,sticky="ew",padx=5,pady=2)
        self.frm_btn.grid(row=0)
        self.lbl_training.grid(row=1,sticky="nsew")
        self.bar.grid(row=2,sticky="e",pady=5,padx=5)
        self.movie_cutter = None   # The MovieCutter object will be created once the user selects a file and directory
        self.window.mainloop()

    def open_vid(self):
        """Get the video file for cutting from the user."""
        # Open a system dialog to get the file path:
        self.vidpath = askopenfilename(filetypes=[("Video Files", ["*.mp4","*.avi"]), ("All Files", "*.*")])
        if not self.vidpath:
            # if no file was chosen, stop the method:
            return
        self.window.title(f"Movie Cutter - {self.vidpath}")  # Set the title of the GUI to match the file path
        # display the next set of user instructions on the GUI:
        self.lbl_training.configure(text='Choose where to save the videos')
        self.lbl_training.update()
        self.bar["value"] = 0   # Set the progress bar value to 0

    def save_dir(self):
        """Get the directory to save the file."""
        self.savepath = askdirectory()  # Open a system dialog to get the desired directory
        if self.vidpath:
            # If a video file was already chosen with the open_vid method, create a new MovieCutter object:
            self.movie_cutter = MovieCutter(self.vidpath, self.savepath,
                                            trainlabel=self.lbl_training, progressbar=self.bar)

    def cut_movies(self):
        """Start the movie cutting operation."""
        self.movie_cutter.cut()  # see the MovieCutter class for more details
        # Note: the progress bar is updated inside the cut method of the MovieCutter class
        # Prompt user when done, show where the video segments were saved:
        messagebox.showinfo('Done Cutting', f'Vids saved to: {self.movie_cutter.folder_path} ')



if __name__ == '__main__':
    CutterApp()

