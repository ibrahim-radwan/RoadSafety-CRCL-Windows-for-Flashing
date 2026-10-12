import cupy as cp

print("CuPy version:", cp.__version__)
print("Device count:", cp.cuda.runtime.getDeviceCount())

props = cp.cuda.runtime.getDeviceProperties(0)
print("GPU name:", props["name"].decode())

a = cp.zeros((1024, 1024), dtype=cp.float32)
print("Array lives on device:", a.device)