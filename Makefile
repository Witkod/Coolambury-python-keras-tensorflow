PYTHON = python3
SERVER_APP := $(shell pwd)/Server/server.py
CLIENT_APP := $(shell pwd)/Client/RunClient.py
CONFIG_PATH = $(shell pwd)/config.json
CONFIG_REMOTE_PATH = $(shell pwd)/configRemote.json
CLIENT_PYTHONPATH := PYTHONPATH='Client'
SERVER_PYTHONPATH := PYTHONPATH='Server'

server: .FORCE
	$(SERVER_PYTHONPATH) $(PYTHON) $(SERVER_APP) $(CONFIG_PATH)

server_remote: .FORCE
	$(SERVER_PYTHONPATH) $(PYTHON) $(SERVER_APP) $(CONFIG_REMOTE_PATH)

client: .FORCE
	$(CLIENT_PYTHONPATH) $(PYTHON) $(CLIENT_APP) $(CONFIG_PATH)

client_remote: .FORCE
	$(CLIENT_PYTHONPATH) $(PYTHON) $(CLIENT_APP) $(CONFIG_REMOTE_PATH)

clean: .FORCE
	find . -name '__pycache__' -exec rm -rf {} \;
	
.PHONY: .FORCE
FORCE:
