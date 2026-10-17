"""Convert the authored help PNG to the game's PS4 BC1/Morton layout (build-time only)."""
from pathlib import Path
from io import BytesIO
from PIL import Image

root = Path(__file__).resolve().parent
im = Image.open(root / 'assets/statik-controls.png').convert('RGB')
im = im.resize((2048, 1024), Image.Resampling.LANCZOS)
stream = BytesIO()
im.save(stream, format='DDS', pixel_format='DXT1')
dds = stream.getvalue()
assert dds[84:88] == b'DXT1' and len(dds) == 128 + 1048576
linear = dds[128:]
tiled = bytearray(len(linear))
for y in range(256):
    for x in range(512):
        morton = sum(((x >> i) & 1) << (2*i) | ((y >> i) & 1) << (2*i+1) for i in range(3))
        target = (((y // 8) * 64 + x // 8) * 64 + morton) * 8
        source = (y * 512 + x) * 8
        tiled[target:target+8] = linear[source:source+8]
(root / 'assets/statik-controls.bc1').write_bytes(tiled)
