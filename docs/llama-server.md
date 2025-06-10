CUDA llama-server

Build
```bash
git clone https://github.com/ggml-org/llama.cpp.git llama-cuda \
&& cd llama-cuda \
&& mkdir build \
&& cd build \
&& cmake .. -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES="86" -DGGML_CUDA_FORCE_MMQ=OFF \
&& make -j$(nproc) llama-server
```

Use
```bash
export LD_LIBRARY_PATH="$(pwd)/llama-cuda/build/bin:$LD_LIBRARY_PATH" \
&& ./llama-cuda/build/bin/llama-server -hf ggml-org/ultravox-v0_5-llama-3_2-1b-GGUF:Q4_K_M --port 8081 -ngl -99
```
