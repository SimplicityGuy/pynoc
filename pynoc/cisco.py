"""Cisco Switch control object."""

import logging

from netaddr import EUI, mac_unix_expanded
from paramiko import SSHClient, AutoAddPolicy


class CiscoSwitch(object):
    """Cisco switch control."""

    MAX_COMMAND_READ = 16

    CMD_LOGIN_SIGNALS = ['>', '#']
    CMD_GENERIC_SIGNALS = ['#']

    CMD_ENABLE = 'enable'
    CMD_ENABLE_SIGNALS = ['Password']

    CMD_VERSION = 'sh version'
    CMD_VERSION_SIGNALS = ['BOOTLDR']

    CMD_TERMINAL_LENGTH = 'terminal length 0'

    CMD_IPDT = 'sh ip device track all'
    CMD_IPDT_SIGNALS = ['Enabled interfaces']

    CMD_MAC_ADDRESS_TABLE = 'sh mac address-table'
    CMD_MAC_ADDRESS_TABLE_SIGNALS = ['Total Mac Addresses']

    CMD_CONFIGURE = 'configure terminal'
    CMD_CONFIGURE_INTERFACE = 'int {0}'
    CMD_CONFIGURE_SIGNALS = ['(config)#', '(config-if)#']

    CMD_POWER_OFF = 'power inline never'
    CMD_POWER_ON = 'power inline auto'

    CMD_VLAN_MODE_ACCESS = 'switchport mode access'
    CMD_VLAN_SET = 'switchport access vlan {0}'

    CMD_END = 'end'

    PORT_NOTATION = {'fastethernet': 'Fa',
                     'gigabitethernet': 'Gi',
                     'tengigabitethernet': 'Ten'}

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
        self._shell = None
        self._enable_needed = False
        self._ready = False

        self._logger = logging.getLogger(__name__)
        self._logger.addHandler(logging.NullHandler())

    def connect(self):
        """Connect to the switch.

        :return:
        """
        self._client = SSHClient()
        self._client.set_missing_host_key_policy(AutoAddPolicy())
        self._client.connect(self._host,
                             username=self._username,
                             password=self._password,
                             allow_agent=False,
                             look_for_keys=False)
        self._shell = self._client.invoke_shell()
        self._ready = True
        output = self._send_command('', self.CMD_LOGIN_SIGNALS)
        if output.find('>') > 0:
            self._enable_needed = True
            self._ready = False
        else:
            self.set_terminal_length()

    def disconnect(self):
        """Disconnect from the switch.

        :return:
        """
        if self._client is not None:
            self._client.close()
            self._client = None
            self._shell = None
            self._ready = False

    def enable(self, password):
        """Put the switch in enable mode.

        :param password: password to use to enable
        :return:
        """
        if self.connected and self._enable_needed:
            self._send_command(self.CMD_ENABLE, self.CMD_ENABLE_SIGNALS)
            self._send_command(password,
                               self.CMD_GENERIC_SIGNALS,
                               log=False)
            self._ready = True
            self.set_terminal_length()

    def set_terminal_length(self):
        """Set terminal length.

        :return:
        """
        if not self._ready:
            return

        self._send_command(self.CMD_TERMINAL_LENGTH, self.CMD_GENERIC_SIGNALS)

    def ipdt(self):
        """IP Device Tracking (IPDT) information.

        :return: IPDT information
        """
        if self._ready:
            output = self._send_command(self.CMD_IPDT,
                                        self.CMD_IPDT_SIGNALS)
            return CiscoSwitch._parse_ipdt_output(output)
        return None

    def mac_address_table(self, ignore_port=None):
        """MAC Address Table Information.

        :param ignore_port: port to ignore, e.g. Gi1/0/48
        :return: ARP information
        """
        if not self._ready:
            return None

        output = self._send_command(self.CMD_MAC_ADDRESS_TABLE,
                                    self.CMD_MAC_ADDRESS_TABLE_SIGNALS)
        return self._parse_mac_address_table_output(output,
                                                    ignore_port=ignore_port)

    def poe_on(self, port):
        """Enable a port for POE.

        :param port: port to enable POE on, e.g. Gi1/0/1
        :return:
        """
        if not self._ready:
            return

        port = self._shorthand_port_notation(port)
        cmds = [(self.CMD_CONFIGURE, self.CMD_CONFIGURE_SIGNALS),
                (self.CMD_CONFIGURE_INTERFACE.format(port),
                 self.CMD_CONFIGURE_SIGNALS),
                (self.CMD_POWER_ON, self.CMD_CONFIGURE_SIGNALS),
                (self.CMD_END, self.CMD_GENERIC_SIGNALS)]
        self._send_commands(cmds)

    def poe_off(self, port):
        """Disable a port for POE.

        :param port: port to disable POE on, e.g. Gi1/0/1
        :return:
        """
        if not self._ready:
            return

        port = self._shorthand_port_notation(port)
        cmds = [(self.CMD_CONFIGURE, self.CMD_CONFIGURE_SIGNALS),
                (self.CMD_CONFIGURE_INTERFACE.format(port),
                 self.CMD_CONFIGURE_SIGNALS),
                (self.CMD_POWER_OFF, self.CMD_CONFIGURE_SIGNALS),
                (self.CMD_END, self.CMD_GENERIC_SIGNALS)]
        self._send_commands(cmds)

    def change_vlan(self, port, vlan):
        """Change the VLAN assignment on a port.

        :param port: port to change VLAN assignment on, e.g. Gi1/0/1
        :param vlan: VLAN id
        :return:
        """
        if not self._ready:
            return

        port = self._shorthand_port_notation(port)
        cmds = [(self.CMD_CONFIGURE, self.CMD_CONFIGURE_SIGNALS),
                (self.CMD_CONFIGURE_INTERFACE.format(port),
                 self.CMD_CONFIGURE_SIGNALS),
                (self.CMD_VLAN_MODE_ACCESS, self.CMD_CONFIGURE_SIGNALS),
                (self.CMD_VLAN_SET.format(vlan), self.CMD_CONFIGURE_SIGNALS),
                (self.CMD_END, self.CMD_GENERIC_SIGNALS)]
        self._send_commands(cmds)

    @property
    def version(self):
        """The Cisco IOS version.

        :return: The Cisco IOS version.
        """
        if self._version is None:
            if self._ready:
                output = self._send_command(self.CMD_VERSION,
                                            self.CMD_VERSION_SIGNALS)
                self._version = self._parse_version_output(output)
        return self._version

    @property
    def host(self):
        """The IP address or hostname of the switch.

        :return: IP address or hostname of the switch
        """
        return self._host

    @property
    def connected(self):
        """Switch connection status.

        :return: has a connection to the switch been made?
        """
        return self._shell is not None

    def _shorthand_port_notation(self, port):
        """Shorthand port notation.

        Takes a port name, such as Gi1/0/48 or GigabitEthernet1/0/48 and
        returns the shorthand notation.

        :param port: port name
        :return: shorthand port name
        """
        if not port:
            return

        lower = port.lower()
        output = port

        if any(lower.find(port) == 0 for port in self.PORT_NOTATION.keys()):
            for item in self.PORT_NOTATION.items():
                if lower.startswith(item[0]):
                    output = lower.replace(item[0], item[1])
                    break

        return output

    def _send_commands(self, commands):
        """Send a list of commands to the SSH shell.

        :param commands: list of commands
        """
        for command in commands:
            self._send_command(command[0], command[1])

    def _send_command(self, command, signals, log=True):
        """Send a command to the SSH shell.

        Sends a command to the SSH shell and waits for the signals to arrive.

        :param command: command to send
        :param signals: signals to wait for
        :param log: specifies if this command should be logged
        :return: output of the command
        """
        send_command = command + '\n'
        if log:
            self._logger.info('Sending command: %s', send_command)

        self._shell.send(send_command)

        read_buffer = ''
        while not any(read_buffer.find(signal) > -1 for signal in signals):
            read_buffer += self._shell.recv(self.MAX_COMMAND_READ)

        if log:
            self._logger.debug('Received output: %s', read_buffer)

        # Manually flush the rest of the buffer.
        while self._shell.recv_ready():
            self._shell.recv(self.MAX_COMMAND_READ)

        return read_buffer

    @staticmethod
    def _parse_version_output(output):
        """Version parsing.

        :param output: the output of the command
        :return: version string
        """
        lines = [line.strip() for line in output.splitlines()]
        version = ''
        search = True
        while len(lines) > 0 and search:
            line = lines.pop()

            if line.find('Cisco IOS') < 0:
                continue

            version_info = line.split(',')

            if len(version_info) > 1:
                version = version_info[2].strip()
                version = version[8:]
                search = False

        return version

    def _parse_mac_address_table_output(self, output, ignore_port=None):
        """Mac Address Table parsing.

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
        lines.append('')
        while len(lines) > 0:
            line = lines.pop()

            # Table entries will always have a '.' for the MAC address.
            # If there isn't one it's not a row we care about.
            if line.find('.') < 0:
                continue

            values = [entry for entry in line.split() if entry]

            # Ignore non-physical ports
            port_types = self.PORT_NOTATION.values()
            if all(values[3].lower().find(port.lower()) != 0
                   for port in port_types):
                continue

            # If the ignore_port is specified and is the port in question,
            # ignore it.
            ignore_port = self._shorthand_port_notation(ignore_port)
            if ignore_port and values[3] == ignore_port:
                continue

            lookup.append(
                {
                    'mac': EUI(values[1], dialect=mac_unix_expanded),
                    'interface': values[3]
                }
            )
        return sorted(lookup, key=lambda k: k['interface'])

    @staticmethod
    def _parse_ipdt_output(output):
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
        lines.append('')
        while len(lines) > 0:
            line = lines.pop()

            # Table entries will always have a '.' for the MAC address.
            # If there isn't one it's not a row we care about.
            if line.find('.') < 0:
                continue

            values = [entry for entry in line.split() if entry]

            # Ignore any 'INACTIVE' entries, meaning that there hasn't been
            # traffic from that MAC Address is has likely been unplugged.
            if values[4] == 'INACTIVE':
                continue

            lookup.append(
                {
                    'ip': values[0],
                    'mac': EUI(values[1], dialect=mac_unix_expanded),
                    'interface': values[3]
                }
            )
        return sorted(lookup, key=lambda k: k['interface'])
