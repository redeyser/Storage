#!/usr/bin/python
# -*- coding: utf-8 -*-
from os import path,stat
import sys
from struct import pack,unpack

""" CYBER WORLD 0.0.003 
    Storage 0.0.003
    Объект хранилище
"""

"""
Хранилище задумывается как организация быстрого чтения/записи 
результатов обработки большого множества однотипных объектов и глобальных для этого множества переменных.
Для объекта хранилища не имеет значения структура сохраняемых записей. Структура глобальных переменных может быть произвольной.

Хранилище представляет собой обычный файл, рассчитанный на хранение:
 - некоторого, ограниченного  количества общих переменных с произвольной структурой
 - некоторого, ограниченного (большого) количества записей строго определенной максимальной длинны
 - индексного битового массива признаков активности/удаленности записей

 Структура его следующая:
 - Дескриптор
 - Данные о формате файла
 - Область глобальных переменных
    - Структура
    - Значения
 - Cтруктура записи
 - битовый индекс
 - записи

 Хранилище не поддерживает блокировок и связей. Все это предполагается организовывать в обработчике
 Связь одна к одной (расширительная) делается копирование структуры и синхронным чтением хранилищ
 Связи записей внутри хранилища и между ними могут храниться в самих записях или в расширительном хранилище
 Одновременная обработка хранилищ разными обработчиками должна синхронизироваться итерацией merge 
 из сформированных коммитов обработчиков (все изменения записей и глобальных переменных).
 Вся логика мерджа должна быть разрулена в итеративном обработчике
"""

NULL=chr(0x0)
FULL=chr(0xff)

delete = False
undelete = True

BUFSIZE=1024
FILEEXT = ".cws"
HD_DESCRIPTOR = "#ObjectStorage_0.0.001"
HD_DESCRIPTOR_SIZE = 64
HD_FORMAT_SIZE = 64

""" Все Count  означают максимальное количество. То есть сколько зарезервировано места под структуру"""
HD_FORMAT_STRUCT = [
    ['storageName'   ,'s',"default"],
    ['recordsCount'  ,'I',1000000*8],
    ['fieldsCount'   ,'I',16],
    ['valuesCount'   ,'I',32],
    ['recSize'       ,'I',256],
    ['varSize'       ,'I',1024],
]
HD_VAR_NAME_SIZE = 16
HD_VAR_SIZE = 17

TYPE_SIZE = {
    's' : HD_VAR_NAME_SIZE,
    'S' : 256,
    'X' : 1024,
    'I' : 4,
    'H' : 2,
    'B' : 1,
    'f' : 4,
    'd' : 8,
    'L' : 8,
    ' ' : 0,
}

TYPE_DECODE = {
    's' : '16s',
    'S' : '256s',
    'X' : '1024s',
    'I' : 'I',
    'H' : 'H',
    'B' : 'B',
    'f' : 'f',
    'd' : 'd',
    'L' : 'L',
    '*' : False,
    ' ' : False,
}

DEFAULT_VARS = [
    ['globalVar1',    'H'],
    ['globalVar2',    'I'],
]

DEFAULT_FIELDS = [
    ['field1',    's'],
    ['field2',    'I'],
]


