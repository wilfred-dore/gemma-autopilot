"""GPU energy measurement (NVML) and power-cap control.

EnergyMeter prefers the driver's cumulative energy counter
(nvmlDeviceGetTotalEnergyConsumption, millijoules since driver load,
available on Volta+) — a delta across the measured window beats sampling.
Backend is injectable for tests.
"""

from __future__ import annotations

import subprocess
import time


class NvmlBackend:
    def __init__(self, index: int = 0):
        import pynvml

        pynvml.nvmlInit()
        self._nvml = pynvml
        self._h = pynvml.nvmlDeviceGetHandleByIndex(index)

    def energy(self) -> int:  # millijoules
        return self._nvml.nvmlDeviceGetTotalEnergyConsumption(self._h)

    def gpu_name(self) -> str:
        name = self._nvml.nvmlDeviceGetName(self._h)
        return name.decode() if isinstance(name, bytes) else name

    def vram_gb(self) -> int:
        return round(self._nvml.nvmlDeviceGetMemoryInfo(self._h).total / 1024**3)


class EnergyMeter:
    def __init__(self, _backend=None, index: int = 0):
        self._b = _backend or NvmlBackend(index)
        self.joules: float = 0.0
        self.mean_power_w: float = 0.0
        self._t0 = 0.0
        self._e0 = 0

    def __enter__(self):
        self._t0 = time.monotonic()
        self._e0 = self._b.energy()
        return self

    def __exit__(self, *exc):
        elapsed = max(time.monotonic() - self._t0, 1e-9)
        self.joules = (self._b.energy() - self._e0) / 1000.0
        self.mean_power_w = self.joules / elapsed
        return False


def set_power_cap(watts: int, index: int = 0) -> bool:
    """Set the GPU power limit. Returns False on any failure (never raises)."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "-i", str(index), "-pl", str(watts)],
            capture_output=True, text=True, timeout=20,
        )
        return r.returncode == 0
    except Exception:
        return False


def hardware_info(index: int = 0) -> dict:
    try:
        b = NvmlBackend(index)
        return {"gpu": b.gpu_name(), "vram_gb": b.vram_gb()}
    except Exception:
        return {"gpu": "unknown", "vram_gb": 0}


if __name__ == "__main__":
    with EnergyMeter() as m:
        time.sleep(5)
    print(f"5s window: {m.joules:.1f} J, mean {m.mean_power_w:.1f} W")
