.PHONY: install test demo run serve docker-build docker-up clean

install:
	python3 -m venv .venv && .venv/bin/pip install -e .

test:
	bash scripts/test_all.sh

demo:
	.venv/bin/python -m neurodaily demo --no-open

run:
	.venv/bin/python -m neurodaily run

serve:
	.venv/bin/python -m neurodaily serve --port 8031

docker-build:
	docker build -t neurodaily:local .

docker-up:
	docker compose up --build

clean:
	rm -rf .venv __pycache__ */__pycache__ */*/__pycache__
