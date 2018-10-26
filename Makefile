clean:
	rm -fR *.png *.zip *.egg *.html *.xml
	rm -fR .eggs/ *.egg-info/ .coverage/ build/ dist/ docs/_build
	find . -name *.pyc -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	python3 setup.py clean --all

format:
	black pynoc

check:
	python3 setup.py check --strict --metadata --verbose
	pylint pynoc
	python3 setup.py flake8

test: check
	python3 setup.py nosetests

docs:
	python3 setup.py build_sphinx --fresh-env --all-files --build-dir docs/_build --config-dir docs --builder html --verbose

build: docs
	python3 setup.py sdist bdist_wheel --dist-dir dist --verbose

install:
	python3 setup.py install

release:
	twine upload dist/*

all: clean format check docs build

allwithtests: all test

.PHONY: clean format check test docs install release
