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


def test_checkpoint_saver_atomically_replaces_target(tmp_path):
    from spirecomm.ai.rl import checkpoint_io

    target = tmp_path / "model.pth"
    target.write_bytes(b"old")

    checkpoint_io.save_torch_checkpoint({"value": 3}, str(target))

    assert checkpoint_io.load_torch_checkpoint(str(target), map_location="cpu") == {
        "value": 3
    }
    assert list(tmp_path.glob("model.pth.tmp_*")) == []


def test_checkpoint_saver_removes_temporary_file_after_failure(tmp_path, monkeypatch):
    from spirecomm.ai.rl import checkpoint_io

    target = tmp_path / "model.pth"
    target.write_bytes(b"old")

    def fail_save(_checkpoint, temporary):
        with open(temporary, "wb") as handle:
            handle.write(b"partial")
        raise RuntimeError("save failed")

    monkeypatch.setattr(checkpoint_io.torch, "save", fail_save)

    try:
        checkpoint_io.save_torch_checkpoint({"value": 3}, str(target))
    except RuntimeError as exc:
        assert str(exc) == "save failed"
    else:
        raise AssertionError("checkpoint save should fail")

    assert target.read_bytes() == b"old"
    assert list(tmp_path.glob("model.pth.tmp_*")) == []
