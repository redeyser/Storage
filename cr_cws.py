#!/usr/bin/python
# -*- coding: utf-8 -*-
S_GROUND = 'slice_ground'
from cws_ground import GroundSlice

stGS = GroundSlice(S_GROUND)
stGS.Create()
stGS.open()
stGS.setDefault()
print stGS
for x in range(9):
    for y in range(9):
        stGS.readblock(x*20,y*20,40,40)
        #stGS.block.decWater(5)
        #stGS.block.addWater(50)
        for n in range(4):
            stGS.block.calc()
        stGS.writeblock()
for x in range(4):
    for y in range(4):
        stGS.readblock(x*50,y*50,50,50)
        #stGS.block.decWater(5)
        #stGS.block.addWater(50)
        for n in range(10):
            stGS.block.calc()
        stGS.writeblock()
stGS.image(name='gr_al',with_water=True)
stGS.image(name='gr_hi',with_water=False)
stGS.image(name='gr_dx',channels = ['DX'], with_water=False,redNull=True)
stGS.image(name='gr_ax',channels = ['AX'], with_water=False)
stGS.image(name='gr_bx',channels = ['BX'], with_water=False)
stGS.image(name='gr_cx',channels = ['CX'], with_water=False)
#stGS.readblock(0,100,50,50)
#stGS.image_block("",15,15)
#for i in xrange(100):
#    stGS.block.calc()
#stGS.image_block("res",15,15)
#stGS.writeblock()
#stGS.image_block("after",15,15)

#for i in xrange(800000):
#    stGS.readRecord(i)
#    if stGS.hd_rec.values['HEIGHT']==0 and stGS.hd_rec.values['WATER']==255:
#        print i,stGS.hd_rec.values

stGS.close()

#simst.open()
#simst.read_vars_vals()
#simst.write_vars_vals({'iter':simst.hd_var.values['iter']+1})
#simst.write_var_values({'tm_day':simst.hd_var.values['tm_day']+1})
#simst.read_vars_vals()
#for k in simst.hd_var.values.keys():
#    print k,simst.hd_var.values[k]
#for k in simst.hd_rec.values.keys():
#    print k,simst.hd_rec.values[k]
#print simst.addRecord({'AX':ord('Z'),'BX':8})
#simst.readRecord(7)
#simst.close()

