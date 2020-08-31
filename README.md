# fish_larvae_feeding
An evidence-based agriculture project to detect feeding events in fish larvae using computer vision and deep learning.

## Phase A - Sample Collection
I've developed a set of tools to help create a database with tagged samples of fish larvae activity.
These tools use simple image processing to detect fish in a video and create smaller video segments with individual fish.

### MovieCutter.py
A script to process full length videos and cut them into short video segments of (ideally) a single fish.
Outputs a folder of video segments and a corresponding log file.
The processing is done for the most part with the OpenCV package.

### MovieCutterGUI.py
A Graphic User Interface (GUI) developed with tkinter. It enables users to choose video files, saving directory, and
cut the file using the MovieCutter class, while monitoring the progress of the cutting process.

### LabelerGUI.py
Another tkinter GUI, used to label the video segments created by the MovieCutter. The user selects a directory of video segments;
These are then loaded into the GUI; The user can then play them, navigate between videos and apply labels
according to the activity of the fish in the frame: Feeding, Not Feeding, Other and more. 
The GUI will save the video labels to the log file and delete unnecessary video files.

### Dependencies:
The code was developed in python 3.8 and assumes the existence of the following libraries:
* OpenCV 
* tkinter
* PIL
* Pandas
* Numpy
* imutils

### Next steps
After creating a database, training a CNN image classifier to detect the fish activity.


