from imutils.video import FPS
import os
import cv2
import numpy as np
import pandas as pd
from datetime import datetime


class MovieProcessor:
    """Process videos to detect fish larvae using classic image processing with OpenCV."""
    def __init__(self,vid_path, save_dir, brighten=50, blur=(0,0), min_width=70, min_height=70,
                 apply_brightness=False, num_train_frame=500, fps=30, start_frame=0, frame_limit=1000):
        """Initiate a processor object. inputs:
        vid_path - location of the video to process
        save_dir - location to save the processed video
        brighten - optional, brighten the image as part of the processing flow
                the default value is set to brighten to 50 so as to mildly brighten the image
        blur - optional, kernel size for blurring the image as part of the processing flow
            the default value is set to (0,0) so that no blurring occurs
        min_width - minimum width of a single blob, helps filter small non-fish objects
        min_height - minimum height of a single blob, helps filter small non-fish objects
        apply_brightness - save the processed videos with the brightened frames
        num_train_frame - number of frames used to train the background subtractor
        fps - define the rate of frames per second for the processed video output
        start_frame  - set the frame from which to start the processing of the video
        frame_limit - set how many frames will be used for the processing preview in process_vid method"""
        self.vid_path = vid_path
        self.folder_path = save_dir
        self.min_width = min_width  # minimal blob width
        self.min_height = min_height  # minimal blob height
        self.brighten = brighten
        if blur[0] != 0:
            self.blur = tuple([num if num%2 == 1 else num+1 for num in list(blur)])  # The default kernel size is set to no blur
        else:
            self.blur = blur
        self.fps = fps
        # Create a video capture object:
        self.cap = cv2.VideoCapture(vid_path)
        # set the number of training frames to use for training the background subtractor:
        self.num_train_frames = num_train_frame
        # Get the number of frames in the original video:
        self.num_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
        # if the number of frames in the video is smaller than the number of training frames
        # for the background subtractor, reduce the amount of training frames:
        if self.num_train_frames > self.num_frames:
            self.num_train_frames = round(self.num_frames / 4)
        # Get the frame dimensions:
        self.SHAPE = [int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))]
        # Create background subtractor object:
        self.bg_sub = cv2.createBackgroundSubtractorMOG2(history=self.num_train_frames, detectShadows=True)
        # Name the output video:
        self.output_vid = vid_path[0:-4]+'_proccesed.avi'
        # The bbox_dict will house the coordinates and dimensions of the bounding boxes around the detected objects,
        # as well as the centroids of these bounding boxes:
        self.bbox_dict = {}
        self.frame = None # video frame, initialize at nobe
        # codec for video writing, see https://www.pyimagesearch.com/2016/02/22/writing-to-video-with-opencv/:
        self.fourcc = cv2.VideoWriter_fourcc(*"MJPG")#cv2.VideoWriter_fourcc(*'RGBA')
        self.start_frame = start_frame  # set the frame of the video where processing will start
        self.frame_limit = frame_limit
        self.apply_brightness = apply_brightness # Apply the brightness adjustment to the saved video

    @staticmethod
    def get_centroid(x, y, w, h):
        """ Get the centroid of the bouding box defined by x, y, w and h"""
        cx = x + int(w / 2)
        cy = y + int(h / 2)
        return cx, cy

    def set_start_frame(self):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)  # Set the start frame to the one selected by the user

    def get_contours(self):
        """ Get the blobs/contours/fish detected in the image.
        Each blob gets an entry in the bbox_dict - the key is the bounding box coordinates and dimensions,
        the value is the centroid of that bounding box.
        """

        # find all contours/blobs in the frame:
        self.bbox_dict = {}
        contours, hierarchy = cv2.findContours(self.combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
        for (i, contour) in enumerate(contours):
            # for each detected object/blob/contour
            # Get the bounding box:
            (x, y, w, h) = cv2.boundingRect(contour)
            # Filter by height and width:
            contour_valid = (w >= self.min_width) and (
                    h >= self.min_height) and (w <= self.min_width*10) and (h <= self.min_height*10)

            if not contour_valid:
                # if the contour isn't valid, skip it:
                continue
            # Get bbox centroid:
            centroid = self.get_centroid(x, y, w, h)
            # Create the bbox entry:
            self.bbox_dict[(x, y, w, h)] = centroid

    def draw_boxes(self):
        """ Draw bounding boxes around objects in image
        """
        BOUNDING_BOX_COLOUR = (255, 10, 0)  # BGR instead of RGB
        CENTROID_COLOUR = (255, 192, 0)  # BGR instead of RGB
        gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)   # convert the image to grayscale
        # begin depicting the processing by using the base frame, brighten it if the apply brightness is set to True
        # else use the original video frame:
        if self.apply_brightness:
            self.processed_frame = cv2.convertScaleAbs(self.frame, alpha=1, beta=self.brighten)
        else:
            self.processed_frame = self.frame

        for bbox, centroid in self.bbox_dict.items():
            # for each blob detected
            x, y, w, h = bbox
            # cut only the blob out of the grayscale and calculate the Laplacian as a measure of image blurriness:
            subframe = gray[y:y + h,x:x + w]
            lap = cv2.Laplacian(subframe, cv2.CV_64F).var()
            # Draw the bounding box and centroid on the processed frame:
            cv2.rectangle(self.processed_frame, (x, y), (x + w - 1, y + h - 1),
                          BOUNDING_BOX_COLOUR, 4)
            cv2.circle(self.processed_frame, centroid, 2, CENTROID_COLOUR, -1)
            # Write the laplacian value next to the detected object:
            cv2.putText(self.processed_frame, f'{lap:.2f}', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)

    def get_filter(self):
        """ Get the foreground mask for a frame,
        use an approach combining OpenCV background subtraction and Canny edge detection
        to avoid detecting floating particles in the water.
        input:
        frame - frame from video
        bg_sub - an open-cv pre-trained background subtractor
        brighten - bool, whether to adjust brightness in the image
        blur - bool, whether to apply gaussian blur to remove background noise from the image
        output:
        combined - a foreground mask created by fine-tuning the background subtractor output with edge detection.
        """
        if self.frame is None:
            _, self.frame = self.cap.read()
        # First process the new frame:
        gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)  # Turn to grayscale
        # Apply gaussian blur to image using the kernel size defined by user:
        if self.blur[0] != 0:
            gray = cv2.GaussianBlur(gray, self.blur, 0)
        # Apply brightness adjustment to image, if brighten=0 image will remain unchanged:
        gray = cv2.convertScaleAbs(gray, alpha=1, beta=self.brighten)
        # Calculate the foreground mask using the trained background subtractor:
        self.fg_mask = self.bg_sub.apply(gray, None, 0.001)
        # Now for the edge detection:
        # Blur out the small particle floating in the water:
        denoise_background = cv2.GaussianBlur(gray, (71, 71), 0)
        # get edges from the blurred image to filter out small floating particles:
        img = cv2.Canny(denoise_background, 10, 10)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (10, 10))  # Define the kernel for closing gaps
        closing = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)  # fill in gaps in the edges
        opening = cv2.morphologyEx(closing, cv2.MORPH_OPEN, kernel)
        # Dilate to merge adjacent blobs
        dilation = cv2.dilate(opening, kernel, iterations=2)
        # get the areas that are detected by both the bg-sub and the edge detection routine:
        self.combined = cv2.bitwise_and(self.fg_mask, closing)

    def train_bg_subtractor(self):
        """ Pre-train the background subtractor.
        input:
        cap - video capture object, the video
        bg_sub - background subtractor object
        num - number of frames to train on
        brighten - bool, whether to adjust brightness in the image
        blur - bool, whether to apply gaussian blur to remove background noise from the image
        output:
        bg_sub - trained background subtractor
        """
        for i in range(self.num_train_frames):
            # iterate over the selected number of frames
            # ret,frame=cap.read() # get one frame
            _, self.frame = self.cap.read()
            gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)  # convert to grayscale
            # apply gaussian blur, default kernel size is set to 0 so that no blurring occurs
            if self.blur[0] != 0:
                gray = cv2.GaussianBlur(gray, self.blur, 0)
            # apply brightening if applicable
            gray = cv2.convertScaleAbs(gray, alpha=1, beta=self.brighten)
            self.fg_mask = self.bg_sub.apply(gray, None, 0.001)  # apply bg_sub to the frame (modified or not)

    def process_vid(self):
        """ Detect objects in a single video and create a new video with the bounding boxes around objects.
        This function is set up as a generator and yields one frame at a time.
        input:
        vid_name - path and filename of the input video
        output_vid - path and filename for the generated video
        brighten - bool, whether to adjust brightness in the image
        blur - bool, whether to apply gaussian blur to remove background noise from the image
        """
        # iterate over the remaining frames:
        counter = 0
        while counter <= self.frame_limit:
            grabbed, self.frame = self.cap.read()  # get frame
            if not grabbed:
                # If the video is finished, stop the loop
                break
            counter += 1
            self.get_filter()  # get foreground mask
            self.get_contours()  # find objects inside the mask, get a list of their bounding boxes
            self.draw_boxes()  # draw bounding boxes on original frame
            #self.processed_frame = cv2.cvtColor(self.processed_frame, cv2.COLOR_BGR2RGB)  # optional: open-cv work in BGR so convert back to RGB
            yield self.processed_frame
        # When done rewind to the start frame:
        self.set_start_frame()

    def save_vid(self):
        vid_writer = cv2.VideoWriter(self.output_vid, self.fourcc, 30,
                                     (self.SHAPE[0], self.SHAPE[1]), True)
        frame_gen = self.process_vid()
        try:
            while True:
                vid_writer.write(next(frame_gen))  # Write frame to the new video file
        except StopIteration:
            # release resources:
            self.vid_writer.release()

    def reset_bg_subtractor(self):
        """ Reset the background subtractor"""
        self.bg_sub = cv2.createBackgroundSubtractorMOG2(history=self.num_train_frames, detectShadows=True)



