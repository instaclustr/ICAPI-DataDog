# Change depending on your environment
PIP := pip3
PYTHON := python3
IMG_TAG := latest
IMG_REPO := tedk42/ic2datadog
FIND := $(if $(shell which gfind),gfind,find) # needed for macos - do a `brew install findutils` to use gfind

deps:
	$(PIP) install -r requirements.txt

unittest: testing-deps
	$(PYTHON) -m pytest tests/*.py --capture=fd -s

build:
	$(eval version = $(shell cat version))
	docker build . -t $(IMG_REPO):$(IMG_TAG)
	docker tag $(IMG_REPO):$(IMG_TAG) $(IMG_REPO):$(version)

build-push-testing:
	docker build . -t $(IMG_REPO):testing
	docker push $(IMG_REPO):testing

lint: deps
	$(PYTHON) -m pycodestyle . --exclude venv && echo "pycodestyle lint ok"
	$(PYTHON) -m pyflakes `$(FIND) -path ./venv -prune -o -name '*.py' -print` && echo "pyflakes lint ok"

push:
	docker push $(IMG_REPO)

coverage: testing-deps
	pytest --cov=. tests/*.py --capture=fd -s

testing-deps: deps
	$(PIP) install -r tests/testing-requirements.txt

version:
	$(PIP) install semver
	$(eval version = `$(PYTHON) version.py`)
	echo $(version) > version
	git tag $(version)
	git push --tags

.PHONY: unittest deps build push build-push-testing testing-deps
