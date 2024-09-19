SPECFILE             = $(shell find -maxdepth 1 -type f -name *.spec)
SPECFILE_NAME        = $(shell awk '$$1 == "Name:"     { print $$2 }' $(SPECFILE) )
SPECFILE_VERSION     = $(shell awk '$$1 == "Version:"  { print $$2 }' $(SPECFILE) )
DIST                ?= $(shell rpm --eval %{dist})

FILES=LICENSE README.md setup.py setup.cfg MANIFEST.in 
PKGNAME=scitags

sources:
	mkdir dist
	cp ${SPECFILE} dist/
	mkdir -p dist/${PKGNAME}-${SPECFILE_VERSION}
	cp -pr ${FILES} sbin etc scitags dist/${PKGNAME}-${SPECFILE_VERSION}/.
	find dist -type d -name .svn | xargs -i rm -rf {}
	find dist -type d -name .git | xargs -i rm -rf {}
	cd dist ; tar cfz ../${PKGNAME}-${SPECFILE_VERSION}.tar.gz ${PKGNAME}-${SPECFILE_VERSION}
	rm -rf dist

srpm: sources
	rpmbuild -bs --define "dist $(DIST)" --define "_topdir $(PWD)/build" --define '_sourcedir $(PWD)/dist' $(SPECFILE)

rpm: sources
	rpmbuild -bb --define "dist $(DIST)" --define "_topdir $(PWD)/build" --define '_sourcedir $(PWD)/dist' $(SPECFILE)

clean:
	rm -rf build/ *.tgz
