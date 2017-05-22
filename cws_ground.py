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
    ]

S_RECSIZE = 8
MAX_WIDTH = 1000
MAX_HEIGHT =800
S_RECCOUNT = MAX_WIDTH*MAX_HEIGHT

class GroundBlock:
    def __init__(self, x, y, rx, ry):
        self.x = x
        self.y = y
        self.rx = rx
        self.ry = ry
        self.data=[]

    def clear(self):
        self.data=[]

    def append(self,data):
        self.data.append(data)

    def readxy(self,x,y):
        return self.data[self.idx(x,y)]
        
    def __calcWater(self,idx):
        """ Перераспределение воды """
        d = self.data[idx]
        deltaWater = min(d['WATER'],d['PWfree'])
        d['DX'] += deltaWater
        d['DX'] = min(255,d['DX'])
        d['WATER'] -= deltaWater
        d['WATER'] = min(255,d['WATER'])

    def __calc(self,idx):
        d = self.data[idx]
        """ Общий объем """
        d['Pa'] = d['AX']+d['BX']+d['CX']+d['DX']
        """ Объем суши """
        d['Pg'] = d['AX']+d['BX']+d['CX']
        """ Свободный объем впитывания """
        d['PWfree'] = d['Pg']/3 - d['DX']
        d['HEIGHT'] = d['Pg'] + d['WATER']

    def __calc2(self,idx,idx2):
        self.__calc(idx)
        self.__calc(idx2)
        d1 = self.data[idx]
        d2 = self.data[idx2]


        """ Распределение воды по высоте """
        if d1['HEIGHT'] > d2['HEIGHT'] and d1['WATER'] > 0:
            deltaHeight = (d1['HEIGHT'] - d2['HEIGHT'])/2
            deltaWater = min(d1['WATER'], deltaHeight)
            d1['WATER'] -= deltaWater/8
            d2['WATER'] += deltaWater/8

        """ Распределение воды по впитыванием """
        if d1['DX'] > d2['DX'] and d2['WATER'] == 0:
            deltaWater = d1['DX'] - (d1['DX'] + d2['DX'])/2
            d1['DX'] -= deltaWater/8
            d2['DX'] += deltaWater/8

    def xy(self,idx):
        y = idx//self.rx
        x = idx%self.rx
        return (x,y)

    def idx(self,x,y):
        return y*self.rx+x

    def around(self,idx):
        x,y = self.xy(idx)
        a=[]
        for i in range(x-1,x+2):
            for j in range(y-1,y+2):
                if i<0 or j<0 or i>=self.rx or j>=self.ry or (i==x and j==y):
                    continue
                a.append(self.idx(i,j))
        return a

    def calc(self):
        for idx in range(len(self.data)):
            a = self.around(idx)
            for j in a:
                self.__calc2(idx,j)
            self.__calcWater(idx)

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
                        'DX'    : 0,
                        'WIND'  : randint(0,255),
                        'WARM'  : randint(0,255),
                        'WATER' : randint(0,50),
                }
                #print "addRecord",j,rec
                #rec['DX']=(rec['AX']+rec['BX']+rec['CX'])/3
                self.__calcWater(rec)
                self.add(rec)

    def __render(self):
        self.__empty()

    def __calcWater(self, values):
        Water = values['WATER']
        DX = values['DX']
        """ Общий объем """
        Pa = values['AX']+values['BX']+values['CX']+values['DX']
        """ Объем суши """
        Pg = values['AX']+values['BX']+values['CX']
        """ Свободный объем впитывания """
        Pfree = Pg/3-DX
        """ Перераспределение воды """
        DeltaWater = min(Water,Pfree)
        DX += DeltaWater
        Water -= DeltaWater
        values['DX'] = min(255,DX)
        values['WATER'] = min(255,Water)

    def readblock(self,x,y,rx,ry):
        self.block=GroundBlock(x,y,rx,ry)
        for dy in range(ry):
            for dx in range(rx):
                self.readxy(x+dx,y+dy)
                self.block.append(self.hd_rec.values)

    def writeblock(self):
        for dy in range(self.block.ry):
            for dx in range(self.block.rx):
                values = self.block.readxy(dx,dy)
                self.writexy(self.block.x+dx,self.block.y+dy, values)

    def readxy(self,x,y):
        return self.readRecord(y*MAX_WIDTH+x)

    def writexy(self,x,y,values):
        return self.writeRecord(y*MAX_WIDTH+x,values)

    def image(self):
        img = Image.new('RGB', (MAX_WIDTH, MAX_HEIGHT), (0,0,0))
        for x in xrange(MAX_WIDTH):
            for y in xrange(MAX_HEIGHT):
                self.readxy(x,y)

                Height = self.hd_rec.values['AX']+self.hd_rec.values['BX']+self.hd_rec.values['CX']
                Water = self.hd_rec.values['WATER']
                Wdeep = 255-Water
                if Water == 0:
                    rgb = (Height/3/2,Height/3/2,0)
                else:
                    rgb = (0,0,Wdeep)
                img.putpixel((x,y),rgb)
        img.save("groundSlice.png")

    def image_block(self,name,w=1,h=1):
        #RGBA
        img = Image.new('RGB', (self.block.rx*w, self.block.ry*h), (0,0,0))
        draw = ImageDraw.Draw(img)
        for x in xrange(self.block.rx):
            for y in xrange(self.block.ry):
                d = self.block.readxy(x,y)

                Height = d['AX']+d['BX']+d['CX']
                Water = d['WATER']
                Wdeep = 255-Water
                if Water == 0:
                    rgb = (Height/3/2,Height/3/2,0)
                else:
                    rgb = (0,0,Wdeep)
                draw.rectangle([(x*w,y*h),(x*w+w,y*h+h)],fill=rgb)
        img.save("groundBlock_%s.png" % name)
