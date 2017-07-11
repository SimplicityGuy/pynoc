import os
import unittest
from pynoc import CiscoSwitch

ENV_NOT_SET = "Please set environment variable: {0}."
TEST_CISCO_ENV_IP_ADDRESS = "CISCO_IP_ADDRESS"
TEST_ENV_USERNAME = "CISCO_USERNAME"
TEST_ENV_PASSWORD = "CISCO_PASSWORD"
TEST_ENV_ENABLE_PASSWORD = "CISCO_ENABLE_PASSWORD"


class TestCisco(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cisco_address = os.getenv(TEST_CISCO_ENV_IP_ADDRESS, None)
        if cisco_address is None:
            raise EnvironmentError(
                ENV_NOT_SET.format(TEST_CISCO_ENV_IP_ADDRESS)
            )
        cisco_username = os.getenv(TEST_ENV_USERNAME, None)
        if cisco_username is None:
            raise EnvironmentError(ENV_NOT_SET.format(TEST_ENV_USERNAME))
        cisco_password = os.getenv(TEST_ENV_PASSWORD, None)
        if cisco_password is None:
            raise EnvironmentError(ENV_NOT_SET.format(TEST_ENV_PASSWORD))
        cisco_enable_password = os.getenv(TEST_ENV_ENABLE_PASSWORD, None)
        if cisco_address is None:
            raise EnvironmentError(
                ENV_NOT_SET.format(TEST_ENV_ENABLE_PASSWORD))
        cls.cisco_enable_password = cisco_enable_password
        cls.cisco = CiscoSwitch(cisco_address, cisco_username, cisco_password)
        cls.port = "Gi1/0/1"

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "cisco") and cls.cisco is not None:
            del cls.cisco

    def test_0_connect(self):
        self.assertFalse(self.cisco.connected)
        self.cisco.connect()
        self.assertTrue(self.cisco.connected)

    def test_1_enable(self):
        self.cisco.enable(self.cisco_enable_password)

    def test_2_set_terminal_length(self):
        self.cisco.set_terminal_length()

    def test_ipdt(self):
        self.assertIsNotNone(self.cisco.ipdt())

    def test_mac_address_table(self):
        self.assertIsNotNone(self.cisco.mac_address_table())

    def test_host(self):
        self.assertIsNotNone(self.cisco.host)

    def test_shorthand_notation(self):
        shorthand = self.cisco._shorthand_port_notation("FastEthernet1/0/1")
        self.assertEqual(shorthand, "Fa1/0/1")
        shorthand = self.cisco._shorthand_port_notation("GigabitEthernet1/0/1")
        self.assertEqual(shorthand, "Gi1/0/1")
        shorthand = self.cisco._shorthand_port_notation(
            "TenGigabitEthernet1/0/1"
        )
        self.assertEqual(shorthand, "Ten1/0/1")

    def test_is_poe(self):
        self.assertIsNotNone(self.cisco.is_poe(self.port))

    def test_vlan(self):
        self.assertIsNot(self.cisco.vlan(self.port), -1)

    def test_version_1(self):
        self.assertIsNotNone(self.cisco.version)

    def test_version_2(self):
        self.assertIsNotNone(self.cisco.version)

    def test_zzz_disconnect(self):
        self.assertTrue(self.cisco.connected)
        self.cisco.disconnect()
        self.assertFalse(self.cisco.connected)

    def test_00_standalone_vlan(self):
        self.assertFalse(self.cisco.connected)
        self.cisco.connect()
        self.assertTrue(self.cisco.connected)
        self.cisco.enable(self.cisco_enable_password)
        self.cisco.set_terminal_length()
        self.assertIsNot(self.cisco.vlan(self.port), -1)
        self.cisco.disconnect()

    def test_00_defs_while_disconnected(self):
        self.assertFalse(self.cisco.connected)
        self.cisco.enable(self.cisco_enable_password)
        self.cisco.set_terminal_length()
        self.assertIs(self.cisco.vlan(self.port), -1)
        self.assertIsNone(self.cisco.ipdt())
        self.assertIsNone(self.cisco.mac_address_table())
        self.assertIsNone(self.cisco.version)
        self.assertFalse(self.cisco.poe_on(self.port))
        self.assertFalse(self.cisco.poe_off(self.port))
        self.assertIs(self.cisco.is_poe(self.port), "unknown")
