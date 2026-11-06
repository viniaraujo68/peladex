import pytest


@pytest.mark.parametrize("name", ["", "g" * 81], ids=["empty", "too_long"])
def test_a_rename_respects_the_name_limits(api, group, name):
    assert api.patch(f"/api/groups/{group}", json={"name": name}).status_code == 422


def test_the_description_is_bounded_on_create_and_update(api, group):
    long = "d" * 501
    assert api.post("/api/groups", json={"name": "Pelada", "description": long}).status_code == 422
    assert api.patch(f"/api/groups/{group}", json={"description": long}).status_code == 422
    ok = api.patch(f"/api/groups/{group}", json={"description": "d" * 500})
    assert ok.status_code == 200
