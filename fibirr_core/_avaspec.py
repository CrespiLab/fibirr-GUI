"""Small ctypes adapter for the AvaSpec functions used by fibirr-core."""

import ctypes
from dataclasses import dataclass
import os
from pathlib import Path
import sys


MAX_PIXELS = 4096
INVALID_HANDLE = 1000
_IDENTITY_SIZE = 75


class FibirrError(RuntimeError):
    """Base error raised by the public fibirr-core API."""


class AvaSpecError(FibirrError):
    """Raised when the AvaSpec library cannot load or returns an error."""


@dataclass(frozen=True)
class DeviceInfo:
    """Identity reported by an attached Avantes spectrometer."""

    serial_number: str
    name: str
    status: int


class _AvsIdentity(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("serial_number", ctypes.c_char * 10),
        ("user_friendly_name", ctypes.c_char * 64),
        ("status", ctypes.c_ubyte),
    ]


class _MeasurementConfig(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("start_pixel", ctypes.c_uint16),
        ("stop_pixel", ctypes.c_uint16),
        ("integration_time_ms", ctypes.c_float),
        ("integration_delay", ctypes.c_uint32),
        ("averages", ctypes.c_uint32),
        ("dynamic_dark_enabled", ctypes.c_uint8),
        ("dynamic_dark_forget_percentage", ctypes.c_uint8),
        ("smoothing_pixels", ctypes.c_uint16),
        ("smoothing_model", ctypes.c_uint8),
        ("saturation_detection", ctypes.c_uint8),
        ("trigger_mode", ctypes.c_uint8),
        ("trigger_source", ctypes.c_uint8),
        ("trigger_source_type", ctypes.c_uint8),
        ("strobe_control", ctypes.c_uint16),
        ("laser_delay", ctypes.c_uint32),
        ("laser_width", ctypes.c_uint32),
        ("laser_wavelength", ctypes.c_float),
        ("store_to_ram", ctypes.c_uint16),
    ]


_IdentityBuffer = ctypes.c_byte * _IDENTITY_SIZE
_SpectrumBuffer = ctypes.c_double * MAX_PIXELS


