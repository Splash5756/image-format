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

def convert(imgname):
    print("Creating /build")
    if not os.path.exists("./build"):
        os.mkdir("./build")

    print(f"reading {imgname}")
    img = Image.open(imgname).convert("RGBA")

    width, height = img.size

    pixels = list(img.getdata())

    print("creating palette")
    unique_colors = set(pixels)
    palette = list(unique_colors)

    p_bin = bytes([SE])

    indexs = {f"h_{i-1}": bytes([i]) for i in range(1,255)}
    indexs["h_253"] = bytes([0xfe,0x01])
    if len(palette) > 255:
        for i in range(254, len(palette)):
            n = int(i/253)
            x = bytes()
            for a in range(n):
                x += b"\xfe"
            n = i - (n*253)
            x += indexs[f"h_{n}"]
            indexs[f"h_{i}"] = x

    hexs = {f"h_{i}": bytes([i]) for i in range(254)}
    hexs["h_254"] = bytes([0xFE, 0x00])
    hexs["h_255"] = bytes([0xFE, 0x01])

    print("creating palette file")
    for i in palette:
        p_bin += indexs[f"h_{palette.index(i)}"] + hexs[f"h_{i[0]}"] + hexs[f"h_{i[1]}"] + hexs[f"h_{i[2]}"] + hexs[f"h_{i[3]}"] + bytes([SS])
    
    p_bin = p_bin[:-1]
    p_bin += bytes([SE])

    print("writing palette file")
    with open("./build/palette.bin","wb") as f:
        f.write(p_bin)

    print("creating chunks")
    rows = [pixels[i * width:(i + 1) * width] for i in range(height)]
    mrows = []
    for i in rows:
        l = bytes()
        for p in i:
            l += indexs[f"h_{palette.index(p)}"] + bytes([SS])
        mrows.append(bytes([SE])+l[:-1]+bytes([SE]))

    print("writing chunk files")
    for i in mrows:
        with open(f"./build/chunk{mrows.index(i)}.bin","wb") as f:
            f.write(i)

    print("generating hash file")    
    generate_hash()
    print("all packed")
    create_uncompressed_zip(output_zip="data.pack")
    print("Compressing the package")
    nm = imgname.split(".")[0]
    compress_with_zstd(input_file="data.pack",output_file=f"{nm}.pmg")
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

