"""/api/process_state — validation before anything reaches the database."""
import uuid

W = str(uuid.uuid4())


def _put(client, kind, eid, doc):
    return client.put(f"/api/process_state/{kind}/{eid}", json={"doc": doc})


def test_unknown_kind(test_client):
    assert _put(test_client, "folder", W, {"id": W}).status_code == 400


def test_id_must_be_a_uuid_and_match_the_doc(test_client):
    assert _put(test_client, "workspace", "nope", {"id": "nope"}).status_code == 400
    other = str(uuid.uuid4())
    res = _put(test_client, "workspace", W, {"id": other})
    assert res.status_code == 400
    assert "Id mismatch" in res.text


def test_children_need_their_parent_id(test_client):
    p = str(uuid.uuid4())
    res = _put(test_client, "pipeline", p, {"id": p, "name": "x"})
    assert res.status_code == 400
    assert "workspaceId" in res.text
    r = str(uuid.uuid4())
    res = _put(test_client, "run", r, {"id": r, "pipelineId": "not-a-uuid"})
    assert res.status_code == 400
    assert "pipelineId" in res.text


def test_body_must_wrap_the_doc(test_client):
    res = test_client.put(f"/api/process_state/workspace/{W}", json={"id": W})
    assert res.status_code == 400
