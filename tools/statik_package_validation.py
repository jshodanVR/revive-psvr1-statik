"""Narrow packaging exception for the authored Statik material recipe.

All other .bin/game files stay forbidden. The recipe must match the builder
shipped in the same archive, not whichever builder happens to be installed.
"""
import hashlib
import re
import struct
import json

MATERIAL_RECIPE='tools/assets/statik-enhanced-material.bin'

def authored_material_recipe(name,data,builder):
    if name!=MATERIAL_RECIPE:return False
    if not 12<=len(data)<=128*1024*1024:raise ValueError('Invalid material recipe size')
    magic=data[:8];count=struct.unpack_from('<I',data,8)[0]
    if not ((magic==b'STATIKM3' and count==4) or (magic==b'STATIKM4' and 4<=count<=256)):
        raise ValueError('Invalid material recipe header')
    hashes=re.findall(rb'public const string MaterialPackHash\s*=\s*"([0-9A-Fa-f]{64})"',builder)
    if len(hashes)!=1 or hashlib.sha256(data).hexdigest()!=hashes[0].decode().lower():
        raise ValueError('Material recipe does not match packaged builder')
    return True

HEIGHT_SOURCES={
    'tools/assets/statik-paint-height.png':'25a2de57c712e63f2356923c4f682f788a242d85daf9a0843d5cac715bf66ea1',
    'tools/assets/statik-metal-height.png':'1deab0de7177cd2788d6a060ab54faa8092eaf65e8a4c598b94d599ee285bf28',
    'tools/assets/statik-fabric-height.png':'f0d928699107b63b208f56c38bce6ea098e8749db79dfb934ade7cad159b1a8c',
}

def reviewed_enhanced_source(name,data,builder):
    """Allow only these authored assets in the reproducible source snapshot."""
    if name==MATERIAL_RECIPE:return authored_material_recipe(name,data,builder)
    if name in HEIGHT_SOURCES:
        if hashlib.sha256(data).hexdigest()!=HEIGHT_SOURCES[name]:
            raise ValueError('Authored height source changed; review before packaging')
        return True
    if name in ('tools/assets/statik-surfaces-manifest.json','tools/assets/statik-surfaces-provenance.json'):
        if len(data)>512*1024:raise ValueError('Oversized surface source metadata')
        value=json.loads(data)
        if name.endswith('manifest.json'):
            if not isinstance(value,list) or not all(isinstance(x,dict) and x.get('kind') in ('texture','material','coverage') for x in value):
                raise ValueError('Invalid surface source manifest')
        elif not isinstance(value,dict) or value.get('mode')!='built-in ImageGen':
            raise ValueError('Invalid authored source provenance')
        return True
    return False
