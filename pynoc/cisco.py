"""Cisco Switch control object."""

import logging
import warnings

from netaddr import EUI, mac_unix_expanded
from netmiko import ConnectHandler


def deprecated(func):
    """Decorate a deprecated function to warn when it is called.

    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.
    """

    def new_func(*args, **kwargs):
        """Set the warning message."""
        warnings.warn(
            "Call to deprecated function {}.".format(func.__name__),
            category=DeprecationWarning,
        )
        return func(*args, **kwargs)

    new_func.__name__ = func.__name__
    new_func.__doc__ = func.__doc__
    new_func.__dict__.update(func.__dict__)

    return new_func


class CiscoSwitch(object):
    """Cisco switch control."""

    # pylint: disable=len-as-condition
    # Parsing command line output has uncertain lengths

    MAX_COMMAND_READ = 16

    CMD_VERSION = "sh version"
    CMD_VERSION_SIGNALS = ["BOOTLDR"]

    CMD_IPDT = "sh ip device track all"

    CMD_MAC_ADDRESS_TABLE = "sh mac address-table"

    CMD_POWER_OFF = "power inline never"
    CMD_POWER_ON = "power inline auto"
    CMD_POWER_LIMIT = "power inline {0} max {1}"
    CMD_POWER_LIMIT_AUTO = "auto"
    CMD_POWER_LIMIT_STATIC = "static"
    CMD_POWER_SHOW = "sh power inline {0}"

    CMD_CONFIGURE_INTERFACE = "int {0}"

    CMD_VLAN_MODE_ACCESS = "switchport mode access"
    CMD_VLAN_SET = "switchport access vlan {0}"
    CMD_VLAN_SHOW = "sh vlan"

    CMD_CARRIAGE_RETURN = "\n"

    PORT_NOTATION = {
        "fastethernet": "Fa",
        "gigabitethernet": "Gi",
        "tengigabitethernet": "Ten",
    }

    def __init__(self, hostname_or_ip_address, username, password):
        """Initialize the CiscoSwitch object.

        :param hostname_or_ip_address: host name or ip address
        :param username: username to login with
        :param password: password to use with username
        :return: CiscoSwitch object
        """
        self._host = hostname_or_ip_address
        self._version = None
        self._username = username
        self._password = password
        self._client = None

        self._logger = logging.getLogger(__name__)
        self._logger.addHandler(logging.NullHandler())

    def connect(self):
        """Connect to the switch.

        :return:
        """
        self._client = ConnectHandler(
            device_type="cisco_ios",
            ip=self._host,
            username=self._username,
            password=self._password,
        )

    def disconnect(self):
        """Disconnect from the switch.

        :return:
        """
        if self._client is not None:
            self._client.disconnect()
            self._client = None

    def enable(self, password):
        """Put the switch in enable mode.

        :param password: password to use to enable
        :return:
        """
        if not self.connected:
            return

        self._client.secret = password
        self._client.enable()

    @deprecated
    def set_terminal_length(self):
        """Set terminal length.

        :return:
        """
        pass

    def ipdt(self):
        """IP Device Tracking (IPDT) information.

        :return: IPDT information
        """
        if not self.connected:
            return None

        output = self._send_command(self.CMD_IPDT)
        return self._parse_ipdt_output(output)

    def mac_address_table(self, ignore_port=None):
        """MAC Address Table Information.

        :param ignore_port: port to ignore, e.g. Gi1/0/48
        :return: ARP information
        """
        if not self.connected:
            return None

        output = self._send_command(self.CMD_MAC_ADDRESS_TABLE)
        return self._parse_mac_address_table_output(
            output, ignore_port=ignore_port
        )

    def poe_on(self, port):
        """Enable a port for POE.

        :param port: port to enable POE on, e.g. Gi1/0/1
        :return: True if the command succeeded, False otherwise
        """
        if not self.connected:
            return False

        port = self._shorthand_port_notation(port)
        cmds = [self.CMD_CONFIGURE_INTERFACE.format(port), self.CMD_POWER_ON]
        self._send_config(cmds)

        verify = self._send_command(self.CMD_POWER_SHOW.format(port))
        matches, _, _ = CiscoSwitch._verify_poe_status(verify, port, "on")
        return matches

    def poe_off(self, port):
        """Disable a port for POE.

        :param port: port to disable POE on, e.g. Gi1/0/1
        :return: True if the command succeeded, False otherwise
        """
        if not self.connected:
            return False

        port = self._shorthand_port_notation(port)
        cmds = [self.CMD_CONFIGURE_INTERFACE.format(port), self.CMD_POWER_OFF]
        self._send_config(cmds)

        verify = self._send_command(self.CMD_POWER_SHOW.format(port))
        matches, _, _ = CiscoSwitch._verify_poe_status(verify, port, "off")
        return matches

    def poe_limit(self, port, milliwatts_limit, static=True):
        """Enable a port for POE, but limit the maximum wattage.

        The default option used is "static", because it ensures the
        power limit is set regardless. The side-effect is that this
        is likely to remove and reapply power to the port if it is
        currently set to "auto", cycling any powered device (PD)
        connected to it.

        :param port: port to enable POE on, e.g. Gi1/0/1
        :param milliwatts_limit: the maximum wattage,
            given in milliwatts, e.g. 15400. Cisco documentation
            gives 4000 to 30000 as the valid range.
        :param static: whether to use the "static" option (default)
            or "auto"
        """
        if not self.connected:
            return False

        option = (
            self.CMD_POWER_LIMIT_STATIC if static else self.CMD_POWER_LIMIT_AUTO
        )
        port = self._shorthand_port_notation(port)
        cmds = [
            self.CMD_CONFIGURE_INTERFACE.format(port),
            self.CMD_POWER_LIMIT.format(option, milliwatts_limit),
        ]
        self._send_config(cmds)

        verify = self._send_command(self.CMD_POWER_SHOW.format(port))
        matches, _, _ = CiscoSwitch._verify_poe_status(verify, port, option)
        return matches

    def is_poe(self, port):
        """Get the POE state for a port.

        :param port: port to determine state of, e.g. Gi1/0/1
        :return: milliwatts_limit (a non-zero integer), evaluating to True if
            POE is enabled, else 0 (False).
        """
        if not self.connected:
            return 0

        port = self._shorthand_port_notation(port)
        verify = self._send_command(self.CMD_POWER_SHOW.format(port))
        _, poe, limit = CiscoSwitch._verify_poe_status(verify, port, "unknown")
        return 0 if poe == "off" else limit

    def change_vlan(self, port, vlan):
        """Change the VLAN assignment on a port.

        :param port: port to change VLAN assignment on, e.g. Gi1/0/1
        :param vlan: VLAN id
        :return: True if the command succeeded, False otherwise
        """
        if not self.connected:
            return False

        port = self._shorthand_port_notation(port)
        cmds = [
            self.CMD_CONFIGURE_INTERFACE.format(port),
            self.CMD_VLAN_MODE_ACCESS,
            self.CMD_VLAN_SET.format(int(vlan)),
        ]
        self._send_config(cmds)

        verify = self._send_command(self.CMD_VLAN_SHOW)
        matches, _ = CiscoSwitch._verify_vlan_status(verify, port, int(vlan))
        return matches

    def vlan(self, port):
        """Get the VLAN assignment on a port.

        :param port: port to determine VLAN assignment on, e.g. Gi1/0/1
        :return: VLAN id
        """
        if not self.connected:
            return -1

        port = self._shorthand_port_notation(port)
        verify = self._send_command(self.CMD_VLAN_SHOW)
        _, vlan = CiscoSwitch._verify_vlan_status(verify, port, 0)
        return vlan

    @property
    def version(self):
        """Retrieve the Cisco IOS version.

        :return: The Cisco IOS version.
        """
        if not self.connected:
            return None

        if self._version is None:
            output = self._send_command(self.CMD_VERSION)
            self._version = self._parse_version_output(output)

        return self._version

    @property
    def host(self):
        """Retrieve the IP address or hostname of the switch.

        :return: IP address or hostname of the switch
        """
        return self._host

    @property
    def connected(self):
        """Switch connection status.

        :return: has a connection to the switch been made?
        """
        if self._client is None:
            return False

        self._send_command(self.CMD_CARRIAGE_RETURN)

        active_ssh = True
        try:
            self._client.find_prompt()
        except ValueError:
            active_ssh = False

        return active_ssh

    def _shorthand_port_notation(self, port):
        """Shorthand port notation.

        Takes a port name, such as Gi1/0/48 or GigabitEthernet1/0/48 and
        returns the shorthand notation.

        :param port: port name
        :return: shorthand port name
        """
        if port is None:
            return ""

        lower = port.lower()
        output = port

        if any(lower.find(port) == 0 for port in self.PORT_NOTATION):
            for item in self.PORT_NOTATION.items():
                if lower.startswith(item[0]):
                    output = lower.replace(item[0], item[1])
                    break

        return output

    def _send_command(self, command):
        """Send command.

        Sends a command to the switch.

        :param command: command to send
        :return: output of the command
        """
        read_buffer = ""
        if self._client is None:
            return read_buffer

        self._client.clear_buffer()
        read_buffer = self._client.send_command(command)

        return read_buffer

    def _send_config(self, configs):
        """Configure switch.

        Sends a series of configuration options to the switch.

        :param configs: config commands
        """
        if self._client is None:
            return

        self._client.clear_buffer()
        self._client.send_config_set(configs)

    @staticmethod
    def _parse_version_output(output):
        """Version parsing.

        :param output: the output of the command
        :return: version string
        """
        lines = [line.strip() for line in output.splitlines()]
        version = ""
        search = True
        while len(lines) > 0 and search:
            line = lines.pop()

            if line.find("Cisco IOS") < 0:
                continue

            version_info = line.split(",")

            if len(version_info) > 1:
                version = version_info[2].strip()
                version = version[8:]
                search = False

        return version

    def _parse_mac_address_table_output(self, output, ignore_port=None):
        """MAC Address Table parsing.

        Parses the output of 'sh mac address-table' command.

        :param output: the output of the command
                      Mac Address Table
            -------------------------------------------
            Vlan    Mac Address       Type        Ports
            ----    -----------       --------    -----
             All    0100.0ccc.cccc    STATIC      CPU
             <snip>
             All    ffff.ffff.ffff    STATIC      CPU
             601    000b.7866.5240    DYNAMIC     Gi1/0/48
             601    0013.20fe.56b4    DYNAMIC     Gi1/0/35
             <snip>
             Total Mac Addresses for this criterion: 59
        :param ignore_port: ignore this port
        :return: list of dicts containing device connection metrics
        """
        lookup = []
        lines = [line.strip() for line in output.splitlines()]
        lines.append("")
        while len(lines) > 0:
            line = lines.pop(0)

            # Table entries will always have a '.' for the MAC address.
            # If there isn't one it's not a row we care about.
            if line.find(".") < 0:
                continue

            values = [entry for entry in line.split() if entry]

            # Ignore non-physical ports
            port_types = self.PORT_NOTATION.values()
            if all(
                values[3].lower().find(port.lower()) != 0 for port in port_types
            ):
                continue

            # If the ignore_port is specified and is the port in question,
            # ignore it.
            ignore_port = self._shorthand_port_notation(ignore_port)
            if ignore_port is not None and ignore_port == values[3]:
                continue

            lookup.append(
                {
                    "mac": EUI(values[1], dialect=mac_unix_expanded),
                    "interface": self._shorthand_port_notation(values[3]),
                }
            )
        return sorted(lookup, key=lambda k: k["interface"])

    def _parse_ipdt_output(self, output):
        """IPDT output parsing.

        Parses the output of the `show ip device track` command.

        :param output: the output of the command
            IP Device Tracking = Enabled
            IP Device Tracking Probe Count = 3
            IP Device Tracking Probe Interval = 30
            IP Device Tracking Probe Delay Interval = 0
            -------------------------------------------------------------------
              IP Address     MAC Address   Vlan  Interface              STATE
            -------------------------------------------------------------------
            192.168.1.12     6cec.eb68.c86f  601  GigabitEthernet1/0/14  ACTIVE
            192.168.1.15     6cec.eb67.836c  601  GigabitEthernet1/0/12  ACTIVE
            <snip>

            Total number interfaces enabled: 47
            Enabled interfaces:
             Gi1/0/1, Gi1/0/2, Gi1/0/3, Gi1/0/4, Gi1/0/5, Gi1/0/6, Gi1/0/7,
             <snip>
        :return: list of dicts containing device connection metrics
        """
        lookup = []
        lines = [line.strip() for line in output.splitlines()]
        lines.append("")
        while len(lines) > 0:
            line = lines.pop(0)

            # Table entries will always have a '.' for the MAC address.
            # If there isn't one it's not a row we care about.
            if line.find(".") < 0:
                continue

            values = [entry for entry in line.split() if entry]

            # Ignore any 'INACTIVE' entries, meaning that there hasn't been
            # traffic from that MAC Address is has likely been unplugged.
            if values[4] == "INACTIVE":
                continue

            lookup.append(
                {
                    "ip": values[0],
                    "mac": EUI(values[1], dialect=mac_unix_expanded),
                    "interface": self._shorthand_port_notation(values[3]),
                }
            )
        return sorted(lookup, key=lambda k: k["interface"])

    @staticmethod
    def _verify_poe_status(output, port, state):
        """Verify that the given port is in the given state.

        :param output: the output of the command
            Interface Admin  Oper       Power   Device              Class Max
                                        (Watts)
            --------- ------ ---------- ------- ------------------- ----- ----
            Gi2/0/16  auto   on         15.4    Ieee PD             0     30.0

            Interface  AdminPowerMax   AdminConsumption
                         (Watts)           (Watts)
            ---------- --------------- --------------------

            Gi2/0/16              30.0                 15.4
        :param port: port to check
        :param state: expected state
        :return: (True, actual_state, milliwatts_limit) if the port is in the
            expected state, (False, actual_state, milliwatts_limit) otherwise.
        """
        if "on" in state:
            state = "auto"

        matches = False
        lines = [line.strip() for line in output.splitlines()]
        lines.append("")
        actual_state = "unknown"
        milliwatts_limit = 0
        while len(lines) > 0:
            line = lines.pop(0)

            # Table entries will always have a '/' for the interface.
            # If there isn't one it's not a row we care about.
            if line.find("/") < 0:
                continue

            values = [entry for entry in line.split() if entry]

            # Is this the port of interest?
            if values[0] != port:
                continue

            matches = state in values[1]
            actual_state = values[1]
            # The last column, "Max", gives Watts to the to tenths spot
            milliwatts_limit = int(float(values[-1]) * 1000.0)
            break

        return matches, actual_state, milliwatts_limit

    @staticmethod
    def _verify_vlan_status(output, port, vlan):
        """Verify that the given port is assigned to the given vlan.

        :param output:
            VLAN Name                             Status    Ports
            ---- -------------------------------- --------- ------------------
            1    default                          active    Te1/0/1, Te1/0/2
            701  NET-701                          active    Gi1/0/1, Gi1/0/2
            702  NET-702                          active    Gi1/0/8
            703  NET-703                          active    Gi1/0/7, Gi1/0/10
            704  NET-704                          active    Gi1/0/5, Gi1/0/9
            705  NET-705                          active

        :param port: port to check
        :param vlan: expected vlan
        :return: (True, actual vlan #) if the port is assigned to the expected
        vlan, (False, actual vlan #) otherwise
        """
        matches = False
        lines = [line.strip() for line in output.splitlines()]
        lines.append("")
        actual_vlan = -1
        current_vlan = -1
        while len(lines) > 0:
            line = lines.pop(0).replace(",", "")

            # Table entries will have a '/' for the ports.
            # If there isn't one it's not a row we care about, even if it's a
            # vlan with no ports assigned to it.
            if line.find("/") < 0:
                continue

            values = [entry for entry in line.split() if entry]
            if "active" in values:
                current_vlan = int(values[0])
                ports = values[3:]
            else:
                ports = values

            # Is the port of interest in the list of ports?
            if port not in ports:
                continue

            actual_vlan = current_vlan
            if actual_vlan == vlan:
                matches = True

        return matches, actual_vlan
