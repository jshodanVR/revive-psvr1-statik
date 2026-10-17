"""Build opt-in surface detail, retaining authored patterns and sensitive users.

Uses explicit material/texture allowlists. Original shared textures are never
overridden: only selected material name tables point to same-size private clones.
All other material bytes (shader, parameters, UVs, alpha/masks) remain identical.
"""
from pathlib import Path
from io import BytesIO
import importlib.util, hashlib, json, struct, re
import numpy as np
from PIL import Image
from statik_pak import index, asset
from statik_material_asset import Package, u32, i32, name_hash

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/statik-material-v4'
spec=importlib.util.spec_from_file_location('paint',Path(__file__).with_name('build-statik-material.py'))
paint=importlib.util.module_from_spec(spec);spec.loader.exec_module(paint)

# Explicitly reviewed physical surface families, excluding symbols, masks,
# bandages, coil geometry, blank controls, UV reveal maps and polished plain maps.
GROUPS={
 'plastic':['PlasticBase_D','PlasticBase_N','PlasticBase_R','GrainyPlastic_N','DirtyScratches_R'],
 'metal':['Painted_Metal_N','Steel_R','MetalBase_D','MetalBase_N','MetalFloor_D','MetalFloor_N','StylisedMetal_D'],
 'wood':['Plywood_01_D','Painted_Wood_N','Pinboard_01','PlanksWorn_01_D','PlanksWorn_01_N','PlanksWorn_01_R'],
 'fabric':['BasicFabric_D','BasicFabric_N','Canvas01_D'],
 'mineral':['Concrete_01_N','CheckerboardTiles_D_01','CheckerboardTiles_D_02','CheckerboardTiles_N_01','HospitalBrick_D_01','HospitalBrick_N_01'],
}
ROOTS={
 'Plastic':['MAT_Plastic_01','MAT_Device_Plastic','MAT_DevicePlastic_01','MAT_Device_Chassis','MAT_Chassi_Plastic_01','MAT_PuzzleBoxBase_Plastic','MAT_PuzzleBoxBase_Plastic02','MAT_PuzzleBoxBase_Plastic03'],
 'Metal':['Mat_Metal_Painted','Mat_Device_Painted','MAT_Device_Steel','MAT_Metal_Brushed_Steel','MAT_Metal_Brushed_Steel2','MAT_Metal_01','MAT_StylisedMetal_01'],
 'Wood':['MAT_Plywood_01','MAT_Plywood_02','MAT_Plywood_03','MAT_Plywood_04','MAT_BasicWood_01','MAT_Wood_Painted','MAT_Pinboard_01','MAT_PlanksWorn_01'],
 'Fabric':['MAT_BasicFabric_01','MAT_Fabric_Coated'],
 'Brick':['MAT_CheckerboardTiles_01','MAT_CheckerboardTiles_02','MAT_CheckerboardTiles_03','MAT_CheckerboardTiles_05','MAT_HospitalBrick_01','MAT_HospitalBrick_03'],
 'Concrete':['MAT_Concrete','MAT_Concrete_01'],
 'Wallpaper':['MAT_WallPaper_01'],
}
EXTRA_ROOTS=[
 'Environment/Furniture/MAT_FoldingChair_01',
 'Environment/Rooms/TheMainRoom/MAT_CheckerboardTiles_02',
 'Environment/Rooms/TheQuestionnaireRoom/Materials/MAT_QuestianareWalls_01',
 'Environment/Rooms/TheQuestionnaireRoom/Materials/MAT_QuestionareFloor_01',
 'Puzzles/Gyrophone/MAT_Device_Steel',
 'Puzzles/Labyrinth/MAT_Labyrinth_Plywood01',
 'Puzzles/Labyrinth/MAT_Labyrinth_Plywood02',
 'Puzzles/Questionnaire/MaterialsAndTextures/MAT_Device_Steel02',
 'Puzzles/RadioLocationv2/MAT_RadioL_Chassi_NoAO',
]
SENSITIVE=re.compile(r'UVReveal|UV_Reveal|Glow|Emissive|Screen|Monitor|Button|SliderSwitch|Painting|Hint|Note|Tag|Logo|Anonym|Particle|Lens|Glass',re.I)

def names(b):
    assert b[:8]==bytes.fromhex('c1832a9ef9ffffff')
    out=[];p=u32(b,45)
    for _ in range(u32(b,41)):
        n=i32(b,p);p+=4;assert 0<n<4096 and b[p+n-1]==0
        text=b[p:p+n-1].decode('ascii');assert u32(b,p+n)==name_hash(text)
        out.append((text,p,n));p+=n+4
    return out

