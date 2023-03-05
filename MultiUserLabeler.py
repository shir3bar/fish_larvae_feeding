import os
import pandas as pd
import tkinter as tk
from tkinter.filedialog import askdirectory
from tkinter import messagebox
from pathlib import Path
from LabelerGUI import MoviePlayer, Labeler
import cv2
import numpy as np
from imutils.video import FileVideoStream
import time



class MultiUserLabeler(Labeler):
    KEYS_TO_LABELS = {'`': 'swim','1': 'strike','2':'Spit/I&O','3': 'partial strike','g':'pre-strike',
                      '5': 'multiple centered fish',
                      '7':'fish offcenter',  '8': 'overexposed image', '9': 'dark image',
                      '-':'very blurry','q': 'no fish','w':'sharp turn','e':'crazy bout',
                      'r':'interrupted swim', 't':'fast swim', 'a':'reverse swim',
                      's':'dark artifact','d':'occlusion', 'f':'floating','g':'mouth opening'}
    MAIN_ACTIVITIES =tuple( ['Swim','Other','Strike','No fish'])
    MULTIPLE_FISH = tuple( ['1','2', 'Many'])
    FISH_LIST =tuple( ['occlusion', 'fish offcenter', 'just head', 'just tail','blurry', 'very blurry', 'ventral','weird angle'])
    SWIM_LIST = tuple(['floating','interrupted swim','reverse swim','fast swim','turn','sharp turn','crazy bout', 'mouth opening'])
    VISUAL_LIST =tuple(['overexposed image', 'dark image',
                  'dark artifact','light artifact', 'camera movement',
                  'lens scratches', 'lots of particles'])
    NOTMULTI_KEY ={MAIN_ACTIVITIES:'Main activity',
                    MULTIPLE_FISH:'Multiple fish'}
    LABEL_LIST = MAIN_ACTIVITIES+FISH_LIST+SWIM_LIST+VISUAL_LIST
    LABEL_MULTICHOICE = {MAIN_ACTIVITIES:False, MULTIPLE_FISH:False, FISH_LIST:True, SWIM_LIST:True, VISUAL_LIST:True}
    def __init__(self):
        self.username = None
        # This is a tkinter based GUI
        # Main consideration was that it should function well cross-platform, as it was developed in a Mac environment
        # and designated to run in a Windows environment.
        self.window = tk.Tk()
        # Define the widgets containing the labels for the videos:
        self.define_label_frm()
        self.btn_save = tk.Button(master=self.window, text='Save Labels', command=self.save_labels)
        # Set the layout of the labeling window:
        self.set_layout()
        # This will be our video player once we load some movies, see the get_dir method:
        self.player = []
        self.log_saved = True  # Track changes to the label log
        self.window.wm_title("Fish Labeler")
        # define what happens when the GUI window is closed by user:
        self.window.wm_protocol("WM_DELETE_WINDOW", self.on_close)
        self.window.mainloop()  # Start the main event loop of the GUI

    def set_layout(self):
        """ Layout all the GUI widgets"""
        # setup the general layout of the window using the grid geometry manager:
        self.window.rowconfigure(0, weight=1, minsize=700)
        self.window.rowconfigure(1, weight=1, minsize=75)
        self.window.columnconfigure(1, weight=1, minsize=700)

        # Place the widgets within the label frame:
        self.lbl_username.grid(row=0, column=0, sticky='w', padx=5, pady=10)
        self.ent_username.grid(row=1, column=0, sticky='w', padx=5, pady=0)
        self.btn_load.grid(row=2, column=0, sticky="ew", padx=5, pady=10)

        # Iterate over the label radio buttons to place them:
        counter=3
        tk.Label(master=self.main_act_frm,text='').grid(row=counter,column=0)
        self.lbl_mainact.grid(row=counter+1,column=0,sticky='ns')
        counter+=2
        for i,label in enumerate(self.btn_labels[self.MAIN_ACTIVITIES]):
            label.grid(row=counter, column=0, sticky='w', padx=5, pady=5)
            counter+=1
        counter=i+6
        tk.Label(master=self.main_act_frm,text='').grid(row=counter,column=0)
        self.lbl_otheractivties.grid(row=counter+1,column=0, sticky='w')
        counter+=2
        for i, label in enumerate(self.btn_labels[self.SWIM_LIST]):
            label.grid(row=counter, column=0, sticky='w', padx=0, pady=5)
            #if i%2!=0:
            counter+=1
        new_row_num = counter+2
        self.lbl_comment.grid(row=new_row_num, column=0, sticky='w', padx=5, pady=5)
        self.ent_comment.grid(row=new_row_num + 1, column=0, sticky='w', padx=5, pady=5)
        self.lbl_multfish.grid(row=0,column=0,sticky='w')
        counter=3
        for i, label in enumerate(self.btn_labels[self.MULTIPLE_FISH]):
            label.grid(row=counter, column=0, sticky='w', padx=5, pady=5)
            counter+=1
        tk.Label(master=self.multiple_frm,text='').grid(row=counter+1,column=0)
        self.lbl_arrange.grid(row=counter+2,column=0,sticky='w')
        #tk.Label(master=self.multiple_frm,text='').grid(row=counter+3,column=0)
        counter+=4
        for i, label in enumerate(self.btn_labels[self.FISH_LIST]):
            label.grid(row=counter, column=i % 2, sticky='w', padx=5, pady=5)
            if i%2!=0:
                counter+=1
        tk.Label(master=self.multiple_frm,text='').grid(row=counter+1,column=0)
        self.lbl_framevis.grid(row=counter+2, column=0, sticky='n')
        #tk.Label(master=self.multiple_frm, text='').grid(row=counter+3, column=0)
        counter+=5
        for i, label in enumerate(self.btn_labels[self.VISUAL_LIST]):
            label.grid(row=counter, column=i % 2, sticky='w', padx=5, pady=5)
            if i%2!=0:
                counter+=1
        # Place the frame label within the window:

        self.main_act_frm.grid(row=0,column=0,sticky='nsew')
        self.multiple_frm.grid(row=0,column=2,sticky='ns')
        self.fish_frm.grid(row=1,column=2,sticky='ns')
        self.swim_frm.grid(row=1,column=0,sticky='nsew')
        self.visual_frm.grid(row=2, column=0, sticky="ns")
        # Place the comments field:

        # Place the Save button:
        self.btn_save.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        self.bind_keystrokes()

    def set_label(self, event=None):
        """Commit changes made in to the video label from the GUI to the log dataframe.
        Handles changes made by either button click (trackpad or mouse) or keystroke (specified keyboard key)."""
        # If label change was initiated by keystroke:
        if event:
            # If the keystroke is coming from an entry widget, ignore it:
            if isinstance(event.widget, tk.Entry):
                return
            # Set the label to the appropriate value:
            val = self.KEYS_TO_LABELS[event.char]
            var = self.label[val]
            if type(var)==tk.IntVar:
                var.set(1)
            else:
                var.set(val)
        # Whether click or key, label variable value is retrieved and saved to the log dataframe:
        for key, var in self.label.items():
            try:
                self.player.log.loc[(self.player.log.clip_name == self.player.curr_clip_name)&
                                    (self.player.log.user_name ==self.username), self.player.column_names[key]] = var.get()
            except:
                print('label setting failed', key)



    def define_label_frm(self):
        """ Define the labeling widgets in the app. A button to select movies to load and three Radio Buttons with the
        three different labels the user can assign to the data."""
        self.main_act_frm = tk.Frame(master=self.window)
        self.multiple_frm = tk.Frame(master=self.window)
        self.fish_frm = tk.Frame(master=self.multiple_frm)
        self.swim_frm = tk.Frame(master=self.window)
        self.visual_frm = tk.Frame(master=self.swim_frm)
        self.frm_label = {self.MAIN_ACTIVITIES:self.main_act_frm,
                          self.MULTIPLE_FISH:self.multiple_frm,
                          self.FISH_LIST:self.multiple_frm,
                          self.SWIM_LIST:self.main_act_frm,
                          self.VISUAL_LIST:self.multiple_frm}

        self.label = {}
        for label_list, multichoice in self.LABEL_MULTICHOICE.items():
            if multichoice:
                for key in label_list:
                    self.label[key] = tk.IntVar()
                    self.label[key].set(0)
            else:
                key = self.NOTMULTI_KEY[label_list]
                self.label[key] = tk.StringVar()
                self.label[key].set(None)  # No default value
        self.btn_load = tk.Button(master=self.main_act_frm, text='Load Movies',
                                  width=10,command=self.get_dir) # load movies
        self.lbl_username = tk.Label(master=self.main_act_frm, text='User name:')
        self.ent_username = tk.Entry(master=self.main_act_frm)
        self.ent_username.bind("<Return>", self.insert_username)
        self.lbl_mainact = tk.Label(master=self.main_act_frm, text='What are they up to? (Choose one)')
        self.lbl_otheractivties = tk.Label(master=self.main_act_frm, text="Can you elaborate?")
        self.lbl_framevis = tk.Label(master=self.multiple_frm, text="How does the frame look?")
        self.lbl_multfish =tk.Label(master=self.multiple_frm, text="How many fish?")
        self.lbl_arrange = tk.Label(master=self.multiple_frm, text="How do they look?")
        # Label options depicted as radio buttons, because of the multitude of labels,
        # we will create a list containing all the radio buttons, defining them iteratively:

        self.btn_labels = {key: [] for key in [self.MAIN_ACTIVITIES,self.MULTIPLE_FISH, self.FISH_LIST, self.SWIM_LIST, self.VISUAL_LIST]}
        for label_list in self.btn_labels.keys():
            multichoice = self.LABEL_MULTICHOICE[label_list]
            for label_name in label_list:
                if multichoice:
                    self.btn_labels[label_list].append(tk.Checkbutton(master=self.frm_label[label_list], text=label_name,
                                                          #onvalue=1, offvalue=0,
                                                          variable=self.label[label_name],
                                                        command=self.set_label))
                else:
                    key = self.NOTMULTI_KEY[label_list]
                    self.btn_labels[label_list].append(tk.Radiobutton(master=self.frm_label[label_list], text=label_name,
                                                                          variable=self.label[key],
                                                          value=label_name, command=self.set_label))
            # An explanation on the labels:
            # Feeding success is when the fish can been seen swallowing a rotifer (small, round object) successfully
            # Feeding fail is when the fish cannot swallow the food item
            # Feeding I&O (In and Out) is when the food item briefly and it pops out
            # Spitting is when the fish spits the food item out (forcefully)
            # Other is when the main part of the frame doesn't contain a fish or the fish is blurry and out-of-focus
        self.lbl_comment = tk.Label(master=self.main_act_frm, text='Comments:')
        self.ent_comment = tk.Entry(master=self.main_act_frm,width=15)
        self.ent_comment.bind("<Return>", self.insert_comment)

    def on_close(self):
        """ Define the behavior of the GUI upon window close."""
        # If a video file is currently open, release it:
        if self.player:
            if self.player.curr_vid:
                self.player.curr_vid.stop()#.release()
                if not self.log_saved:
                    # If the log has been change without saving, open a window prompt:
                    result = messagebox.askquestion('Save log','Do you want to save changes?')
                    if result == 'yes':
                        # Save labels if requested to by the user:
                        self.save_labels()
                # Delete videos tagged for deletion and move the swim videos to a new folder


        self.window.quit()

    def get_dir(self):
        """ Define a new MoviePlayer instance, get the desired directory from user and load videos to GUI for analysis.
        """
        # If we already loaded some movies before, warn users to save their work:
        if self.player:
            result = messagebox.askquestion('Switch Player', "You are about to open a new Movie Player instance,"
                                                             "this will delete any unsaved labels. Are you sure?")
            if result != "yes":
                return
        # Define the movie player that will handle video display and navigation,
        # we pass the label var and comment widget so that their values can be set when we load a new
        # video to the GUI:
        if not self.username:
            messagebox.showinfo('Choose user name first!',
                                "Choose user name before loading video clips por favor, don't forget to press Enter")
        else:
            self.player = MultiUserMoviePlayer(self.window, label_var=self.label, comment_widget=self.ent_comment,
                                      multichoice=self.LABEL_MULTICHOICE, username=self.username,
                                    notmulti_key=self.NOTMULTI_KEY)
            self.player.load_directory()  # See the Movie Player class for details


    def insert_username(self,event):
        """Commits changes made to the comments entry field from the GUI to the log dataframe."""
        self.username = self.ent_username.get()
        if self.player:
            self.player.username=self.username
        self.log_saved = False
        self.window.focus_set()

