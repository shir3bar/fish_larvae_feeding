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
    # Class variables to define which key strokes will control the labeling:
    KEYS_TO_LABELS = {'q': 'Not Feeding', 'w': 'Other', 'a': 'Feeding Success',
                      's': 'Feeding Fail', 'd': 'Feeding I&O', 'z': 'Spitting'}
    def __init__(self):
        """ Initialize a new instance of the FeedingLabeler application."""
        # This is a tkinter based GUI
        # Main consideration was that it should function well cross-platform, as it was developed in a Mac environment
        # and designated to run in a Windows environment.
        self.window = tk.Tk()
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
                                           value='Not Feeding', command=self.set_label)
        # Other is when the main part of the frame doesn't contain a fish or the fish is blurry and out-of-focus:
        self.btn_other = tk.Radiobutton(master=self.frm_label, text='Other', variable=self.label,
                                        value='Other', command=self.set_label)
        # Feeding success is when the fish can been seen swallowing a rotifer (small, round object) successfully:
        self.btn_feed_s = tk.Radiobutton(master=self.frm_label, text='Feeding Success', variable=self.label,
                                         value='Feeding Success', command=self.set_label)
        # Feeding fail is when the fish cannot swallow the food item:
        self.btn_feed_f = tk.Radiobutton(master=self.frm_label, text='Feeding Fail', variable=self.label,
                                         value='Feeding Fail', command=self.set_label)
        # Feeding I&O (In and Out) is when the food item briefly and it pops out:
        self.btn_feed_io = tk.Radiobutton(master=self.frm_label, text='Feeding I&O', variable=self.label,
                                          value='Feeding I&O', command=self.set_label)
        # Spitting is when the fish spits the food item out (forcefully):
        self.btn_spitting = tk.Radiobutton(master=self.frm_label, text='Spitting', variable=self.label,
                                           value='Spitting', command=self.set_label)

    def set_layout(self):
        """ Layout all the GUI widgets"""
        # setup the general layout of the window using the grid geometry manager:
        self.window.rowconfigure(0, weight=1, minsize=500)
        self.window.rowconfigure(1, weight=1, minsize=75)
        self.window.columnconfigure(1, weight=1, minsize=500)
        # Place the widgets within the label frame:
        self.btn_load.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.btn_not_feed.grid(row=2, column=0, sticky="ew", padx=5, pady=10)
        self.btn_other.grid(row=3, column=0, sticky='ew', padx=5, pady=10)
        self.btn_feed_s.grid(row=4, column=0, sticky="ew", padx=5, pady=10)
        self.btn_feed_f.grid(row=5, column=0, sticky="ew", padx=5, pady=10)
        self.btn_feed_io.grid(row=6, column=0, sticky="ew", padx=5, pady=10)
        self.btn_spitting.grid(row=7, column=0, sticky="ew", padx=5, pady=10)
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
            # Delete videos tagged as 'Other':
            self.delete_others()
            # Check for missing video labels and prompt user:
            if self.player.log.label.isna().any():
                result = messagebox.askokcancel('Missing Labels',
                                       'Some videos are missing labels, are you sure you want to leave?')
                if result: # If the user is sure, close the window:
                    self.window.quit()  # Close the window

        self.window.quit()

    def delete_others(self):
        """ Upon closing, delete videos tagged as "Other" to free up space in the computer.
        Ask user before deleting!"""
        # Pop up a question dialog:
        result = messagebox.askquestion('Delete Others', 'Do you want to delete "Others"?')
        if result == 'yes':
            # If the user wants to delete, iterate over all movies and remove the file and log entry:
            for index, row in self.player.log.iterrows():
                if row['label'] == 'Other':
                    os.remove(os.path.join(self.player.directory, row['movie_name']))  # Remove file
                    self.player.log.drop(index, inplace=True)  # Remove log entry
            self.save_labels()  # Save the log

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
        self.player.load_directory()  # See the Movie Player class for details
        self.bind_keystrokes()

    def bind_keystrokes(self):
        """ Use specific keystrokes to change the labels of each video.
        Meant to improve the workflow for the end user."""
        for char,label in self.KEYS_TO_LABELS.items():
            self.window.bind(f'<{char}>',self.set_label)


    def set_label(self,event=None):
        """Commit changes made in to the video label from the GUI to the log dataframe.
        Handles changes made by either button click (trackpad or mouse) or keystroke (specified keyboard key)."""
        # If label change was initiated by keystroke:
        if event:
            # Set the label to the appropriate value:
            self.label.set(self.KEYS_TO_LABELS[event.char])
        # Whether click or key, label variable value is retrieved and saved to the log dataframe:
        self.player.log.loc[self.player.log.movie_name == self.player.curr_movie_name, ['label']] \
            = self.label.get()
        self.log_saved = False  # Track changes that are not saved to .csv file