def rename_refs(b,mapping):
    out=bytearray(b);changed=[]
    for text,pos,n in names(b):
        if text not in mapping:continue
        replacement=mapping[text];assert len(text)==len(replacement)
        out[pos:pos+n-1]=replacement.encode('ascii')
        struct.pack_into('<I',out,pos+n,name_hash(replacement));changed.append(text)
    assert len(out)==len(b)
    return bytes(out),changed

def parent(b):
    # The parent property of an instance is independent of its shader data.
    try:
        p=Package(b);props,_=p.properties();q=next((q for q in props if q['name']=='Parent'),None)
        if not q:return None
        ref=i32(p.payload,q['data']);assert ref<0
        imp=p.imports[-ref-1];outer=i32(imp,16);assert outer<0
        package=p.names[u32(p.imports[-outer-1],20)]
        return 'Deadlock/Content/'+package.removeprefix('/Game/')+'.uasset'
    except (AssertionError,IndexError,struct.error,ValueError):return None

def material_properties(b):
    p=Package.__new__(Package);p.names=[x[0] for x in names(b)]
    eo=u32(b,61);io=u32(b,69);ref=i32(b,eo);assert ref<0
    kind=p.names[u32(b,io+(-ref-1)*28+20)]
    assert kind=='Material',kind
    size,at=struct.unpack_from('<II',b,eo+28);p.payload=b[at:at+size]
    props,_=p.properties()
    # Omitted properties use UE's opaque/default-lit surface defaults.
    for q in props:
        if q['name'] in ('BlendMode','MaterialDomain','ShadingModel'):
            raise AssertionError('Nondefault surface model: '+q['name'])
    return props

def height(family,size,stem=''):
    source='metal' if family in ('metal','wood') else 'fabric' if family=='fabric' else 'paint'
    if 'Pinboard' in stem:source='paint'
    im=Image.open(ROOT/f'tools/assets/statik-{source}-height.png').convert('L').resize((256,256),Image.Resampling.LANCZOS)
    if 'PlanksWorn' in stem:im=im.transpose(Image.Transpose.ROTATE_90)
    a=paint.periodic(np.asarray(im,dtype=np.float32)/255)
    # Remove low-frequency generated shading: use it only as microstructure.
    from numpy.fft import fft2,ifft2,fftfreq
    fy,fx=np.meshgrid(fftfreq(256),fftfreq(256),indexing='ij')
    a-=ifft2(fft2(a)*np.exp(-2*np.pi**2*3**2*(fx*fx+fy*fy))).real
    a/=max(a.std(),1e-6);a=np.clip(a,-2.5,2.5)
    # Common UV field for every linked map, independent of source resolution.
    return resample(a,size)

def resample(a,size):
    mode=Image.Resampling.BILINEAR if size[0]>a.shape[1] or size[1]>a.shape[0] else Image.Resampling.BOX
    return np.asarray(Image.fromarray(a.astype(np.float32)).resize(size,mode))

def decode(b,mip,fmt):
    start,size,w,h=mip;normal=fmt=='PF_BC5';linear=paint.tiling(b[start:start+size],w,h,16 if normal else 8,True)
    im=Image.frombytes('RGB' if normal else 'RGBA',(w,h),linear,'bcn',5 if normal else 1)
    if not normal:assert im.getchannel('A').getextrema()==(255,255),'Nonopaque surface excluded'
    return np.asarray(im).copy(),linear

