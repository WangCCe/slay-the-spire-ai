def test_checkpoint_loader_requests_weights_only(monkeypatch):
    from spirecomm.ai.rl import checkpoint_io

    calls = []

    def fake_load(path, **kwargs):
        calls.append((path, kwargs))
        return {"ok": True}

    monkeypatch.setattr(checkpoint_io.torch, "load", fake_load)

    checkpoint = checkpoint_io.load_torch_checkpoint("model.pth", map_location="cpu")

    assert checkpoint == {"ok": True}
    assert calls == [
        ("model.pth", {"map_location": "cpu", "weights_only": True}),
    ]


def test_checkpoint_loader_supports_old_torch_without_weights_only(monkeypatch):
    from spirecomm.ai.rl import checkpoint_io

    calls = []

    def fake_load(path, **kwargs):
        calls.append((path, kwargs))
        if "weights_only" in kwargs:
            raise TypeError("unexpected keyword argument 'weights_only'")
        return {"legacy": True}

    monkeypatch.setattr(checkpoint_io.torch, "load", fake_load)

    checkpoint = checkpoint_io.load_torch_checkpoint("legacy.pth", map_location="cpu")

    assert checkpoint == {"legacy": True}
    assert calls == [
        ("legacy.pth", {"map_location": "cpu", "weights_only": True}),
        ("legacy.pth", {"map_location": "cpu"}),
    ]
