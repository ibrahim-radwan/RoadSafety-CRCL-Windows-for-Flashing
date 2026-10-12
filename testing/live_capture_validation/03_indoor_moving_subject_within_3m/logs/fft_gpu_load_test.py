import cupy as cp
import numpy as np
import time

# Radar-like dimensions
N_RANGE = 256
N_LOOPS = 64
N_CH = 48
BATCH = N_LOOPS * N_CH

print("Using GPU:", cp.cuda.runtime.getDeviceProperties(0)["name"].decode())

# ✅ Correct complex random generation
x = (
    cp.random.randn(BATCH, N_RANGE, dtype=cp.float32)
    + 1j * cp.random.randn(BATCH, N_RANGE, dtype=cp.float32)
).astype(cp.complex64)

# Warm-up
for _ in range(5):
    cp.fft.fft(x, axis=1)
cp.cuda.Device().synchronize()

# Timed FFT loop
N_ITER = 50
t0 = time.time()

for _ in range(N_ITER):
    y = cp.fft.fft(x, axis=1)

cp.cuda.Device().synchronize()
dt = time.time() - t0

print(f"Ran {N_ITER} GPU FFT batches")
print(f"Total time: {dt:.3f} s")
print(f"Average per FFT batch: {dt/N_ITER*1000:.3f} ms")

# Correctness check
y_cpu = np.fft.fft(cp.asnumpy(x), axis=1)
print("Correctness:", np.allclose(y_cpu, cp.asnumpy(y), atol=1e-5))