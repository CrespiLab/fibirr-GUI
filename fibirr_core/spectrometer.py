"""High-level, GUI-independent Avantes spectrometer interface."""

from dataclasses import dataclass
from pathlib import Path
import time

from ._avaspec import AvaSpecDriver, AvaSpecError, DeviceInfo, FibirrError


class DeviceNotFoundError(FibirrError):
    """Raised when no matching spectrometer is connected."""


class SpectrumTimeoutError(FibirrError):
    """Raised when a spectrum is not ready before the acquisition timeout."""


@dataclass(frozen=True)
class AcquisitionSettings:
    """Settings that may change between acquisitions."""

    integration_time_ms: float = 5.0
    averages: int = 1
    high_resolution_adc: bool = True

    def __post_init__(self):
        if self.integration_time_ms <= 0:
            raise ValueError("integration_time_ms must be positive")
        if not isinstance(self.averages, int) or isinstance(self.averages, bool):
            raise TypeError("averages must be an integer")
        if self.averages < 1:
            raise ValueError("averages must be at least 1")


@dataclass(frozen=True)
class Spectrum:
    """One raw intensity spectrum returned by the spectrometer."""

    wavelengths_nm: tuple[float, ...]
    intensities: tuple[float, ...]
    timestamp_ticks: int

    def __post_init__(self):
        if len(self.wavelengths_nm) != len(self.intensities):
            raise ValueError("wavelength and intensity arrays must have equal length")

    @property
    def timestamp_seconds(self):
        """Instrument timestamp in seconds (one AvaSpec tick is 10 microseconds)."""

        return self.timestamp_ticks * 10e-6


class AvantesSpectrometer:
    """Own an AvaSpec connection and acquire raw spectra.

    ``driver`` is an internal test seam. Normal callers should provide only a
    DLL path and, when needed, a serial number.
    """

    def __init__(
        self,
        serial_number=None,
        library_path: str | Path | None = None,
        *,
        driver=None,
    ):
        self.serial_number = serial_number
        self._driver = driver or AvaSpecDriver(library_path)
        self._initialized = False
        self._handle = None
        self._device = None
        self._wavelengths = ()
        self._measuring = False

    @property
    def connected(self):
        return self._handle is not None

    @property
    def device(self):
        if self._device is None:
            raise FibirrError("spectrometer is not connected")
        return self._device

    @property
    def wavelengths_nm(self):
        if not self.connected:
            raise FibirrError("spectrometer is not connected")
        return self._wavelengths

    def connect(self):
        """Initialize AvaSpec and connect to the selected USB spectrometer."""

        if self.connected:
            return self

        try:
            self._driver.initialize()
            self._initialized = True
            devices = self._driver.list_devices()
            self._device = self._select_device(devices)
            self._handle = self._driver.activate(self._device.serial_number)
            pixel_count = self._driver.get_pixel_count(self._handle)
            self._wavelengths = tuple(
                self._driver.get_wavelengths(self._handle, pixel_count)
            )
        except Exception:
            self.close()
            raise
        return self

    def acquire(self, settings=None, *, timeout_s=None):
        """Acquire one raw spectrum using polling rather than GUI callbacks."""

        if not self.connected:
            raise FibirrError("spectrometer is not connected")
        settings = settings or AcquisitionSettings()
        if not isinstance(settings, AcquisitionSettings):
            raise TypeError("settings must be an AcquisitionSettings instance")
        if timeout_s is None:
            exposure_s = settings.integration_time_ms * settings.averages / 1000
            timeout_s = max(5.0, exposure_s + 2.0)
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")

        pixel_count = len(self._wavelengths)
        self._driver.set_high_resolution_adc(
            self._handle, settings.high_resolution_adc
        )
        self._driver.prepare_measurement(self._handle, pixel_count, settings)
        self._driver.start_measurement(self._handle)
        self._measuring = True
        deadline = time.monotonic() + timeout_s

        try:
            while not self._driver.data_ready(self._handle):
                if time.monotonic() >= deadline:
                    self._driver.stop_measurement(self._handle)
                    raise SpectrumTimeoutError(
                        f"spectrum was not ready after {timeout_s:g} seconds"
                    )
                time.sleep(0.001)
            timestamp, intensities = self._driver.get_scope_data(
                self._handle, pixel_count
            )
        finally:
            self._measuring = False

        return Spectrum(self._wavelengths, tuple(intensities), timestamp)

    def stop(self):
        """Stop the active acquisition, if any."""

        if self.connected and self._measuring:
            self._driver.stop_measurement(self._handle)
            self._measuring = False

    def close(self):
        """Release the device and AvaSpec library resources."""

        try:
            self.stop()
            if self._handle is not None:
                self._driver.deactivate(self._handle)
        finally:
            self._handle = None
            self._device = None
            self._wavelengths = ()
            if self._initialized:
                self._driver.done()
                self._initialized = False

    def _select_device(self, devices):
        if not devices:
            raise DeviceNotFoundError("no Avantes USB spectrometer found")
        if self.serial_number is None:
            return devices[0]
        for device in devices:
            if device.serial_number == self.serial_number:
                return device
        available = ", ".join(device.serial_number for device in devices)
        raise DeviceNotFoundError(
            f"spectrometer {self.serial_number!r} not found; available: {available}"
        )

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


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
