#!/usr/bin/python
# -*- coding: utf-8 -*-
from storage import SimStorage
from time import time
from os import path,stat
from random import randint
from PIL import Image, ImageDraw


S_VARS = [
    ['iter','L'],
    ['tm_unix','L'],
    ['max_height','I'],
    ['max_width','I'],
    ['tm_year','I'],
    ['tm_month','H'],
    ['tm_day','B'],
    ['freewater','f'],
    ['rain','f'],
    ['wind','f'],
    ['warm','f'],
]

S_RECORD = [
        ['AX','B'],
        ['BX','B'],
        ['CX','B'],
        ['DX','B'],
        ['WIND','B'],
        ['WARM','B'],
        ['WATER','B'],
        ['HEIGHT','B'],
    ]

S_RECSIZE = 8
MAX_WIDTH = 1000
MAX_HEIGHT =800
S_RECCOUNT = MAX_WIDTH*MAX_HEIGHT

class GroundSlice(SimStorage):
    def Create(self):
        if not self.exist():
            r = self.create(1,S_RECSIZE,S_RECCOUNT,4,32)
            if not r:
                sys.exit(0)
                print "not create!"
            self.open()
            self.rwstruct_vars(S_VARS)
            self.rwstruct_rec(S_RECORD)
            self.__render()
            self.close()

    def setDefault(self):
        values = {
         'iter'     :0,
         'tm_unix'  :int(time()),
         'max_height'   : 80,
         'max_width'    : 100,
         'tm_year'      : 1,
         'tm_month'     : 1,
         'tm_day'       : 1,
         'freewater'    : 8000,
         'rain'         : 0.1,
         'wind'         : 0.1,
         'warm'         : 0.5,
        }
        self.write_vars_vals(values)

    def __empty(self):
            for j in xrange(S_RECCOUNT):
                rec = { 'AX'    : randint(0,255),
                        'BX'    : randint(0,255),
                        'CX'    : randint(0,255),
                        'DX'    : randint(0,255),
                        'WIND'  : randint(0,255),
                        'WARM'  : randint(0,255),
                        'WATER' : randint(0,255),
                        'HEIGHT': randint(0,255),
                }
                #print "addRecord",j,rec
                self.add(rec)

    def __render(self):
        self.__empty()

    def readxy(self,x,y):
        return self.readRecord(y*MAX_WIDTH+x)

    def image(self):
        img = Image.new('RGB', (MAX_WIDTH, MAX_HEIGHT), (0,0,0))
        #draw = ImageDraw.Draw(img)
        for x in xrange(MAX_WIDTH):
            for y in xrange(MAX_HEIGHT):
                self.readxy(x,y)
                if self.hd_rec.values['HEIGHT'] >= self.hd_rec.values['WATER']:
                    rgb = (self.hd_rec.values['WARM']/2,self.hd_rec.values['HEIGHT']/2,0)
                else:
                    rgb = (0,0,255-self.hd_rec.values['WATER'])

                img.putpixel((x,y),rgb)
        img.save("groundSlice.png")


        
        
        




