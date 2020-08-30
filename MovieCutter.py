from imutils.video import FPS
import os
import cv2
import numpy as np
import pandas as pd
from imutils.video import count_frames


class MovieProcessor:
    """Process videos to detect fish larvae using classic image processing with OpenCV."""
    def __init__(self,vid_path, save_dir, brighten=True, blur=False,
                 min_width=70, min_height=70, num_train_frame=500, fps=30):
        """Initiate a processor object. inputs:
        vid_path - location of the video to process
        save_dir - location to save the processed video
        brighten - optional, brighten the image as part of the processing flow
        blur - optional, blur the image as part of the processing flow
        min_width - minimum width of a single blob, helps filter small non-fish objects
        min_height - minimum height of a single blob, helps filter small non-fish objects
        num_train_frame - number of frames used to train the background subtractor
        fps - define the rate of frames per second for the processed video output"""
        self.vid_path = vid_path
        self.folder_path = save_dir
        self.min_width = min_width  # minimal blob width
        self.min_height = min_height  # minimal blob height
        self.brighten = brighten
        self.blur = blur
        self.num_train_frames = num_train_frame
        self.fps = 30
        # Create a video capture object:
        self.cap = cv2.VideoCapture(vid_path)
        # Get the frame dimensions:
        self.SHAPE = [self.cap.get(cv2.CAP_PROP_FRAME_WIDTH), self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)]
        # Create background subtractor object:
        self.bg_sub = cv2.createBackgroundSubtractorMOG2(history=num_train_frame, detectShadows=True)
        # Name the output video:
        self.output_vid = vid_path[0:-4]+'_proccesed.avi'
        # The bbox_dict will house the coordinates and dimensions of the bounding boxes around the detected objects,
        # as well as the centroids of these bounding boxes:
        self.bbox_dict = {}
        self.frame = None # video frame, initialize at nobe
        # codec for video writing, see https://www.pyimagesearch.com/2016/02/22/writing-to-video-with-opencv/:
        self.fourcc = cv2.VideoWriter_fourcc(*"MJPG")


    @staticmethod
    def get_centroid(x, y, w, h):
        """ Get the centroid of the bouding box defined by x, y, w and h"""
        cx = x + int(w / 2)
        cy = y + int(h / 2)
        return cx, cy

    def get_contours(self):
        """ Get the blobs/contours/fish detected in the image.
        Each blob gets an entry in the bbox_dict - the key is the bounding box coordinates and dimensions,
        the value is the centroid of that bounding box.
        """

        # find all contours/blobs in the frame:
        self.bbox_dict={}
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
        self.processed_frame = self.frame  # begin depicting the processing by using the base frame
        for bbox, centroid in self.bbox_dict.items():
            # for each blob detected
            x, y, w, h = bbox
            # cut only the blob out of the grayscale and calculate the Laplacian as a measure of image blurriness:
            subframe = gray[y:y + h, x:x + w]
            lap = cv2.Laplacian(subframe, cv2.CV_64F).var()
            # Draw the bounding box and centroid on the processed frame:
            cv2.rectangle(self.processed_frame, (x, y), (x + w - 1, y + h - 1),
                          BOUNDING_BOX_COLOUR, 4)
            cv2.circle(self.processed_frame, centroid, 2, CENTROID_COLOUR, -1)
            # Write the laplacian value next to the detected object:
            cv2.putText(self.processed_frame, f'{lap:.2f}', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)



    def get_filter(self):
        """ Get the foreground mask for a frame
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
        gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)  # Turn to grayscale
        denoise = cv2.GaussianBlur(gray, (71, 71), 0)
        if self.blur:
            # Apply gaussian blur to image
            gray = denoise
        if self.brighten:
            # Apply brightness adjustment to image
            gray = cv2.convertScaleAbs(gray, alpha=1, beta=50)
        self.fg_mask = self.bg_sub.apply(gray, None, 0.001)  # calculate foreground mask
        img = cv2.Canny(denoise, 10, 10)  # get edges from the blurred image to filter out small floating particles
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (10, 10))
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
            if self.brighten:
                # modify brightness if applicable:
                gray = cv2.convertScaleAbs(gray, alpha=1, beta=50)
            if self.blur:
                # apply gaussian blur if applicable:
                gray = cv2.GaussianBlur(gray, (71, 71), 0)
            self.fg_mask = self.bg_sub.apply(gray, None, 0.001)  # apply bg_sub to the frame (modified or not)

    def process_vid(self):
        """ Detect objects in a single video and create a new video with the bounding boxes around objects.
        input:
        vid_name - path and filename of the input video
        output_vid - path and filename for the generated video
        brighten - bool, whether to adjust brightness in the image
        blur - bool, whether to apply gaussian blur to remove background noise from the image
        """
        self.vid_writer = cv2.VideoWriter(self.output_vid, self.fourcc, 30,
                                          (self.SHAPE[1], self.SHAPE[0]), True)
        self.train_bg_subtractor()  # pre-training
        # iterate over the remaining frames:
        counter=0
        while True:
            grabbed, self.frame = self.cap.read()  # get frame
            if not grabbed:
                # If the video is finished, stop the loop
                break
            counter += 1
            self.get_filter()  # get foreground mask
            self.get_contours()  # find objects inside the mask, get a list of their bounding boxes
            self.draw_boxes()  # draw bounding boxes on original frame
            self.processed_frame = cv2.cvtColor(self.processed_frame, cv2.COLOR_BGR2RGB)  # optional: open-cv work in BGR so convert back to RGB
            self.vid_writer.write(self.processed_frame)  # Write frame to the new video file
            # fps.update()
        # release resources:
        self.vid_writer.release()
        self.cap.release()


class MovieCutter(MovieProcessor):
    def __init__(self, vid_path, save_dir, padding=250, fps=30, movie_format='.avi',
                 movie_length=100,progressbar=[], trainlabel=[]):
        super().__init__(vid_path,save_dir)
        self.padding = padding
        self.fps = fps
        folder = os.path.basename(vid_path).split('.')[0]
        self.folder_name = os.path.join(save_dir,folder)
        self.movie_format = movie_format
        self.counter = 0
        self.movie_counter = 0
        self.idx = 0
        self.contour_dict = {}
        self.movie_dict = {}
        self.movie_name = 'cutout_'
        self.med_laplacian = []
        self.movie_length = movie_length + 1
        self.log = pd.DataFrame(columns=['movie_name', 'frame', 'coordinates', 'label'])
        self.progressbar = progressbar
        self.trainlabel = trainlabel

    def in_bounds(self, centroid):
        x1 = centroid[1] - self.padding
        if x1 < 0:
            x1 = 0
        x2 = centroid[1] + self.padding
        if x2 > self.SHAPE[0]:
            x2 = self.SHAPE[0]
        y1 = centroid[0] - self.padding
        if y1 < 0:
            y1 = 0
        y2 = centroid[0] + self.padding
        if y2 > self.SHAPE[1]:
            y2 = self.SHAPE[1]
        return x1, x2, y1, y2

    def find_fish(self):
        for contour, centroid in self.bbox_dict.items():
            if contour not in self.contour_dict.keys():
                x1, x2, y1, y2 = self.in_bounds(centroid)
            self.contour_dict[contour] = [(x1, x2), (y1, y2), 0, []]
            new_name = self.movie_name + 'frame' + str(self.counter) + 'fish' + str(
                self.movie_counter) + self.movie_format
            movie_path = self.folder_name + os.path.sep + new_name
            self.movie_dict[contour] = [cv2.VideoWriter(movie_path, self.fourcc,
                                                        self.fps, (self.padding * 2, self.padding * 2), False),
                                        movie_path]
            self.log.loc[self.idx, :] = {'movie_name': new_name, 'frame': self.counter, 'coordinates': centroid,
                                         'label': None}
            self.idx += 1
            self.movie_counter += 1

    def write_movies(self):
        for key in list(self.contour_dict):
            entry = self.contour_dict[key]
            if entry[2] == self.movie_length:
                self.med_laplacian.append(np.mean(entry[3]))

                self.contour_dict.pop(key)
                tmp = self.movie_dict.pop(key)
                tmp[0].release()
                if self.med_laplacian[-1] < 4:
                    os.remove(tmp[1])
                    self.log.drop(self.log[self.log.movie_name == tmp[1]].index, inplace=True)
                continue
            cutout = []
            x, y, w, h = key
            subframe = self.frame[y:y + h, x:x + w]
            subframe = cv2.cvtColor(subframe, cv2.COLOR_BGR2GRAY)
            lap = cv2.Laplacian(subframe, cv2.CV_64F).var()
            cutout = self.frame[entry[0][0]:entry[0][1], entry[1][0]:entry[1][1]]
            cutout = cv2.cvtColor(cutout, cv2.COLOR_BGR2GRAY)
            # lap=cv2.Laplacian(cutout, cv2.CV_64F).var()
            entry[3].append(lap)
            output = np.zeros((self.padding * 2, self.padding * 2), dtype="uint8")
            output[0:cutout.shape[0], 0:cutout.shape[1]] = cutout
            self.movie_dict[key][0].write(output)
            entry[2] += 1

    def cut(self):
        try:
            os.mkdir(self.folder_name)
        except FileExistsError:
            self.folder_name = self.folder_name + '2'
            os.mkdir(self.folder_name)
        self.trainlabel.configure(text='counting frames...')
        self.trainlabel.update()
        self.num_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if self.num_train_frames > self.num_frames:
            self.num_train_frames=round(self.num_frames/4)
        if self.progressbar:
            self.progressbar["maximum"] = self.num_frames - self.num_train_frames
        fps = FPS().start()
        self.trainlabel.configure(text='training background subtractor...')
        self.trainlabel.update()
        self.train_bg_subtractor()
        self.trainlabel.configure(text='begin cutting:')
        self.trainlabel.update()
        while True:
            grabbed, self.frame = self.cap.read()  # get frame
            if not grabbed:
                break
            if self.counter % 80 == 0:
                self.get_filter()  # get foreground mask
                self.get_contours()  # find objects inside the mask, get a list of their bounding boxes
                self.find_fish()
            self.write_movies()
            if self.progressbar and self.counter%10 == 0:
                self.progressbar["value"]=self.counter
                self.progressbar.update()
            self.counter += 1
            fps.update()
        for movie in self.movie_dict.values():
            movie[0].release()
        self.cap.release()
        fps.stop()
        self.log.to_csv(self.folder_name + os.path.sep + 'log.csv', index=False)
        self.trainlabel.configure(text='Done!')
        self.trainlabel.update()

        print("[INFO] elasped time: {:.2f}".format(fps.elapsed()))
        print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))




