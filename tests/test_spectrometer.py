import unittest
from unittest.mock import patch

from fibirr_core import (
    AcquisitionSettings,
    AvantesSpectrometer,
    DeviceInfo,
    DeviceNotFoundError,
    FibirrError,
    Spectrum,
    SpectrumTimeoutError,
)


class FakeDriver:
    def __init__(self, devices=None, ready=True):
        self.devices = devices if devices is not None else (
            DeviceInfo("A123", "FIBIRR", 1),
        )
        self.ready = ready
        self.events = []
        self.prepared = None

    def initialize(self):
        self.events.append("initialize")

    def done(self):
        self.events.append("done")

    def list_devices(self):
        self.events.append("list_devices")
        return self.devices

    def activate(self, serial_number):
        self.events.append(("activate", serial_number))
        return 42

    def deactivate(self, handle):
        self.events.append(("deactivate", handle))

    def get_pixel_count(self, handle):
        return 3

    def get_wavelengths(self, handle, pixel_count):
        return (400.0, 500.0, 600.0)

    def set_high_resolution_adc(self, handle, enabled):
        self.events.append(("high_resolution_adc", enabled))

    def prepare_measurement(self, handle, pixel_count, settings):
        self.prepared = (handle, pixel_count, settings)

    def start_measurement(self, handle):
        self.events.append(("start", handle))

    def data_ready(self, handle):
        return self.ready

    def get_scope_data(self, handle, pixel_count):
        return 250_000, (10.0, 20.0, 30.0)

    def stop_measurement(self, handle):
        self.events.append(("stop", handle))


class SpectrometerTests(unittest.TestCase):
    def test_context_manager_connects_acquires_and_closes(self):
        driver = FakeDriver()
        settings = AcquisitionSettings(integration_time_ms=12.5, averages=3)

        with AvantesSpectrometer(driver=driver) as spectrometer:
            spectrum = spectrometer.acquire(settings)
            self.assertTrue(spectrometer.connected)
            self.assertEqual(spectrometer.device.serial_number, "A123")

        self.assertEqual(
            spectrum,
            Spectrum(
                wavelengths_nm=(400.0, 500.0, 600.0),
                intensities=(10.0, 20.0, 30.0),
                timestamp_ticks=250_000,
            ),
        )
        self.assertAlmostEqual(spectrum.timestamp_seconds, 2.5)
        self.assertEqual(driver.prepared, (42, 3, settings))
        self.assertEqual(driver.events[-2:], [("deactivate", 42), "done"])

    def test_requested_serial_number_is_selected(self):
        devices = (
            DeviceInfo("FIRST", "One", 1),
            DeviceInfo("SECOND", "Two", 1),
        )
        driver = FakeDriver(devices)

        spectrometer = AvantesSpectrometer("SECOND", driver=driver).connect()

        self.assertEqual(spectrometer.device.serial_number, "SECOND")
        self.assertIn(("activate", "SECOND"), driver.events)
        spectrometer.close()

    def test_missing_device_cleans_up_initialized_library(self):
        driver = FakeDriver(devices=())

        with self.assertRaisesRegex(DeviceNotFoundError, "no Avantes"):
            AvantesSpectrometer(driver=driver).connect()

        self.assertEqual(driver.events, ["initialize", "list_devices", "done"])

    def test_acquire_requires_connection(self):
        with self.assertRaisesRegex(FibirrError, "not connected"):
            AvantesSpectrometer(driver=FakeDriver()).acquire()

    def test_timeout_stops_measurement(self):
        driver = FakeDriver(ready=False)
        spectrometer = AvantesSpectrometer(driver=driver).connect()

        with (
            patch("fibirr_core.spectrometer.time.monotonic", side_effect=(0.0, 1.0)),
            patch("fibirr_core.spectrometer.time.sleep"),
            self.assertRaisesRegex(SpectrumTimeoutError, "0.5 seconds"),
        ):
            spectrometer.acquire(timeout_s=0.5)

        self.assertIn(("stop", 42), driver.events)
        spectrometer.close()

    def test_invalid_settings_are_rejected(self):
        invalid = (
            ({"integration_time_ms": 0}, ValueError),
            ({"averages": 0}, ValueError),
            ({"averages": 1.5}, TypeError),
            ({"averages": True}, TypeError),
        )
        for arguments, error in invalid:
            with self.subTest(arguments=arguments), self.assertRaises(error):
                AcquisitionSettings(**arguments)

    def test_spectrum_lengths_must_match(self):
        with self.assertRaisesRegex(ValueError, "equal length"):
            Spectrum((400.0,), (1.0, 2.0), 0)

    def test_constructing_default_spectrometer_does_not_load_dll(self):
        spectrometer = AvantesSpectrometer()
        self.assertFalse(spectrometer.connected)


if __name__ == "__main__":
    unittest.main()