class MultiUserMoviePlayer(MoviePlayer):
    COORDINATE_COLUMN_NAME = 'centroid'
    LOG_FILENAME = 'preds_labeled.csv'
    def __init__(self,window, label_var=[],comment_widget=[], multichoice=False,username=None,notmulti_key=None):
        self.window = window
        self.label_var = label_var
        self.comment_widget = comment_widget
        self.username = username
        self.notmulti_key = notmulti_key
        self.multichoice = multichoice # multichoice label vars will be loaded differently
        self.column_names = {label_name : label_name.lower().replace(' ', '_')
                                 for label_name in self.label_var.keys()}
        print(self.column_names)
        self.curr_vid_idx = 0  # Current video index
        self.num_vids = 0  # Total number of videos loaded
        self.panel = tk.Canvas(master=self.window, width=500, height=500)  # Used to display the video
        #self.panel.bind("<Configure>", self.resize_frame)
        self.directory = None  # Directory where the videos are saved
        self.curr_vid = None   # Current video capture object
        self.log_filepath = ''  # Log file location
        self.curr_clip_name = ''  # Current Movie file name
        self.file_paths = []  # List of video file paths
        self.snap_idx = 0  # Index to name snapshot files
        self.log = pd.DataFrame()   # Log file dataframe
        self.pause = True  # Play/pause marker, to make the play button function as a pause as well
        self.define_vid_btn_frm()  # Define the buttons
        self.set_layout()  # Set the GUI layout
        self.window.bind('<Key>',self.handle_keystroke)
        self.frame = np.zeros(1)
        self.play_speed = 5
        self.resize = False


    #    super().__init__(window,label_var,comment_widget,multichoice)
    def handle_missing_log(self):
        """ Create a new log file if no log file exists in the folder"""
        # Create the dataframe for the log:
        self.log = pd.DataFrame(columns=['clip_name','user_name'])
        for key in self.label_var.keys():
            if self.column_names[key] not in self.log.columns:
                self.log[self.column_names[key]] = 0
        self.log['comments'] = np.NaN
        #for i, vid in enumerate(self.file_paths):
            # Iterate over the video files that were loaded and enter them as new rows in the dataframe:
        #    clip_name = os.path.basename(vid)  # Get video name
         #   entry = self.get_entry(clip_name)
         #   self.log.loc[i, :] = entry
        # Create a filepath for the log:
        self.log_filepath = os.path.join(os.path.dirname(self.file_paths[0]), self.LOG_FILENAME)
        self.log.to_csv(self.log_filepath, index=False)  # Save the csv

    def load_log(self,root,filename):
        self.log_filepath = os.path.join(root, filename)  # save path
        if not os.path.isfile(self.log_filepath):
            self.handle_missing_log()
        else:
            self.log = pd.read_csv(self.log_filepath)  # load log\
            
            if 'user_name' not in self.log.columns:
                self.log['user_name'] = ''
        for key in self.label_var.keys():
            if self.column_names[key] not in self.log.columns:
                self.log[self.column_names[key]] = 0

    def get_entry(self,clip_name):
        # name format is [experiment_name]_midframe_[frame_num]_fish_[fish_id]_coordinate_[centroidx-centroidy].avi
        processed_name = clip_name.strip('.avi').split('_')
        frame_num = int(processed_name[-5])
        fish_id = int(processed_name[-3])
        coords = processed_name[-1].split('-')
        # As we don't have any of the data about the parent video, we'll leave it blank for the user to fill later:
        entry = {'clip_name':clip_name, 'user_name':self.username,'frame': frame_num,
        'fish_id': fish_id,
        'centroid': coords,'comments':''
        }
        for key in self.label_var.keys():
            entry[self.column_names[key]] = 0
        return entry

    def get_log_entries(self):
        """ Gets the label and comments fields from the log for the video that is loaded to the GUI"""
        if self.label_var:
            # Set the label variable to the label of the video in the log dataframe:
            #try:
                for label_list, multichoice in self.multichoice.items():
                    if multichoice:
                        for key in label_list:
                            var = self.label_var[key]
                            value_to_set = self.log.loc[(self.log.clip_name == self.curr_clip_name)&(self.log.user_name == self.username),
                                                 self.column_names[key]].values[0]
                            if np.isnan(value_to_set):
                                 value_to_set = 0
                            # else:
                            #     value_to_set = 0
                            var.set(int(value_to_set))
                    else:
                        key = self.notmulti_key[label_list]
                        var = self.label_var[key]
                        value_to_set = self.log.loc[(self.log.clip_name == self.curr_clip_name)&(self.log.user_name == self.username), self.column_names[key]].values[0]
                        if type(value_to_set)!=str:
                            value_to_set = None
                        var.set(value_to_set)
        if self.comment_widget:
            # Write the comment data from the log to the comment entry field
            # check if field exists, if not create it:
            if 'comments' not in self.log.columns:
                self.log['comments'] = ['']*len(self.log)
                self.log.to_csv(self.log_filepath, index=False)

            # get the text from dataframe:
            if len(self.log)>0:
                txt = self.log.loc[(self.log.clip_name == self.curr_clip_name)&(self.log.user_name == self.username)].comments
                if len(txt)>0:
                    # change the dataframe's null value to present an empty string in the GUI:
                    txt = txt.values[0]
                else:
                    txt = ''
                self.comment_widget.delete(0, tk.END)  # delete any existing text
                self.comment_widget.insert(0, txt)  # insert the text

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
        self.curr_clip_name = os.path.basename(self.file_paths[self.curr_vid_idx])
        # If integrated with the FeedingLabeler GUI, get the label and comments from the log:
        log_entries = self.log.loc[(self.log.clip_name == self.curr_clip_name) & (self.log.user_name == self.username)]
        if len(log_entries)==0:
            entry = self.get_entry(self.curr_clip_name)
            self.log = self.log.append(entry, ignore_index=True)
        self.get_log_entries()
        # Display the frame and coordinates (in the original video) from which this video was cut:
        txt = self.log.loc[(self.log.clip_name == self.curr_clip_name)&(self.log.user_name == self.username),
                              ['frame', self.COORDINATE_COLUMN_NAME]].to_string(index=False)  # retrieve the relevant data
        self.lbl_frame_centroid.configure(text=txt)  # display the text in the widget
        # And finally, open the video file:
        # self.curr_vid = cv2.VideoCapture(self.file_paths[self.curr_vid_idx])
        self.curr_vid = FileVideoStream(self.file_paths[self.curr_vid_idx]).start()#(reshape_size=min(self.panel.winfo_width(),
                                                                                 #           self.panel.winfo_height()))

        # if self.resize:
        #     self.save_resized(min(self.panel.winfo_width(), self.panel.winfo_height()))
        self.display_frame()  # display the first frame in the video
        self.window.title(self.curr_clip_name)  # change the GUI title to the current video name
        # Start playing the video automatically when a new video is set
        self.handle_play()
        #now = time.time()
        self.play_vid()  # event is set to True so that the play button would be handled as if clicked
        #end = time.time()
        #print(f'clip {end-now}')



if __name__ == '__main__':
    MultiUserLabeler()