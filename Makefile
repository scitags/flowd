SPECFILE             = $(shell find -maxdepth 1 -type f -name *.spec)
SPECFILE_NAME        = $(shell awk '$$1 == "Name:"     { print $$2 }' $(SPECFILE) )
SPECFILE_VERSION     = $(shell awk '$$1 == "Version:"  { print $$2 }' $(SPECFILE) )
DIST                ?= $(shell rpm --eval %{dist})

sources:
	/usr/bin/python3 setup.py sdist

srpm: sources
	rpmbuild -bs --define "dist $(DIST)" --define "_topdir $(PWD)/build" --define '_sourcedir $(PWD)/dist' $(SPECFILE)

rpm: sources
	rpmbuild -bb --define "dist $(DIST)" --define "_topdir $(PWD)/build" --define '_sourcedir $(PWD)/dist' $(SPECFILE)

clean:
	rm -rf build/ *.tgz
