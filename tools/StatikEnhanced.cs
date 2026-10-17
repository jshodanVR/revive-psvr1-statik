// Builds an optional Unreal PAK from the user's verified original Statik files.
// Source assets remain untouched; the optional PAK can contain isolated paint maps.
using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;

public static class StatikEnhanced {
    public const string Revision = "surfaces-v4";
    public const string MaterialPackHash = "74726D7948C0AEACF52210AAC1931023BA29F9A491FDC55CE0879104B4431BDC";
    static readonly string[] Names = {
        "Deadlock/Config/DefaultEngine.ini", "Engine/Config/BaseDeviceProfiles.ini",
        "Deadlock/Content/Puzzles/IntroductionPuzzle/Materials/MAT_Gyrophone_Chassi_02.uasset"
    };
    static readonly string[] Expected = {
        "4D7B8990BAB887E7C19CA8EC1EC6CB47EB392ECE9C99449F683C5D3CFE4DE5A5",
        "ADDED81FCB52D17F13D6612A8104B267B22C374E0EA8D981935E6D96AF931DAF",
        "193213F50C185A188B590550AE5252531318976EB0452D94E3AC1BF41B20A357"
    };
    static byte[] Read(BinaryReader r, int n) {
        if(n<0 || n>32*1024*1024) throw new InvalidDataException("Unsupported PAK size");
        byte[] b=r.ReadBytes(n); if(b.Length!=n) throw new EndOfStreamException(); return b;
    }
    static string Str(BinaryReader r) {
        int n=r.ReadInt32(); if(n<1 || n>4096) throw new InvalidDataException("Invalid PAK string");
        byte[] b=Read(r,n); if(b[n-1]!=0) throw new InvalidDataException("Invalid PAK string");
        return Encoding.UTF8.GetString(b,0,n-1);
    }
    static void Str(BinaryWriter w,string s) { byte[] b=Encoding.UTF8.GetBytes(s); w.Write(b.Length+1); w.Write(b); w.Write((byte)0); }
    static byte[] Sha1(byte[] b) { using(var h=SHA1.Create()) return h.ComputeHash(b); }
    static string Sha256(byte[] b) { using(var h=SHA256.Create()) return BitConverter.ToString(h.ComputeHash(b)).Replace("-",""); }
    static bool Equal(byte[] a,byte[] b) { if(a.Length!=b.Length)return false; for(int i=0;i<a.Length;i++)if(a[i]!=b[i])return false; return true; }

