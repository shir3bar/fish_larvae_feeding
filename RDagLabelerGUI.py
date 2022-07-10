import os
import pandas as pd
import tkinter as tk
from tkinter.filedialog import askdirectory
from tkinter import messagebox
from pathlib import Path
from LabelerGUI import MoviePlayer, Labeler
import cv2
import numpy as np

class RDagLabeler(Labeler):
    KEYS_TO_LABELS = {'1': 'Swim','2': 'Strike','3':'Spit/I&O','3': 'Other'}
    LABEL_LIST = ['Swim','Strike','Spit/I&O','Other']
    LABEL_MULTICHOICE = False

   # def __init__(self):
    #    pass

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
                        # Save labels if requested to by the
                        # user:
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
        self.player = RDagMoviePlayer(self.window, label_var=self.label, comment_widget=self.ent_comment,
                                  multichoice=self.LABEL_MULTICHOICE)
        self.player.load_directory()  # See the Movie Player class for details
        self.bind_keystrokes()


class RDagMoviePlayer(MoviePlayer):

    LOG_FILENAME = 'preds_labeled.csv'
    FOLDERNAME_TO_IGNORE = 'removed_doubles'
    COORDINATE_COLUMN_NAME = 'centroid'


    def handle_missing_log(self):
        """ Override the behavior of MoviePlayer for handling missing log files"""

        filename = 'preds.csv'
        if os.path.isfile(os.path.join(self.directory,filename)):
            self.log_filepath = os.path.join(self.directory, 'preds.csv')  # save path
            self.log = pd.read_csv(self.log_filepath)  # load log
            if 'clip_name' in self.log.columns:
                # if log uses old column names, change it to comply with new naming system
                self.log = self.log.loc[self.log.clip_name.notna(),
                           :]  # filter out swims (which don't have a clip name) leave only strikes
        else:
            self.log = pd.DataFrame(columns=['vid_name','frame','clip_name','fish_id','centroid',
                                             'bboxs','detection_scores','detection_pred_class','action_preds',
                                             'strike_scores','reviewer_label'])
            for i, vid in enumerate(self.file_paths):
                # Iterate over the video files that were loaded and enter them as new rows in the dataframe:
                clip_name = os.path.basename(vid)  # Get video name
                entry = self.get_entry(clip_name)
                self.log.loc[i, :] = entry
        self.log['reviewer_label'] = np.NaN
        new_filename = filename.split('.')[0] + '_labeled.csv'
        self.log_filepath = os.path.join(self.directory, new_filename)
        self.log.to_csv(self.log_filepath,index=False)


    def load_log(self,root,filename):
        self.log_filepath = os.path.join(root, filename)  # save path
        self.log = pd.read_csv(self.log_filepath)  # load log
        if not self.multichoice:
            if 'label' in self.log.columns:
                # if log uses old column names, change it to comply with new naming system
                self.log = self.log.rename(columns={'label': 'reviewer_label'})
            elif not 'reviewer_label' in self.log.columns:
                self.log['reviewer_label'] = np.NaN
        else:
            for key in self.label_var.keys():
                if self.column_names[key] not in self.log.columns:
                    self.log[self.column_names[key]] = 0

    def get_entry(self,clip_name):
        # name format is [experiment_name]_midframe_[frame_num]_fish_[fish_id]_coordinate_[centroidx-centroidy].avi
        processed_name = clip_name.strip('.avi').split('_')
        frame_num = int(processed_name[-5])
        fish_id = int(processed_name[-3])
        coords = processed_name[-1].split('-')
        vid_name = processed_name[0]
        # As we don't have any of the data about the parent video, we'll leave it blank for the user to fill later:
        entry = {'vid_name':vid_name,
        'frame': frame_num,
        'clip_name': clip_name,
        'fish_id': fish_id,
        'centroid': coords,
        'bboxs': np.NaN,
        'detection_scores': np.NaN,
        'detection_pred_class': np.NaN,
        'action_preds': np.NaN,
        'strike_scores': np.NaN,
        'reviewer_label':None}
        return entry





if __name__ == '__main__':
    RDagLabeler()