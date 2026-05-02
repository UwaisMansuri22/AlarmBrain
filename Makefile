.PHONY: install test package deploy destroy clean local

install:
	pip3.11 install -r requirements.txt

test:
	python3.11 -m pytest tests/ -v

package:
	rm -rf package/ lambda.zip
	mkdir -p package
	docker run --rm \
		--platform linux/amd64 \
		-v $(PWD):/var/task \
		public.ecr.aws/sam/build-python3.11 \
		pip install -r requirements.txt \
			--platform manylinux2014_x86_64 \
			--target /var/task/package \
			--implementation cp \
			--python-version 3.11 \
			--only-binary=:all: \
			--upgrade
	cp -r app package/
	cd package && zip -r ../lambda.zip . && cd ..
	rm -rf package/
	@echo "✅ lambda.zip ready for Linux/amd64"

deploy: package
	cd infra && terraform init && terraform apply \
		-var="claude_api_key=$(CLAUDE_API_KEY)" \
		-auto-approve

destroy:
	cd infra && terraform destroy \
		-var="claude_api_key=$(CLAUDE_API_KEY)" \
		-auto-approve

clean:
	rm -rf package/ lambda.zip
	find . -type d -name __pycache__ -exec rm -rf {} +

local:
	python3.11 -m uvicorn app.main:app --reload
