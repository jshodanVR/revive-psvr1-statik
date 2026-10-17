# Builds a local texture-only Unreal patch from the user's verified Statik asset.
# The original game PAK is opened read-only. No original game asset is distributed.
function Install-StatikControlsGuide([string]$Game, [string]$Payload = '', [string]$Destination = '') {
    if (!$Payload) { $Payload = Join-Path $PSScriptRoot 'assets\statik-controls.bc1' }
    if (!(Test-Path -LiteralPath $Payload)) { throw 'Statik controls texture is missing from tools/assets.' }
    $pakFolder = Join-Path (Split-Path -Parent $Game) 'deadlock\content\paks'
    if (!$Destination) { $Destination = Join-Path $pakFolder 'revivepsvr1-controls_P.pak' }
    if (!('RevivePSVR1.StatikControlsPak' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Text;
using System.Security.Cryptography;
namespace RevivePSVR1 {
public static class StatikControlsPak {
    const string AssetName = "Deadlock/Content/Puzzles/VRSync/TEX_Controller_Options_02.uasset";
    const string AssetHash = "E02AF630CE59223A2C244F67F37893B57F9225C04CF236C61278D0F805715E55";
    static byte[] Read(BinaryReader r, int size) {
        byte[] b=r.ReadBytes(size); if(b.Length!=size) throw new InvalidDataException("Short PAK read"); return b;
    }
    static string FString(BinaryReader r) {
        int n=r.ReadInt32(); if(n<=0 || n>4096) throw new InvalidDataException("Unsupported PAK string");
        byte[] b=Read(r,n); if(b[n-1]!=0) throw new InvalidDataException("Invalid PAK string");
        return Encoding.UTF8.GetString(b,0,n-1);
    }
    static void FString(BinaryWriter w,string s) { byte[] b=Encoding.UTF8.GetBytes(s); w.Write(b.Length+1); w.Write(b); w.Write((byte)0); }
    static byte[] SHA1(byte[] b) { using(var h=System.Security.Cryptography.SHA1.Create()) return h.ComputeHash(b); }
    static string SHA256(byte[] b) { using(var h=System.Security.Cryptography.SHA256.Create()) return BitConverter.ToString(h.ComputeHash(b)).Replace("-",""); }
    static bool Equal(byte[] a,byte[] b) { if(a.Length!=b.Length)return false; for(int i=0;i<a.Length;i++)if(a[i]!=b[i])return false; return true; }
    static void Entry(BinaryWriter w,long size,byte[] hash) { w.Write(0L); w.Write(size); w.Write(size); w.Write(0); w.Write(hash); w.Write((byte)0); w.Write(0); }
    public static string Build(string source,string payload,string destination) {
        byte[] texture=File.ReadAllBytes(payload);
        if(texture.Length!=1048576) throw new InvalidDataException("Expected 2048x1024 BC1 texture");
        byte[] asset=null;
        using(var file=new FileStream(source,FileMode.Open,FileAccess.Read,FileShare.Read))
        using(var r=new BinaryReader(file)) {
            if(file.Length<44) throw new InvalidDataException("Incomplete PAK");
            file.Position=file.Length-44;
            if(r.ReadUInt32()!=0x5a6f12e1 || r.ReadInt32()!=3) throw new InvalidDataException("Unsupported Statik PAK version");
            long off=r.ReadInt64(),len=r.ReadInt64(); byte[] hash=Read(r,20);
            if(off<0 || len<0 || len>16777216 || off>file.Length-44-len) throw new InvalidDataException("Invalid PAK index range");
            file.Position=off; byte[] index=Read(r,(int)len);
            if(!Equal(SHA1(index),hash)) throw new InvalidDataException("PAK index hash mismatch");
            using(var ir=new BinaryReader(new MemoryStream(index))) {
                if(FString(ir)!="../../../") throw new InvalidDataException("Unsupported PAK mount");
                int count=ir.ReadInt32(); if(count<1 || count>100000) throw new InvalidDataException("Invalid PAK entry count");
                for(int i=0;i<count;i++) {
                    string name=FString(ir); long at=ir.ReadInt64(),stored=ir.ReadInt64(),unpacked=ir.ReadInt64(); int method=ir.ReadInt32();
                    byte[] entryHash=Read(ir,20); int blocks=0;
                    if(method!=0) { blocks=ir.ReadInt32(); if(blocks<0 || blocks>100000) throw new InvalidDataException("Invalid compression blocks"); Read(ir,checked(blocks*16)); }
                    byte encrypted=ir.ReadByte(); ir.ReadInt32();
                    if(name!=AssetName) continue;
                    if(asset!=null || method!=0 || encrypted!=0 || stored!=1049534 || stored!=unpacked || at<0 || at>off-53-stored)
                        throw new InvalidDataException("Unsupported controls asset layout");
                    file.Position=at+53; asset=Read(r,(int)stored);
                    if(!Equal(SHA1(asset),entryHash) || SHA256(asset)!=AssetHash) throw new InvalidDataException("Controls asset hash mismatch; original left unchanged");
                }
                if(ir.BaseStream.Position!=ir.BaseStream.Length) throw new InvalidDataException("Unexpected PAK index data");
            }
        }
        if(asset==null) throw new InvalidDataException("Statik controls asset was not found");
        // One PS4 BC1 mip in Morton 8x8 block order; all cooked headers remain unchanged.
        Buffer.BlockCopy(texture,0,asset,0x3aa,texture.Length);
        byte[] assetSha=SHA1(asset), pak;
        using(var stream=new MemoryStream()) using(var w=new BinaryWriter(stream)) {
            Entry(w,asset.Length,assetSha); w.Write(asset); long indexOffset=stream.Position;
            byte[] index;
            using(var ix=new MemoryStream()) using(var iw=new BinaryWriter(ix)) {
                FString(iw,"../../../"); iw.Write(1); FString(iw,AssetName); Entry(iw,asset.Length,assetSha); index=ix.ToArray();
            }
            w.Write(index); w.Write(0x5a6f12e1U); w.Write(3); w.Write(indexOffset); w.Write((long)index.Length); w.Write(SHA1(index)); pak=stream.ToArray();
        }
        if(File.Exists(destination) && Equal(File.ReadAllBytes(destination),pak)) return "Controls guide already current";
        string temp=destination+".tmp-"+Guid.NewGuid().ToString("N");
        try {
            File.WriteAllBytes(temp,pak);
            if(File.Exists(destination)) File.Replace(temp,destination,null); else File.Move(temp,destination);
        } finally { if(File.Exists(temp)) File.Delete(temp); }
        return "Installed local PCVR controls guide (original game PAK unchanged), SHA256="+SHA256(pak);
    }
}
}
'@
    }
    [RevivePSVR1.StatikControlsPak]::Build((Join-Path $pakFolder 'deadlock-ps4.pak'),$Payload,$Destination)
}
