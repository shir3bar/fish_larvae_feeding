import tkinter as tk
from tkinter.filedialog import askdirectory
import os
import cv2
import PIL.Image, PIL.ImageTk
from tkinter import ttk
import pandas as pd
from tkinter import messagebox


class LabelApp():
    def __init__(self):
        self.window = tk.Tk()
        self.window.rowconfigure(0, weight=1, minsize=500)
        self.window.rowconfigure(1, weight=1, minsize=75)
        self.window.columnconfigure(1, weight=1, minsize=500)
        self.new_vid_idx = tk.IntVar()
        self.curr_vid_idx = 0
        self.define_label_frm()
        self.define_vid_btn_frm()
        self.panel = tk.Canvas(master=self.window,width=500,height=500)
        self.btn_save=tk.Button(master=self.window,text='Save Labels', command=self.save_labels)
        self.set_layout()
        self.directory = None
        self.curr_vid = None
        self.log_filepath = ''
        self.log_saved = True
        self.num_frames = 0
        self.snap_idx=0
        self.log = pd.DataFrame()
        self.pause=True
        self.file_paths = []
        self.window.wm_title("Fish Labeler")
        self.window.wm_protocol("WM_DELETE_WINDOW", self.onClose)
        self.window.mainloop()


    def onClose(self):
        if self.curr_vid:
            self.curr_vid.release()
            if not self.log_saved:
                result = messagebox.askquestion('Save log','Do you want to save changes?')
                if result == 'yes':
                    self.save_labels()
        self.window.quit()

    def save_labels(self):
        try:
            self.log.to_csv(self.log_filepath,index=False)
            messagebox.showinfo('Labels Saved', f'Log saved to: {self.log_filepath} ')
            self.log_saved = True
        except:
           messagebox.showinfo('Error', f'Error saving log file')


    def define_label_frm(self):
        self.frm_label = tk.Frame(master=self.window)
        self.label = tk.StringVar()
        self.label.set('Feeding')
        self.btn_load = tk.Button(master=self.frm_label, text='Load Movies', command=self.get_dir)
        self.btn_not_feed = tk.Radiobutton(master=self.frm_label, text='Not Feeding', variable=self.label,
                                      value='Not feeding', command=self.set_label)
        self.btn_feed = tk.Radiobutton(master=self.frm_label, text='Feeding', variable=self.label, value='Feeding', command=self.set_label)
        self.btn_other = tk.Radiobutton(master=self.frm_label, text='Other', variable=self.label, value='Other', command=self.set_label)

    def define_vid_btn_frm(self):
        self.frm_vid_btns = tk.Frame(master=self.window)
        self.vids_list=ttk.Combobox(master=self.frm_vid_btns,width=5, textvariable=self.new_vid_idx, state='readonly')
        self.btn_back = tk.Button(master=self.frm_vid_btns, text="\N{LEFTWARDS ARROW}",command=self.prev_vid)
        self.btn_play = tk.Button(master=self.frm_vid_btns, text='Play/Pause', command=self.play_vid)
        self.btn_play.bind('<Button-1>', self.handle_play)
        self.btn_next = tk.Button(master=self.frm_vid_btns, text="\N{RIGHTWARDS ARROW}", command=self.next_vid)
        self.btn_snapshot = tk.Button(master=self.frm_vid_btns, text='Snapshot', command=self.get_snapshot)

    def handle_play(self, event):
        self.pause = not self.pause

    def get_snapshot(self):
        path = self.directory + os.path.sep + 'snapshots'
        if self.snap_idx == 0:
            try:
                os.mkdir(path)
            except:
                print('Snap directory already exists!')
        filepath=path + os.path.sep + self.curr_movie_name[0:-4] + '_snap' + str(self.snap_idx) + '.jpg'
        cv2.imwrite(filepath, self.frame)
        self.snap_idx+=1
        tk.messagebox.showinfo('Save Snapshot', f'Snapshot saved at {filepath}')

    def display_frame(self):
        ret, frame = self.curr_vid.read()
        self.frame = frame
        self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
        self.panel.create_image(0, 0, image=self.photo, anchor=tk.NW)

    def on_select(self, event):
        if event:
            print(event.widget.get())
            self.curr_vid_idx=self.new_vid_idx.get()
            self.curr_vid = cv2.VideoCapture(self.file_paths[self.curr_vid_idx])
            self.display_frame()

    def set_layout(self):
        self.btn_load.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.btn_feed.grid(row=2, column=0, sticky="ew", padx=5, pady=10)
        self.btn_not_feed.grid(row=3, column=0, sticky="ew", padx=5, pady=10)
        self.btn_other.grid(row=4, column=0, sticky='ew', padx=5, pady=10)

        self.btn_save.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        self.vids_list.grid(row=0,column=0,sticky="w",padx=10 )
        self.vids_list.bind('<<ComboboxSelected>>', self.on_select)
        self.btn_back.grid(row=0, column=2, sticky="e", padx=10)
        self.btn_play.grid(row=0, column=3, sticky="e", padx=10)
        self.btn_next.grid(row=0, column=4, sticky="e", padx=10)
        self.btn_snapshot.grid(row=0, column=5, sticky="e", padx=10)

        self.frm_label.grid(row=0, column=0, sticky="ns")
        self.panel.grid(row=0, column=1, sticky='nsew')
        self.frm_vid_btns.grid(row=1, column=1)

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
        try:
            self.curr_vid = cv2.VideoCapture(self.file_paths[self.curr_vid_idx])
            self.display_frame()
        except IndexError:
            self.curr_vid_idx=self.num_frames-1
            self.panel.create_text(250, 250, text='Done!')
        self.curr_movie_name = self.file_paths[self.curr_vid_idx].split(os.path.sep)[-1]
        self.label.set(self.log.loc[self.log.movie_name == self.curr_movie_name].label.values[0])

    def prev_vid(self):
        self.curr_vid.release()
        self.curr_vid_idx -= 1
        if self.curr_vid_idx >= 0:
            self.curr_vid = cv2.VideoCapture(self.file_paths[self.curr_vid_idx])
            self.display_frame()
        else:
            self.curr_vid_idx = 0
        self.curr_movie_name = self.file_paths[self.curr_vid_idx].split(os.path.sep)[-1]
        self.label.set(self.log.loc[self.log.movie_name == self.curr_movie_name].label.values[0])

    def get_dir(self):
        self.directory = askdirectory()
        for root, directories, files in os.walk(self.directory):
            for filename in files:
                # Join the two strings in order to form the full filepath.
                if filename.endswith('.avi'):
                    filepath = os.path.join(root, filename)
                    self.file_paths.append(filepath)  # Add it to the list.
                elif filename.endswith('.csv'):
                    self.log_filepath = os.path.join(root, filename)
                    self.log = pd.read_csv(self.log_filepath)

        self.num_frames=len(self.file_paths)
        self.curr_vid_idx=0
        try:
            self.vids_list['values'] = list(range(self.num_frames))
            self.curr_movie_name = self.file_paths[self.curr_vid_idx].split(os.path.sep)[-1]
            self.label.set(self.log.loc[self.log.movie_name == self.curr_movie_name].label.values[0])
            self.curr_vid = cv2.VideoCapture(self.file_paths[self.curr_vid_idx])

            self.display_frame()
        except:
            self.panel.create_text(0, 0, text='No video in directory')

    def set_label(self):

        self.log.loc[self.log.movie_name == self.curr_movie_name, ['label']] = self.label.get()
        print(self.log.loc[self.log.movie_name == self.curr_movie_name])
        self.log_saved = False


if __name__ == '__main__':
    LabelApp()
