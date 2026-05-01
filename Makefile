.PHONY: install test package deploy destroy clean

install:
	pip install -r requirements.txt

test:
	python3 -m pytest tests/ -v

package:
	pip install -r requirements.txt -t package/
	cp -r app package/
	cd package && zip -r ../lambda.zip .
	rm -rf package/

deploy: package
	cd infra && terraform init && terraform apply -var="claude_api_key=$(CLAUDE_API_KEY)"

destroy:
	cd infra && terraform destroy -var="claude_api_key=$(CLAUDE_API_KEY)"

clean:
	rm -rf package/ lambda.zip
	find . -type d -name __pycache__ -exec rm -rf {} +

local:
	python3 -m uvicorn app.main:app --reload
