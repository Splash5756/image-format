import io, zipfile, os
import zstandard as zstd
from PIL import Image
import shutil

def decompress_pmg(pmg_path):
    with open(pmg_path, "rb") as f:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(f) as reader:
            decompressed = reader.read()

    # Zip arşivini aç
    zip_bytes = io.BytesIO(decompressed)
    with zipfile.ZipFile(zip_bytes) as z:
        z.extractall("cache")

    return "cache"

def readhash():
    pass

def readpalette():
    path = "cache\\palette.bin"
    with open(path,"rb") as f:
        data = f.read()
    if data.startswith(bytes([0x00])) and data.endswith(bytes([0x00])):
        data = data[1:-1]
        colors = data.split(b"\xff")
        cache = b""
        cache2 = []
        palette = {}
        color_hexs = {bytes([i]): i for i in range(256)}
        for color in colors:
            # byte yapısı id,r,g,b,a şeklinde arada seperator yok ve fefexx fexx fexx gibi olabiliyor yani burada dönüştürmeyi fe olmayan bir değer dönene kadar okuyarak yapıcaz
            for byte in color:
                if bytes([byte]) != b"\xfe":
                    cache += bytes([byte])
                    cache2.append(cache)
                    cache = b""
                else:
                    cache += b"\xfe"
            for i in range(1,5):
                if len(cache2[i]) == 2:
                    if cache2[i] == b"\xfe\x00":
                        cache2[i] = b"\xfe"
                    elif cache2[i] == b"\xfe\x01":
                        cache2[i] = b"\xff"
            palette[cache2[0]] = str(color_hexs[cache2[1]]) + "," + str(color_hexs[cache2[2]]) + "," + str(color_hexs[cache2[3]]) + "," + str(color_hexs[cache2[4]])
            cache2 = []
        return palette
    else:
        return "file damaged"

def readchunks(chunkcount,palette):
    rawpixels = []
    for i in range(chunkcount):
        path = f"cache\\chunk{i}.bin"
        with open(path,"rb") as f:
            data = f.read()
        if data.startswith(b"\x00") and data.endswith(b"\x00"):
            data = data[1:-1]
            pixelsdata = data.split(b"\xff")

            for i in pixelsdata:
                try:
                    colordata = palette[i]
                except:
                    colordata = "0,0,0,255"
                spliteddata = colordata.split(",")
                for i in spliteddata:
                    spliteddata[spliteddata.index(i)] = int(i)
                pixelcolor = tuple(spliteddata)
                rawpixels.append(pixelcolor)
        else:
            return None
    return rawpixels

def createimg(pixeldatas,chunkcount,filename):
    img = Image.new("RGBA", (int(len(pixeldatas)/chunkcount), chunkcount))
    img.putdata(pixeldatas)
    img.save(filename+".png")
    img.show()

def cleanup():
    folderpath = "cache"
    if os.path.isdir(folderpath):
        try:
            shutil.rmtree(folderpath)
        except:
            pass

def parse(filename):
    decompress_pmg(filename)
    folder_path = "cache"
    file_count = sum(1 for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)))
    palette = readpalette()
    if type(palette) == str:
        return palette
    rawdata = readchunks(file_count-2,palette)
    if rawdata == None:
        return "chunks damaged"
    #createimg(rawdata,file_count-2,filename)
    cleanup()
    return (rawdata, int(len(rawdata)/(file_count-2)), (file_count-2))