class AvaSpecDriver:
    """Thin, lazy-loading adapter around the proprietary AvaSpec library."""

    def __init__(self, library_path=None):
        self._library_path = Path(library_path) if library_path else None
        self._library = None
        self._identities = {}

    def initialize(self):
        self._check(self._load().AVS_Init(0), "AVS_Init")

    def done(self):
        if self._library is not None:
            self._check(self._library.AVS_Done(), "AVS_Done")

    def list_devices(self):
        library = self._load()
        count = self._check(
            library.AVS_UpdateUSBDevices(), "AVS_UpdateUSBDevices"
        )
        if count == 0:
            self._identities = {}
            return ()

        identities = (_AvsIdentity * count)()
        required_size = ctypes.c_uint32()
        allocated_size = ctypes.sizeof(identities)
        result = library.AVS_GetList(
            allocated_size, ctypes.byref(required_size), identities
        )
        self._check(result, "AVS_GetList")
        if required_size.value > allocated_size:
            raise AvaSpecError(
                "AVS_GetList reported more devices than AVS_UpdateUSBDevices"
            )

        copied = [
            _AvsIdentity.from_buffer_copy(bytes(identity)) for identity in identities
        ]
        self._identities = {
            _decode(identity.serial_number): identity for identity in copied
        }
        return tuple(
            DeviceInfo(
                serial_number=_decode(identity.serial_number),
                name=_decode(identity.user_friendly_name),
                status=identity.status,
            )
            for identity in copied
        )

    def activate(self, serial_number):
        try:
            identity = self._identities[serial_number]
        except KeyError as error:
            raise AvaSpecError(
                f"device {serial_number!r} was not returned by AVS_GetList"
            ) from error
        raw_identity = _IdentityBuffer.from_buffer_copy(identity)
        handle = self._load().AVS_Activate(raw_identity)
        if handle < 0 or handle == INVALID_HANDLE:
            raise AvaSpecError(f"AVS_Activate failed with code {handle}")
        return handle

    def deactivate(self, handle):
        if not self._load().AVS_Deactivate(handle):
            raise AvaSpecError("AVS_Deactivate did not recognize the device handle")

    def get_pixel_count(self, handle):
        pixel_count = ctypes.c_uint16()
        self._check(
            self._load().AVS_GetNumPixels(handle, ctypes.byref(pixel_count)),
            "AVS_GetNumPixels",
        )
        if not 1 <= pixel_count.value <= MAX_PIXELS:
            raise AvaSpecError(
                f"AVS_GetNumPixels returned invalid count {pixel_count.value}"
            )
        return pixel_count.value

    def get_wavelengths(self, handle, pixel_count):
        wavelengths = _SpectrumBuffer()
        self._check(
            self._load().AVS_GetLambda(handle, ctypes.byref(wavelengths)),
            "AVS_GetLambda",
        )
        return tuple(wavelengths[:pixel_count])

    def set_high_resolution_adc(self, handle, enabled):
        self._check(
            self._load().AVS_UseHighResAdc(handle, enabled),
            "AVS_UseHighResAdc",
        )

    def prepare_measurement(self, handle, pixel_count, settings):
        config = _MeasurementConfig(
            start_pixel=0,
            stop_pixel=pixel_count - 1,
            integration_time_ms=settings.integration_time_ms,
            integration_delay=0,
            averages=settings.averages,
        )
        self._check(
            self._load().AVS_PrepareMeasure(handle, ctypes.byref(config)),
            "AVS_PrepareMeasure",
        )

    def start_measurement(self, handle):
        self._check(self._load().AVS_Measure(handle, 0, 1), "AVS_Measure")

    def data_ready(self, handle):
        return bool(self._load().AVS_PollScan(handle))

    def get_scope_data(self, handle, pixel_count):
        timestamp = ctypes.c_uint32()
        intensities = _SpectrumBuffer()
        self._check(
            self._load().AVS_GetScopeData(
                handle, ctypes.byref(timestamp), ctypes.byref(intensities)
            ),
            "AVS_GetScopeData",
        )
        return timestamp.value, tuple(intensities[:pixel_count])

    def stop_measurement(self, handle):
        self._check(self._load().AVS_StopMeasure(handle), "AVS_StopMeasure")

    def _load(self):
        if self._library is not None:
            return self._library
        path = self._resolve_library_path()
        try:
            if sys.platform == "win32":
                self._library = ctypes.WinDLL(str(path))
            else:
                self._library = ctypes.CDLL(str(path))
        except OSError as error:
            raise AvaSpecError(f"cannot load AvaSpec library {path}: {error}") from error
        self._configure_signatures()
        return self._library

    def _resolve_library_path(self):
        if self._library_path is not None:
            return self._library_path.expanduser().resolve()

        environment_path = os.environ.get("AVASPEC_LIBRARY")
        if environment_path:
            return Path(environment_path).expanduser().resolve()

        if sys.platform == "win32":
            name = "avaspecx64.dll" if ctypes.sizeof(ctypes.c_void_p) == 8 else "avaspec.dll"
            candidates = (
                Path.cwd() / "avantes" / name,
                Path.cwd() / name,
                Path(__file__).resolve().parent.parent / "avantes" / name,
            )
        elif sys.platform == "darwin":
            candidates = (Path("/usr/local/lib/libavs.0.dylib"),)
        else:
            candidates = (Path("/usr/local/lib/libavs.so.0"),)
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
        raise AvaSpecError(
            "AvaSpec library not found; pass library_path or set AVASPEC_LIBRARY"
        )

    def _configure_signatures(self):
        library = self._library
        library.AVS_Init.argtypes = [ctypes.c_int]
        library.AVS_Init.restype = ctypes.c_int
        library.AVS_Done.argtypes = []
        library.AVS_Done.restype = ctypes.c_int
        library.AVS_UpdateUSBDevices.argtypes = []
        library.AVS_UpdateUSBDevices.restype = ctypes.c_int
        library.AVS_GetList.argtypes = [
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(_AvsIdentity),
        ]
        library.AVS_GetList.restype = ctypes.c_int
        library.AVS_Activate.argtypes = [_IdentityBuffer]
        library.AVS_Activate.restype = ctypes.c_int
        library.AVS_Deactivate.argtypes = [ctypes.c_int]
        library.AVS_Deactivate.restype = ctypes.c_bool
        library.AVS_GetNumPixels.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_uint16),
        ]
        library.AVS_GetNumPixels.restype = ctypes.c_int
        library.AVS_GetLambda.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(_SpectrumBuffer),
        ]
        library.AVS_GetLambda.restype = ctypes.c_int
        library.AVS_UseHighResAdc.argtypes = [ctypes.c_int, ctypes.c_bool]
        library.AVS_UseHighResAdc.restype = ctypes.c_int
        library.AVS_PrepareMeasure.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(_MeasurementConfig),
        ]
        library.AVS_PrepareMeasure.restype = ctypes.c_int
        window_handle = ctypes.c_void_p if sys.platform == "win32" else ctypes.c_int
        library.AVS_Measure.argtypes = [ctypes.c_int, window_handle, ctypes.c_uint16]
        library.AVS_Measure.restype = ctypes.c_int
        library.AVS_PollScan.argtypes = [ctypes.c_int]
        library.AVS_PollScan.restype = ctypes.c_bool
        library.AVS_GetScopeData.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(_SpectrumBuffer),
        ]
        library.AVS_GetScopeData.restype = ctypes.c_int
        library.AVS_StopMeasure.argtypes = [ctypes.c_int]
        library.AVS_StopMeasure.restype = ctypes.c_int

    @staticmethod
    def _check(result, function_name):
        if result < 0:
            raise AvaSpecError(f"{function_name} failed with code {result}")
        return result


def _decode(value):
    return bytes(value).split(b"\0", 1)[0].decode("ascii", errors="replace")
