# Change depending on your environment
PIP := pip3
PYTHON := python3
IMG_TAG := latest
IMG_REPO := tedk42/ic2datadog

deps:
	$(PIP) install -r requirements.txt --user

unittest: testing-deps
	$(PYTHON) -m unittest test
	rm test-data/instaclustr.json # Keep the file if you wish...

build:
	docker build . -t $(IMG_REPO):$(IMG_TAG)

push: build
	docker push $(IMG_REPO):$(IMG_TAG)

coverage: testing-deps
	coverage run test.py
	coverage report --omit '/usr/local/lib/*' --skip-covered
	coverage html
	rm test-data/instaclustr.json # Keep the file if you wish...
	open htmlcov/ic2datadog_py.html

testing-deps:
	$(PIP) install -r requirements.txt --user
	$(PIP) install -r testing-requirements.txt --user

.PHONY: unittest deps build push testing-deps
