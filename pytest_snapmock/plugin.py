import json
import os
import pytest


def pytest_addoption(parser):
    group = parser.getgroup('snapmock')
    group.addoption(
        '--snapshot-mocks',
        action='store_true',
        help='Update snapshot files instead of testing against them.',
    )


@pytest.fixture
def snapmock(request, capsys):
    spatch = SnapMock(request, capsys)
    yield spatch
    spatch.undo()
    if spatch.outlines:
        pytest.fail('\n'.join(spatch.outlines), pytrace=False)


class BaseSnap:
    def __init__(self, target, name, request, capsys, serializer):
        self.target = target
        self.name = name
        self.request = request
        self.capsys = capsys
        self.serializer =serializer
        self.func = getattr(target, name)
        self.call_count = 0
        self.outlines = []

    def snap_dir(self):
        return self.request.node.path.parent / '__snapshot__'

    def filename(self, suffix):
        f = f'{self.request.node.name}_{self.target.__name__}_{self.name}_{self.call_count}.{suffix}'
        return self.snap_dir() / f

    def _hash_inputs(self, args, kwargs, kwd_mark=(object(),)):
        return str(hash(args + kwd_mark + tuple(sorted(kwargs.items()))))

    def __call__(self, *args, **kwargs):
        raise NotImplementedError


class SaveSnap(BaseSnap):

    def __call__(self, *args, **kwargs):
        res = self.func(*args, **kwargs)
        fname = self.filename('snap')
        fname.parent.mkdir(exist_ok=True)
        with open(fname, 'w') as f:
            f.write(self.serializer.dumps(res))
        with open(self.filename('hash'), 'w') as f:
            f.write(self._hash_inputs(args, kwargs))
        self.outlines.append(f'  - Generated snapshot for call #{self.call_count} to {self.func.__name__}')
        self.call_count += 1
        return res


class UnsnappedTest(Exception):
    pass


class StaleSnapshot(Exception):
    pass


class LoadSnap(BaseSnap):

    def __call__(self, *args, **kwargs):
        try:
            try:
                fname = self.filename('hash')
                with open(fname) as f:
                    snap_hash = f.read()
                run_hash = self._hash_inputs(args, kwargs)
                if snap_hash != run_hash:
                    raise StaleSnapshot("Inputs to function updated, snapshot is stale. Run pytest with snapshot.")
            except FileNotFoundError:
                raise UnsnappedTest(f"Could not find hash file={fname}. Run pytest with snapshot.")

            try:
                fname = self.filename('snap')
                with open(fname, 'r') as f:
                    res = self.serializer.loads(f.read())
            except FileNotFoundError:
                raise UnsnappedTest(f"Could not find snap file={fname}. Run pytest with snapshot.")
            return res
        finally:
            self.call_count += 1


class SnapMock:

    def __init__(self, request, capsys):
        self._request = request
        self._capsys = capsys
        self._monkeypatch = pytest.MonkeyPatch()
        self.outlines = []
        self._snap = None

    def undo(self):
        self.outlines += self._snap.outlines
        self._monkeypatch.undo()

    def snapit(self, target, name, serializer=json):
        snap_cls = SaveSnap if os.environ.get('SNAPIT') else LoadSnap
        self._snap = snap_cls(target, name, self._request, self._capsys, serializer)
        self._monkeypatch.setattr(target, name, self._snap)
