def bar(n):
    return {"x": n}


def foo(n=1):
    return bar(n)


def double_foo():
    foo()
    return foo()
