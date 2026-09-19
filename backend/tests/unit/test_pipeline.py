from types import SimpleNamespace
import numpy as np
import pytest
from src.services.vision_pipeline import VisionPipelineOrchestrator
from src.core.exceptions import AppException

def recognition_stack(food_id="FOOD_TEST", score=.91, requires_confirmation=False):
    candidate=SimpleNamespace(food_id=food_id,score=score)
    match=SimpleNamespace(food_id=food_id,score=score,candidates=[candidate],
                          requires_confirmation=requires_confirmation)
    embedder=SimpleNamespace(encode=lambda crop:np.array([1.,0.],np.float32))
    retriever=SimpleNamespace(search=lambda embedding,top_k=3:match)
    nutrition=SimpleNamespace(
        food_name=lambda value:"시험 음식",
        calculate=lambda value,volume:{
            "foodId":value,"foodName":"시험 음식","densityGCm3":1.,
            "weightG":round(volume,2),"caloriesKcal":round(volume,2),
            "carbsG":round(volume*.2,2),"proteinG":round(volume*.03,2),
            "fatG":round(volume*.01,2),"sodiumMg":round(volume*.04,2),
            "interactionTags":["test"],
        },
    )
    return embedder,retriever,nutrition

def test_missing_metric_model_has_no_synthetic_fallback():
    pipeline=VisionPipelineOrchestrator(None,SimpleNamespace(session=None))
    with pytest.raises(AppException) as exc:
        pipeline.process_image(np.zeros((100,100,3),np.uint8))
    assert exc.value.status_code==503

def test_injected_pipeline_uses_depth_plane_and_food_specific_nutrition(tmp_path):
    mask=np.zeros((100,100),np.uint8);mask[40:60,40:60]=1
    depth=np.full((100,100),.6,np.float32);depth[mask.astype(bool)]=.55
    segmentor=SimpleNamespace(segment=lambda image,**kwargs:[{'class_name':'test_food','mask':mask,'confidence':.1,'box':[40,40,60,60]}])
    estimator=SimpleNamespace(session=object(),infer=lambda image:depth)
    embedder,retriever,nutrition=recognition_stack()
    pipeline=VisionPipelineOrchestrator(segmentor,estimator,patch_embedder=embedder,
        food_retriever=retriever,nutrition_service=nutrition,metric=True)
    result=pipeline.process_image(np.zeros((100,100,3),np.uint8),36)
    food=result['foodItems'][0]
    expected=400*(.6**3-.55**3)/(3*100*100)*1e6
    assert food['volumeCm3']==pytest.approx(expected,abs=.05)
    assert food['weightG']==food['caloriesKcal']
    assert food['requiresConfirmation'] is True
    assert len(food['bbox3d']['vertices'])==8
    cloud=result['visualization3d']['pointCloud']
    assert len(cloud['positions'])==cloud['count']*3
    assert 'test' in result['triggers'][food['id']]


def test_pills_are_excluded_from_plane_samples_and_nutrition(tmp_path):
    from src.ml.geometry_integrator import NumericalVolumeIntegrator
    from unittest.mock import Mock

    food = np.zeros((100, 100), np.uint8)
    food[40:60, 40:60] = 1
    pill = np.zeros_like(food)
    pill[:30, :30] = 1
    depth = np.full(food.shape, .6, np.float32)
    depth[food.astype(bool)] = .55
    depth[pill.astype(bool)] = .4
    detections = [
        dict(class_name='test_food', mask=food, confidence=.9, box=[40, 40, 60, 60]),
        dict(class_name='test_pill', mask=pill, confidence=.9, box=[0, 0, 30, 30]),
    ]
    embedder,retriever,nutrition=recognition_stack()
    geometry = NumericalVolumeIntegrator()
    geometry.fit_plane_ransac = Mock(return_value=({'a': 0, 'b': 0, 'c': 1, 'd': -.6}, 1))
    pipeline = VisionPipelineOrchestrator(
        SimpleNamespace(segment=lambda *args, **kwargs: detections),
        SimpleNamespace(session=object(), infer=lambda image: depth),
        patch_embedder=embedder,food_retriever=retriever,nutrition_service=nutrition,
        geometry_integrator=geometry,metric=True,
    )
    result = pipeline.process_image(np.zeros((100, 100, 3), np.uint8), 36)
    samples = geometry.fit_plane_ransac.call_args.args[0]
    assert len(samples) == 10000 - 400 - 900
    assert np.allclose(samples[:, 2], .6)
    assert [item['foodId'] for item in result['foodItems']] == ['FOOD_TEST']
    assert len(result['detectedPills']) == 1
    assert result['detectedPills'][0]['class_name'] == 'test_pill'


def test_pill_only_image_does_not_raise_zero_objects(tmp_path):
    from src.ml.geometry_integrator import NumericalVolumeIntegrator
    from unittest.mock import Mock

    pill = np.zeros((100, 100), np.uint8)
    pill[:30, :30] = 1
    depth = np.full((100, 100), .6, np.float32)
    depth[pill.astype(bool)] = .4
    detections = [
        dict(class_name='coumadin_pill', mask=pill, confidence=.95, box=[0, 0, 30, 30]),
    ]
    embedder, retriever, nutrition = recognition_stack()
    geometry = NumericalVolumeIntegrator()
    geometry.fit_plane_ransac = Mock(return_value=({'a': 0, 'b': 0, 'c': 1, 'd': -.6}, 1))
    pipeline = VisionPipelineOrchestrator(
        SimpleNamespace(segment=lambda *args, **kwargs: detections),
        SimpleNamespace(session=object(), infer=lambda image: depth),
        patch_embedder=embedder, food_retriever=retriever, nutrition_service=nutrition,
        geometry_integrator=geometry, metric=True,
    )
    result = pipeline.process_image(np.zeros((100, 100, 3), np.uint8), 36)
    assert result['foodItems'] == []
    assert len(result['detectedPills']) == 1
    assert result['detectedPills'][0]['class_name'] == 'coumadin_pill'
    assert result['totalNutrition']['caloriesKcal'] == 0
    assert result['visualization3d']['pointCloud']['count'] == 0



def test_detector_retriever_disagreement_requires_confirmation():
    mask = np.zeros((100, 100), np.uint8); mask[40:60, 40:60] = 1
    depth = np.full((100, 100), .6, np.float32); depth[mask.astype(bool)] = .55
    segmentor = SimpleNamespace(segment=lambda image, **kwargs: [{'class_name': 'banana', 'mask': mask, 'confidence': .92, 'box': [40, 40, 60, 60]}])
    estimator = SimpleNamespace(session=object(), infer=lambda image: depth)
    embedder, retriever, nutrition = recognition_stack(food_id='white_rice', score=.91)
    nutrition.catalog = {'white_rice': object(), 'banana': object()}
    names = {'white_rice': '백미밥', 'banana': '바나나'}
    nutrition.calculate = lambda value, volume: {'foodId': value, 'foodName': names[value], 'densityGCm3': 1., 'weightG': round(volume, 2), 'caloriesKcal': round(volume, 2), 'carbsG': 1., 'proteinG': 1., 'fatG': 1., 'sodiumMg': 1., 'interactionTags': []}
    pipeline = VisionPipelineOrchestrator(segmentor, estimator, patch_embedder=embedder, food_retriever=retriever, nutrition_service=nutrition, metric=True)
    item = pipeline.process_image(np.zeros((100, 100, 3), np.uint8), 36)['foodItems'][0]
    assert item['requiresConfirmation'] is True
    assert [row['foodId'] for row in item['topCandidates']][:2] == ['banana', 'white_rice']