def clone_texture(original,path,family):
    base=Path(path).stem;new=('E'+hashlib.sha256(path.encode()).hexdigest()[:9]).ljust(len(base),'_')
    package='/Game/'+path.removeprefix('Deadlock/Content/')[:-7]
    target=path.rsplit('/',1)[0]+'/'+new+'.uasset';newpackage=package.rsplit('/',1)[0]+'/'+new
    b,renamed=rename_refs(original,{base:new,package:newpackage});assert len(renamed)==2
    b=bytearray(b);fmt,mips=paint.mip_layout(original);top,linear=decode(original,mips[0],fmt)
    w,h=mips[0][2:];field=height(family,(w,h),base)
    normal=fmt=='PF_BC5';rough=base.endswith('_R')
    amp={'plastic':.035,'metal':.022,'wood':.015,'fabric':.020,'mineral':.008}[family]
    # Preserve macro geometry, veins, weave, joints, scratches and base colors.
    if normal:
        fieldsmall=height(family,(256,256),base)
        detail=np.stack((-(np.roll(fieldsmall,-1,1)-np.roll(fieldsmall,1,1)),np.roll(fieldsmall,-1,0)-np.roll(fieldsmall,1,0)),axis=2)*amp
    else:
        rgb=top[:,:,:3].astype(np.float32)/255
        if rough:
            assert np.max(np.ptp(rgb,axis=2))<.045,'Packed/non-grayscale map excluded'
            targetrgb=np.clip(rgb+field[:,:,None]*.009,0,1)
        else:
            lin=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
            lin*=1+field[:,:,None]*.018
            targetrgb=np.where(lin<=.0031308,lin*12.92,1.055*np.maximum(lin,0)**(1/2.4)-.055)
        targetrgb=np.clip(targetrgb,0,1)
    metrics=[]
    for level,mip in enumerate(mips):
        start,size,mw,mh=mip;old,_=decode(original,mip,fmt)
        # Fade microdetail into the original lower mips, including the artist's
        # original mip normals. Tiny distant levels remain byte-identical.
        if min(mw,mh)<64:
            metrics.append({'level':level,'width':mw,'height':mh,'unchanged':True,'alpha_unchanged':True});continue
        fade=min(1.,min(mw,mh)/256.)
        if normal:
            xy=old[:,:,:2].astype(np.float32)/127.5-1
            z=np.sqrt(np.maximum(1-np.sum(xy*xy,axis=2),.001));slope=xy/np.maximum(z[:,:,None],.15)
            filtered=np.stack([resample(detail[:,:,c],(mw,mh)) for c in range(2)],axis=2)
            # No detail on steep authored edges, panel joints or seams.
            slope+=filtered*np.clip((z-.8)/.2,0,1)[:,:,None]*fade
            n=np.dstack((slope,np.ones_like(z)));n/=np.linalg.norm(n,axis=2,keepdims=True)
            pixels=np.uint8(np.clip(np.rint((n*.5+.5)*255),0,255));codec='BC5'
        else:
            # Apply only the filtered *delta* to the authored mip, preserving its
            # artist-generated mip appearance instead of regenerating it.
            delta=targetrgb-top[:,:,:3].astype(np.float32)/255
            delta=np.stack([paint.resize_float(delta[:,:,c],(mw,mh)) for c in range(3)],axis=2)
            pixels=np.uint8(np.clip(np.rint(old[:,:,:3]+delta*255*fade),0,255));codec='DXT1'
        stream=BytesIO();Image.fromarray(pixels).save(stream,format='DDS',pixel_format=codec)
        linear=stream.getvalue()[148 if normal else 128:]
        if not normal:
            check=Image.frombytes('RGBA',(mw,mh),linear,'bcn',1)
            assert check.getchannel('A').tobytes()==old[:,:,3].tobytes()
        tiled=paint.tiling(linear,mw,mh,16 if normal else 8);assert len(tiled)==size
        assert paint.tiling(tiled,mw,mh,16 if normal else 8,True)==linear
        b[start:start+size]=tiled;metrics.append({'level':level,'width':mw,'height':mh,'unchanged':False,'alpha_unchanged':True})
    newpixels,_=decode(b,mips[0],fmt)
    before=Image.fromarray(top[:,:,:3]);after=Image.fromarray(newpixels[:,:,:3])
    before.save(OUT/(base+'-before.png'));after.save(OUT/(base+'-after.png'))
    return target,bytes(b),{base:new,package:newpackage},metrics

def make_recipe(records):
    def string(s):b=s.encode()+b'\0';return struct.pack('<I',len(b))+b
    out=bytearray(b'STATIKM4'+struct.pack('<I',len(records)))
    for source,target,a,b in records:
        if len(a)!=len(b):
            # Only the already-tested introductory instance grows.
            assert source==paint.MATERIAL
            spans=__import__('difflib').SequenceMatcher(None,a,b,autojunk=False).get_opcodes()
            ops=[b'\0'+struct.pack('<II',l,r-l) if op=='equal' else b'\1'+struct.pack('<I',y-x)+b[x:y] for op,l,r,x,y in spans if op=='equal' or y>x]
        else:
            # Byte runs, coalesced across short equal gaps, give linear complexity.
            changed=np.flatnonzero(np.frombuffer(a,np.uint8)!=np.frombuffer(b,np.uint8));ops=[];cursor=0
            if len(changed):
                cuts=np.flatnonzero(np.diff(changed)>64)+1
                for run in np.split(changed,cuts):
                    lo,hi=int(run[0]),int(run[-1])+1
                    if lo>cursor:ops.append(b'\0'+struct.pack('<II',cursor,lo-cursor))
                    # Ship a delta against the verified original, not a complete
                    # recompressed copy of the game's color/normal texture data.
                    delta=np.bitwise_xor(np.frombuffer(a,np.uint8)[lo:hi],np.frombuffer(b,np.uint8)[lo:hi]).tobytes()
                    ops.append(b'\2'+struct.pack('<II',lo,hi-lo)+delta);cursor=hi
            if cursor<len(a):ops.append(b'\0'+struct.pack('<II',cursor,len(a)-cursor))
        out+=string(source)+string(target)+hashlib.sha256(a).digest()+hashlib.sha256(b).digest()
        out+=struct.pack('<III',len(a),len(b),len(ops))+b''.join(ops)
    return bytes(out)

