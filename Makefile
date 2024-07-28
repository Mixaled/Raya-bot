model="Llama3_1.gguf"
ifeq ($(OS),Windows_NT)
	OS_NAME="Windows" 
    # Windows-specific commands
else
    UNAME_S := $(shell uname -s)
    ifeq ($(UNAME_S),Linux)
		OS_NAME="Linux" 
        # Linux-specific commands
    endif
    ifeq ($(UNAME_S),Darwin)
		OS_NAME="macOS" 
        # macOS-specific commands
    endif
endif

all: greetings install_llama run_server


greetings:
	echo $(OS_NAME)

install_llama:
	cd third_party/llama.cpp && make

install_llama_cuda:
	cd third_party/llama.cpp && make GGML_CUDA=1

run_server:
	cd third_party/llama.cpp && .\llama-server.exe -m ../../$(model) --port 8080

	