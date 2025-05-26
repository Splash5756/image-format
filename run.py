import convert
import parser
import render
import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Lütfen birlikte açılan dosyanın yolunu argüman olarak verin.")
        return

    file_path = sys.argv[1]

    if not os.path.isfile(file_path):
        print("Geçersiz dosya yolu.")
        return

    try:
        if file_path.lower().endswith(".pmg"):
            rawimg, width, height = parser.parse(file_path)
            if isinstance(rawimg, list):  # veya beklediğin tür
                render.main(width, height, rawimg)
            else:
                print("Resim çözümlenemedi.")
        else:
            convert.convert(file_path)
    except Exception as e:
        print("Bir hata oluştu:", e)

try:
    if __name__ == "__main__":
        main()
except Exception as e:
    print(e)