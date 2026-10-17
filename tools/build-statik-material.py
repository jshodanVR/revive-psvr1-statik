"""Bake a coordinated, isolated paint material from an authored height field.

Build-time only (Pillow/numpy). Original game is read-only. Output includes a
verified copy/insert recipe, not original game assets, for the opt-in launcher.
"""
from pathlib import Path
from io import BytesIO
import hashlib,json,struct,sys,difflib
import numpy as np
from PIL import Image
from statik_material_asset import Package,u32,i32
from statik_pak import index,asset

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/statik-material-v3'
MATERIAL='Deadlock/Content/Puzzles/IntroductionPuzzle/Materials/MAT_Gyrophone_Chassi_02.uasset'
TEMPLATES=[('TEX_PlasticBase_D','TEX_EnhPaint___D_','BaseColor_Texture'),
           ('TEX_GrainyPlastic_N','TEX_EnhPaint_____N','Normal_Texture'),
           ('TEX_DirtyScratches_R','TEX_EnhPaint______R','Roughness_Texture')]

def resize_float(a,size):
    return np.asarray(Image.fromarray(a.astype(np.float32)).resize(size,Image.Resampling.BOX),dtype=np.float32)

def periodic(a):
    # Periodic-plus-smooth decomposition removes opposite-edge discontinuities.
    h,w=a.shape;v=np.zeros_like(a)
    v[0,:]=a[-1,:]-a[0,:];v[-1,:]=-v[0,:]
    v[:,0]+=a[:,-1]-a[:,0];v[:,-1]-=a[:,-1]-a[:,0]
    denom=2*np.cos(2*np.pi*np.arange(w)/w)[None,:]+2*np.cos(2*np.pi*np.arange(h)/h)[:,None]-4
    denom[0,0]=1
    smooth=np.fft.fft2(v)/denom;smooth[0,0]=0
    return a-np.fft.ifft2(smooth).real

def maps():
    src=Image.open(ROOT/'tools/assets/statik-paint-height.png').convert('L').resize((1024,1024),Image.Resampling.LANCZOS)
    h=periodic(np.asarray(src,dtype=np.float32)/255)
    h-=h.mean();h*=0.035/max(h.std(),1e-6)
    # The generated grayscale is explicitly treated as height, not as lighting.
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))*3
    dy=(np.roll(h,-1,0)-np.roll(h,1,0))*3
    n=np.stack((-dx,dy,np.ones_like(h)),axis=2);n/=np.linalg.norm(n,axis=2,keepdims=True)
    rough=np.clip(.48+h*3.5,.20,.78)
    linear=np.array([.2961379885673523,.10224200040102005,.05951099842786789])
    col=linear[None,None,:]*np.clip(1+h[:,:,None]*1.2,.92,1.08)
    col=np.where(col<=.0031308,col*12.92,1.055*col**(1/2.4)-.055)
    rgb=np.uint8(np.clip(np.rint(col*255),0,255));normal=np.uint8(np.rint((n*.5+.5)*255))
    Image.fromarray(rgb).save(OUT/'paint-color.png');Image.fromarray(normal).save(OUT/'paint-normal-preview.png')
    Image.fromarray(np.uint8(np.rint(rough*255))).save(OUT/'paint-roughness.png')
    return rgb,n,rough

def mip_layout(b):
    import re
    found=[]
    for m in re.finditer(rb'PF_(DXT1|BC5)\0',b[:4096]):
        p=m.start();w,h,slices,length=struct.unpack_from('<IIII',b,p-16)
        if slices==1 and length==len(m.group()) and 32<=w<=4096 and 32<=h<=4096:
            first,count=struct.unpack_from('<II',b,m.end())
            if first==0 and 1<=count<=14:found.append((m.end()+8,w,h,m.group()[:-1].decode(),count))
    assert len(found)==1;cursor,w,h,fmt,count=found[0];bulk=struct.unpack_from('<q',b,165)[0];mips=[]
    for level in range(count):
        cooked,flags,count,size,off=struct.unpack_from('<IIIIq',b,cursor);cursor+=24
        assert cooked==1 and flags in (0x401,0x48) and count==size
        start=bulk+off if flags==0x401 else cursor
        if flags==0x48:assert off==cursor;cursor+=size
        mw,mh=struct.unpack_from('<II',b,cursor);cursor+=8
        assert (mw,mh)==(max(4,w>>level),max(4,h>>level))
        assert start>=0 and start+size<=len(b)-4
        mips.append((start,size,mw,mh))
    return fmt,mips

