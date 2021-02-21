from keras.models import load_model
from keras.utils import np_utils
from keras import metrics
import numpy as np
import pandas as pd
import os
import sys
import cairocffi as cairo
import random


class QDRecognizer:

    @staticmethod
    def top_3_acc(y_true, y_pred):
        return metrics.top_k_categorical_accuracy(y_true, y_pred, k=3)

    @staticmethod
    def prepare_model(model_path, labels_path):
        QDRecognizer.labels = pd.read_csv(
            labels_path, index_col=0, header=None, squeeze=True).to_dict()
        QDRecognizer.model = load_model(model_path, custom_objects={
                                        "top_3_acc": QDRecognizer.top_3_acc})

    def __init__(self):
        self.img_height = 28
        self.img_width = 28
        self.img_size = self.img_height * self.img_width
        self.img_dim = 1
        self.num_classes = 1
        self.drawing = []

    def add_stroke(self, stroke):
        self.drawing.append(stroke)

    def undo_stroke(self):
        self.drawing = self.drawing[:-1]

    def clear_drawing(self):
        self.drawing = []

    # strokes are encoded as list of (x,y),(x,y) instead     [x,x,x],[y,y,y] so it has to be converted
    # because vector_to_raster works on [x,x,x][y,y,y]
    def convert_strokes_encoding(self, strokes):
        new_strokes = []
        for coordinates in strokes:
            x = []
            y = []
            new_stroke = []
            for coordinate in coordinates:
                x.append(coordinate[0])
                y.append(coordinate[1])
            new_stroke.append(x)
            new_stroke.append(y)
            new_strokes.append(new_stroke)
        return new_strokes

    # model analyses rastered image, not vector of colored pixel coordinates so conversion is needed
    # works the best with orginal_side = 256
    def vector_to_raster(self, vector_images, side=28, line_diameter=16, padding=16, bg_color=(0, 0, 0), fg_color=(1, 1, 1)):
        """
        padding and line_diameter are relative to the original 256x256 image.
        """

        original_side = 256.

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, side, side)
        ctx = cairo.Context(surface)
        ctx.set_antialias(cairo.ANTIALIAS_BEST)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_width(line_diameter)

        # scale to match the new size
        # add padding at the edges for the line_diameter
        # and add additional padding to account for antialiasing
        total_padding = padding * 2. + line_diameter
        new_scale = float(side) / float(original_side + total_padding)
        ctx.scale(new_scale, new_scale)
        ctx.translate(total_padding / 2., total_padding / 2.)

        raster_images = []
        for vector_image in vector_images:
            # clear background
            ctx.set_source_rgb(*bg_color)
            ctx.paint()

            bbox = np.hstack(vector_image).max(axis=1)
            offset = ((original_side, original_side) - bbox) / 2.
            offset = offset.reshape(-1, 1)
            centered = [stroke + offset for stroke in vector_image]

            # draw strokes, this is the most cpu-intensive part
            ctx.set_source_rgb(*fg_color)
            for xv, yv in centered:
                ctx.move_to(xv[0], yv[0])
                for x, y in zip(xv, yv):
                    ctx.line_to(x, y)
                ctx.stroke()

            data = surface.get_data()
            raster_image = np.copy(np.asarray(data)[::4])
            raster_images.append(raster_image)

        return raster_images

    # bitmap has to be prepared for model before prediction
    def prepare(self, bitmaps):
        bitmaps = np.array(bitmaps)
        bitmaps = bitmaps.astype('float16') / 255.
        bitmaps_to_analyse = np.empty(
            [self.num_classes, len(bitmaps), self.img_size])
        bitmaps_to_analyse[0] = bitmaps
        bitmaps_to_analyse = bitmaps_to_analyse.reshape(
            bitmaps_to_analyse.shape[0] * bitmaps_to_analyse.shape[1], self.img_size)
        bitmaps_to_analyse = bitmaps_to_analyse.reshape(
            bitmaps_to_analyse.shape[0], self.img_width, self.img_height, self.img_dim)
        return bitmaps_to_analyse

    def hurry_up(self):
        hurry_up_texts = ["Come on!", "I'm bored...",
                          "You're drawing it ages", "how much longer????",
                          "I'could draw it faster despite i'm a bot..", "noob",
                          "nooooooooooooob", "n00b", "i'm gonna quit if he won't draw anything in a moment...",
                          "Am I supposed to do this for you ...?", "hurry up!", "¯\_(ツ)_/¯"]
        return random.choice(hurry_up_texts)

    def guess(self):

        try:
            if not self.drawing:
                answer = self.hurry_up()
            else:
                properly_encoded_drawing = self.convert_strokes_encoding(
                    self.drawing)
                drawings = []
                drawings.append(properly_encoded_drawing)
                rastered_drawings = self.vector_to_raster(drawings)
                prepared_drawings = self.prepare(rastered_drawings)
                predictions = QDRecognizer.model.predict(prepared_drawings)
                answer = QDRecognizer.labels[predictions[0].argmax()]
        except:
            answer = "I have no idea ¯\_(ツ)_/¯"

        return answer
