.PHONY: demo verify

demo:
	PYTHONPATH=. python3 ui/server.py

verify:
	PYTHONPATH=. python3 tests/test_demo.py
	PYTHONPATH=. python3 demo.py all >/tmp/reliable-ai-workflow-demo.json
	@echo "verification output: /tmp/reliable-ai-workflow-demo.json"
