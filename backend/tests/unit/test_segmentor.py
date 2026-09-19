from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from src.ml.onnx_segmentor import ONNXSegmentor
from src.ml.dataset_pipeline import CLASSES


def make_segmentor(names):
    session = SimpleNamespace(
        get_inputs=lambda: [SimpleNamespace(name="images")],
        get_modelmeta=lambda: SimpleNamespace(custom_metadata_map={"names": names}),
    )
    with patch("src.ml.onnx_segmentor.ort.InferenceSession", return_value=session):
        return ONNXSegmentor("unused.onnx")


@pytest.mark.parametrize("class_id", range(10))
def test_exported_class_id_is_preserved_in_detection(class_id):
    segmentor = make_segmentor(repr(dict(reversed(list(CLASSES.items())))))
    prediction = np.zeros((1, 4 + len(CLASSES) + 2, 1), dtype=np.float32)
    prediction[0, :4, 0] = [32, 32, 32, 32]
    prediction[0, 4 + class_id, 0] = 0.95
    prediction[0, 4 + len(CLASSES):, 0] = 1.0
    proto = np.ones((1, 2, 16, 16), dtype=np.float32)

    results = segmentor.postprocess([prediction, proto], (64, 64), 1, (0, 0))

    assert len(results) == 1
    assert results[0]["class_id"] == class_id
    assert results[0]["class_name"] == CLASSES[class_id]


def test_class_count_is_taken_from_model():
    segmentor = make_segmentor('{"1": "second", "0": "first"}')
    prediction = np.zeros((1, 7, 1), dtype=np.float32)
    prediction[0, :, 0] = [32, 32, 32, 32, 0.01, 0.95, 1]
    proto = np.ones((1, 1, 16, 16), dtype=np.float32)
    result = segmentor.postprocess([prediction, proto], (64, 64), 1, (0, 0))
    assert result[0]["class_name"] == "second"


def test_list_metadata():
    assert make_segmentor('["rice", "banana"]').classes == ["rice", "banana"]


@pytest.mark.parametrize("names", [None, "", "not metadata", "{}", '{1: "rice"}',
                                   '{0: ""}', '{0: 123}', '{True: "rice"}'])
def test_invalid_metadata_is_rejected(names):
    with pytest.raises(ValueError, match="ONNX"):
        make_segmentor(names)


def test_output_class_count_mismatch_is_rejected():
    segmentor = make_segmentor('["rice"]')
    with pytest.raises(ValueError, match="채널 수"):
        segmentor.postprocess(
            [np.zeros((1, 46, 2)), np.zeros((1, 32, 16, 16))],
            (64, 64), 1, (0, 0),
        )


@pytest.mark.parametrize("shape", [
    (320, 640), (640, 320), (640, 640),
    (333, 640), (640, 333), (666, 1280),
])
def test_letterbox_mask_restores_original_coordinates(shape):
    segmentor = make_segmentor('["rice"]')
    h, w = shape
    _, scale, (pad_x, pad_y) = segmentor.preprocess(np.zeros((h, w, 3), dtype=np.uint8))
    resized_h, resized_w = int(h * scale), int(w * scale)
    prediction = np.zeros((1, 6, 1), dtype=np.float32)
    # Full-image box prevents box cropping from hiding an incorrect mask transform.
    prediction[0, :, 0] = [pad_x + resized_w / 2, pad_y + resized_h / 2,
                           resized_w, resized_h, 0.95, 1]
    proto = np.full((1, 1, 160, 160), -10, dtype=np.float32)
    proto[0, 0, 65:85, 70:90] = 10
    results = segmentor.postprocess([prediction, proto], shape, scale, (pad_x, pad_y))

    assert len(results) == 1
    mask = results[0]["mask"]
    assert mask.shape == shape
    assert mask.dtype == np.uint8
    # Known rectangle in the padded input: x=[280,360), y=[260,340).
    x1, x2 = (np.array([280, 360]) - pad_x) * w / resized_w
    y1, y2 = (np.array([260, 340]) - pad_y) * h / resized_h
    yy, xx = np.indices(shape)
    expected = (xx + 0.5 >= x1) & (xx + 0.5 < x2) & (yy + 0.5 >= y1) & (yy + 0.5 < y2)
    intersection = np.count_nonzero((mask > 0) & expected)
    union = np.count_nonzero((mask > 0) | expected)
    assert intersection / union > 0.97
    assert results[0]["mask_pixel_count"] == np.count_nonzero(mask)