class VarsStruct:
    def __init__(self, buf=None, count=0, struct=None):
        self.count = count
        self.clearStruct()
        if buf!=None:
            self.readStruct(buf)
        elif struct!=None:
            self.createStruct(struct)
        self.values = {}

    def __str__(self):
        s=""
        for i in range(len(self.arr)):
            a=self.arr[i]
            s+="%s. %s[%s]\t[%s,%s,%s] +%s\n" % (i,a['fname'],a['alias'],a['ftype'],a['rtype'],a['fsize'],a['pos'])
        return s

    def decodetype(self, fname, ftype):
        """ По имени получаем алиас, размер и реальный тип  """
        _fname = fname.strip()
        if ftype == '*':
            i = fname.find("#")
            if i == -1:
                _ftype = False
                _fsize = 0
            else:
                try:
                    _fsize = int(_fname[i+1:])
                    _ftype = "%ss" % _fsize
                    _fname = _fname[:i]
                except:
                    _ftype = False
                    _fsize = 0
        else:
            _fsize=TYPE_SIZE[ftype]
            _ftype=TYPE_DECODE[ftype]
        return (_fname, _ftype, _fsize)

    def _field(self, *argv):
        order = ['fname','ftype','fsize','alias','rtype','pos']
        field = {}
        for i in range(len(order)):
            field[order[i]]=argv[i]
        return field

    def add_field(self, *argv):
        f = self._field(*argv)
        self.idx[f['alias']] = len(self.arr)
        self.arr.append(f)

    def get_field(self, fd):
        if self.idx.has_key(fd):
            return self.arr[self.idx[fd]]
        return None

    def createStruct(self, struct, maxsize=0):
        """ Из массива в структуру """
        self.clearStruct()
        pos=0
        for a in struct:
            fname = a[0]
            ftype = a[1]
            (_alias,_rtype,_fsize) = self.decodetype(a[0],a[1])
            self.add_field(fname, ftype, _fsize, _alias, _rtype, pos)
            pos+=_fsize
        if maxsize>pos:
            fname='autosize#'+str(maxsize-pos)
            ftype='*'
            (_alias,_rtype,_fsize) = self.decodetype(fname,ftype)
            self.add_field(fname, ftype, _fsize, _alias, _rtype, pos)
            pos+=_fsize
        self.size = pos

    def clearStruct(self):
        self.arr=[]
        self.idx={}

    def makeStruct(self):
        """ получить массив """
        return  [ a[:2] for a in self.arr ]

    def readStruct(self, buf):
        """ Из бинарного в структуру """
        self.clearStruct()
        pos=0
        for n in range(self.count):
            start=n*HD_VAR_SIZE
            end=start+HD_VAR_NAME_SIZE
            fname = buf[start:end]
            ftype = buf[end:end+1]
            (_alias,_rtype,_fsize) = self.decodetype(fname,ftype)
            self.add_field(fname, ftype, _fsize, _alias, _rtype, pos)
            pos+=_fsize
        self.size = pos

    def writeStruct(self):
        """ Перевод структуры в бинарный вид """
        buf=''
        for fd in self.arr:
            buf += fd['fname'].ljust(HD_VAR_NAME_SIZE,' ') + fd['ftype']
        if self.count>len(self.arr):
            buf += (self.count-len(self.arr))*HD_VAR_SIZE*' '
        return buf

    def readValues(self, buf):
        """ Бинарное выражение расшифровывается в переменные """
        size=0
        self.values = dict()
        for fd in self.arr:
            if fd['rtype']:
                value = unpack(fd['rtype'], buf[ fd['pos']: fd['pos']+fd['fsize'] ])[0]
                self.values[fd['alias']] = value
            size+=fd['fsize']

    def writeValues(self):
        """ Перевод массива данных в бинарный вид """
        size=0
        buf = ""
        for fd in self.arr:
            if self.values.has_key(fd['alias']):
                val=pack(fd['rtype'], self.values[fd['alias']])
            else:
                val=NULL*fd['fsize']
            buf += val
        return buf

    def writeValue(self, key, value):
        """ Перевод конкретной переменной бинарный вид """
        buf = ""
        if self.idx.has_key(key):
            fd=self.get_field(key)
            buf=pack(fd['rtype'], value)
        return buf