class MoviePlayer:
    """A GUI designed to show videos cut by the Movie Cutting application.
     Once the user chooses a directory, all .avi files in that directory are mapped.
     The user can navigate between videos in the directory, play them and save snapshots."""
    def __init__(self, window,label_var=[]):
        """ Initialize a Movie Player instance.
        Function receives a tkinter window to build the app in.
        An optional label variable is used to interact with the Feeding Label application.
        """
        self.window = window
        self.label_var = label_var
        self.curr_vid_idx = 0  # Current video index
        self.num_vids = 0  # Total number of videos loaded
        self.panel = tk.Canvas(master=self.window, width=500, height=500)  # Used to display the video
        self.directory = None  # Directory where the videos are saved
        self.curr_vid = None   # Current video capture object
        self.log_filepath = ''  # Log file location
        self.curr_movie_name = ''  # Current Movie file name
        self.file_paths = []  # List of video file paths
        self.snap_idx = 0  # Index to name snapshot files
        self.log = pd.DataFrame()   # Log file dataframe
        self.pause = True  # Play/pause marker, to make the play button function as a pause as well
        self.define_vid_btn_frm()  # Define the buttons
        self.set_layout()  # Set the GUI layout

    def define_vid_btn_frm(self):
        """ Define all the GUI buttons"""
        self.frm_vid_btns = tk.Frame(master=self.window)  # Frame container for all the buttons
        # Field for user selected video index:
        self.ent_vid_idx = tk.Entry(master=self.frm_vid_btns,text=str(self.curr_vid_idx), width=3)
        self.ent_vid_idx.bind("<Return>", self.set_new_vid)  # When user presses "Enter", current video will change
        # Display total number of videos loaded:
        self.lbl_numvids = tk.Label(master=self.frm_vid_btns,text='/ '+str(self.num_vids))
        # Navigation buttons:
        self.btn_back = tk.Button(master=self.frm_vid_btns, text="\N{LEFTWARDS ARROW}",command=self.prev_vid)
        self.btn_next = tk.Button(master=self.frm_vid_btns, text="\N{RIGHTWARDS ARROW}", command=self.next_vid)
        # Play button:
        self.btn_play = tk.Button(master=self.frm_vid_btns, text='Play/Pause', command=self.play_vid)
        self.btn_play.bind('<Button-1>', self.handle_play)  # Set the play/pause marker
        # Snapshot button:
        self.btn_snapshot = tk.Button(master=self.frm_vid_btns, text='Snapshot', command=self.get_snapshot)
        # Show the frame and the coordinates the video was cut from in the original video:
        self.lbl_frame_centroid = tk.Label(master=self.frm_vid_btns, text='')

    def set_layout(self):
        """ Layout all the GUI widgets"""
        self.ent_vid_idx.grid(row=0, column=0,sticky="e")
        self.lbl_numvids.grid(row=0, column=1, sticky="w", padx=2)
        self.btn_back.grid(row=0, column=2, sticky="e", padx=10)
        self.btn_play.grid(row=0, column=3, sticky="e", padx=10)
        self.btn_next.grid(row=0, column=4, sticky="e", padx=10)
        self.btn_snapshot.grid(row=0, column=5, sticky="e", padx=10)
        self.lbl_frame_centroid.grid(row=0, column=6, sticky="e", padx=10)
        self.panel.grid(row=0, column=1, sticky='nsew')
        self.frm_vid_btns.grid(row=1, column=1)

    def bind_keystrokes(self):
        """ Use specific keystrokes to navigate between videos.
        Meant to improve the workflow for the end user."""
        # Move to the previous video:
        self.window.bind("<Left>", self.prev_vid)
        # Move to the first video:
        self.window.bind("<Right>", self.next_vid)
        # Play the video:
        self.window.bind("<space>", self.play_vid)
        # Move to the previous frame:
        self.window.bind('<,>', self.rewind_one_frame)
        # Move to the next frame:
        self.window.bind('<.>', self.display_frame)

    def rewind_one_frame(self, event):
        """ Move one frame backwards in the current video"""
        # Get the current frame position:
        curr_frame=self.curr_vid.get(cv2.CAP_PROP_POS_FRAMES)
        # Rewind the video capture object so the next we'll display will be previous one:
        self.curr_vid.set(cv2.CAP_PROP_POS_FRAMES, curr_frame-2)
        self.display_frame()

    def load_directory(self):
        """ Load all videos from user-selected directory to the GUI.
        Loads videos cut by the MovieCutterGUI and the corresponding log file."""
        self.directory=askdirectory() # get directory
        for root, directories, files in os.walk(self.directory):
            # Iterate ove all files in the directory:
            for filename in files:
                # Join the two strings in order to form the full filepath.
                if filename.endswith('.avi'):
                    # if a file is video add it's path to the video path list:
                    filepath = os.path.join(root, filename)  # Assemble the full path
                    self.file_paths.append(filepath)  # Add it to the list
                elif filename.endswith('.csv'):
                    # if it's the log.csv file load it to a pandas data frame:
                    self.log_filepath = os.path.join(root, filename)   # save path
                    self.log = pd.read_csv(self.log_filepath)  # load log
        self.bind_keystrokes()  # Bind keystrokes to GUI functions
        self.num_vids = len(self.file_paths)-1  # Get the total number of videos loaded
        self.lbl_numvids.configure(text='/ '+str(self.num_vids))  # display that number in the designated label
        self.lbl_numvids.update()  # update the gui label
        try:
            # Try to display the first video in the GUI:
            vid_idx=0
            self.set_vid(vid_idx)
        except:
            # In case of a mishap display a message to user:
            self.panel.create_text(250, 250, text='Video load failed')



    def handle_play(self, event=None):
        """ Handle play button click, if it is clicked once turn it into a pause button."""
        self.pause = not self.pause  # Now when the "Play" button will be clicked again it will pause the video

    def set_new_vid(self,event):
        """Receives video index from user via the ent_vid_idx and displays it in the GUI.
        This method is initiated when the user clicks 'Enter' or 'Return' inside the ent_vid_idx widget."""
        try:
            # If the value entered is an integer this should work:
            user_selection = int(self.ent_vid_idx.get()) # Get the user selected value
            if user_selection>self.num_vids:
                # If the user selected a video index out of range, replace the value with the last video index:
                user_selection = self.num_vids
            self.curr_vid.release()  # release the video capture object
            self.set_vid(user_selection)   # load the new video in the GUI
        except ValueError:
            # If the value entered is not a number, display a prompt and revert to the current video index:
            messagebox.showinfo('Not a number!',
                                "You typed something that isn't a number, please select a legal video index.")
            self.ent_vid_idx.delete(0, tk.END)
            self.ent_vid_idx.insert(0, self.curr_vid_idx)

        self.btn_play.focus_set()  # Move the focus from the ent_vid_idx text field to the play button

    def get_snapshot(self):
        """ Save the current frame as an image file. This method is activated by the snapshot button. """
        path = self.directory + os.path.sep + 'snapshots'  # define the path where snapshots are saved
        if self.snap_idx == 0:
            try:
                os.mkdir(path)  # If it's the first snap taken, try creating the path
            except:
                print('Snap directory already exists!')  # if it exists, all good, just print a prompt
        # define the filename according to the following format - movie-name(without .avi)_snap_snap-id-number:
        filename = self.curr_movie_name[0:-4] + '_snap' + str(self.snap_idx) + '.jpg'
        cv2.imwrite(path + os.path.sep + filename, self.frame)  # save snapshot to file
        self.snap_idx += 1 # update snap index
        # display a prompt informing the user where the file was saved:
        messagebox.showinfo('Save Snapshot', f'Snapshot saved at {filepath}')

    def display_frame(self, event=None):
        """Read a single frame from the current video and display it onto the GUI."""
        ret, frame = self.curr_vid.read()  # Read a single frame
        self.frame = frame  # Save that frame
        self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))  # Convert frame to display it on GUI
        self.panel.create_image(0, 0, image=self.photo, anchor=tk.NW)  # Draw the image in the Panel widget

    def set_vid(self, vid_idx):
        """ Load a new video with index vid_idx onto the GUI.
        This task includes displaying the first frame of the video in the panel, displaying its index
        and displaying extra information about the video from the log. The method receives the new video index as input.
        """
        # Set the new video index to be the current:
        self.curr_vid_idx = vid_idx
        # Write the new video index in the entry widget:
        self.ent_vid_idx.delete(0, tk.END)  # delete any existing text
        self.ent_vid_idx.insert(0, self.curr_vid_idx)  # write the current index
        # Change current movie name:
        self.curr_movie_name = os.path.basename(self.file_paths[self.curr_vid_idx])
        # If integrated with the FeedingLabeler GUI:
        if self.label_var:
            # Set the label variable to the label of the video in the log dataframe:
            self.label_var.set(self.log.loc[self.log.movie_name == self.curr_movie_name].label.values[0])
            # setting this label_var will also display the label in the labeler GUI

        # Display the frame and coordinates (in the original video) from which this video was cut:
        txt=self.log.loc[self.log.movie_name == self.curr_movie_name,
                         ['frame', 'coordinates']].to_string(index=False)  # retrieve the relevant data
        self.lbl_frame_centroid.configure(text=txt)  # display the text in the widget
        # And finally, open the video file:
        self.curr_vid = cv2.VideoCapture(self.file_paths[self.curr_vid_idx])
        self.display_frame()  # display the first frame in the video
        self.window.title(self.curr_movie_name)  # change the GUI title to the current video name
        # The main user of the software requested that the new video will start playing automatically:
        self.play_vid()

    def play_vid(self,event=None):
        """ This method plays the video file currently loaded to the GUI.
        The video is played by recursively calling this method using the window.after() tkinter method.
        The method will stop when the video is paused or reaches its end.
        This method is invoked either by pressing the play button, or by pressing the space bar.

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
                self.window.after(15, self.play_vid)
        except AttributeError:
            # If the video reached its end tkinter will raise an AttributeError, we'll catch it and reset the video:
            self.curr_vid.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Rewind the video capture object to frame 0
            self.display_frame()  # display the first frame
            self.pause = not self.pause  # Change the status of the play/pause button from "Pause" to "Play"

    def next_vid(self,event=None):
        """Load the next video in the video list.
        This method is invoke either by the next_vid button or by the Right-Arrow key stroke. """
        self.curr_vid.release()   # Release the current video capture object
        new_idx = self.curr_vid_idx + 1  # Set the new video index
        if new_idx > self.num_vids:
            # if the new index is out of range, set it to the last video index:
            new_idx = self.num_vids
            messagebox.showinfo('Done', 'Done! No more videos :)')  # Show a prompt to user stating that they're done
        self.set_vid(new_idx)  # Load the new video to GUI


    def prev_vid(self,event=None):
        """Load the previous video in the video list.
                This method is invoke either by the next_vid button or by the Left-Arrow key stroke. """
        self.curr_vid.release()  # Release the current video capture object
        new_idx=self.curr_vid_idx - 1
        if new_idx < 0:
            # if the new index is out of range, set it to the first video index:
            new_idx = 0
        self.set_vid(new_idx)  # Load the new video to GUI

if __name__ == '__main__':
    FeedingLabeler()