    static byte[][] ReadSources(string path) {
        return ReadSources(path,Names,Expected);
    }
    static byte[][] ReadSources(string path,string[] names,string[] expected) {
        byte[][] result=new byte[names.Length][];
        using(var f=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read))
        using(var r=new BinaryReader(f)) {
            if(f.Length<44) throw new InvalidDataException("Incomplete Statik PAK");
            f.Position=f.Length-44;
            if(r.ReadUInt32()!=0x5a6f12e1 || r.ReadInt32()!=3) throw new InvalidDataException("Unsupported Statik PAK version");
            long off=r.ReadInt64(),size=r.ReadInt64(); byte[] sha=Read(r,20);
            if(off<0 || size<0 || size>32*1024*1024 || off!=f.Length-44-size) throw new InvalidDataException("Invalid PAK index bounds");
            f.Position=off;byte[] index=Read(r,(int)size);
            if(!Equal(Sha1(index),sha))throw new InvalidDataException("Statik PAK index checksum failed");
            using(var ir=new BinaryReader(new MemoryStream(index))) {
                if(Str(ir)!="../../../")throw new InvalidDataException("Unsupported PAK mount");
                int count=ir.ReadInt32();if(count<1 || count>100000)throw new InvalidDataException("Invalid PAK count");
                for(int i=0;i<count;i++) {
                    string name=Str(ir);long at=ir.ReadInt64(),stored=ir.ReadInt64(),unpacked=ir.ReadInt64();int method=ir.ReadInt32();byte[] entrySha=Read(ir,20);
                    if(method!=0) { int blocks=ir.ReadInt32();if(blocks<0 || blocks>100000)throw new InvalidDataException("Invalid PAK blocks");Read(ir,checked(blocks*16)); }
                    byte encrypted=ir.ReadByte();ir.ReadInt32();
                    int which=Array.IndexOf(names,name);if(which<0)continue;
                    if(result[which]!=null || method!=0 || encrypted!=0 || stored!=unpacked || stored<1 || stored>8*1024*1024 || at<0 || at>off-53-stored)
                        throw new InvalidDataException("Unsupported Enhanced source entry");
                    f.Position=at+53;byte[] data=Read(r,(int)stored);
                    if(!Equal(Sha1(data),entrySha) || Sha256(data)!=expected[which])
                        throw new InvalidDataException("Enhanced edition requires the verified original Statik assets; game files were not changed");
                    result[which]=data;
                }
                if(ir.BaseStream.Position!=ir.BaseStream.Length)throw new InvalidDataException("Unexpected PAK index data");
            }
        }
        foreach(byte[] b in result)if(b==null)throw new InvalidDataException("Missing Statik Enhanced source");
        return result;
    }
    static byte[] Engine(byte[] original) {
        string s=Encoding.UTF8.GetString(original);
        // SystemSettings has higher priority than the game's scalability presets.
        // Keep streaming and its existing memory budget enabled. No negative LOD bias.
        s+="\r\n; RevivePSVR1 Enhanced edition - "+Revision+"\r\n[SystemSettings]\r\nr.MaxAnisotropy=16\r\nr.Streaming.MipBias=0\r\nr.Streaming.Boost=1.5\r\n";
        return Encoding.UTF8.GetBytes(s);
    }
    static byte[] Profiles(byte[] original) {
        string s=Encoding.UTF8.GetString(original);
        // Color, normal and specular groups are changed together. Effects/UI,
        // shadow maps and render targets deliberately keep their authored filters.
        int changed=0;
        s=Regex.Replace(s,@"(?m)^\+?TextureLODGroups=\(Group=TEXTUREGROUP_(?:World|Character|Weapon)(?:NormalMap|Specular)?,[^\r\n]*",delegate(Match m) {
            if(!m.Value.Contains("MinMagFilter=aniso,MipFilter=point,"))throw new InvalidDataException("Unexpected texture group filter");
            changed++;return m.Value.Replace("MipFilter=point,","MipFilter=linear,");
        });
        if(changed!=9)throw new InvalidDataException("Expected nine matched material texture groups");
        return Encoding.UTF8.GetBytes(s);
    }
    static void Entry(BinaryWriter w,long offset,byte[] data) {
        w.Write(offset);w.Write((long)data.Length);w.Write((long)data.Length);w.Write(0);w.Write(Sha1(data));w.Write((byte)0);w.Write(0);
    }
    static byte[] IntroMaterial(byte[] original) {
        // This checksum-locked instance is used by SM_IntroPuzzle_Base_8 and
        // SM_Corner_3. Its parent chain reaches MAT_Chassi_Plastic_01. Change
        // only its existing Roughness_Strength scalar, not a shared parent,
        // texture reference, shader, color, specular, metallic or opacity value.
        // Verify the complete serialized NameProperty + FloatProperty tag too.
        byte[] tag = {
            21,0,0,0,0,0,0,0, 17,0,0,0,0,0,0,0, 8,0,0,0,0,0,0,0,0,
            25,0,0,0,0,0,0,0, 22,0,0,0,0,0,0,0, 11,0,0,0,0,0,0,0,
            4,0,0,0,0,0,0,0,0
        };
        const int at=1915;
        if(original.Length!=2621 || BitConverter.ToSingle(original,at)!=0.8f)
            throw new InvalidDataException("Unexpected introductory material scalar");
        for(int i=0;i<tag.Length;i++) if(original[at-tag.Length+i]!=tag[i])
            throw new InvalidDataException("Unexpected introductory material property");
        byte[] data=(byte[])original.Clone();
        Buffer.BlockCopy(BitConverter.GetBytes(0.55f),0,data,at,4);
        return data;
    }
    public static byte[] Build(string source) {
        return Build(source,true);
    }
    // The false variant is for controlled comparisons with identical filtering.
    // The public launcher's OFF path removes the whole managed PAK instead.
    public static byte[] Build(string source,bool material) {
        byte[][] data=ReadSources(source);data[0]=Engine(data[0]);data[1]=Profiles(data[1]);
        if(material)data[2]=IntroMaterial(data[2]);
        return WritePak(Names,data);
    }
    public static byte[] Build(string source,string materialPack) {
        // The recipe is shipped with the launcher. Its fixed hash prevents a
        // changed recipe from mounting arbitrary files or altering other assets.
        var info=new FileInfo(materialPack);
        if(!info.Exists || info.Length>128*1024*1024)throw new InvalidDataException("Missing or oversized Enhanced material pack");
        byte[] pack=File.ReadAllBytes(materialPack);
        if(Sha256(pack)!=MaterialPackHash)throw new InvalidDataException("Enhanced material pack checksum failed");
        var names=new List<string>(Names);var data=new List<byte[]>(ReadSources(source));
        data[0]=Engine(data[0]);data[1]=Profiles(data[1]);
        using(var r=new BinaryReader(new MemoryStream(pack))) {
            string magic=Encoding.ASCII.GetString(Read(r,8));int records=r.ReadInt32();
            if(magic!="STATIKM4" || records<4 || records>256)
                throw new InvalidDataException("Unsupported Enhanced material recipe");
            for(int record=0;record<records;record++) {
                string originalName=Str(r),target=Str(r);
                string originalHash=BitConverter.ToString(Read(r,32)).Replace("-","");
                byte[] expectedHash=Read(r,32);
                int oldSize=r.ReadInt32(),newSize=r.ReadInt32(),count=r.ReadInt32();
                if(oldSize<1 || oldSize>8*1024*1024 || newSize<1 || newSize>8*1024*1024 || count<1 || count>32768)
                    throw new InvalidDataException("Invalid Enhanced recipe bounds");
                byte[] original=ReadSources(source,new[]{originalName},new[]{originalHash})[0];
                if(original.Length!=oldSize)throw new InvalidDataException("Unexpected material source size");
                byte[] output=new byte[newSize];int cursor=0;
                for(int op=0;op<count;op++) {
                    byte type=r.ReadByte();int offset=type==0 || type==2?r.ReadInt32():0;int size=r.ReadInt32();
                    if(type>2 || size<0 || size>newSize-cursor || offset<0 || ((type==0 || type==2) && offset>oldSize-size))
                        throw new InvalidDataException("Invalid Enhanced recipe operation");
                    byte[] chunk=type==0?original:Read(r,size);
                    if(type==2) {
                        for(int j=0;j<size;j++)output[cursor+j]=(byte)(original[offset+j]^chunk[j]);
                    } else Buffer.BlockCopy(chunk,offset,output,cursor,size);
                    cursor+=size;
                }
                byte[] hash;using(var sha=SHA256.Create())hash=sha.ComputeHash(output);
                if(cursor!=newSize || !Equal(hash,expectedHash))throw new InvalidDataException("Enhanced material output did not verify");
                int at=names.IndexOf(target);
                if(at>=0)data[at]=output;else{names.Add(target);data.Add(output);}
            }
            if(r.BaseStream.Position!=r.BaseStream.Length)throw new InvalidDataException("Trailing Enhanced recipe data");
        }
        return WritePak(names.ToArray(),data.ToArray());
    }
    static byte[] WritePak(string[] names,byte[][] data) {
        using(var stream=new MemoryStream())using(var w=new BinaryWriter(stream)) {
            long[] offsets=new long[data.Length];
            for(int i=0;i<data.Length;i++){offsets[i]=stream.Position;Entry(w,0,data[i]);w.Write(data[i]);}
            long indexOffset=stream.Position;byte[] index;
            using(var ix=new MemoryStream())using(var iw=new BinaryWriter(ix)) {
                Str(iw,"../../../");iw.Write(names.Length);
                for(int i=0;i<names.Length;i++){Str(iw,names[i]);Entry(iw,offsets[i],data[i]);}
                index=ix.ToArray();
            }
            w.Write(index);w.Write(0x5a6f12e1U);w.Write(3);w.Write(indexOffset);w.Write((long)index.Length);w.Write(Sha1(index));return stream.ToArray();
        }
    }
}
