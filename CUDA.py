import torch
print("PyTorch 版本:", torch.__version__)
print("CUDA 是否可用:", torch.cuda.is_available())
print("CUDA 版本:", torch.version.cuda if torch.cuda.is_available() else "N/A")
print("GPU 数量:", torch.cuda.device_count() if torch.cuda.is_available() else 0)