def tiling(linear,w,h,blocksize,inverse=False):
    bw,bh=(w+3)//4,(h+3)//4;tw,th=(bw+7)//8,(bh+7)//8
    out=bytearray((bw*bh if inverse else tw*th*64)*blocksize)
    for y in range(th*8):
        for x in range(tw*8):
            morton=sum((((x>>i)&1)<<(2*i))|(((y>>i)&1)<<(2*i+1)) for i in range(3))
            tiled=(((y//8)*tw+x//8)*64+morton)*blocksize
            flat=(min(y,bh-1)*bw+min(x,bw-1))*blocksize
            if inverse:
                if x<bw and y<bh:out[flat:flat+blocksize]=linear[tiled:tiled+blocksize]
            else:out[tiled:tiled+blocksize]=linear[flat:flat+blocksize]
    return bytes(out)

def bake_texture(original,new_name,kind,paint):
    rgb,normal,rough=paint;p=Package(original)
    old=next(x for x in p.names if x.startswith('/Game/'))
    oldname=old.rsplit('/',1)[1]
    # Same string lengths keep cooked mip offsets unchanged.
    new_name=new_name[:len(oldname)].ljust(len(oldname),'_')
    newpath=old.rsplit('/',1)[0]+'/'+new_name
    p.rename(old,newpath);p.rename(oldname,new_name)
    b=bytearray(p.encode());assert p.payload_start==u32(b,24)
    fmt,mips=mip_layout(b);metrics=[]
    for level,(start,size,w,h) in enumerate(mips):
        if kind=='Normal_Texture':
            averaged=np.stack([resize_float(normal[:,:,c],(w,h)) for c in range(3)],axis=2)
            averaged/=np.maximum(np.linalg.norm(averaged,axis=2,keepdims=True),1e-8)
            pixels=np.uint8(np.clip(np.rint((averaged*.5+.5)*255),0,255))
            im=Image.fromarray(pixels);codec='BC5';assert fmt=='PF_BC5'
        elif kind=='Roughness_Texture':
            averaged=np.stack([resize_float(normal[:,:,c],(w,h)) for c in range(3)],axis=2)
            variance=np.maximum(0,1-np.linalg.norm(averaged,axis=2))
            value=np.sqrt(np.clip(resize_float(rough**2,(w,h))+variance,0,1))
            im=Image.fromarray(np.uint8(np.rint(value*255))).convert('RGB');codec='DXT1'
        else:
            im=Image.fromarray(rgb).resize((w,h),Image.Resampling.LANCZOS);codec='DXT1'
        stream=BytesIO();im.save(stream,format='DDS',pixel_format=codec)
        dds=stream.getvalue();linear=dds[148 if codec=='BC5' else 128:]
        bs=16 if codec=='BC5' else 8
        assert len(linear)==((w+3)//4)*((h+3)//4)*bs
        tiled=tiling(linear,w,h,bs);assert len(tiled)==size
        assert tiling(tiled,w,h,bs,True)==linear
        # Preserve decoded alpha/coverage at EVERY mip, not just top-level.
        if codec=='DXT1':
            oldlinear=tiling(original[start:start+size],w,h,8,True)
            oldim=Image.frombytes('RGBA',(w,h),oldlinear,'bcn',1)
            decoded=Image.frombytes('RGBA',(w,h),linear,'bcn',1)
            assert oldim.getchannel('A').tobytes()==decoded.getchannel('A').tobytes()
            assert decoded.getchannel('A').getextrema()==(255,255)
        b[start:start+size]=tiled;metrics.append(dict(level=level,width=w,height=h,bytes=size,alpha_unchanged=True))
    Package(bytes(b));start,size,w,h=mips[0]
    linear=tiling(b[start:start+size],w,h,16 if fmt=='PF_BC5' else 8,True)
    image=Image.frombytes('RGB' if fmt=='PF_BC5' else 'RGBA',(w,h),linear,'bcn',5 if fmt=='PF_BC5' else 1)
    image.save(OUT/(new_name+'-decoded.png'))
    return newpath,bytes(b),metrics

def write_pak(entries,path):
    def string(s):b=s.encode()+b'\0';return struct.pack('<i',len(b))+b
    def entry(at,b):return struct.pack('<qqqI20sBI',at,len(b),len(b),0,hashlib.sha1(b).digest(),0,0)
    out=bytearray();ix=bytearray(string('../../../')+struct.pack('<I',len(entries)))
    for name,b in entries.items():
        ix+=string(name)+entry(len(out),b);out+=entry(0,b)+b
    at=len(out);out+=ix;out+=struct.pack('<IIqq20s',0x5a6f12e1,3,at,len(ix),hashlib.sha1(ix).digest());path.write_bytes(out)

def recipe(records):
    def string(s):b=s.encode()+b'\0';return struct.pack('<i',len(b))+b
    out=bytearray(b'STATIKM3'+struct.pack('<I',len(records)))
    for source,target,a,b in records:
        # Metadata is small. Exact payload ranges let large authored textures
        # replace whole mips without quadratic byte-by-byte diff matching.
        if target==MATERIAL:
            spans=difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes()
        else:
            _,mips=mip_layout(a);boundaries=sorted(set([0,len(a)]+[v for s,n,_,_ in mips for v in (s,s+n)]))
            spans=[]
            for l,r in zip(boundaries,boundaries[1:]):
                if a[l:r]==b[l:r]:spans.append(('equal',l,r,l,r))
                else:spans.append(('replace',l,r,l,r))
        ops=[]
        for op,l,r,x,y in spans:
            if op=='equal':ops.append(b'\0'+struct.pack('<II',l,r-l))
            elif y>x:ops.append(b'\1'+struct.pack('<I',y-x)+b[x:y])
        out+=string(source)+string(target)+hashlib.sha256(a).digest()+hashlib.sha256(b).digest()
        out+=struct.pack('<III',len(a),len(b),len(ops))+b''.join(ops)
    return bytes(out)

def main():
    OUT.mkdir(parents=True,exist_ok=True);es=index();paint=maps();entries={};records=[];manifest=[];parameters=[]
    for template,new,parameter in TEMPLATES:
        source=next(n for n in es if n.endswith('/'+template+'.uasset'));a=asset(es[source])
        newpath,b,mips=bake_texture(a,new,parameter,paint)
        target='Deadlock/Content/'+newpath.removeprefix('/Game/')+'.uasset'
        entries[target]=b;records.append((source,target,a,b));parameters.append((parameter,newpath,newpath.rsplit('/',1)[1]))
        manifest.append(dict(source=source,target=target,mips=mips,original_sha256=hashlib.sha256(a).hexdigest(),new_sha256=hashlib.sha256(b).hexdigest()))
    a=asset(es[MATERIAL]);p=Package(a)
    p.scalar('BaseColor_Blend',0);p.scalar('Roughness_Strength',0.8)
    p.add_texture_parameters(parameters)
    p.add_scalar_parameters([('UTiling_Color',4),('VTiling_Color',4),('UTiling_Normal',4),('VTiling_Normal',4),('Roughness_Blend',1)])
    b=p.encode();Package(b);entries[MATERIAL]=b;records.append((MATERIAL,MATERIAL,a,b))
    write_pak(entries,OUT/'material-only.pak')
    pack=recipe(records);(OUT/'material.bin').write_bytes(pack)
    manifest.append(dict(source=MATERIAL,target=MATERIAL,original_sha256=hashlib.sha256(a).hexdigest(),new_sha256=hashlib.sha256(b).hexdigest()))
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Built',len(entries),'isolated material assets; recipe bytes',len(pack),'SHA256',hashlib.sha256(pack).hexdigest())

if __name__=='__main__':main()
