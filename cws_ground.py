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
MAX_WIDTH = 200
MAX_HEIGHT = 200
S_RECCOUNT = MAX_WIDTH*MAX_HEIGHT

SPEED_ITER=1
SPEED_DX=2
SPEED_GD=4
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

        #if idx==810:
        #    print self.xy(idx)
        #    print d1
        #    print d2
        #    print '-'*20
                

        """ Распределение воды по высоте """
        if d1['HEIGHT'] > d2['HEIGHT'] and d1['WATER'] > 0:
            deltaHeight = (d1['HEIGHT'] - d2['HEIGHT'])/2
            deltaWater = min(d1['WATER'], deltaHeight)
            d1['WATER'] -= deltaWater/SPEED_ITER
            d2['WATER'] += deltaWater/SPEED_ITER

        """ Распределение воды впитыванием """
        if d1['DX'] > d2['DX']:
            deltaWater = d1['DX'] - (d1['DX'] + d2['DX'])/2
            delta = max(deltaWater,1)
            speedWater = max(d1['DX']/delta,1)
            d1['DX'] -= deltaWater/SPEED_ITER/SPEED_DX/speedWater
            d2['DX'] += deltaWater/SPEED_ITER/SPEED_DX/speedWater

        """ Распределение суши осыпанием """
        if d1['WATER'] >0 and d1['Pg'] < d2['Pg']:
            deltaGround = d2['Pg'] - (d1['Pg'] + d2['Pg'])/2
            delta = max(deltaGround,1)
            speedGround = max(255/delta,1)
            v = deltaGround/SPEED_ITER/speedGround
            for xx in ('CX','BX','AX'):
                d = min(d2[xx], v)
                d = min(d,255-d1[xx])
                v = v - d
                d1[xx] += d
                d2[xx] -= d

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
    
    def addWater(self,val):
        for idx in range(len(self.data)):
            d1 = self.data[idx]
            if d1['WATER']>0:
                d1['WATER']+=val
            d1['WATER'] = min(255,d1['WATER'])

    def decWater(self,val):
        for idx in range(len(self.data)):
            d1 = self.data[idx]
            delta = min(val,d1['WATER'])
            d1['WATER'] -= delta
            delta = val - delta
            if delta>0:
                delta = min(delta,d1['DX'])
                d1['DX'] -= delta

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
         'max_height'   : 200,
         'max_width'    : 200,
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
                        'DX'    : 30,
                        'WIND'  : randint(0,255),
                        'WARM'  : randint(0,255),
                        'WATER' : randint(0,130),
                }
                #print "addRecord",j,rec
                #rec['DX']=(rec['AX']+rec['BX']+rec['CX'])/3
                #self.__calcWater(rec)
                self.add(rec)

    def __render(self):
        self.__empty()

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


    def _image_cell_rgb(self,d,channels,kf=0.8):
        def addcolor(d,el):
            r = d[el]*KF*0.30
            g = d[el]*KF*0.30
            b = d[el]*KF*0.20
            return (r,g,b)
        KF=0.8
        cr = cg = cb = 0
        for el in channels:
            (r,g,b) = addcolor(d,el)
            cr += r
            cg += g
            cb += b

        cb=min(255,int(cb))
        cr=min(255,int(cr))
        cg=min(255,int(cg))
        return (cr,cg,cb)

    def image(self,name="groundSlice", channels = ['AX', 'BX', 'CX'], with_water=True, redNull=False):
        img = Image.new('RGB', (MAX_WIDTH, MAX_HEIGHT), (0,0,0))
        for x in xrange(MAX_WIDTH):
            for y in xrange(MAX_HEIGHT):
                self.readxy(x,y)
                Water = self.hd_rec.values['WATER']
                d=self.hd_rec.values
                if len(channels) == 1:
                    kf = 3
                else:
                    kf = 0.8
                (cr,cg,cb) = self._image_cell_rgb(d,channels)
                if redNull and cr+cg+cb == 0:
                    cr=128
                if Water != 0 and with_water:
                    rgb = (0,0,(255-Water)/2)
                else:
                    rgb = (cr,cg,cb)
                img.putpixel((x,y),rgb)
        img.save(name+".png")

    def image_block(self,name="groundBlock", channels = ['AX', 'BX', 'CX'], with_water=True, redNull=False):
        img = Image.new('RGB', (self.block.rx*w, self.block.ry*h), (0,0,0))
        draw = ImageDraw.Draw(img)
        for x in xrange(self.block.rx):
            for y in xrange(self.block.ry):
                d = self.block.readxy(x,y)
                Water = d['WATER']
                if len(channels) == 1:
                    kf = 3
                else:
                    kf = 0.8
                (cr,cg,cb) = self._image_cell_rgb(d,channels)
                if redNull and cr+cg+cb == 0:
                    cr=128
                if Water != 0 and with_water:
                    rgb = (0,0,(255-Water)/2)
                else:
                    rgb = (cr,cg,cb)
                draw.rectangle([(x*w,y*h),(x*w+w,y*h+h)],fill=rgb)
        img.save(name+".png")
