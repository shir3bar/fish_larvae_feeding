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
    KEYS_TO_LABELS = {'1': 'swim','2': 'strike','3':'Spit/I&O','3': 'Other'}
    LABEL_LIST = ['swim','strike','Spit/I&O','Other']
    LABEL_MULTICHOICE = False

   # def __init__(self):
    #    pass

    def on_close(self):
        """ Define the behavior of the GUI upon window close."""
        # If a video file is currently open, release it:
        if self.player:
            if self.player.curr_vid:
                self.player.curr_vid.release()
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
        self.player = UncuratedMoviePlayer(self.window, label_var=self.label, comment_widget=self.ent_comment,
                                  multichoice=self.LABEL_MULTICHOICE)
        self.player.load_directory()  # See the Movie Player class for details
        self.bind_keystrokes()


class UncuratedMoviePlayer(MoviePlayer):

    LOG_FILENAME = 'labeled_preds.csv'
    FOLDERNAME_TO_IGNORE = 'removed_doubles'
    COORDINATE_COLUMN_NAME = 'centroid'
    #def __init__(self,window, label_var=[],comment_widget=[], multichoice=False):
    #    super().__init__(window,label_var,comment_widget,multichoice)

    def handle_missing_log(self):
        """ Override the behavior of MoviePlayer for handling missing log files"""
        msg = ''
        for filename in ['preds_without_removed.csv','preds.csv']:
            if os.path.isfile(os.path.join(self.directory,filename)):
                self.log_filepath = os.path.join(self.directory, 'preds.csv')  # save path
                self.log = pd.read_csv(self.log_filepath)  # load log
                if self.multichoice:
                    for key in self.label_var.keys():
                        if self.column_names[key] not in self.log.columns:
                            self.log[self.column_names[key]] = 0
                else:
                    self.log['reviewer_label'] = np.NaN
                self.log.to_csv(self.log_filepath,index=False)
                break
        if len(msg)==0:
            msg = f'Error no preds file found. App will not function right, choose a different folder.'
        messagebox.showinfo('Notice', msg)



    def get_entry(self,clip_name):
        # name format is [experiment_name]_midframe_[frame_num]_fish_[fish_id]_coordinate_[centroidx-centroidy].avi
        processed_name = clip_name.strip('.avi').split('_')
        frame_num = int(processed_name[-5])
        fish_id = int(processed_name[-3])
        coords = processed_name[-1].split('-')
        # As we don't have any of the data about the parent video, we'll leave it blank for the user to fill later:
        entry = {'frame': frame_num,
        'fish_id': fish_id,
        'centroid': coords,
        'bboxs': np.NaN,
        'detection_scores': np.NaN,
        'detection_pred_class': np.NaN,
        'action_preds': np.NaN,
        'strike_scores': np.NaN,
        'strike_labels': np.NaN,
        'spit_labels': np.NaN,
        'clip_name': clip_name,
        'reviewer_label':None}
        return entry


if __name__ == '__main__':
    RDagLabeler()