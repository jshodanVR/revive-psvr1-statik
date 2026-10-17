"""Scoped build-time reader/writer for Statik's single-export cooked UE4 assets.

Original packages are opened read-only. Supports the exact observed summary,
name/import/export tables and tagged properties; rejects unfamiliar layouts.
Name hashes follow UE's ASCII Strihash_DEPRECATED and UTF-32 StrCrc32 algorithms
(format reference: UAssetAPI/CRCGenerator.cs). No external library is vendored.
"""
import struct
import zlib

def u32(b,p): return struct.unpack_from('<I',b,p)[0]
def i32(b,p): return struct.unpack_from('<i',b,p)[0]
def p32(b,p,v): struct.pack_into('<I',b,p,v)
def fname(i): return struct.pack('<II',i,0)

def name_hash(s):
    h=0
    for c in s.upper().encode('ascii'):
        q=((h^c)&255)<<24
        for _ in range(8): q=((q<<1)^(0x04c11db7 if q&0x80000000 else 0))&0xffffffff
        h=(h>>8)^q
    return (h&65535)|((zlib.crc32(s.encode('utf-32le'))&65535)<<16)

class Package:
    def __init__(self,b):
        self.original=bytes(b)
        assert b[:8]==bytes.fromhex('c1832a9ef9ffffff')
        assert b[8:24]==bytes(16) and b[28:37]==b'\x05\0\0\0None\0'
        assert b[-4:]==b[:4] and u32(b,57)==1 and u32(b,45)==189
        self.summary=bytearray(b[:189]); self.names=[];self.namebytes=[]
        p=189
        for _ in range(u32(b,41)):
            start=p;n=i32(b,p);p+=4;assert 0<n<4096 and b[p+n-1]==0
            s=b[p:p+n-1].decode('ascii');p+=n
            assert u32(b,p)==name_hash(s),(s,hex(u32(b,p)),hex(name_hash(s)))
            p+=4;self.names.append(s);self.namebytes.append(b[start:p])
        assert p==u32(b,69)
        count=u32(b,65);self.imports=[b[p+i*28:p+(i+1)*28] for i in range(count)]
        p+=count*28;assert p==u32(b,61)
        # Preserve the 96-byte export plus the following four-byte zero word.
        # This reader deliberately supports only the observed single-export layout.
        self.export=bytearray(b[p:p+100]);p+=100
        assert p==u32(b,81)==u32(b,161)
        assert u32(b,185)==p+4 and u32(b,24)==p+4
        self.depends=b[p:p+4];assert self.depends==bytes(4)
        self.serial_size=u32(self.export,28)
        assert 0<self.serial_size<=len(b)-(p+4)-4
        assert u32(self.export,32)==p+4
        self.payload=bytes(b[p+4:-4])
        self.bulk_relative=struct.unpack_from('<q',b,165)[0]-(p+4)
        self.payload_start=p+4
        assert self.encode()==b,'Identity reserialization failed'

    def name(self,s):
        if s not in self.names:
            raw=s.encode('ascii')+b'\0';self.names.append(s)
            self.namebytes.append(struct.pack('<i',len(raw))+raw+struct.pack('<I',name_hash(s)))
        return self.names.index(s)

    def rename(self,old,new):
        assert old in self.names and new not in self.names
        i=self.names.index(old);self.names[i]=new
        raw=new.encode('ascii')+b'\0'
        self.namebytes[i]=struct.pack('<i',len(raw))+raw+struct.pack('<I',name_hash(new))

    def texture_import(self,package,object_name):
        # Texture2D import whose outer is its newly added Package import.
        engine=self.name('/Script/Engine');core=self.name('/Script/CoreUObject')
        package_class=self.name('Package');texture_class=self.name('Texture2D')
        self.imports.append(fname(core)+fname(package_class)+struct.pack('<i',0)+fname(self.name(package)))
        outer=-len(self.imports)
        self.imports.append(fname(engine)+fname(texture_class)+struct.pack('<i',outer)+fname(self.name(object_name)))
        return -len(self.imports)

    def encode(self):
        b=bytearray(self.summary);names=b''.join(self.namebytes);imports=b''.join(self.imports)
        import_at=189+len(names);export_at=import_at+len(imports);dep_at=export_at+100;body_at=dep_at+4
        for p,v in [(24,body_at),(41,len(self.names)),(61,export_at),(65,len(self.imports)),(69,import_at),(81,dep_at),(113,len(self.names)),(161,dep_at),(185,body_at)]:p32(b,p,v)
        struct.pack_into('<q',b,165,body_at+self.bulk_relative)
        exp=bytearray(self.export)
        struct.pack_into('<II',exp,28,self.serial_size,body_at)
        return bytes(b)+names+imports+bytes(exp)+self.depends+self.payload+self.original[-4:]

    def properties(self,b=None):
        b=self.payload if b is None else b;p=0;out=[]
        while True:
            start=p;ni=u32(b,p);num=u32(b,p+4);p+=8
            assert ni<len(self.names) and num==0
            name=self.names[ni]
            if name=='None':return out,p
            ti=u32(b,p);assert u32(b,p+4)==0;p+=8
            typ=self.names[ti];size=u32(b,p);idx=u32(b,p+4);p+=8;extra=None
            if typ=='StructProperty':
                extra=self.names[u32(b,p)];p+=24
            elif typ=='ArrayProperty':
                extra=self.names[u32(b,p)];p+=8
            elif typ=='BoolProperty':p+=1
            elif typ in ('ByteProperty','EnumProperty'):p+=8
            assert b[p]==0,('Property GUID unsupported',name);p+=1
            assert p+size<=len(b)
            out.append(dict(name=name,type=typ,extra=extra,start=start,data=p,size=size,end=p+size,index=idx))
            p+=size

    def scalar(self,name,value):
        tag=(fname(self.name('ParameterName'))+fname(self.name('NameProperty'))+struct.pack('<II',8,0)+b'\0'
             +fname(self.name(name))+fname(self.name('ParameterValue'))+fname(self.name('FloatProperty'))+struct.pack('<II',4,0)+b'\0')
        assert self.payload.count(tag)==1,name
        at=self.payload.index(tag)+len(tag);b=bytearray(self.payload);struct.pack_into('<f',b,at,value);self.payload=bytes(b)

    def add_texture_parameters(self,parameters):
        items=[]
        for parameter,package,obj in parameters:
            items.append((parameter,struct.pack('<i',self.texture_import(package,obj))))
        self.append_parameters('TextureParameterValues','TextureParameterValue','ObjectProperty',items)

    def add_scalar_parameters(self,parameters):
        self.append_parameters('ScalarParameterValues','ScalarParameterValue','FloatProperty',
                               [(name,struct.pack('<f',value)) for name,value in parameters])

    def append_parameters(self,array,struct_type,value_type,parameters):
        props,_=self.properties()
        prop=next(x for x in props if x['name']==array)
        assert prop['extra']=='StructProperty'
        value=self.payload[prop['data']:prop['end']]
        # UE's array-of-struct header repeats the property tag before elements.
        count=u32(value,0);assert count>=1
        header_size=53
        assert self.names[u32(value,4)]==array
        assert self.names[u32(value,12)]=='StructProperty'
        assert self.names[u32(value,28)]==struct_type
        members,end=self.properties(value[header_size:]);template=value[header_size:header_size+end]
        pn=next(x for x in members if x['name']=='ParameterName')
        pv=next(x for x in members if x['name']=='ParameterValue')
        guid=next(x for x in members if x['name']=='ExpressionGUID')
        assert pn['size']==8 and pv['type']==value_type and pv['size']==4 and guid['size']==16
        additions=[]
        for parameter,raw in parameters:
            item=bytearray(template)
            item[pn['data']:pn['end']]=fname(self.name(parameter))
            item[pv['data']:pv['end']]=raw
            item[guid['data']:guid['end']]=bytes(16)
            additions.append(bytes(item))
        v=bytearray(value);p32(v,0,count+len(additions));p32(v,20,u32(v,20)+sum(map(len,additions)))
        v+=b''.join(additions)
        body=bytearray(self.payload[:prop['data']]);p32(body,prop['start']+16,len(v))
        body+=v+self.payload[prop['end']:]
        delta=len(body)-len(self.payload);self.bulk_relative+=delta;self.serial_size+=delta;self.payload=bytes(body)
