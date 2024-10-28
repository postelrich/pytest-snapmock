from __future__ import annotations

import hashlib
import json
import os
import pathlib
from types import ModuleType
from typing import Any, overload

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
    """Wrapper class for a function to create a snapshot from it's output or load from an existing snapshot."""
    SNAP_SUFFIX = 'snap'
    HASH_SUFFIX = 'hash'

    def __init__(self, target: ModuleType, name: str, request: None, capsys: None, serializer):
        self.target = target
        self.name = name
        self.request = request
        self.capsys = capsys
        self.serializer =serializer
        self.func = getattr(target, name)
        self.call_count = 0
        self.outlines = []

    def snap_dir(self) -> pathlib.Path:
        """Directory to store the snapshot, relative to test file."""
        return self.request.node.path.parent / '__snapshot__'

    def filename(self, suffix: str) -> pathlib.Path:
        """Filename for snapshots based on the test name, function name, and call count."""
        f = f'{self.request.node.name}_{self.target.__name__}_{self.name}_{self.call_count}.{suffix}'
        return self.snap_dir() / f

    def _hash_inputs(self, args, kwargs, kwd_mark=(object(),)) -> str:
        """Hash the arguments to the wrapped function. 

        Used to identify if the inputs have changed and thus require a new snapshot to be generated.
        """
        return hashlib.md5(self.serializer.dumps(args + tuple(sorted(kwargs.items()))).encode()).hexdigest()

    def __call__(self, *args: tuple(Any), **kwargs: Dict[str, Any]) -> Any:
        raise NotImplementedError


class SaveSnap(BaseSnap):
    """Subclass snapshot wrapper that calls the function, saves it to a snapshot and returns function output."""

    def __call__(self, *args: tuple(Any), **kwargs: Dict[str, Any]) -> Any:
        # save function output to file
        res = self.func(*args, **kwargs)
        fname = self.filename(BaseSnap.SNAP_SUFFIX)
        fname.parent.mkdir(exist_ok=True)
        with open(fname, 'w') as f:
            f.write(self.serializer.dumps(res))

        # save function input hash to file
        with open(self.filename(BaseSnap.HASH_SUFFIX), 'w') as f:
            snap_hash = self._hash_inputs(args, kwargs)
            f.write(snap_hash)

        self.outlines.append(f'  - Generated snapshot for call #{self.call_count} to {self.func.__name__}')

        # increment call count to save separate snapshot in case mocked function is called multiple times
        self.call_count += 1
        return res


class UnsnappedTest(Exception):
    pass


class StaleSnapshot(Exception):
    pass


class LoadSnap(BaseSnap):
    """Subclass snapshot wrapper that loads the output from the snapshot instead of calling the function."""

    def __call__(self, *args: tuple(Any), **kwargs: Dict[str, Any]) -> Any:
        try:
            # check inputs haven't changed
            try:
                fname = self.filename(BaseSnap.HASH_SUFFIX)
                with open(fname) as f:
                    snap_hash = f.read()
                run_hash = self._hash_inputs(args, kwargs)
                if snap_hash != run_hash:
                    raise StaleSnapshot("Inputs to function updated, snapshot is stale. Run pytest with snapshot.")
            except FileNotFoundError:
                raise UnsnappedTest(f"Could not find hash file={fname}. Run pytest with snapshot.")

            # load and return snapshot
            try:
                fname = self.filename(BaseSnap.SNAP_SUFFIX)
                with open(fname, 'r') as f:
                    res = self.serializer.loads(f.read())
            except FileNotFoundError:
                raise UnsnappedTest(f"Could not find snap file={fname}. Run pytest with snapshot.")
            return res
        finally:
            self.call_count += 1


class SnapMock:
    """Snapshot monkeypatched objects."""

    def __init__(self, request, capsys):
        self._request = request
        self._capsys = capsys
        self._monkeypatch = pytest.MonkeyPatch()
        self.outlines = []
        self._snap = None

    def undo(self) -> None:
        """Set output lines and undo monkeypatch."""
        self.outlines += self._snap.outlines
        self._monkeypatch.undo()

    def snapit(self, target: str | ModuleType, name: str, serializer=json) -> None:
        """Monkeypatch an object with a snapshot wrapper."""
        if isinstance(target, str):
            target = importlib.import_module(target)
        snap_cls = SaveSnap if self._request.config.option.snapshot_mocks or os.environ.get('SNAPIT') else LoadSnap
        self._snap = snap_cls(target, name, self._request, self._capsys, serializer)
        self._monkeypatch.setattr(target, name, self._snap)
