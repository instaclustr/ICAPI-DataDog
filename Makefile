# Change depending on your environment
PIP := pip3
PYTHON := python3
IMG_TAG := latest
IMG_REPO := tedk42/ic2datadog

deps:
	$(PIP) install -r requirements.txt

unittest: testing-deps
	$(PYTHON) -m unittest test
	rm test-data/instaclustr.json # Keep the file if you wish...

build:
	$(eval version = $(shell cat version))
	docker build . -t $(IMG_REPO):$(IMG_TAG)
	docker tag $(IMG_REPO):$(IMG_TAG) $(IMG_REPO):$(version)

push:
	docker push $(IMG_REPO)

coverage: testing-deps
	coverage run test.py
	coverage report --omit '/usr/local/lib/*' --skip-covered
	coverage html
	rm test-data/instaclustr.json # Keep the file if you wish...
	open htmlcov/ic2datadog_py.html

testing-deps:
	$(PIP) install -r requirements.txt
	$(PIP) install -r testing-requirements.txt

version:
	$(PIP) install semver
	$(eval version = `$(PYTHON) version.py`)
	echo $(version) > version
	git tag $(version)
	git push --tags

.PHONY: unittest deps build push testing-deps
