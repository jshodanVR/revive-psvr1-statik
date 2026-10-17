"""Read-only Statik PAK v3 reader; validates index and selected asset hashes."""
from pathlib import Path
import struct, io, hashlib

ROOT = Path(__file__).resolve().parents[1]
PAK = ROOT/'games/Statik-CUSA06929/uroot/deadlock/content/paks/deadlock-ps4.pak'

def read_exact(f,n):
    assert 0 <= n <= 64*1024*1024
    b=f.read(n)
    assert len(b)==n
    return b

def unpack(f,fmt):
    return struct.unpack(fmt,read_exact(f,struct.calcsize(fmt)))

def string(f):
    n,=unpack(f,'<i')
    assert 0<n<4096
    s=read_exact(f,n)
    assert s[-1]==0
    return s[:-1].decode('utf-8')

def index(path=PAK):
    with path.open('rb') as f:
        f.seek(-44,2)
        magic,version,offset,size,sha=unpack(f,'<IIqq20s')
        assert magic==0x5a6f12e1 and version==3
        assert offset>0 and offset+size==path.stat().st_size-44
        f.seek(offset); raw=read_exact(f,size)
    assert hashlib.sha1(raw).digest()==sha
    s=io.BytesIO(raw)
    assert string(s)=='../../../'
    count,=unpack(s,'<i')
    entries={}
    for _ in range(count):
        name=string(s)
        at,stored,size,method,sha=unpack(s,'<qqqI20s')
        blocks=[]
        if method:
            n,=unpack(s,'<i')
            assert 0<=n<=100000
            blocks=[unpack(s,'<qq') for i in range(n)]
        encrypted,blocksize=unpack(s,'<BI')
        assert at>=0 and at+stored<=offset
        entries[name]=dict(at=at,stored=stored,size=size,method=method,sha=sha,blocks=blocks,encrypted=encrypted)
    assert s.tell()==len(raw)
    return entries

def asset(entry,path=PAK):
    assert not entry['encrypted'] and entry['method']==0
    assert entry['stored']==entry['size']
    with path.open('rb') as f:
        f.seek(entry['at']+53)
        raw=read_exact(f,entry['size'])
    assert hashlib.sha1(raw).digest()==entry['sha']
    return raw

