from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from statik_package_validation import MATERIAL_RECIPE,authored_material_recipe,reviewed_enhanced_source,HEIGHT_SOURCES
root=Path(__file__).resolve().parents[2]
data=(root/MATERIAL_RECIPE).read_bytes();builder=(root/'tools/StatikEnhanced.cs').read_bytes()
assert authored_material_recipe(MATERIAL_RECIPE,data,builder)
for other in ('eboot.bin','tools/assets/other.bin','games/Statik/eboot.bin','../'+MATERIAL_RECIPE):
    assert not authored_material_recipe(other,data,builder)
for bad,source in ((data+b'!',builder),(data,b''),(b'STATIKM4'+bytes(4),builder)):
    try:authored_material_recipe(MATERIAL_RECIPE,bad,source)
    except ValueError:pass
    else:raise AssertionError('Invalid recipe accepted')
print('PASS: Only the exact authored recipe path with matching packaged-builder hash is exempt from the binary-file ban.')
for name in [*HEIGHT_SOURCES,'tools/assets/statik-surfaces-manifest.json','tools/assets/statik-surfaces-provenance.json',MATERIAL_RECIPE]:
    assert reviewed_enhanced_source(name,(root/name).read_bytes(),builder)
assert not reviewed_enhanced_source('tools/assets/unknown.png',b'anything',builder)
try:reviewed_enhanced_source(next(iter(HEIGHT_SOURCES)),b'changed image',builder)
except ValueError:pass
else:raise AssertionError('Unreviewed image accepted')
print('PASS: Reproducible source snapshots accept the exact reviewed authoring assets and reject unrelated or modified images.')
