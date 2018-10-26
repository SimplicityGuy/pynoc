clean:
	rm -fR *.png *.zip *.egg *.html *.xml
	rm -fR .eggs/ *.egg-info/ .coverage/ build/ dist/ docs/_build
	find . -name *.pyc -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	python setup.py clean --all

format:
	black pynoc

check:
	python setup.py check --strict --metadata --verbose
	pylint pynoc
	python setup.py flake8

test: check
	python setup.py nosetests

docs:
	python setup.py build_sphinx --fresh-env --all-files --build-dir docs/_build --config-dir docs --builder html --verbose

build: docs
	python setup.py sdist bdist_wheel --dist-dir dist --verbose

install:
	python setup.py install

release:
	twine upload dist/*

all: clean check docs build

allwithtests: all test

allwithformat: clean format check docs build

.PHONY: clean format check test docs install release
