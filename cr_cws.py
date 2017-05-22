#!/usr/bin/python
# -*- coding: utf-8 -*-
S_GROUND = 'slice_ground'
from cws_ground import GroundSlice

stGS = GroundSlice(S_GROUND)
stGS.Create()
stGS.open()
stGS.setDefault()
print stGS
#for x in range(20):
#    for y in range(16):
#        stGS.readblock(max(x*50-2,0),max(y*50-2,0),52,52)
#        for n in range(10):
#            stGS.block.calc()
#        stGS.writeblock()
stGS.image()
stGS.readblock(0,100,50,50)
stGS.image_block("",15,15)
#stGS.block.addWater(100)
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

