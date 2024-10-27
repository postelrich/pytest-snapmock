from setuptools import setup


setup(
    name='pytest-snapmock',  # This line is only needed to make the Github dependency graph work
    packages=['pytest_snapmock'],  # This line is only needed to make the Github dependency graph work
    use_scm_version={"write_to": "pytest_snapmock/_version.py"},
)
