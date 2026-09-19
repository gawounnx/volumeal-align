import zipfile
from pathlib import Path

fpath = Path('/workspace/aihub_extracted/122.음식_분류를_위한_음식종류_및_양에_따른_칼로리_데이터셋(재료,_양념,_완제품_등)/01.데이터/2.Validation/라벨링데이터/음식분류_라벨링_VAL_1223_add.zip.part0')

with zipfile.ZipFile(str(fpath), 'r') as z:
    for name in z.namelist():
        if name.endswith('.xml'):
            print(f"Sample XML file: {name}")
            content = z.read(name).decode('utf-8', errors='ignore')
            print("Content preview:")
            print(content[:1500])
            break
