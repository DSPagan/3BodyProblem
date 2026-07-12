"""Round-trip tests for the shareable-orbit encoding."""

from __future__ import annotations

from threebody import presets, share


def test_encode_decode_round_trip():
    sys = presets.figure_eight().system
    back = share.decode(share.encode(sys))
    assert back.n == sys.n
    assert abs(back.G - sys.G) < 1e-9
    assert abs(back.softening - sys.softening) < 1e-9
    for i in range(sys.n):
        assert abs(back.pos[i].x - sys.pos[i].x) < 1e-5
        assert abs(back.pos[i].y - sys.pos[i].y) < 1e-5
        assert abs(back.vel[i].x - sys.vel[i].x) < 1e-5
        assert abs(back.vel[i].y - sys.vel[i].y) < 1e-5
        assert abs(back.mass[i] - sys.mass[i]) < 1e-5


def test_scenario_from_token_is_runnable():
    sys = presets.sun_and_planets().system
    scenario = share.scenario_from_token(share.encode(sys))
    assert scenario.system.n == 3
    assert scenario.view_scale > 0
    # a couple of steps should not blow up
    scenario.system.step(0.001)


def test_token_is_url_safe():
    token = share.encode(presets.moth().system)
    assert all(c.isalnum() or c in "-_" for c in token)
