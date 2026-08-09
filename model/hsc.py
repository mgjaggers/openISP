#!/usr/bin/python
import numpy as np

class HSC:
    'Hue Saturation Control'

    def __init__(self, img, hue, saturation, clip):
        self.img = img
        self.hue = hue
        self.saturation = saturation
        self.clip = clip

    def clipping(self):
        np.clip(self.img, 0, self.clip, out=self.img)
        return self.img

    def lut(self):
        ind = np.array([i for i in range(360)])
        sin = np.sin(ind * np.pi / 180) * 256
        cos = np.cos(ind * np.pi / 180) * 256
        lut_sin = dict(zip(ind, [round(sin[i]) for i in ind]))
        lut_cos = dict(zip(ind, [round(cos[i]) for i in ind]))
        return lut_sin, lut_cos

    def execute(self):
        lut_sin, lut_cos = self.lut()
        img_h = self.img.shape[0]
        img_w = self.img.shape[1]
        img_c = self.img.shape[2]
        if img_c != 2:
            raise ValueError('Hue/saturation control expects two chroma channels')
        # Work in a signed, wide type.  Saturation must be applied to the hue-
        # rotated values; the old code overwrote the rotation with the original
        # chroma planes (checklist item 114).
        chroma0 = self.img[:,:,0].astype(np.float64) - 128.0
        chroma1 = self.img[:,:,1].astype(np.float64) - 128.0
        rotated0 = (chroma0 * lut_cos[self.hue] + chroma1 * lut_sin[self.hue]) / 256.0
        rotated1 = (chroma1 * lut_cos[self.hue] - chroma0 * lut_sin[self.hue]) / 256.0
        hsc_img = np.empty((img_h, img_w, img_c), np.float64)
        hsc_img[:,:,0] = self.saturation * rotated0 / 256.0 + 128.0
        hsc_img[:,:,1] = self.saturation * rotated1 / 256.0 + 128.0
        self.img = hsc_img
        return self.clipping()