class IdxBit:
    def __init__(self, stg):
        self.stg=stg
        self.count=stg.fmstruct['recordsCount']
        self.sizeBytes = self.count/8
        self.seek = self.stg.addr_idx

    def __getBit(self, nBit=None):
        if nBit!=None:
            self.nBit=nBit
        vBit = 0b1<<self.nBit
        if vBit&ord(self.curByte) == vBit:
            return True
        else:
            return False

    def __findBit(self, Bit):
        result=None
        for nBit in range(8):
            B = self.__getBit(nBit)
            if B==Bit:
                result = nBit
                break
        return result

    def __putBit(self, Bit):
        vBit = 0b1<<self.nBit
        if Bit:
            self.curByte = chr(vBit|ord(self.curByte))
        else:
            self.curByte = chr(vBit^ord(self.curByte))

    def __calcPos(self, nBit):
        self.nByte=(nBit)//8
        self.nBit=(nBit)%8

    def __seekIdByte(self, nByte=None):
        if nByte != None:
            self.nByte = nByte
        self.stg.handle.seek(self.seek+self.nByte)

    def __readBuf(self, count):
        size=min(count, self.sizeBytes-self.nByte)
        self.nByte += size
        return self.stg.handle.read(size)

    def __writeBuf(self, Byte, count):
        size=min(count, self.sizeBytes-self.nByte)
        self.stg.handle.write(Byte*size)
        self.nByte += size
    
    def __writeByte(self):
        self.__seekIdByte()
        self.stg.handle.write(self.curByte)
        
    def __readByte(self):
        self.__seekIdByte()
        self.curByte=self.stg.handle.read(1)

    def clearAll(self):
        self.__seekIdByte(0)
        while self.nByte < self.sizeBytes:
            self.__writeBuf(NULL, BUFSIZE)

    def readBit(self, idBit):
        self.__calcPos(idBit)
        self.__readByte()
        return self.__getBit()

    def writeBit(self, idBit, Bit):
        gBit = self.readBit(idBit)
        if gBit!=Bit:
            self.__putBit(Bit)
            self.__writeByte()

    def findBit(self, Bit):
        self.__seekIdByte(0)
        result = None
        while self.nByte < self.sizeBytes and result==None:
            buf = self.__readBuf(BUFSIZE)
            for curid in range(len(buf)):
                self.curByte=buf[curid]
                if Bit:
                    if self.curByte!=NULL:
                        result = self.__findBit(Bit)
                        break
                else:
                    if self.curByte!=FULL:
                        result = self.__findBit(Bit)
                        break
        if result!=None:
            result+=curid*8
        return result

    def readNext(self, Bit):
        while self.nByte < self.sizeBytes:
            buf = self.__readBuf(BUFSIZE)
            for Byte in buf:
                if Byte!=NULL:
                    for nBit in range(8):
                        B = __getBit(nBit)
                        if B==Bit:
                            yield nBit+self.nByte*8
                    
