import copy
import pytest
import backend.content as content


def test_all_six_exhibits_have_assets_and_reachable_positions():
    assert set(content.load_exhibits()) == {"fern", "cactus", "sunflower", "lotus", "bonsai", "orchid"}


@pytest.mark.parametrize("mutation", ["duplicate", "missing_asset", "outside", "overlap", "blocked", "enclosed"])
def test_content_errors_fail_early(monkeypatch, mutation):
    original = content.read_json
    exhibits = copy.deepcopy(original("exhibits.json"))
    world = copy.deepcopy(original("garden.json"))
    if mutation == "duplicate": exhibits[1]["id"] = exhibits[0]["id"]
    if mutation == "missing_asset": exhibits[0]["asset"] = "/art/missing.svg"
    if mutation == "outside": exhibits[0]["tile"]["x"] = 90
    if mutation == "overlap": exhibits[0]["tile"] = exhibits[1]["tile"]
    if mutation == "blocked": exhibits[0]["tile"] = {"x": 0, "y": 0}
    if mutation == "enclosed":
        x, y = exhibits[0]["tile"]["x"], exhibits[0]["tile"]["y"]
        world["obstacles"].extend({"x": nx * 16, "y": ny * 16, "width": 16, "height": 16} for nx, ny in [(x-1,y), (x+1,y), (x,y-1), (x,y+1)])
    monkeypatch.setattr(content, "read_json", lambda name: exhibits if name == "exhibits.json" else world)
    with pytest.raises(ValueError): content.load_exhibits()
