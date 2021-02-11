import struct
import numpy as np
from datetime import datetime
import cv2


class SEQReader:
    INITIAL_BYTES_TO_DISCARD = 548

    def __init__(self, filedir, endiantype='<'):
        self.filedir = filedir
        self.endiantype = endiantype
        self.file_handle = open(filedir, "rb")
        self.read_header()
        self.frame_pointer = -1
        self.image_buffers = np.array([],dtype='uint32')
        self.buff_sums = np.zeros(self.properties['AllocatedFrames'],dtype='int64')

    def read_header(self):
        properties = {}
        dat = []
        self.file_handle.seek(self.INITIAL_BYTES_TO_DISCARD)
        for i in range(24):
            dat.append(struct.unpack('<I', self.file_handle.read(4))[0])
        properties['ImageWidth'] = dat[0]
        properties['ImageHeight'] = dat[1]
        properties['ImageBitDepth'] = dat[2]
        properties['ImageBitDepthReal'] = dat[3]
        properties['ImageSizeBytes'] = dat[4]
        # get image format:
        fmts = {0: 'Unknown', 100: 'Monochrome', 101: 'Raw Bayer', 200: 'BGR',
                300: 'Planar', 400: 'RGB', 500: 'BGRx', 600: 'YUV422', 610: 'YUV422_20',
                620: 'YUV422_PACKED', 700: 'UVY422', 800: 'UVY411', 900: 'UVY444'}
        properties['ImageFormat'] = fmts[dat[5]]
        self.file_handle.seek(572)
        properties['AllocatedFrames'] = struct.unpack(self.endiantype+'I', self.file_handle.read(4))[0]
        self.file_handle.seek(620)
        properties['Compression'] = struct.unpack(self.endiantype+'I', self.file_handle.read(4))[0]
        self.file_handle.seek(28)
        properties['HeaderVersion'] = struct.unpack(self.endiantype+'l', self.file_handle.read(4))[0]
        self.file_handle.seek(32)
        properties['HeaderSize'] = struct.unpack(self.endiantype+'l', self.file_handle.read(4))[0]
        self.file_handle.seek(592)
        DescriptionFormat = struct.unpack(self.endiantype+'l', self.file_handle.read(4))[0]
        self.file_handle.seek(36)
        Description = []
        for i in range(512):
            Description.append(struct.unpack(self.endiantype+'H', self.file_handle.read(2))[0])
        if DescriptionFormat == 0:  # ok Unicode
            Description = ''.join([chr(t) for t in Description])
        elif DescriptionFormat == 1:  # ok ASCII
            Description = ''.join([chr(t) for t in Description])
        properties['Description'] = Description
        self.file_handle.seek(580)
        properties['TrueImageSize'] = struct.unpack(self.endiantype+'L', self.file_handle.read(4))[0]
        self.file_handle.seek(584)
        properties['FrameRate'] = struct.unpack(self.endiantype+'d', self.file_handle.read(8))[0]
        assert (properties[
                    'ImageFormat'] == 'Monochrome'), f'Image format is not monochrome but {properties["ImageFormat"]}.'
        assert (properties['Compression'] == 1), 'Only compressed SEQs are supported'
        self.properties = properties

    def get_imagebuffers(self, idx):
        read_so_far = len(self.image_buffers)
        # new images to read until reaching desired index:
        buffs = np.zeros(idx - read_so_far + 1, dtype='int64')

        for i in range(len(buffs)):
            # The header size, plus of the buffers we've traversed so far
            # plus 8 bytes coding the timestamp and buffer size per image
            # will give us the location of the current image buffer bytes:
            id_sum = len(self.image_buffers) + i
            pointer = self.properties['HeaderSize'] + self.buff_sums[max(0, id_sum - 1)] + 8 * read_so_far
            read_so_far += 1
            self.file_handle.seek(pointer)
            # unpack the image buffer size and store in the relevant index:
            buffs[i] = struct.unpack('<I', self.file_handle.read(4))[0]
            self.buff_sums[id_sum] = self.buff_sums[max(0, id_sum - 1)] + buffs[i]
        self.image_buffers = np.concatenate([self.image_buffers, buffs])

    def readTimestamp(self):
        imageTimestamp = struct.unpack('<i', self.file_handle.read(4))[0]
        subSec = np.frombuffer(self.file_handle.read(4), dtype='int16')
        add_zeros = lambda s: ('00' + str(s))[-3:]
        subSec = np.array(list(map(add_zeros, subSec)))
        timestampDateNum = datetime.fromtimestamp(imageTimestamp)
        time = f'{timestampDateNum.strftime("%m/%d/%Y, %H:%M:%S")}:{subSec[0]}{subSec[1]}'
        return time

    def __getitem__(self, idx):
        if idx < 0:
            idx = self.properties['AllocatedFrames'] + idx
        if len(self.image_buffers) < idx + 1:
            self.get_imagebuffers(idx)
        buff = self.image_buffers[idx]  # get wanted image buffer size
        # set frame pointer:
        readStart = self.properties['HeaderSize'] + self.buff_sums[idx-1]+8*idx#self.image_buffers[:idx].sum(dtype='int64')+8*idx
        # read compressed image:
        readStart = readStart + 4  # jump past the bytes encoding the image buffer size
        self.file_handle.seek(readStart)
        SEQ = np.frombuffer(self.file_handle.read(buff), dtype='uint8')  # get the compressed jpg data
        # read timestamp:
        readStart = readStart + buff - 4
        self.file_handle.seek(readStart)
        timestamp = self.readTimestamp()

        # decode jpeg:
        # frame = decode_jpeg(SEQ,colorspace='GRAY')
        frame = cv2.imdecode(SEQ, cv2.IMREAD_GRAYSCALE)
        self.frame_pointer = idx
        return {'frame': frame, 'timestamp': timestamp}

    def read(self):
        if self.frame_pointer < self.properties['AllocatedFrames'] - 1:
            frame = self.__getitem__(self.frame_pointer + 1)['frame']
            ret = True
        else:
            frame = None
            ret = False
        return ret, frame

    def __len__(self):
        return self.properties['AllocatedFrames']

    def release(self):
        self.file_handle.close()