class Storage:
    def __init__(self):
        self.__isfile__=False
        self.fileName=''
        self.hd_var=None
        self.hd_rec=None
        self.hd_idx=None
        self.curRecord=0

    def __addr_set(self):
        self.__addr_vars_struct = HD_DESCRIPTOR_SIZE+HD_FORMAT_SIZE
        self.__addr_vars_vals = self.__addr_vars_struct + HD_VAR_SIZE * self.fmstruct['valuesCount']
        self.__addr_rec_struct = self.__addr_vars_vals + self.fmstruct['varSize']
        self.addr_idx = self.__addr_rec_struct + HD_VAR_SIZE * self.fmstruct['fieldsCount']
        self.addr_data = self.addr_idx + self.fmstruct['recordsCount']/8

    def __str__(self):
        line="-"*40
        if not self.__isfile__:
            return ""
        str_fmstruct = "\n".join(["%s: %s" % (k,v) for k,v in self.fmstruct.items()])
        str_vars    =str(self.hd_var)
        str_fields  =str(self.hd_rec)
        count=self.__len__()
        s="%s\nversion: %s\nhead: %s\n%s\n%s\n%s\n%s%s\n%s%s\nrecords:%s"\
        % (line,self.desc,self.head_size,line,str_fmstruct,line,str_vars,line,str_fields,line,count)
        return s
    
    def __verify_fmstruct__(self):
        """ Проверяем структуру формата. Дополняем значениями по умолчанию """
        result = True
        for v in HD_FORMAT_STRUCT:
            k=v[0]
            if not self.fmstruct.has_key(k):
                self.fmstruct[k] = v[2]
                result=False
            if v[1]=='s':
                self.fmstruct[k]=self.fmstruct[k].ljust(HD_VAR_NAME_SIZE,' ')
        return result 

    def __write_struct__(self,Struct):
        """ Запись структуры """
        self.handle.write( Struct.writeStruct() )

    def __read_struct__(self,count):
        """ Чтение структуры """
        buf = self.handle.read(HD_VAR_SIZE*count)
        return  VarsStruct(buf,count)

    def __truncate__(self):
        """ Создаем файл хранилища по заданной структуре """
        try:
            self.handle = open(self.fileName,"wb")
            """ Декриптор, дополненный пробелами """
            self.handle.write(HD_DESCRIPTOR.ljust(HD_DESCRIPTOR_SIZE," "))
            """ Формируем блок формата """
            self.__verify_fmstruct__()
            bin_fmstruct=''
            for v in HD_FORMAT_STRUCT:
                k=v[0]
                fmt=TYPE_DECODE[v[1]]
                bin_fmstruct += pack(fmt,self.fmstruct[k])
            bin_fmstruct = bin_fmstruct.ljust(HD_FORMAT_SIZE,NULL)
            self.handle.write(bin_fmstruct)
            """ Область переменных. Структура """
            self.__write_struct__(self.hd_var)
            """ Вывод области значений переменных """
            self.handle.write(NULL*self.fmstruct['varSize'])
            """ Область полей. Структура записи """
            self.__write_struct__(self.hd_rec)
            """ Вывод бинарных индексов """
            self.handle.write(NULL*(self.fmstruct['recordsCount']/8))
            self.__close__()
            return True
        except Exception,ex:
            print ex
            return False

    def __rewrite_varstruct__(self, struct):
        """ Перезаписываем структуру глобальных переменных """
        try:
            self.handle.seek(self.__addr_vars_struct)
            self.hd_var.createStruct(struct,self.fmstruct['varSize'])
            self.__write_struct__(self.hd_var)
            return True
        except Exception,ex:
            print ex
            return False

    def __rewrite_recstruct__(self, struct):
        """ Перезаписываем структуру записи """
        try:
            self.handle.seek(self.__addr_rec_struct)
            self.hd_rec.createStruct(struct,self.fmstruct['recSize'])
            self.__write_struct__(self.hd_rec)
            return True
        except:
            return False

    def __read_vars_vals__(self):
        """ Читаем все переменные """
        try:
            self.handle.seek(self.__addr_vars_vals)
            buf = self.handle.read(self.fmstruct['varSize'])
            self.hd_var.readValues(buf)
            return True
        except Exception,ex:
            print ex
            return False

    def __write_vars_vals__(self,values):
        """ Записываем весь блок переменных, считанных до этого  """
        try:
            if not self.__read_vars_vals__():
                return False
            self.hd_var.values.update(values)
            self.handle.seek(self.__addr_vars_vals)
            self.handle.write(self.hd_var.writeValues())
            return True
        except Exception,ex:
            print ex
            return False

    def __write_var_values__(self, values):
        """ Запись произвольного списка переменных из dict{key:value}
            Каждая переменная позиционируется и записывается отдельно
        """
        try:
            if len(values) == 0:
                return False
            for k,v in values.items():
                fd = self.hd_var.get_field(k)
                fpos = fd['pos']
                if fpos!=None:
                    self.handle.seek(self.__addr_vars_vals+fpos)
                    self.handle.write(self.hd_var.writeValue(k,v))
            return True
        except Exception,ex:
            print ex
            return False
                
    def __create__(self, fmstruct={}, stvar=DEFAULT_VARS, strec=DEFAULT_FIELDS):
        """ Задаем структуру хранилища, по которой создаем пустое хранилище """
        self.fmstruct = fmstruct
        self.hd_var = VarsStruct(count=self.fmstruct['valuesCount'],struct=stvar)
        self.hd_rec = VarsStruct(count=self.fmstruct['fieldsCount'],struct=strec)
        result=self.__truncate__()
        if result:
            result=self.__initial__(self.fileName)
        return result

    def __readformat__(self):
        """ Читаем формат """
        try:
            self.handle.seek(0)
            self.desc = self.handle.read(HD_DESCRIPTOR_SIZE)
            if self.desc!=HD_DESCRIPTOR.ljust(HD_DESCRIPTOR_SIZE,' '):
                self.__isfile__=False
                return False

            bin_fmstruct = self.handle.read(HD_FORMAT_SIZE)
            start=0
            self.fmstruct={}
            for v in HD_FORMAT_STRUCT:
                k=v[0]
                fmt=TYPE_DECODE[v[1]]
                end=start+TYPE_SIZE[v[1]]
                self.fmstruct[k] = unpack(fmt,bin_fmstruct[start:end])[0]
                start=end
            self.__addr_set()
            self.hd_var = self.__read_struct__(self.fmstruct['valuesCount'])
            self.handle.seek(self.__addr_rec_struct)
            self.hd_rec = self.__read_struct__(self.fmstruct['fieldsCount'])
            self.hd_idx = IdxBit(self)

            self.head_size=HD_DESCRIPTOR_SIZE+HD_FORMAT_SIZE+\
                            HD_VAR_SIZE*self.fmstruct['valuesCount']+\
                            self.fmstruct['varSize']+\
                            HD_VAR_SIZE*self.fmstruct['fieldsCount']+\
                            self.fmstruct['recordsCount']/8
            self.__isfile__=True
            return True
        except Exception,ex:
            print ex
            self.__isfile__=False
            return False

    def __initial__(self,filename):
        self.fileName=filename
        self.__isfile__=False
        try:
            self.handle = open(self.fileName,"rb+")
            self.__readformat__()
            self.__close__()
            self.recordCount=self.__size__()
            return self.__isfile__
        except:
            return False

    def __open__(self):
        """ Открываем файл """
        if not self.__isfile__:
            return False
        try:
            self.handle = open(self.fileName,"rb+")
        except:
            return False
        return True

    def __close__(self):
        """ Закрываем файл """
        try:
            self.handle.close()
        except:
            return False
        return True

    def __size__(self):
        st=stat(self.fileName)
        return (st.st_size-self.head_size)/self.fmstruct['recSize']

    def __len__(self):
        return self.recordCount

    def __findidx(self,idx):
        """ Ищем индекс """
        return self.hd_idx.findBit(idx)

    def __getidx(self):
        """ Читаем бит-индекс """
        self.hd_idx.readBit(self.curRecord)

    def __putidx(self, Bit):
        """ Записываем бит-индекс """
        self.hd_idx.writeBit(self.curRecord, Bit)

    def __seekRecord(self, nRec=None):
        if nRec==None:
            nRec=self.curRecord
        #print nRec,self.addr_data,nRec*self.fmstruct['recSize']
        self.handle.seek(self.addr_data+nRec*self.fmstruct['recSize'])
        self.curRecord=nRec

    def __seekLast(self):
        self.handle.seek(0,2)
        self.curRecord=self.__len__()

    def __seekFirst(self):
        self.handle.seek(0,0)
        self.curRecord=0

    def __write_record__(self,nRec=None,values={}):
        """ Записываем весь блок полей, считанных до этого  """
        try:
            self.__seekRecord(nRec)
            self.hd_rec.values.update(values)
            self.handle.write(self.hd_rec.writeValues())
            return True
        except Exception,ex:
            print ex
            return False

    def __read_record__(self,nRec=None):
        """ Читаем весь блок полей, считанных до этого  """
        try:
            self.__seekRecord(nRec)
            self.hd_rec.readValues(self.handle.read(self.fmstruct['recSize']))
            return True
        except Exception,ex:
            print ex
            return False
    
    def __write_fields__(self,nRec=None,values={}):
        """ Записываем блок полей  
            Необходимо по каждому полю рассчитать бинарное значение и указатель для seek
            Затем устанавливать указатель и делать запись
        """
        pass

    def __read_fields__(self,nRec=None):
        pass

    def __append__(self,values,find=True):
        """ Добавление записи """
        try:
            self.curRecord = self.__len__()
            if find and self.curRecord != 0:
                nRec = self.__findidx(delete)
                if nRec == None:
                    return False
                else:
                    self.curRecord = nRec
            self.__putidx(undelete)
            if not self.__write_record__(values=values):
                self.__putidx(delete)
                return False
            else:
                self.recordCount+=1
                return True
        except Exception, ex:
            print ex
            return False

    def __delete__(self, nRec):
        try:
            self.curRecord = nRec
            self.__putidx(delete)
            return True
        except:
            return  False

    def __undelete__(self, nRec):
        try:
            self.curRecord = nRec
            self.__putidx(undelete)
            return True
        except:
            return  False


    def __readrecordBuf__(self,idrec,seek=True):
        return True
    def __writerecordBuf__(self,idrec,seek=True):
        return True

