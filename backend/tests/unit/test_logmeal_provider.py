import pytest

from src.core.exceptions import AppException
from src.services.food_recognition_provider import parse_logmeal_response


def test_parse_logmeal_response_normalizes_processed_coordinates_and_keeps_provider_id():
    results = parse_logmeal_response(
        {
            "processed_image_size": {"width": 500, "height": 400},
            "segmentation_results": [
                {
                    "contained_bbox": {"x": 100, "y": 80, "w": 200, "h": 160},
                    "polygon": [100, 80, 300, 80, 300, 240],
                    "recognition_results": [{"id": 1474, "name": "bibimbap", "prob": 0.91}],
                }
            ],
        },
        original_width=1000,
        original_height=800,
    )

    result = results[0]
    assert result.provider_item_id == "1474"
    assert result.confidence == pytest.approx(0.91)
    assert result.polygons[0][0].x == pytest.approx(0.2)
    assert result.polygons[0][0].y == pytest.approx(0.2)
    assert result.bbox.xmax == pytest.approx(0.6)
    assert result.bbox.ymax == pytest.approx(0.6)
    assert (result.processed_width, result.processed_height) == (500, 400)


def test_parse_logmeal_response_rejects_empty_segmentation():
    with pytest.raises(AppException) as error:
        parse_logmeal_response(
            {"processed_image_size": {"width": 500, "height": 400}, "segmentation_results": []},
            original_width=1000,
            original_height=800,
        )
    assert error.value.code == "ERR_FOOD_PROVIDER_EMPTY"