import json
import pytest
from src.ml.dataset_pipeline import convert_coco_json_to_yolo

def test_unknown_coco_category_is_not_silently_mapped_to_rice(tmp_path):
    source=tmp_path/'source.json'
    source.write_text(json.dumps({'categories':[{'id':999,'name':'unknown-food'}],'images':[],'annotations':[]}))
    with pytest.raises(ValueError,match='COCO 클래스'):
        convert_coco_json_to_yolo(str(source),str(tmp_path),tmp_path/'out')

def test_category_id_is_resolved_by_name(tmp_path):
    source=tmp_path/'source.json'
    (tmp_path/'sample.jpg').write_bytes(b'test')
    source.write_text(json.dumps({'categories':[{'id':999,'name':'banana'}],
        'images':[{'id':1,'file_name':'sample.jpg','width':10,'height':10}],
        'annotations':[{'image_id':1,'category_id':999,'segmentation':[[0,0,5,0,5,5]]}]}))
    convert_coco_json_to_yolo(str(source),str(tmp_path),tmp_path/'out')
    assert (tmp_path/'out/labels/train/sample.txt').read_text().startswith('6 ')
