clean:
	rm -fR *.png *.zip *.egg *.html *.xml *.mib
	rm -fR .eggs/ *.egg-info/ .coverage/ build/ dist/ docs/_build
	find . -name '*~' -exec rm -f {} +
	python setup.py clean --all

mib:
	curl -G ftp://ftp.apc.com/apc/public/software/pnetmib/mib/417/powernet417.mib > powernet.mib
	build-pysnmp-mib -o PowerNet-MIB.py powernet.mib
	sed -i '1 a # NOTE: This line has been added by `make mib` ------------------------------!' PowerNet-MIB.py
	sed -i '2 a # flake8: noqa' PowerNet-MIB.py
	sed -i '3 a # pylint: skip-file' PowerNet-MIB.py
	sed -i '4 a # ----------------------------------------------------------------------------' PowerNet-MIB.py
	sed -i '14 a # NOTE: This line has been added by `make mib` ------------------------------!' PowerNet-MIB.py
	sed -i '15 a ( Unsigned32, ) = mibBuilder.importSymbols("SNMPv2-SMI", "Unsigned32")' PowerNet-MIB.py
	sed -i '16 a # ----------------------------------------------------------------------------' PowerNet-MIB.py
	mv PowerNet-MIB.py pynoc/

check: mib
	python setup.py check --strict --metadata --verbose
	python setup.py lint --lint-output="pylint.html"
	python setup.py flake8

test: check
	python setup.py nosetests

docs:
	python setup.py build_sphinx --fresh-env --all-files --build-dir docs/_build --config-dir docs --builder html --verbose

build: docs
	python setup.py sdist bdist_wheel --dist-dir dist --verbose

all: clean mib check docs build

allwithtests: all test

.PHONY: clean check test docs