def select_materials(ix):
    # Read every material instance, including ones outside the Materials folder.
    parents={};material_data={}
    for path,e in ix.items():
        if path.startswith('Deadlock/Content/') and path.endswith('.uasset') and e['size']<8*1024*1024 and ('/MAT_' in path or '/Mat_' in path):
            a=asset(e)
            if b'MaterialInstanceConstant\0' not in a[:5000] and b'Material\0' not in a[:5000]:continue
            material_data[path]=a;p=parent(a)
            if p:parents[path]=p
    selected={f'Deadlock/Content/Materials/{folder}/{n}.uasset' for folder,ns in ROOTS.items() for n in ns}
    selected|={f'Deadlock/Content/{n}.uasset' for n in EXTRA_ROOTS}
    missing=selected-set(material_data);assert not missing,missing
    for path in selected:material_properties(material_data[path])
    while True:
        new={p for p,par in parents.items() if par in selected}
        if new<=selected:break
        selected|=new
    risky=[p for p in selected if SENSITIVE.search(Path(p).stem)]
    assert not risky,('Unsafe descendant of selected root',risky)
    return material_data,selected

def main():
    OUT.mkdir(parents=True,exist_ok=True);ix=index()
    material_data,selected=select_materials(ix)
    paint.main()
    baseline=index(paint.OUT/'material-only.pak');oldmanifest=json.loads((paint.OUT/'manifest.json').read_text())
    sources={m['target']:m['source'] for m in oldmanifest};entries={n:asset(e,paint.OUT/'material-only.pak') for n,e in baseline.items()}
    records=[(sources[n],n,asset(ix[sources[n]]),b) for n,b in entries.items()]
    textures=[];mapping={};manifest=[]
    for family,stems in GROUPS.items():
        for stem in stems:
            path=next(n for n in ix if n.startswith('Deadlock/Content/Materials/') and n.endswith('/TEX_'+stem+'.uasset'))
            a=asset(ix[path]);target,b,m,levels=clone_texture(a,path,family)
            mapping.update(m);textures.append((path,target,a,b));manifest.append(dict(kind='texture',family=family,source=path,target=target,mips=levels))
            print('Baked',stem,flush=True)
    used=set();material_count=0
    for path in sorted(selected):
        if path==paint.MATERIAL:continue # Keep the approved v3 paint trial.
        a=material_data[path];b,changed=rename_refs(a,mapping)
        if not changed:continue
        used.update(changed);entries[path]=b;records.append((path,path,a,b));material_count+=1
        manifest.append(dict(kind='material',source=path,target=path,rebound_names=changed))
    for path,target,a,b in textures:
        package='/Game/'+path.removeprefix('Deadlock/Content/')[:-7]
        if package not in used:
            manifest=[m for m in manifest if m['target']!=target];continue
        entries[target]=b;records.append((path,target,a,b))
    for m in manifest:
        record=next(r for r in records if r[1]==m['target'])
        m.update(original_sha256=hashlib.sha256(record[2]).hexdigest(),new_sha256=hashlib.sha256(record[3]).hexdigest())
    manifest.append(dict(kind='coverage',selected_materials=len(selected),rebound_materials=material_count,
                         inherited_materials=sorted(selected),excluded_policy=SENSITIVE.pattern))
    pack=make_recipe(records);(OUT/'material.bin').write_bytes(pack)
    paint.write_pak(entries,OUT/'surfaces-only.pak')
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Surface textures',sum(m.get('kind')=='texture' for m in manifest),'rebound materials',material_count,'eligible family members',len(selected),flush=True)
    print('Recipe records',len(records),'bytes',len(pack),'SHA256',hashlib.sha256(pack).hexdigest(),flush=True)

if __name__=='__main__':main()