class MovieCutter(MovieProcessor):
    """ Process a fish larvae video and cut movie segments of individual fish.
    The size of the area around the fish can be adjusted, as well as the framerate and the length of the segment.
    The fish are detected using the MovieProcessor parent class.
    A new folder is created with all the segments, as well as a log containing the file name, the coordinates of the
    detected fish, and the frame from which the segment was cut.
    New fish are detected after 80% of the segment video length, this is to make sure there is an overlap between
    the segments and minimize the possibility of missing some of the fish behavior.
    When a segment is done a mean Laplacian value is calculated for all it's frames, if it is below the threshold
    the video will be deleted, this is done to filter out blurry fish."""
    # Class variables, txt messages to GUI users if GUI integration is invoked:
    BG_SUB_TRAIN_MSG = 'training background subtractor...'
    CUTTING_MSG = 'begin cutting:'
    END_MSG = 'Done!'
    MOVIE_PREFIX = 'cutout_'  # movie file name prefix

    def __init__(self, vid_path, save_dir, padding=250, fps=30, start_frame=0,  movie_format='.avi',
                 movie_length=100,  progressbar=[], trainlabel=[]):
        """ Initiate a MovieCutter instance to chop fish larvae movies into segments.
        inputs:
        vid_path - path of the video file to cut
        save_dir - path to save the cut segments
        padding - sets the size of the cut video frame, pads the centroid of each fish detected from each side
        fps - set the frames per second for the cut videos
        movie_length - sets the number of frames in each cut segment
        progressbar - a tk progressbar widget, optional integration, to show updates on the MovieCutterGUI
        trainlabel - a tk label widget, optional integration, to show updates on the MovieCutterGUI
        movie - an index of current video if several videos were selected in the GUI."""
        # Invoke the parent (movie processor) initialization:
        super().__init__(vid_path, save_dir, start_frame=start_frame, fps=fps)
        self.padding = padding   # Save the padding, the video frame size would be padding*2 X padding*2
        self.fps = fps
        # Get parent video name:
        self.parent_video_name = os.path.basename(vid_path)
        # this can be filled with '.' as it is usually dates of videos, so we'll get rid of them:
        folder=''.join(self.parent_video_name.split('.')[0:-1])
        # and create a new folder in the save directory, named after the video file:
        self.folder_name = os.path.join(save_dir,folder)

        self.movie_format = movie_format
        self.counter = 0   # Will track the original video frame number
        self.movie_counter = 0  # Track the number of video segments
        self.fish_idx = 0  # Track the number of blobs/fish in a frame
        # Contour_dict, holds the coordinates and bounding boxes of the fish as keys , the centroids as value:
        self.contour_dict = {}
        # Movie_dict holds the coordinates and bounding boxes of the fish as keys,
        # and the video capture objects as values:
        self.movie_dict = {}
        self.med_laplacian = []  # mean laplacian value for each video segment
        self.movie_length = movie_length + 1  # Set the length of movies
        # Initiate the log dataframe:
        self.log = pd.DataFrame(columns=['movie_name','parent_video','frame', 'coordinates','comments', 'label'])
        # And now the widgets and GUI integrations:
        self.progressbar = progressbar  # tkinter progress bar widget
        self.trainlabel = trainlabel  # tkinter label widget
        self.videos_released = False   # monitors whether video resources were closed properly
          # will apply the change in brightness to the saved video segments

    def __repr__(self):
         return f'Brighten {self.brighten}; Blur {self.blur}; Minimum Width {self.min_width};' \
             f' Minimum Height {self.min_height}; Clip Length {self.movie_length-1}; Start Frame {self.start_frame};' \
             f' Apply Brightness {self.apply_brightness}'

    def get_bounds(self, centroid):
        """ Get the bounds of a new video segment. This is makes sure all video
        files have the same frame size.
        Practically, it means that the centroid + padding and the centroid - padding
        in every direction is within the original frame dimensions."""
        x1 = centroid[0] - self.padding  # Leftmost x point
        if x1 < 0:
            # If negative, switch for 0:
            x1 = 0
        x2 = centroid[0] + self.padding  # Rightmost x point
        if x2 > self.SHAPE[0]:
            # If overshoots original frame size, replace by the frame width:
            x2 = int(self.SHAPE[0])
        y1 = centroid[1] - self.padding  # Leftmost y point
        if y1 < 0:
            # If negative, replace by 0:
            y1 = 0
        y2 = int(centroid[1] + self.padding)  # Rightmost y point
        if y2 > self.SHAPE[1]:
            # If overshoots original frame size, replace by the frame height:
            y2 = int(self.SHAPE[1])
        return x1, x2, y1, y2  # Return the bounds for the video segments

    def initiate_movies(self):
        """ Find the fish in a frame and initiate video segments for each detection."""
        # First find the fish:
        self.get_filter()  # get foreground mask for the frame
        self.get_contours()  # find objects/fish inside the mask, get a dictionary of their detections
        self.fish_idx = 0  # Restart fish counting
        # Go over the detections dict from the frame, contains the contour(bounding box) and centroid (object center):
        for contour, centroid in self.bbox_dict.items():
            if contour in self.contour_dict.keys():
                entry = self.contour_dict[contour]
                self.close_segment(entry[3],contour)
            # If this contour doesn't have a movie already, get the bounds of the new video:
            x1, x2, y1, y2 = self.get_bounds(centroid)
            # Create a new entry for this fish - dimensions, frame counter,
            # empty list for Laplacian values (calculate blurriness):
            self.contour_dict[contour] = [(x1, x2), (y1, y2), 0, []]
            self.create_movie_dict(contour,centroid)  # Create the video segments capture files and update the log
            self.fish_idx += 1  # Count one more fish
            self.movie_counter += 1  # Count one more movie

    def create_movie_dict(self,contour,centroid):
        """ Create a new video for a fish. Create the name and full path for the movie and update
        the movie dictionary with a new video capture object. Update the log dataframe with the movie details."""
        # Create a file name for the video segment:
        new_name = self.MOVIE_PREFIX + 'frame' + str(self.counter) + 'fish' + \
                   str(self.fish_idx) + self.movie_format
        movie_path = self.folder_name + os.path.sep + new_name  # Create the full path for the video segment
        # Create a list with the VideoWriter object for the new fish and the video file path:
        self.movie_dict[contour] = [cv2.VideoWriter(movie_path, self.fourcc, self.fps,
                                                    (self.padding * 2, self.padding * 2), False), movie_path]
        # Create a new log entry:
        self.log.loc[self.movie_counter, :] = {'movie_name': new_name, 'parent_video': self.vid_path,
                                               'frame': self.counter, 'coordinates': centroid,
                                               'comments': '', 'label': None}

    def close_segment(self,laplacian,key):
        """Close a movie segment, release resources and check if it is too blurry."""
        self.med_laplacian.append(np.mean(laplacian))  # Add the mean Laplacian value for this video to the list
        self.contour_dict.pop(key)  # Take the contour/fish-bounds out of the dictionary
        tmp = self.movie_dict.pop(key)   # Take the video capture object out
        tmp[0].release()  # Release it
        # Filter out blurry videos:
        if self.med_laplacian[-1] < np.mean(self.med_laplacian) - 1.5:
            # if the mean laplacian is 1.5 point below the mean of all videos, remove it.
            # This is an experimental value that needs testing.
            # Remove the video file:
            os.remove(tmp[1])
            # Remove the log entry:
            self.log.drop(self.log[self.log.movie_name == os.path.basename(tmp[1])].index, inplace=True)

    def write_movies(self):
        """ Main loop for writing the video segments for the detected fish."""
        # For each detected fish:
        for key in list(self.contour_dict):
            entry = self.contour_dict[key]
            # Check if the length of the current video segment has reached the desired length:
            if entry[2] == self.movie_length:
                # Close the video segment to release resources:
                self.close_segment(entry[3], key)
                continue  # And move on to the next video
            # If it hasn't reached desired length, write movies:
            x, y, w, h = key  # Get the current fish bounding box dimensions
            # Convert to grayscale to optimize and calculate laplacian:
            gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
            # Get the object subframe and calculate laplacian on it:
            subframe = gray[y:(y + h), x:(x + w)]
            lap = cv2.Laplacian(subframe, cv2.CV_64F).var()
            # Cutout the video segment subframe:
            cutout = self.frame[entry[1][0]:entry[1][1], entry[0][0]:entry[0][1]]
            if self.apply_brightness:
                cutout = cv2.convertScaleAbs(cutout, alpha=1, beta=self.brighten)
            # Add the laplacian calculation to the dictionary entry
            entry[3].append(lap)
            # Deal with cases where the centroid is too close to the edges of the original frame,
            # this makes sure all videos will be the same size - (padding*2 X padding*2):
            output = np.zeros((self.padding * 2, self.padding * 2), dtype="uint8")  # create a frame the desired size
            output[0:cutout.shape[0], 0:cutout.shape[1]] = cutout  # Paste in our cutout from the original frame
            self.movie_dict[key][0].write(output)  # Write the frame to file
            entry[2] += 1  # Add a frame to the segment frame count

    def update_gui_lbl(self,msg):
        """ Update a LabelerGUI with a message to the user."""
        self.trainlabel.configure(text=msg)
        self.trainlabel.update()

    def create_saving_dir(self):
        """ Create a directory to save movie segments in, name it after video file name."""
        try:
            # Try creating a new folder for the segments:
            os.mkdir(self.folder_name)
        except FileExistsError:
            # If a folder name already exists, add a timestamp to the folder name:
            current_time = datetime.now().strftime("%H%M%S")
            self.folder_name = self.folder_name + current_time
            os.mkdir(self.folder_name)

    def pre_cutting(self):
        """ Does the logistics before starting to cut the videos, create directory for segments, train background
        subtractor, update GUI if applicable."""
        self.create_saving_dir()  # set up new directory
        # If there is GUI integration, update the progress bar:
        if self.progressbar:
            # set the maximal value for the progress bar:
            self.progressbar["maximum"] = self.num_frames - self.num_train_frames
        self.fps_timer = FPS().start()  # Start timing
        if self.trainlabel:
            # Update the GUI label to inform user of the stage of the processing:
            self.update_gui_lbl(self.BG_SUB_TRAIN_MSG)
        self.train_bg_subtractor()  # Train the background subtractor

    def cut(self):
        """ Main loop for cutting the original video file to segments."""
        # Do pre-cutting logistics:
        self.pre_cutting()
        # Set the gap between checks for fish, this is roughly 80% of the length of a video segment.
        # As an example, if video segments are to be a 100 frames in length, then check for fish every 80 frames:
        check_every = round(self.movie_length * 0.8)
        if self.trainlabel:
            # Update the GUI label to inform user of the stage of the processing:
            self.update_gui_lbl(self.CUTTING_MSG)
        # Now for the main cutting event:
        while True:
            grabbed, self.frame = self.cap.read()  # get frame from the main video
            if not grabbed:
                # if the video is finished, stop:
                break
            if self.counter % check_every == 0:
                # If we need to check for fish:
                self.initiate_movies()  # create the fish movie segments for this frame

            self.write_movies()  # Write a frame to the movie segments initiated

            if self.progressbar and self.counter % 10 == 0:
                # Update the progress bar in decimal increments:
                self.progressbar["value"] = self.counter
                self.progressbar.update()

            self.counter += 1  # Monitor the number of frames in the original vid
            self.fps_timer.update()   # update the fps timer
        # When done, release the remaining resources and save log:
        self.close_everything()

    def release_videos(self):
        """ Release all video files"""
        for movie in self.movie_dict.values():
            # Release all remaining segments
            movie[0].release()
        self.cap.release()  # Release the original video
        self.videos_released = True

    def close_everything(self):
        """ Release resources, save log and display end message."""
        self.release_videos()
        self.fps_timer.stop()  # Stop the fps_timer
        self.log.to_csv(os.path.join(self.folder_name,'log.csv'), index=False)  # Save the log dataframe to file
        f=open(os.path.join(self.folder_name,'cutter_profile.txt'),'w')
        f.write(self.__repr__())
        f.close()
        self.update_gui_lbl(self.END_MSG)  # Inform the user cutting is done
        # Print the timing results:
        print("[INFO] elasped time: {:.2f}".format(self.fps_timer.elapsed()))
        print("[INFO] approx. FPS: {:.2f}".format(self.fps_timer.fps()))

