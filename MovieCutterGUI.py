from MovieCutter import MovieCutter
import tkinter as tk
from tkinter.filedialog import askopenfilename, askdirectory
from tkinter.ttk import Progressbar
import os
import cv2
import PIL.Image, PIL.ImageTk
from tkinter import ttk
import pandas as pd
from tkinter import messagebox

class CutterApp():
    def __init__(self):
        self.window=tk.Tk()
        self.frm_btn = tk.Frame(self.window)
        self.btn_open = tk.Button(self.frm_btn, text="Open", command=self.open_vid)
        self.btn_save = tk.Button(self.frm_btn,text='Save to', command=self.save_dir)
        self.btn_start = tk.Button(self.frm_btn, text="Start Cutting", command=self.cut_movies)
        self.lbl_training = tk.Label(self.window, text='Choose a video file first')
        self.bar = Progressbar(self.window, length=300, orient="horizontal",
                                    style='black.Horizontal.TProgressbar', mode="determinate")
        self.window.rowconfigure([0,1],weight=1,minsize=100)
        self.btn_open.grid(row=0,column=0, sticky="ew",padx=5,pady=2)
        self.btn_save.grid(row=0,column=1,sticky="ew",padx=5,pady=2)
        self.btn_start.grid(row=0,column=2,sticky="ew",padx=5,pady=2)
        self.frm_btn.grid(row=0)
        self.lbl_training.grid(row=1,sticky="nsew")
        self.bar.grid(row=2,sticky="e",pady=5,padx=5)
        self.movie_cutter = None
        self.window.mainloop()

    def open_vid(self):
        self.vidpath = askopenfilename(filetypes=[("Video Files", ["*.mp4","*.avi"]), ("All Files", "*.*")])
        if not self.vidpath:
            return
        self.window.title(f"Movie Cutter - {self.vidpath}")
        self.lbl_training.configure(text='Choose where to save the videos')
        self.lbl_training.update()
        self.bar["value"] = 0

    def save_dir(self):
        self.savepath = askdirectory()
        if self.vidpath:
            self.movie_cutter = MovieCutter(self.vidpath, self.savepath,
                                            trainlabel=self.lbl_training, progressbar=self.bar)

    def cut_movies(self):
        self.movie_cutter.cut()
        messagebox.showinfo('Done Cutting', f'Vids saved to: {self.movie_cutter.folder_path} ')




CutterApp()

