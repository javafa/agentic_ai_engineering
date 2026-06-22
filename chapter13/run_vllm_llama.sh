VLLM_USE_FLASHINFER_SAMPLER=0 vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.90 \
    --port 8000