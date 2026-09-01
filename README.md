# fibirr-core

`fibirr-core` is a small, GUI-independent Python interface for acquiring spectra
from an Avantes spectrometer. It contains only the spectrometer lifecycle and
single-spectrum acquisition code needed by the FIBIRR setup.

The previous Qt interface, plotting, file handling, Arduino prototype, global
state, vendor demos, and historical copies have intentionally been removed.
Data processing and the forthcoming LED controller belong in separate modules
that can coordinate this package without changing its AvaSpec layer.

## Install

Python 3.12 or newer is required.

```powershell
python -m pip install -e .
```

The proprietary AvaSpec library is not distributed with this repository. Pass
its path when constructing the spectrometer, or set the `AVASPEC_LIBRARY`
environment variable. On 64-bit Windows the file is normally named
`avaspecx64.dll`.

## Acquire a spectrum

```python
from fibirr_core import AcquisitionSettings, AvantesSpectrometer

settings = AcquisitionSettings(integration_time_ms=5.0, averages=1)

with AvantesSpectrometer(library_path=r"C:\path\to\avaspecx64.dll") as spectrometer:
    spectrum = spectrometer.acquire(settings)

print(spectrum.wavelengths_nm[:5])
print(spectrum.intensities[:5])
```

If several spectrometers are attached, select one explicitly:

```python
spectrometer = AvantesSpectrometer(
    serial_number="A1234567",
    library_path=r"C:\path\to\avaspecx64.dll",
)
```

`AvantesSpectrometer` owns only spectrometer concerns: discovery, connection,
measurement configuration, polling, acquisition, stopping, and cleanup. A
future LED controller should remain independent and call `acquire()` from an
experiment coordinator. The private AvaSpec driver can also be replaced in
tests, so higher-level timing logic does not require hardware.

## Test

```powershell
python -m unittest discover -s tests -v
```

The unit tests use a fake driver. A real-device smoke test is still required on
the FIBIRR instrument whenever the AvaSpec DLL or spectrometer firmware changes.
