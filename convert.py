# jpeg, png gibi fotoğraf formatlarını .pimg kodlamasına çevirir

# hex tanımlamaları
SE = 0x00
SS = 0xFF

MN = 0x70696D67

from PIL import Image
import os
import hashlib
import zipfile
import zstandard as zstd
import shutil

def rgba_to_int(r, g, b, a):
    return (r << 24) | (g << 16) | (b << 8) | a

def int_to_rgba(val):
    r = (val >> 24) & 0xFF
    g = (val >> 16) & 0xFF
    b = (val >> 8) & 0xFF
    a = val & 0xFF
    return (r, g, b, a)

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
                    r = 0  # overflow için istersen hata at
    return r, g, b, a

def create_ranges(sorted_colors):
    """
    sorted_colors: list of int (converted rgba)
    Returns list of (start_rgba_tuple, count)
    """
    ranges = []
    if not sorted_colors:
        return ranges

    start = sorted_colors[0]
    count = 1
    prev = start

    for current in sorted_colors[1:]:
        # increment prev color once
        r, g, b, a = int_to_rgba(prev)
        r2, g2, b2, a2 = increment_color(r, g, b, a)
        expected = rgba_to_int(r2, g2, b2, a2)

        if current == expected:
            # ardışık devam ediyor
            count += 1
        else:
            # aralık bitti, yeni aralık başlıyor
            ranges.append((int_to_rgba(start), count))
            start = current
            count = 1
        prev = current

    # son aralığı ekle
    ranges.append((int_to_rgba(start), count))
    return ranges

# Örnek kullanım:
def process_image(img_path):
    img = Image.open(img_path).convert("RGBA")
    pixels = list(img.getdata())

    unique_colors = sorted(set(pixels), key=lambda c: (c[0]<<24)|(c[1]<<16)|(c[2]<<8)|c[3])
    unique_ints = [rgba_to_int(*c) for c in unique_colors]

    ranges = create_ranges(unique_ints)
    return (ranges,unique_colors)

def write_palette_ranges(filename, ranges):
    with open(filename, "wb") as f:
        for start_rgba, count in ranges:
            f.write(bytes([0xFC]))  # range flag
            f.write(bytes(start_rgba))  # 4 byte başlangıç renk
            f.write(bytes([0xAB]))  # count flag
            f.write(bytes([count]))  # kaç renk
            f.write(bytes([0x00]))  # range sonu

def convert(imgname):
    print("Creating /build")
    if not os.path.exists("./build"):
        os.mkdir("./build")

    print(f"reading {imgname}")
    img = Image.open(imgname).convert("RGBA")
    width, height = img.size
    pixels = list(img.getdata())

    print("creating palette")
    ranges, unique_colors = process_image(imgname)
    unique_colors = list(dict.fromkeys(unique_colors))  # Ordered unique
    palette = unique_colors
    
    # 🔁 index map (uyumlu ve hızlı)
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

    # 🌈 Renk bileşeni encode map
    hexs = {}
    for i in range(256):
        if i == 254:
            hexs[i] = bytes([0xFE, 0x00])
        elif i == 255:
            hexs[i] = bytes([0xFE, 0x01])
        else:
            hexs[i] = bytes([i])

    # 🚀 Hızlı renk -> index eşleşmesi
    palette_lookup = {color: idx for idx, color in enumerate(palette)}

    print("creating palette file")
    #p_bin = bytearray([SE])
    #for color in palette:
    #    idx = palette_lookup[color]
    #    r, g, b, a = color
    #    p_bin += indexs[f"h_{idx}"] + hexs[r] + hexs[g] + hexs[b] + hexs[a] + bytes([SS])
    #p_bin = p_bin[:-1] + bytes([SE])  # last SS -> SE

    print("writing palette file")
    #with open("./build/palette.bin", "wb") as f:
    #    f.write(p_bin)
    write_palette_ranges("./build/palette.bin",ranges)

    print("creating chunks")

    # Satırları ayır
    rows = [pixels[i * width:(i + 1) * width] for i in range(height)]

    mrows = []
    for row in rows:
        l = bytearray()
        for p in row:
            idx = palette_lookup[p]
            l += indexs[f"h_{idx}"] + bytes([SS])
        mrows.append(bytes([SE]) + l[:-1] + bytes([SE]))

    print("writing chunk files")
    for idx, row in enumerate(mrows):
        with open(f"./build/chunk{idx}.bin", "wb") as f:
            f.write(row)

    print("generating hash file")    
    generate_hash()
    print("all packed")
    create_uncompressed_zip(output_zip="data.pack")
    print("Compressing the package")
    compress_with_zstd(input_file="data.pack",output_file=f"{imgname}.pmg")
    print("cleaning up")
    cleanup()

def generate_hash(build_dir="build", output_file="build/hash.bin"):
    #created by gpt idontknow how its working
    hasher = hashlib.sha256()

    # Dosya adlarını sıralı ve tutarlı şekilde işle
    bin_files = sorted(
        [f for f in os.listdir(build_dir) if f.endswith(".bin") and f != "hash.bin"]
    )

    for file_name in bin_files:
        file_path = os.path.join(build_dir, file_name)
        with open(file_path, "rb") as f:
            data = f.read()
            hasher.update(data)

    digest = hasher.digest()

    # SHA-256 çıktısını dosyaya yaz
    with open(output_file, "wb") as f:
        f.write(digest)

    print(f"SHA-256 hash created: {digest.hex()}")

def create_uncompressed_zip(source_dir="build", output_zip="data.pack"):
    #created by gpt
    with zipfile.ZipFile(output_zip, 'w', compression=zipfile.ZIP_STORED) as zipf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                path = os.path.join(root, file)
                arcname = os.path.relpath(path, start=source_dir)
                zipf.write(path, arcname=arcname)

def compress_with_zstd(input_file="data.pack", output_file="img.pmg", level=22):
    #created by gpt
    cctx = zstd.ZstdCompressor(level=level)

    with open(input_file, "rb") as fin, open(output_file, "wb") as fout:
        cctx.copy_stream(fin, fout)

def cleanup(build_dir="build", packed_file="data.pack"):
    if os.path.isdir(build_dir):
        try:
            shutil.rmtree(build_dir)
        except:
            pass

    for file in [packed_file]:
        if os.path.exists(file):
            os.remove(file)

