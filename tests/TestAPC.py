import os
import unittest
from pynoc import APC

ENV_NOT_SET = "Please set environment variable: {0}."
TEST_APC_ENV_IP_ADDRESS = "APC_IP_ADDRESS"
TEST_ENV_PUBLIC_COMMUNITY = "APC_PUBLIC_COMMUNITY"
TEST_ENV_PRIVATE_COMMUNITY = "APC_PRIVATE_COMMUNITY"


class TestAPC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        apc_address = os.getenv(TEST_APC_ENV_IP_ADDRESS, None)
        if apc_address is None:
            raise EnvironmentError(ENV_NOT_SET.format(TEST_APC_ENV_IP_ADDRESS))
        public_community = os.getenv(TEST_ENV_PUBLIC_COMMUNITY, None)
        if public_community is None:
            raise EnvironmentError(
                ENV_NOT_SET.format(TEST_ENV_PUBLIC_COMMUNITY))
        private_community = os.getenv(TEST_ENV_PRIVATE_COMMUNITY, None)
        if private_community is None:
            raise EnvironmentError(
                ENV_NOT_SET.format(TEST_ENV_PRIVATE_COMMUNITY))
        cls.apc = APC(apc_address, public_community=public_community,
                      private_community=private_community)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "apc") and cls.apc is not None:
            del cls.apc

    def test_host(self):
        self.assertIsNotNone(self.apc.host)

    def test_vendor(self):
        self.assertIsNotNone(self.apc.vendor)

    def test_identification(self):
        self.assertIsNotNone(self.apc.identification)

    def test_location(self):
        self.assertIsNotNone(self.apc.location)

    def test_hardware_revision(self):
        self.assertIsNotNone(self.apc.hardware_revision)

    def test_firmware_revision(self):
        self.assertIsNotNone(self.apc.firmware_revision)

    def test_date_of_manufacture(self):
        self.assertIsNotNone(self.apc.date_of_manufacture)

    def test_model_number(self):
        self.assertIsNotNone(self.apc.model_number)

    def test_serial_number(self):
        self.assertIsNotNone(self.apc.serial_number)

    def test_num_outlets(self):
        self.assertIsNotNone(self.apc.num_outlets)
        self.assertGreater(self.apc.num_outlets, -1)

    def test_num_switched_outlets(self):
        self.assertIsNotNone(self.apc.num_switched_outlets)
        self.assertGreater(self.apc.num_switched_outlets, -1)

    def test_num_metered_outlets(self):
        self.assertIsNotNone(self.apc.num_metered_outlets)
        self.assertGreater(self.apc.num_metered_outlets, -1)

    def test_max_current(self):
        self.assertIsNotNone(self.apc.max_current)
        self.assertGreater(self.apc.max_current, -1)

    def test_voltage(self):
        self.assertIsNotNone(self.apc.voltage)
        self.assertGreater(self.apc.voltage, -1)

    def test_load_state(self):
        self.assertIsNotNone(self.apc.load_state)
        self.assertIn(self.apc.load_state,
                      ['lowLoad', 'normal', 'nearOverload', 'overload'])

    def test_current(self):
        self.assertIsNotNone(self.apc.current)
        self.assertGreater(self.apc.current, -1)

    def test_power(self):
        self.assertIsNotNone(self.apc.power)
        self.assertGreater(self.apc.power, -1)

    def test_current(self):
        self.assertIsNotNone(self.apc.current)
        self.assertGreater(self.apc.current, -1)

    def test_is_sensor_present(self):
        self.assertIsNotNone(self.apc.is_sensor_present)

    def test_sensor_name(self):
        self.assertIsNotNone(self.apc.sensor_name)

    def test_sensor_type(self):
        self.assertIsNotNone(self.apc.sensor_type)
        self.assertIn(self.apc.sensor_type,
                      ['temperatureOnly', 'temperatureHumidity', 'commsLost',
                       'notInstalled'])

    def test_sensor_comm_status(self):
        self.assertIsNotNone(self.apc.sensor_comm_status)
        self.assertIn(self.apc.sensor_comm_status,
                      ['notPresent', 'belowMin', 'belowLow', 'normal',
                       'aboveHigh', 'aboveMax'])

    def test_temperature(self):
        self.assertIsNotNone(self.apc.temperature)
        self.apc.use_centigrade = True
        self.assertIsNotNone(self.apc.temperature)
        self.apc.use_centigrade = False

    def test_humidity(self):
        self.assertIsNotNone(self.apc.humidity)

    def test_temperature_status(self):
        self.assertIsNotNone(self.apc.temperature_status)
        self.assertIn(self.apc.temperature_status,
                      ['notPresent', 'belowMin', 'belowLow', 'normal',
                       'aboveHigh', 'aboveMax'])

    def test_humidity_status(self):
        self.assertIsNotNone(self.apc.humidity_status)
        self.assertIn(self.apc.humidity_status,
                      ['notPresent', 'belowMin', 'belowLow', 'normal',
                       'aboveHigh', 'aboveMax'])

    def test_get_outlet_name(self):
        for num in range(1, self.apc.num_outlets + 1):
            self.assertIsNotNone(self.apc.get_outlet_name(num))

    def test_outlet_status(self):
        for num in range(1, self.apc.num_outlets + 1):
            self.assertIsNotNone(self.apc.outlet_status(num))
            self.assertIn(self.apc.outlet_status(num),
                          ['off', 'on'])