@pytest.mark.parametrize("shape", [(320, 640), (640, 320)])
def test_letterbox_padding_does_not_become_food(shape):
    segmentor = make_segmentor('["rice"]')
    h, w = shape
    _, scale, pad = segmentor.preprocess(np.zeros((h, w, 3), dtype=np.uint8))
    prediction = np.zeros((1, 6, 1), dtype=np.float32)
    prediction[0, :, 0] = [320, 320, 640, 640, 0.95, 1]
    proto = np.full((1, 1, 160, 160), -10, dtype=np.float32)
    if h < w:
        proto[0, 0, :30, :] = 10
    else:
        proto[0, 0, :, :30] = 10
    assert segmentor.postprocess([prediction, proto], shape, scale, pad) == []


def test_different_classes_do_not_suppress_each_other():
    segmentor = make_segmentor('["rice", "banana"]')
    prediction = np.zeros((1, 7, 2), dtype=np.float32)
    prediction[0, :4, :] = np.array([[32, 32, 32, 32], [32, 32, 32, 32]]).T
    prediction[0, 4, 0] = .95
    prediction[0, 5, 1] = .90
    prediction[0, 6, :] = 1
    results = segmentor.postprocess([prediction, np.ones((1, 1, 16, 16), np.float32)], (64, 64), 1, (0, 0))
    assert {r['class_name'] for r in results} == {'rice', 'banana'}


@pytest.mark.parametrize('shape', [(1, 2000), (2000, 1)])
def test_thin_images_keep_nonempty_letterbox_and_mask(shape):
    segmentor = make_segmentor('["rice"]')
    blob, scale, pad = segmentor.preprocess(np.zeros((*shape, 3), np.uint8))
    assert blob.shape == (1, 3, 640, 640)
    prediction = np.zeros((1, 6, 1), np.float32)
    prediction[0, :, 0] = [320, 320, 640, 640, .95, 1]
    results = segmentor.postprocess(
        [prediction, np.ones((1, 1, 160, 160), np.float32)], shape, scale, pad,
    )
    assert results[0]['mask'].shape == shape
    assert results[0]['mask_pixel_count'] == np.prod(shape)


def test_gpu_libraries_are_preloaded_before_session_creation():
    events = []
    session = SimpleNamespace(
        get_inputs=lambda: [SimpleNamespace(name="images")],
        get_modelmeta=lambda: SimpleNamespace(custom_metadata_map={"names": '["rice"]'}),
    )
    def preload(**kwargs):
        events.append("preload")
    def create(*args, **kwargs):
        assert events == ["preload"]
        assert kwargs["providers"][0] == "CUDAExecutionProvider"
        return session
    with patch("src.ml.onnx_segmentor.ort.preload_dlls", side_effect=preload, create=True), \
         patch("src.ml.onnx_segmentor.ort.get_available_providers", return_value=["CUDAExecutionProvider", "CPUExecutionProvider"]), \
         patch("src.ml.onnx_segmentor.ort.InferenceSession", side_effect=create):
        ONNXSegmentor("unused.onnx", use_cuda=True)


def test_cpu_path_does_not_load_gpu_libraries():
    with patch("src.ml.onnx_segmentor.ort.preload_dlls", create=True) as preload:
        make_segmentor('["rice"]')
    preload.assert_not_called()
