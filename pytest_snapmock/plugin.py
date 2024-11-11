from __future__ import annotations

import hashlib
import importlib
import json
import os
import pathlib
from types import ModuleType
from typing import Any

import pytest


def pytest_addoption(parser):
    group = parser.getgroup("snapmock")
    group.addoption(
        "--snapshot-mocks",
        action="store_true",
        help="Update snapshot files instead of testing against them. Skips files that are already generated with the same hash.",
    )
    group.addoption(
        "--snapshot-mocks-all", action="store_true", help="Force update all snapshot files even if hash is unchanged."
    )


@pytest.fixture
def snapmock(request):
    spatch = SnapMock(request)
    yield spatch
    spatch.undo()
    if spatch.outlines:
        print("\n" + "\n".join(spatch.outlines))


class BaseSnap:
    """Wrapper class for a function to create a snapshot from it's output or load from an existing snapshot."""

    SNAP_SUFFIX = "snap"
    HASH_SUFFIX = "hash"

    def __init__(
        self, target: ModuleType, name: str, request: pytest.FixtureRequest, output_serializer, arg_serializer
    ):
        self.target = target
        self.name = name
        self.request = request
        self.output_serializer = output_serializer
        self.arg_serializer = arg_serializer
        self.func = getattr(target, name)
        self.call_count = 0
        self.outlines: list[str] = []

    def snap_dir(self) -> pathlib.Path:
        """Directory to store the snapshot, relative to test file."""
        return self.request.node.path.parent / "__snapshot__"

    def filename(self, suffix: str) -> pathlib.Path:
        """Filename for snapshots based on the test name, function name, and call count."""
        f = f"{self.request.node.name}_{self.target.__name__}_{self.name}_{self.call_count}.{suffix}"
        return self.snap_dir() / f

    def _hash_inputs(self, args, kwargs, kwd_mark=(object(),)) -> str:
        """Hash the arguments to the wrapped function.

        Used to identify if the inputs have changed and thus require a new snapshot to be generated.
        """
        return hashlib.md5(self.arg_serializer.dumps(args + tuple(sorted(kwargs.items()))).encode()).hexdigest()

    def _read_hash(self) -> str | None:
        try:
            fname = self.filename(BaseSnap.HASH_SUFFIX)
            with open(fname) as f:
                snap_hash = f.read().strip()
                return snap_hash
        except FileNotFoundError:
            return None

    def _write_hash(self, *args: tuple[Any], **kwargs: dict[str, Any]) -> None:
        fname = self.filename(BaseSnap.HASH_SUFFIX)
        with open(fname, "w") as f:
            snap_hash = self._hash_inputs(args, kwargs)
            f.write(snap_hash)

    def _read_output(self) -> Any:
        try:
            fname = self.filename(BaseSnap.SNAP_SUFFIX)
            with open(fname, "r") as f:
                res = self.output_serializer.loads(f.read())
                return res
        except FileNotFoundError:
            return None

    def _write_output(self, output: Any) -> None:
        fname = self.filename(BaseSnap.SNAP_SUFFIX)
        fname.parent.mkdir(exist_ok=True)
        with open(fname, "w") as f:
            f.write(self.output_serializer.dumps(output))

    def __call__(self, *args: tuple[Any], **kwargs: dict[str, Any]) -> Any:
        raise NotImplementedError


class SaveSnap(BaseSnap):
    """Subclass snapshot wrapper that calls the function, saves it to a snapshot and returns function output."""

    def __call__(self, *args: tuple[Any], **kwargs: dict[str, Any]) -> Any:
        # skip generating output if it hasn't changed
        if not self.request.config.option.snapshot_mocks_all:
            existing_hash = self._read_hash()
            snap_hash = self._hash_inputs(args, kwargs)
            if existing_hash is not None and existing_hash == snap_hash:
                return

        # save function output and hash to file
        res = self.func(*args, **kwargs)
        self._write_output(res)
        self._write_hash(*args, **kwargs)

        self.outlines.append(f"  - Generated snapshot for call #{self.call_count} to {self.func.__name__}")

        # increment call count to save separate snapshot in case mocked function is called multiple times
        self.call_count += 1
        return res


class UnsnappedTest(Exception):
    pass


class StaleSnapshot(Exception):
    pass


class LoadSnap(BaseSnap):
    """Subclass snapshot wrapper that loads the output from the snapshot instead of calling the function."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        try:
            # check inputs haven't changed
            snap_hash = self._read_hash()
            if snap_hash is None:
                raise UnsnappedTest("Could not find hash file. Run pytest with snapshot.")
            run_hash = self._hash_inputs(args, kwargs)
            if snap_hash != run_hash:
                raise StaleSnapshot("Inputs to function updated, snapshot is stale. Run pytest with snapshot.")

            # load and return snapshot
            output = self._read_output()
            if output is None:
                raise UnsnappedTest("Could not find snap file. Run pytest with snapshot.")
            return output
        finally:
            self.call_count += 1


class SnapMock:
    """Snapshot monkeypatched objects."""

    def __init__(self, request):
        self._request = request
        self._monkeypatch = pytest.MonkeyPatch()
        self.outlines = []
        self._snap = None

    def undo(self) -> None:
        """Set output lines and undo monkeypatch."""
        self.outlines += self._snap.outlines
        self._monkeypatch.undo()

    def snapit(self, target: str | ModuleType, name: str, output_serializer=json, arg_serializer=json) -> None:
        """Monkeypatch an object with a snapshot wrapper."""
        if isinstance(target, str):
            target = importlib.import_module(target)
        snap_cls = (
            SaveSnap
            if self._request.config.option.snapshot_mocks
            or self._request.config.option.snapshot_mocks_all
            or os.environ.get("SNAPIT")
            else LoadSnap
        )
        self._snap = snap_cls(target, name, self._request, output_serializer, arg_serializer)
        self._monkeypatch.setattr(target, name, self._snap)
