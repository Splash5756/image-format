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


def increment_color(r, g, b, a):
    a += 1
    if a > 0xFF:
        a = 0
        b += 1
        if b > 0xFF:
            b = 0
            g += 1
            if g > 0xFF:
                g = 0
                r += 1
                if r > 0xFF:
                    r = 0  # istersen buraya overflow için hata atabilirsin
    return r, g, b, a

def read_palette_ranges(filename):
    palette = []

    with open(filename, "rb") as f:
        data = f.read()

    i = 0
    while i < len(data):
        flag = data[i]
        i += 1

        if flag == 0xFC:
            start_rgba = data[i:i+4]
            i += 4

            count_flag = data[i]
            i += 1
            if count_flag != 0xAB:
                raise ValueError("Beklenen count flag 0xAB değil")

            count = data[i]
            i += 1

            end_flag = data[i]
            i += 1
            if end_flag != 0x00:
                raise ValueError("Beklenen end flag 0x00 değil")

            r, g, b, a = start_rgba
            for _ in range(count):
                palette.append((r, g, b, a))
                r, g, b, a = increment_color(r, g, b, a)

        else:
            raise ValueError(f"Beklenmeyen flag: {flag}")

    return palette

def readchunks(chunkcount, palette):
    rawpixels = []
    widths = []

    for i in range(chunkcount):
        path = f"cache\\chunk{i}.bin"
        with open(path, "rb") as f:
            data = f.read()
        if data.startswith(b"\x00") and data.endswith(b"\x00"):
            data = data[1:-1]
            pixelsdata = data.split(b"\xff")
            row = []

            for px in pixelsdata:
                if px in palette:
                    row.append(palette[px])
                else:
                    row.append((0, 0, 0, 255))  # Hatalı piksel için varsayılan renk
            rawpixels.extend(row)
            widths.append(len(row))
        else:
            return None, None

    return rawpixels, widths

from PIL import Image

def createimg(pixeldatas, widths, filename):
    height = len(widths)
    width = max(widths)

    img = Image.new("RGBA", (width, height))
    pixels_for_image = []

    current = 0
    for w in widths:
        row = pixeldatas[current:current + w]
        current += w
        if len(row) < width:
            row += [(0, 0, 0, 0)] * (width - len(row))  # Eksik pikselleri şeffaf yap
        pixels_for_image.extend(row)

    img.putdata(pixels_for_image)
    img.save(filename + ".png")
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
    palette = read_palette_ranges("cache/palette.bin")
    
    # Palette index encoder
    indexs = {}
    for idx in range(len(palette)):
        encoded = bytearray()
        n = idx
        while n >= 253:
            encoded.append(0xFE)
            n -= 253
        if n == 254:
            encoded.extend([0xFE, 0x00])
        elif n == 255:
            encoded.extend([0xFE, 0x01])
        else:
            encoded.append(n + 1)
        indexs[f"h_{idx}"] = bytes(encoded)

    # Lookup dictionary
    palette_lookup = {indexs[f"h_{idx}"]: color for idx, color in enumerate(palette)}

    # Pixel data
    rawdata, widths = readchunks(file_count - 2, palette_lookup)
    if rawdata is None:
        return "chunks damaged"

    #createimg(rawdata, widths, filename)
    cleanup()
    return (rawdata, max(widths), len(widths))
