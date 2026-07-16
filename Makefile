.PHONY: install format lint typecheck test build smoke-wheel check cleanup-merged

PYTHON ?= python3

install:
	bash scripts/install.sh

format:
	bash scripts/format.sh

lint:
	bash scripts/lint.sh

typecheck:
	bash scripts/typecheck.sh

test:
	bash scripts/test.sh

build:
	rm -rf build dist
	$(PYTHON) -m build

smoke-wheel: build
	bash scripts/smoke_wheel.sh dist/*.whl

check: lint typecheck test smoke-wheel

cleanup-merged:
	bash scripts/cleanup_merged_worktrees.sh
