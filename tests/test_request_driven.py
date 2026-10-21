from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from gis.factory import FactoryStore, DemoCommand, Batch, Observation, install_factory


@pytest.fixture
def scaled(monkeypatch):
    monkeypatch.setenv('REQUEST_DRIVEN_DEMO','1')
    monkeypatch.setenv('DEMO_MODE','1')
    monkeypatch.setenv('FACTORY_ANALYSIS_DEMO','0')
    monkeypatch.delenv('DATABASE_URL',raising=False)


def test_scaled_instances_reload_manual_observations_and_preserve_instance_id(tmp_path,scaled):
    a=FactoryStore(tmp_path/'factory.db');b=FactoryStore(tmp_path/'factory.db')
    a.observe(Batch(observations=[Observation(id='P023',x=-41,z=12)]))
    known=next(e for e in b.snapshot()['entities'] if e['id']=='P023')
    assert known['anchor'][0]==-41 and known['positionSource']=='telemetry'
    b.tick()
    assert next(e for e in a.snapshot()['entities'] if e['id']=='P023')['anchor'][0]==-41
    assert a.snapshot()['instanceId']==b.snapshot()['instanceId']


def test_route_survives_new_instance_and_stop_is_shared(tmp_path,scaled):
    a=FactoryStore(tmp_path/'factory.db')
    a.command(DemoCommand(action='start',key='vehicle'))
    b=FactoryStore(tmp_path/'factory.db')
    assert b.snapshot()['demo']['key']=='vehicle'
    b.command(DemoCommand(action='stop',key='vehicle'))
    assert a.snapshot()['demo'] is None


def test_parallel_instances_do_not_overwrite_each_others_imports(tmp_path,scaled):
    a=FactoryStore(tmp_path/'factory.db');b=FactoryStore(tmp_path/'factory.db')
    def update(store,id,x):
        store.observe(Batch(observations=[Observation(id=id,x=x,z=12)]))
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda args:update(*args),[(a,'P023',-41),(b,'P024',-42)]))
    data={e['id']:e for e in a.snapshot()['entities']}
    assert data['P023']['anchor'][0]==-41 and data['P024']['anchor'][0]==-42


def test_request_mode_has_no_background_sampler_but_reads_advance_state(tmp_path,scaled,monkeypatch):
    monkeypatch.setenv('FACTORY_DB_PATH',str(tmp_path/'factory.db'))
    app=FastAPI();install_factory(app)
    with TestClient(app) as client:
        assert not hasattr(app.state,'factory_sampler')
        before=app.state.factory.snapshot()['revision']
        assert client.get('/factory/state').status_code==200
        assert app.state.factory.snapshot()['revision']>before


def test_vercel_mode_refuses_to_publish_ephemeral_database(monkeypatch):
    import cloud_gateway
    monkeypatch.setenv('REQUIRE_DURABLE_STORAGE','1')
    monkeypatch.delenv('DATABASE_URL',raising=False)
    with pytest.raises(RuntimeError,match='persistent DATABASE_URL'):
        with TestClient(cloud_gateway.app):pass
