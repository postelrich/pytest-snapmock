import mylib
import pytest
from pytest_snapmock.plugin import snapmock


@pytest.mark.parametrize('n', [
    1, 2, 100
])
def test_foo_paramed(n, snapmock):
    snapmock.snapit(mylib, 'foo')
    assert mylib.foo(n) == {'x': n}


def test_foo(snapmock):
    snapmock.snapit(mylib, 'foo')
    assert mylib.foo() == {'x': 1}


def test_double_foo(snapmock):
    snapmock.snapit(mylib, 'foo')
    assert mylib.double_foo() == {'x': 1}
