import io
import uuid
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock, MagicMock
import numpy as np
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from src.main import app
from src.api.deps import get_current_user
from src.core.database import get_db_session
from src.api.v1.endpoints.vision import get_pipeline
from src.core.exceptions import AppException, VolumeOutOfBoundsException
from src.schemas.vision import SparsePointCloudPayload
from src.services.geometry_integrator import GeometryIntegrator
from src.ml.geometry_integrator import NumericalVolumeIntegrator
from src.ml.onnx_segmentor import ONNXSegmentor

@pytest.fixture
def client():
    mock_db = AsyncMock(spec=AsyncSession)
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid.uuid4())
    app.dependency_overrides[get_db_session] = lambda: mock_db
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()

def png():
    stream = io.BytesIO()
    Image.new('RGB',(20,20)).save(stream,format='PNG')
    return stream.getvalue()

@pytest.mark.parametrize('data', [b'',b'invalid'])
def test_bad_upload_returns_422_without_loading_models(client,data):
    with patch('src.api.v1.endpoints.vision.get_pipeline') as model:
        response=client.post('/api/v1/vision/estimate',files={'file':('x.png',data,'image/png')})
    assert response.status_code==422
    assert response.json()['error']['code']=='ERR_INVALID_IMAGE'
    model.assert_not_called()

@pytest.mark.parametrize('field,value', [('focal_length_mm','-1'),('focal_length_mm','nan'),('focal_length_mm','inf'),('conf_threshold','2'),('conf_threshold','-0.1')])
def test_invalid_numeric_input_rejected(client,field,value):
    response=client.post('/api/v1/vision/estimate',files={'file':('x.png',png(),'image/png')},data={field:value})
    assert response.status_code==422


def test_missing_model_returns_actionable_503(client):
    with patch('src.api.v1.endpoints.vision.get_pipeline',side_effect=AppException(503,'ERR_MODEL_UNAVAILABLE','model missing')):
        response=client.post('/api/v1/vision/estimate',files={'file':('x.png',png(),'image/png')})
    assert response.status_code==503
    assert response.json()['error']['code']=='ERR_MODEL_UNAVAILABLE'


def test_routes_require_authentication():
    with TestClient(app) as client:
        for route in ('meals',):
            assert client.get('/api/v1/'+route).status_code==401
        assert client.post('/api/v1/vision/estimate',files={'file':('x.png',png(),'image/png')}).status_code==401
        assert client.post('/api/v1/vision/confirm',json={'confirmedItems':[]}).status_code==401



def test_confirm_validation_errors(client):
    # Empty confirmedItems rejected with 422
    assert client.post('/api/v1/vision/confirm', json={'confirmedItems': []}).status_code == 422

    # Missing volume data rejected with 422
    item_id = str(uuid.uuid4())
    res_no_vol = client.post('/api/v1/vision/confirm', json={
        'confirmedItems': [{'itemId': item_id, 'foodId': 'white_rice'}]
    })
    assert res_no_vol.status_code == 422
    assert res_no_vol.json()['error']['code'] == 'ERR_INVALID_VOLUME'

    # Unknown foodId rejected with 400
    res_unknown = client.post('/api/v1/vision/confirm', json={
        'confirmedItems': [{'itemId': item_id, 'foodId': 'unknown_alien_food', 'volumeCm3': 100.0}]
    })
    assert res_unknown.status_code == 400
    assert res_unknown.json()['error']['code'] == 'ERR_UNKNOWN_FOOD'

    # Invalid itemId format rejected with 422
    res_bad_id = client.post('/api/v1/vision/confirm', json={
        'confirmedItems': [{'itemId': 'not-a-valid-uuid', 'foodId': 'white_rice', 'volumeCm3': 100.0}]
    })
    assert res_bad_id.status_code == 422
    assert res_bad_id.json()['error']['code'] == 'ERR_INVALID_ITEM_ID'



def test_point_cloud_count_and_finite_values():
    with pytest.raises(ValidationError):
        SparsePointCloudPayload(count=5,positions=[0,0,1],colors=[1,1,1])
    with pytest.raises(ValidationError):
        SparsePointCloudPayload(count=1,positions=[0,float('nan'),1],colors=[1,1,1])

@pytest.mark.parametrize('volume',[float('nan'),float('inf'),4.99,5000.01])
def test_raw_volume_bounds(volume):
    with pytest.raises(VolumeOutOfBoundsException):
        NumericalVolumeIntegrator().validate_volume_bounds(volume)


def test_large_mask_cannot_be_clamped_to_success():
    with pytest.raises(VolumeOutOfBoundsException):
        GeometryIntegrator().compute_volume_and_mass(np.full((1000,1000),.55),np.ones((1000,1000)),'apple')


def test_preprocessing_converts_bgr_to_rgb():
    segmentor=ONNXSegmentor.__new__(ONNXSegmentor)
    image=np.zeros((640,640,3),np.uint8)
    image[:,:,2]=255
    blob,_,_=segmentor.preprocess(image)
    assert blob[0,0,0,0]==1
    assert blob[0,2,0,0]==0
