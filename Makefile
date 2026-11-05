UV ?= uv
INPUT ?= input
OUTPUT ?= output

.DEFAULT_GOAL := help
.PHONY: help setup run check

help:
	@printf '%s\n' \
		'make setup                 Install project dependencies' \
		'make run                   Convert HTML from input/ to output/' \
		'make run INPUT=... OUTPUT=...  Use custom directories' \
		'make check                 Check Python syntax'

setup:
	$(UV) sync

run:
	$(UV) run article-spoiler --input "$(INPUT)" --output "$(OUTPUT)"

check:
	$(UV) run python -m compileall -q src
