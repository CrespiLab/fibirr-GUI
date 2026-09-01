"""Minimal Avantes spectrometer acquisition API."""

from .spectrometer import (
    AcquisitionSettings,
    AvaSpecError,
    AvantesSpectrometer,
    DeviceInfo,
    DeviceNotFoundError,
    FibirrError,
    Spectrum,
    SpectrumTimeoutError,
)

__all__ = [
    "AcquisitionSettings",
    "AvaSpecError",
    "AvantesSpectrometer",
    "DeviceInfo",
    "DeviceNotFoundError",
    "FibirrError",
    "Spectrum",
    "SpectrumTimeoutError",
]