class SimStorage(Storage):
    def __init__(self, name):
        Storage.__init__(self)
        self.name = name
        filename = name + FILEEXT
        self.init(filename)
        
    def create(self, maxFieldSize, fieldCount, recordCount, maxVarSize, varCount):
        """ Создание хранилища """
        fmstruct = {
            'storageName'   :self.name,
            'recordsCount'  :recordCount,
            'fieldsCount'   :fieldCount,
            'valuesCount'   :varCount,
            'recSize'       :fieldCount*maxFieldSize,
            'varSize'       :varCount*maxVarSize,
        }
        fmvars = []
        for i in range(varCount):
            fmvars.append(['var_%s#%s' %(i,maxVarSize),'*'])
        fmrec = []
        for i in range(fieldCount):
            fmrec.append(['fd_%s#%s' % (i,maxFieldSize),'*'])
        return self.__create__(fmstruct=fmstruct,stvar=fmvars,strec=fmrec)

    def init(self,filename):
        return self.__initial__(filename)

    def truncate(self):
        """ Обнуляет файл """
        if not self.fmstruct:
            return False
        return self.__truncate__()

    def exist(self):
        return self.__isfile__

    def open(self):
        return self.__open__()

    def close(self):
        return self.__close__()

    def read_hd_var(self):
        return self.hd_var.makeStruct()

    def read_hd_rec(self):
        return self.hd_rec.makeStruct()

    def rwstruct_vars(self,struct):
        return self.__rewrite_varstruct__(struct)

    def rwstruct_rec(self,struct):
        return self.__rewrite_recstruct__(struct)

    def read_vars_vals(self):
        return self.__read_vars_vals__()

    def write_vars_vals(self,values):
        return self.__write_vars_vals__(values)

    def write_var_values(self,values):
        """ Выводим любые переменные выборочно """
        return self.__write_var_values__(values)

    def addRecord(self,values):
        return self.__append__(values)

    def add(self,values):
        return self.__append__(values,find=False)

    def upd(self,values):
        return self.__write_fields__(values,find=False)

    def delRecord(self, nRec):
        return self.__delete__(nRec)

    def undelRecord(self, nRec):
        return self.__undelete__(nRec)

    def readRecord(self,nRec):
        return self.__read_record__(nRec)

    def writeRecord(self,nRec,values):
        return self.__write_record__(nRec,values)


