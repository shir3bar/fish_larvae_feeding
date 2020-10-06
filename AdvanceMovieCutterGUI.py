
import tkinter as tk
import PIL.Image, PIL.ImageTk

class AdvanceMovieCutterGUI:

    def __init__(self, movie_cutters):
        self.window = tk.Toplevel()
        self.frm_attributes = tk.Frame(self.window)
        self.movie_cutters = movie_cutters
        self.visited = [0] * len(movie_cutters)
        self.curr_cutter_idx = 0
        self.curr_movie_cutter = self.movie_cutters[self.curr_cutter_idx]
        self.visited[self.curr_cutter_idx] = 1
        self.curr_movie_cutter.train_bg_subtractor()
        self.curr_frame_gen = self.curr_movie_cutter.process_vid()

        self.apply_brightness = tk.BooleanVar()
        self.attribute_value_dict = {}
        self.attribute_labels_entries_dict = {}
        self.set_attribute_vars()
        self.set_attribute_widgets()
        self.display_attributes()
        self.btn_apply_brightness = tk.Checkbutton(master=self.frm_attributes,text='Save brightened videos',
                                                   variable=self.apply_brightness,command=self.set_brightness)
        self.btn_apply_changes = tk.Button(master=self.frm_attributes, text='Apply Changes', command=self.apply_changes)
        self.frm_vid_control = tk.Frame(master=self.window)
        self.btn_preview = tk.Button(master=self.frm_vid_control, text="Preview", command=self.play_vid)
        self.btn_preview.bind('<Button-1>', self.handle_preview)
        self.btn_back = tk.Button(master=self.frm_vid_control, text="\N{LEFTWARDS ARROW}",command=self.prev_vid)
        self.btn_next = tk.Button(master=self.frm_vid_control, text="\N{RIGHTWARDS ARROW}", command=self.next_vid)
        self.panel = tk.Canvas(master=self.window, width=self.curr_movie_cutter.SHAPE[0],
                               height=800)
        self.display_frame()
        self.pause = True
        self.set_layout()

        # define what happens when the GUI window is closed by user:
        self.window.wm_protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.curr_movie_cutter.set_start_frame()
        self.curr_movie_cutter.reset_bg_subtractor()
        self.window.destroy()

    def set_brightness(self,event=None):
        self.curr_movie_cutter.apply_brightness = self.apply_brightness.get()

    def handle_preview(self, event=None):
        self.pause = not self.pause

    def set_attribute_vars(self):
        def set_bright(x):
            self.curr_movie_cutter.brighten = int(x)


        def set_blur(x):
            x=int(x)
            if x%2 == 0:
                x += 1
            #x=[int(num) for num in x.strip('(').strip(')').split(',')]
            #x=tuple([num if num % 2 == 1 else num + 1 for num in x])
            self.curr_movie_cutter.blur = (x, x)

        def set_width(x):
            self.curr_movie_cutter.min_width = int(x)

        def set_height(x):
            self.curr_movie_cutter.min_height = int(x)

        def set_length(x):
            self.curr_movie_cutter.movie_length = int(x) + 1

        def set_start(x):
            self.curr_movie_cutter.start_frame = int(x)
            self.curr_movie_cutter.set_start_frame()

        self.attribute_value_dict = {'brighten': (self.curr_movie_cutter.brighten, 'Brighten', set_bright),
                                     'blur': (self.curr_movie_cutter.blur[0], 'Blur', set_blur),
                                     'min_width': (self.curr_movie_cutter.min_width, 'Minimum Blob Width', set_width),
                                     'min_height': (self.curr_movie_cutter.min_height, 'Minimum Blob Height', set_height),
                                     'clip_length': (self.curr_movie_cutter.movie_length-1, 'Clip Length', set_length),
                                     'start_frame': (self.curr_movie_cutter.start_frame, 'Start Frame', set_start)}

    def focus_next(self, event):
        self.update_attributes(event)
        event.widget.tk_focusNext().focus()

    def set_attribute_widgets(self):
        for attribute, value in self.attribute_value_dict.items():
            label = tk.Label(master=self.frm_attributes, text=value[1])
            entry = tk.Entry(master=self.frm_attributes, name=attribute)
            entry.bind('<Return>', self.update_attributes)
            entry.bind('<Tab>', self.focus_next)
            self.attribute_labels_entries_dict[attribute] = [label, entry]

    def display_attributes(self):
        for attribute, value in self.attribute_value_dict.items():
            entry = self.attribute_labels_entries_dict[attribute][1]
            entry.delete(0, tk.END)
            entry.insert(0, str(value[0]))
        self.apply_brightness.set(self.curr_movie_cutter.apply_brightness)

    def set_layout(self):
        self.window.rowconfigure(0, weight=1, minsize=900)
        self.window.rowconfigure(1, weight=1, minsize=75)
        self.window.columnconfigure(1, weight=1, minsize=800)
        counter = 0
        for label, entry in self.attribute_labels_entries_dict.values():
            label.grid(row=counter, column=0, sticky="ew", padx=5, pady=10)
            counter += 1
            entry.grid(row=counter, column=0, sticky="ew", padx=5, pady=10)
            counter += 1
        self.btn_apply_brightness.grid(row=counter+1, column=0, sticky="ew", padx=5, pady=10)
        self.btn_apply_changes.grid(row=counter+2, column=0, sticky="ew", padx=5, pady=10)
        self.frm_attributes.grid(row=0, column=0, sticky="ns")

        self.panel.grid(row=0, column=1, sticky="nsew")
        self.btn_preview.grid(row=0, column=0, sticky="ew", padx=10, pady=2)
        self.btn_back.grid(row=0, column=1, sticky="ew", padx=10, pady=2)
        self.btn_next.grid(row=0, column=2, sticky="ew", padx=10, pady=2)
        self.frm_vid_control.grid(row=1,column=1)

    def set_cutter(self):
        self.curr_movie_cutter = self.movie_cutters[self.curr_cutter_idx]
        if self.visited[self.curr_cutter_idx] == 0:
            print('training bg subtractor...')
            self.curr_movie_cutter.train_bg_subtractor()
            self.visited[self.curr_cutter_idx] = 1
        self.curr_frame_gen = self.curr_movie_cutter.process_vid()
        self.set_attribute_vars()
        self.display_attributes()

    def prev_vid(self):
        self.curr_cutter_idx -= 1
        if self.curr_cutter_idx<0:
            self.curr_cutter_idx=0
        else:
            self.set_cutter()
            self.display_frame()

    def next_vid(self):
        self.curr_cutter_idx += 1
        if self.curr_cutter_idx >= len(self.movie_cutters):
            self.curr_cutter_idx = len(self.movie_cutters)-1
        else:
            self.set_cutter()
            self.display_frame()

    def display_frame(self):
        """Read a single frame from the current video and display it onto the GUI."""
        frame = next(self.curr_frame_gen)  # Save that frame
        # Convert frame to display it on GUI:
        self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
        self.panel.create_image(0, 0, image=self.photo, anchor=tk.NW)  # Draw the image in the Panel widget

    def play_vid(self):
        try:
            if not self.pause:
                self.display_frame()
                self.window.after(15, self.play_vid)
        except:
            self.curr_frame_gen = self.curr_movie_cutter.process_vid()
            self.handle_preview()

    def update_attributes(self, event):
        attribute_name = str(event.widget).split('.')[-1]
        value = self.attribute_labels_entries_dict[attribute_name][1].get()
        self.attribute_value_dict[attribute_name][2](value)

    def apply_changes(self):
        print(self.curr_movie_cutter)
        self.curr_movie_cutter.set_start_frame()
        self.curr_movie_cutter.reset_bg_subtractor()
        self.curr_movie_cutter.train_bg_subtractor()
        self.curr_frame_gen = self.curr_movie_cutter.process_vid()
        self.display_frame()




