#!/usr/bin/python2
__author__ = 'ringo'
import struct
import os

import PIL
import PIL.Image


class Palette:
    colors = []

    def __init__(self, filename):
        pal_file = open(filename, 'rb')
        for i in range(os.stat(filename).st_size / 3):
            color = []
            _bytes_ = pal_file.read(3)
            color.append(struct.unpack('B', _bytes_[0])[0])
            color.append(struct.unpack('B', _bytes_[1])[0])
            color.append(struct.unpack('B', _bytes_[2])[0])
            if i == 0:
                color.append(0)
            else:
                color.append(255)
            self.colors.append(tuple(color))
        pal_file.close()


class PCK:
    images = []

    def __init__(self, pck_filename, tab_filename, colour_palette, index=-1):
        self.process_file(pck_filename, tab_filename, colour_palette, index)

    def process_file(self, pck_filename, tab_filename, colour_palette, index):
        pck = open(pck_filename, 'rb')
        tab = open(tab_filename, 'rb')
        version = struct.unpack('<H', pck.read(2))[0]
        pck.seek(0)
        if version == 0:
            self.load_version1_format(pck, tab, index, colour_palette)
        elif version == 1:
            self.load_version2_format(pck, tab, index, colour_palette)
        pck.close()
        tab.close()
        return

    def get_item_count(self):
        return len(self.images)

    def load_version1_format(self, pck, tab, index, colour_palette):
        """
        :param pck: file
        :param tab: file
        :param index: int
        :param colour_palette: file?
        :return:
        """

        # c0_offset: 16bit int
        palette = Palette(colour_palette)
        c0_image_data = []
        if index < 0:
            min_rec = 0
            max_rec = os.stat(tab.name).st_size / 4
        else:
            min_rec = index
            max_rec = index + 1
        for i in range(min_rec, max_rec):
            tab.seek(i * 4)
            offset = struct.unpack('<I', tab.read(4))[0]
            pck.seek(offset)
            c0_offset = struct.unpack('<H', pck.read(2))[0]

            c0_row_widths = []
            c0_max_width = 0
            c0_height = 0
            while c0_offset != 0xFFFF:
                c0_width = read_16_le(pck)
                c0_row_widths.append(c0_width)
                if c0_max_width < c0_width:
                    c0_max_width = c0_width
                c0_buffer_ptr = len(c0_image_data)
                list_fill(c0_image_data, c0_width + c0_offset % 640)
                read_file_to_list(pck, c0_image_data, c0_buffer_ptr + c0_offset % 640, c0_width)
                c0_height += 1
                c0_offset = read_16_le(pck)
            tmp_img = PIL.Image.new('RGBA', (c0_max_width, c0_height))
            # tmp_img.size()
            c0_idx = 0
            for c0_y in range(c0_height):
                for c0_x in range(c0_max_width):
                    if c0_x < c0_row_widths[c0_y]:
                        tmp_img.putpixel((c0_x, c0_y), palette.colors[c0_image_data[c0_idx]])
                    c0_idx += 1
            self.images.append(tmp_img)
        return

    def load_version2_format(self, pck, tab, index, colour_palette):
        palette = Palette(colour_palette)
        if index < 0:
            min_rec = 0
            max_rec = os.stat(tab.name).st_size / 4
        else:
            min_rec = index
            max_rec = index + 1
        for i in range(min_rec, max_rec):
            tab.seek(i * 4)
            offset = struct.unpack('<I', tab.read(4))[0] * 4
            pck.seek(offset)
            compression_method = read_16_le(pck)
            if compression_method == 1:
                image_header = C1ImageHeader(pck)
                img = PIL.Image.new('RGBA', (image_header.right_most_pixel, image_header.bottom_most_pixel))
                c1_pixels_to_skip = read_32_le(pck)
                while c1_pixels_to_skip != 0xFFFFFFFF:
                    compression_header = PCKCompressionHeader(pck)
                    c1_y = c1_pixels_to_skip / 640
                    if c1_y < image_header.bottom_most_pixel:
                        if compression_header.bytes_in_row != 0:
                            read_32_le(pck)
                            for c1_x in range(image_header.left_most_pixel, compression_header.bytes_in_row):
                                if c1_x > image_header.right_most_pixel:
                                    color_index = struct.unpack('B', pck.read(1))[0]
                                    img.putpixel((c1_x, c1_y), palette.colors[color_index])
                                else:
                                    pck.read(1)
                        else:
                            for c1_x in range(compression_header.pixels_in_row):
                                if compression_header.column_to_start_at + c1_x - image_header.left_most_pixel < \
                                        image_header.right_most_pixel - image_header.left_most_pixel:
                                    color_index = struct.unpack('B', pck.read(1))[0]
                                    img.putpixel((compression_header.column_to_start_at + c1_x, c1_y),
                                                 palette.colors[color_index])
                                else:
                                    pck.read(1)
                    c1_pixels_to_skip = read_32_le(pck)
                self.images.append(img)
            else:
                print("Unknown compression type: %s" % compression_method)
        return


class C1ImageHeader:
    reserved1 = None
    reserved2 = None
    left_most_pixel = None
    right_most_pixel = None
    top_most_pixel = None
    bottom_most_pixel = None

    def __init__(self, file_ptr):
        self.reserved1 = struct.unpack('B', file_ptr.read(1))[0]
        self.reserved2 = struct.unpack('B', file_ptr.read(1))[0]
        self.left_most_pixel = read_16_le(file_ptr)
        self.right_most_pixel = read_16_le(file_ptr)
        self.top_most_pixel = read_16_le(file_ptr)
        self.bottom_most_pixel = read_16_le(file_ptr)
        return


class PCKCompressionHeader:
    column_to_start_at = None
    pixels_in_row = None
    bytes_in_row = None
    padding_in_row = None

    def __init__(self, file_ptr):
        self.column_to_start_at = struct.unpack('B', file_ptr.read(1))[0]
        self.pixels_in_row = struct.unpack('B', file_ptr.read(1))[0]
        self.bytes_in_row = struct.unpack('B', file_ptr.read(1))[0]
        self.padding_in_row = struct.unpack('B', file_ptr.read(1))[0]


def read_16_le(file_ptr):
    """
    :param file_ptr: file object
    :return: 16 bit value (Little Endian)
    """
    return struct.unpack('<H', file_ptr.read(2))[0]


def read_32_le(file_ptr):
    """
    :param file_ptr: file object
    :return: 32 bit value (Little Endian)
    """
    return struct.unpack('<I', file_ptr.read(4))[0]


def list_fill(lst, size):
    for i in range(len(lst), len(lst) + size):
        lst.append(0)


def read_file_to_list(file_ptr, lst, start, length):
    for i in range(start, start + length):
        try:
            _byte_ = file_ptr.read(1)
            lst[i] = struct.unpack('B', _byte_)[0]
        except KeyError as e:
            print(e)
        except Exception as e:
            print(e)