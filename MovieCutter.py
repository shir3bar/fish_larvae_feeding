from imutils.video import FPS
import os
import cv2
import numpy as np
import pandas as pd
from imutils.video import count_frames


class MovieProcessor():
    def __init__(self,vid_path, save_dir, brighten = True, blur = False, min_width = 70, min_height = 70,num_train_frame=500):
        self.vid_path = vid_path
        self.folder_path=save_dir #os.path.sep.join(vid_path.split(os.path.sep)[0:-1])
        self.centroid_list = []
        self.min_width = min_width
        self.min_height = min_height
        self.SHAPE = [1080,1920]
        self.cap=cv2.VideoCapture(vid_path)
        self.num_frames=count_frames(self.vid_path)
        self.bg_sub=cv2.createBackgroundSubtractorMOG2(history=num_train_frame, detectShadows=True)
        self.brighten = brighten
        self.blur = blur
        if num_train_frame > self.num_frames:
            num_train_frame=round(self.num_frames/4)
        self.num_train_frames=num_train_frame
        self.output_vid=vid_path[0:-4]+'_proccesed.avi'
        self.bbox_dict={}
        self.frame = None
        # codec for video writing, see: https://www.pyimagesearch.com/2016/02/22/writing-to-video-with-opencv/:
        self.fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        # the video writer is defined by output filename, selected codec, the fps selected is the same as the input video,
        # frame size that is also identical to input video, and a boolean specific whether to save a color video:




    @staticmethod
    def get_centroid(x, y, w, h):
        """ Get bounding box centroid"""
        x1 = int(w / 2)
        y1 = int(h / 2)

        cx = x + x1
        cy = y + y1

        return (cx, cy)


    def get_contours(self):
        """ Get the blobs or contours detected in the image
        input:
        image - a frame
        min_width - the minimal width of a blob, all blobs below threshold will be disregarded
        min_height - the minimal width of a blob, all blobs below threshold will be disregarded
        returns:
        matches - a list of tuples, each tuple contains two tuples with information about each detected blob.
            first tuple is the bounding box coordinates, width and height
            second tuple contains the centroid coordinates
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
                continue
                # Get bbox centroid:
            centroid = self.get_centroid(x, y, w, h)
            self.bbox_dict[(x, y, w, h)]=centroid

    def draw_boxes(self):
        """ Draw bounding boxes around objects in image
        """
        BOUNDING_BOX_COLOUR = (255, 10, 0)  # BGR
        CENTROID_COLOUR = (255, 192, 0)  # BGR
        gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        self.processed_frame=self.frame
        for contour, centroid in self.bbox_dict.items():
            x, y, w, h = contour
            subframe = gray[y:y + h, x:x + w]
            lap = cv2.Laplacian(subframe, cv2.CV_64F).var()
            cv2.rectangle(self.processed_frame, (x, y), (x + w - 1, y + h - 1),
                          BOUNDING_BOX_COLOUR, 4)
            cv2.circle(self.processed_frame, centroid, 2, CENTROID_COLOUR, -1)
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
                break
            counter+=1
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
    def __init__(self, vid_path, save_dir, padding=250, fps=30, movie_format='.avi', movie_length=100,progressbar=[]):
        super().__init__(vid_path,save_dir)
        self.vid_path = vid_path
        #os.chdir(self.folder_path)
        self.padding = padding
        self.fps = fps
        print(''.join(vid_path.split(os.path.sep)[-1].split('.')[0:-1]))
        self.folder_name = save_dir+''.join(vid_path.split(os.path.sep)[-1].split('.')[0:-1])
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
        self.progressbar=progressbar
        self.progressbar["maximum"]=self.num_frames-self.num_train_frames
        self.progressbar["value"]=0

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
        fps = FPS().start()
        self.train_bg_subtractor()
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
        print("[INFO] elasped time: {:.2f}".format(fps.elapsed()))
        print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))




