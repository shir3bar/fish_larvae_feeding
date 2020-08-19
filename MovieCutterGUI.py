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
        self.btn_open = tk.Button(self.window, text="Open", command=self.open_vid)
        self.btn_save = tk.Button(self.window,text='Save to', command=self.save_dir)
        self.btn_start = tk.Button(self.window, text="Start Cutting", command=self.cut_movies)
        self.bar = Progressbar(self.window, length=300, orient="horizontal",
                                    style='black.Horizontal.TProgressbar', mode="determinate")
        self.window.rowconfigure([0,1],weight=1,minsize=100)
        self.btn_open.grid(row=0,column=0, sticky="ew",padx=5,pady=5)
        self.btn_save.grid(row=0,column=1,sticky="ew",padx=5,pady=5)
        self.btn_start.grid(row=0,column=2,sticky="ew",padx=5,pady=5)
        self.bar.grid(row=1,sticky="ew")
        self.movie_cutter = None
        self.window.mainloop()

    def open_vid(self):
        self.vidpath = askopenfilename(filetypes=[("Video Files", ["*.mp4","*.avi"]), ("All Files", "*.*")])
        if not self.vidpath:
            return

        self.window.title(f"Movie Cutter - {self.vidpath}")

    def save_dir(self):
        self.savepath = askdirectory()
        if self.vidpath:
            self.movie_cutter = MovieCutter(self.vidpath, self.savepath,progressbar=self.bar)

    def cut_movies(self):
        self.movie_cutter.cut()
        messagebox.showinfo('Done Cutting', f'Vids saved to: {self.movie_cutter.folder_path} ')




CutterApp()

