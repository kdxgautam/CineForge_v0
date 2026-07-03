import ctypes
import os
import site
from pathlib import Path


def configure_cuda_runtime() -> None:
    """Expose uv-installed CUDA/cuDNN shared libraries to child processes."""

    lib_dirs = []

    for base in site.getsitepackages():
        site_path = Path(base)
        candidates = [
            site_path / "nvidia" / "cudnn" / "lib",
            site_path / "nvidia" / "cublas" / "lib",
            site_path / "nvidia" / "cuda_nvrtc" / "lib",
            site_path / "ctranslate2.libs",
        ]
        lib_dirs.extend(str(path) for path in candidates if path.exists())

    if not lib_dirs:
        return

    existing = os.environ.get("LD_LIBRARY_PATH", "")
    parts = [part for part in existing.split(":") if part]
    merged = []

    for path in [*lib_dirs, *parts]:
        if path not in merged:
            merged.append(path)

    os.environ["LD_LIBRARY_PATH"] = ":".join(merged)

    for directory in lib_dirs:
        for library in Path(directory).glob("*.so*"):
            try:
                ctypes.CDLL(str(library), mode=ctypes.RTLD_GLOBAL)
            except OSError:
                pass


def runtime_env() -> dict[str, str]:
    configure_cuda_runtime()
    return os.environ.copy()
