"""APC Power Distribution Unit control object."""

import logging
from datetime import datetime

from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto import rfc1902
from retrying import retry, RetryError


class APC(object):
    """APC Power Distribution Unit."""

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods
    # This class requires more attributes and public methods to cover the
    # functionality of the device.

    ERROR_MSG = "SNMP {} of {} on {} failed."

    SNMP_VERSION_2_2C = 1
    SNMP_PORT = 161
    SNMP_TIMEOUT = 1.5  # 1.5 seconds
    SNMP_RETRIES = 2

    MAX_STOP_DELAY = 15000  # 15 seconds
    INTER_RETRY_WAIT = 500  # 0.5 seconds

    # APC PowerNet-MIB Base OID
    BASE_OID = (1, 3, 6, 1, 4, 1, 318, 1, 1, 26)

    # Static readonly data
    # PowerNet-MIB::rPDU2IdentName.1
    Q_NAME = BASE_OID + (2, 1, 3, 1)
    # PowerNet-MIB::rPDU2IdentLocation.1
    Q_LOCATION = BASE_OID + (2, 1, 4, 1)
    # PowerNet-MIB::rPDU2IdentHardwareRev.1
    Q_HARDWARE_REV = BASE_OID + (2, 1, 5, 1)
    # PowerNet-MIB::rPDU2IdentFirmwareRev.1
    Q_FIRMWARE_REV = BASE_OID + (2, 1, 6, 1)
    # PowerNet-MIB::rPDU2IdentDateOfManufacture.1
    Q_MANUFACTURE_DATE = BASE_OID + (2, 1, 7, 1)
    # PowerNet-MIB::rPDU2IdentModelNumber.1
    Q_MODEL_NUMBER = BASE_OID + (2, 1, 8, 1)
    # PowerNet-MIB::rPDU2IdentSerialNumber.1
    Q_SERIAL_NUMBER = BASE_OID + (2, 1, 9, 1)
    # PowerNet-MIB::rPDU2DevicePropertiesNumOutlets.1
    Q_NUM_OUTLETS = BASE_OID + (4, 2, 1, 4, 1)
    # PowerNet-MIB::rPDU2DevicePropertiesNumSwitchedOutlets.1
    Q_NUM_SWITCHED_OUTLETS = BASE_OID + (4, 2, 1, 5, 1)
    # PowerNet-MIB::rPDU2DevicePropertiesNumMeteredOutlets.1
    Q_NUM_METERED_OUTLETS = BASE_OID + (4, 2, 1, 6, 1)
    # PowerNet-MIB::rPDU2DevicePropertiesMaxCurrentRating.1
    Q_MAX_CURRENT_RATING = BASE_OID + (4, 2, 1, 9, 1)
    # PowerNet-MIB::rPDU2PhaseStatusVoltage.1
    Q_PHASE_VOLTAGE = BASE_OID + (6, 3, 1, 6, 1)

    # Dynamic readonly data
    # PowerNet-MIB::rPDU2PhaseStatusLoadState.1
    Q_PHASE_LOAD_STATE = BASE_OID + (6, 3, 1, 4, 1)
    # PowerNet-MIB::rPDU2PhaseStatusCurrent.1
    Q_PHASE_CURRENT = BASE_OID + (6, 3, 1, 5, 1)
    # PowerNet-MIB::rPDU2DeviceStatusPower.1
    Q_POWER = BASE_OID + (4, 3, 1, 5, 1)
    # PowerNet-MIB::rPDU2SensorTempHumidityStatusType.1
    Q_SENSOR_TYPE = BASE_OID + (10, 2, 2, 1, 5, 1)
    # PowerNet-MIB::rPDU2SensorTempHumidityStatusName.1
    Q_SENSOR_NAME = BASE_OID + (10, 2, 2, 1, 3, 1)
    # PowerNet-MIB::rPDU2SensorTempHumidityStatusCommStatus.1
    Q_SENSOR_COMM_STATUS = BASE_OID + (10, 2, 2, 1, 6, 1)
    # PowerNet-MIB::rPDU2SensorTempHumidityStatusTempF.1
    Q_SENSOR_TEMP_F = BASE_OID + (10, 2, 2, 1, 7, 1)
    # PowerNet-MIB::rPDU2SensorTempHumidityStatusTempC.1
    Q_SENSOR_TEMP_C = BASE_OID + (10, 2, 2, 1, 8, 1)
    # PowerNet-MIB::rPDU2SensorTempHumidityStatusTempStatus.1
    Q_SENSOR_TEMP_STATUS = BASE_OID + (10, 2, 2, 1, 9, 1)
    # PowerNet-MIB::rPDU2SensorTempHumidityStatusRelativeHumidity.1
    Q_SENSOR_HUMIDITY = BASE_OID + (10, 2, 2, 1, 10, 1)
    # PowerNet-MIB::rPDU2SensorTempHumidityStatusHumidityStatus.1
    Q_SENSOR_HUMIDITY_STATUS = BASE_OID + (10, 2, 2, 1, 11, 1)
    # PowerNet-MIB::rPDU2OutletSwitchedStatusName.24
    Q_OUTLET_NAME = BASE_OID + (9, 2, 3, 1, 3)  # Requires outlet number
    # PowerNet-MIB::rPDU2OutletSwitchedStatusState.24
    Q_OUTLET_STATUS = BASE_OID + (9, 2, 3, 1, 5)  # Requires outlet number

    # Dynamic readwrite data
    # PowerNet-MIB::rPDU2SensorTempHumidityConfigName.1
    Q_SENSOR_NAME_RW = BASE_OID + (10, 2, 1, 1, 3, 1)
    # PowerNet-MIB::rPDU2OutletSwitchedConfigName.24
    Q_OUTLET_NAME_RW = BASE_OID + (9, 2, 1, 1, 3)  # Requires outlet number
    # PowerNet-MIB::rPDU2OutletSwitchedControlCommand.24
    Q_OUTLET_COMMAND_RW = BASE_OID + (9, 2, 4, 1, 5)  # Requires outlet number

    # Lookups
    LOAD_STATES = ["", "lowLoad", "normal", "nearOverload", "overload"]
    SENSOR_TYPES = [
        "",
        "temperatureOnly",
        "temperatureHumidity",
        "commsLost",
        "notInstalled",
    ]
    COMM_STATUS_TYPES = ["", "notInstalled", "commsOK", "commsLost"]
    SENSOR_STATUS_TYPES = [
        "",
        "notPresent",
        "belowMin",
        "belowLow",
        "normal",
        "aboveHigh",
        "aboveMax",
    ]
    OUTLET_STATUS_TYPES = ["", "off", "on"]

    def __init__(
        self, hostname_or_ip_address, public_community, private_community
    ):
        """Create an APC object.

        :param hostname_or_ip_address: hostname or ip address of PDU
        :param public_community: public community string
        :param private_community: private community string
        :return: APC object
        """
        self._host = hostname_or_ip_address
        self._vendor = "APC"

        self._transport = cmdgen.UdpTransportTarget(
            (self._host, self.SNMP_PORT),
            timeout=self.SNMP_TIMEOUT,
            retries=self.SNMP_RETRIES,
        )
        self._public = cmdgen.CommunityData(
            public_community, mpModel=self.SNMP_VERSION_2_2C
        )
        self._private = cmdgen.CommunityData(
            private_community, mpModel=self.SNMP_VERSION_2_2C
        )

        # Generic information (static)
        self._identification = self.__get(self.Q_NAME)
        self._location = self.__get(self.Q_LOCATION)
        self._hardware_rev = self.__get(self.Q_HARDWARE_REV)
        self._firmware_rev = self.__get(self.Q_FIRMWARE_REV)
        self._manufacture_date = datetime.strptime(
            str(self.__get(self.Q_MANUFACTURE_DATE)), "%m/%d/%Y"
        )
        self._model_number = self.__get(self.Q_MODEL_NUMBER)
        self._serial_number = self.__get(self.Q_SERIAL_NUMBER)

        # Device status (static)
        self._num_outlets = self.__get(self.Q_NUM_OUTLETS)
        self._num_switched_outlets = self.__get(self.Q_NUM_SWITCHED_OUTLETS)
        self._num_metered_outlets = self.__get(self.Q_NUM_METERED_OUTLETS)
        self._max_current = self.__get(self.Q_MAX_CURRENT_RATING)

        # Phase status (static)
        self._power_factor = 100
        self._current_factor = 10
        self._phase_voltage = int(self.__get(self.Q_PHASE_VOLTAGE))

        self._use_centigrade = False

        self._logger = logging.getLogger(__name__)
        self._logger.addHandler(logging.NullHandler())

    @property
    def host(self):
        """Hostname or IP Address of PDU.

        :return: PDU hostname or ip address
        """
        self._logger.info("Host: %s", self._host)
        return self._host

    @property
    def vendor(self):
        """Vendor/Manufacturer of PDU.

        :return: PDU vendor/manufacturer
        """
        self._logger.info("Vendor: %s", self._vendor)
        return self._vendor

    @property
    def identification(self):
        """Identification string.

        :return: PDU identification
        """
        self._logger.info("Identification: %s", self._identification)
        return self._identification

    @property
    def location(self):
        """Location of the PDU.

        :return: PDU location
        """
        self._logger.info("Location: %s", self._location)
        return self._location

    @property
    def hardware_revision(self):
        """Hardware revision.

        :return: PDU hardware revision
        """
        revision = str(self._hardware_rev)
        self._logger.info("Hardware revision: %s", revision)
        return revision

    @property
    def firmware_revision(self):
        """Firmware revision.

        :return: PDU firmware revision
        """
        revision = str(self._firmware_rev)
        self._logger.info("Firmware revision: %s", revision)
        return revision

    @property
    def date_of_manufacture(self):
        """Date of manufacture.

        :return: PDU date of manufacture
        """
        self._logger.info(
            "Date of Manufacture: %s", str(self._manufacture_date)
        )
        return self._manufacture_date

    @property
    def model_number(self):
        """Model number.

        :return: PDU model number
        """
        model = str(self._model_number)
        self._logger.info("Model number: %s", model)
        return model

    @property
    def serial_number(self):
        """Return the serial number.

        :return: PDU serial number
        """
        serial = str(self._serial_number)
        self._logger.info("Serial number: %s", serial)
        return serial

    @property
    def num_outlets(self):
        """Return the number of outlets in the PDU.

        :return: total number of outlets in the PDU
        """
        num = int(self._num_outlets)
        self._logger.info("Number of outlets: %d", num)
        return num

    @property
    def num_switched_outlets(self):
        """Return the number of switched outlets in the PDU.

        :return: number of switched outlets in the PDU
        """
        num = int(self._num_switched_outlets)
        self._logger.info("Number of switched outlets: %d", num)
        return num

    @property
    def num_metered_outlets(self):
        """Return the number of metered outlets in the PDU.

        :return: number of metered outlets in the PDU
        """
        num = int(self._num_metered_outlets)
        self._logger.info("Number of metered outlets: %d", num)
        return num

    @property
    def max_current(self):
        """Maximum current for the PDU.

        :return: maximum current for the PDU
        """
        current = int(self._max_current)
        self._logger.info("Maximum current: %d", current)
        return current

    @property
    def voltage(self):
        """Line voltage of the PDU.

        :return: PDU line voltage
        """
        voltage = int(self._phase_voltage)
        self._logger.info("Line voltage: %d", voltage)
        return voltage

    @property
    def load_state(self):
        """Load state of the PDU.

        :return: one of ['lowLoad', 'normal', 'nearOverload', overload']
        """
        state = int(self.__get(self.Q_PHASE_LOAD_STATE))
        self._logger.info("Load state: %s", self.LOAD_STATES[state])
        return self.LOAD_STATES[state]

    @property
    def current(self):
        """Return the current utilization of the PDU.

        :return: current, in amps
        """
        current = float(self.__get(self.Q_PHASE_CURRENT) / self._current_factor)
        self._logger.info("Current: %.2f", current)
        return current

    @property
    def power(self):
        """Return the power utilization of the PDU.

        :return: power, in kW
        """
        power = float(self.__get(self.Q_POWER) / self._power_factor)
        self._logger.info("Power: %.2f", power)
        return power

    @property
    def is_sensor_present(self):
        """Determine if a sensor is present on the PDU.

        :return: Is the sensor present?
        """
        state = self.__get(self.Q_SENSOR_TYPE)
        present = 1 < int(state) < 3
        self._logger.info("Sensor present: %s", str(present))
        return present

    @property
    def sensor_name(self):
        """Name of the sensor.

        :return: name of the sensor
        """
        name = None
        if self.is_sensor_present:
            name = str(self.__get(self.Q_SENSOR_NAME))
        self._logger.info("Sensor name: %s", name)
        return name

    @sensor_name.setter
    def _set_sensor_name(self, name):
        """Name of the sensor.

        :param name: name of the sensor
        :return:
        """
        if self.is_sensor_present:
            self.__set(self.Q_SENSOR_NAME_RW, name)
            self._logger.info("Updating sensor name to: %s", name)

    @property
    def sensor_type(self):
        """Type of sensor.

        :return: type of sensor, one of
            ['temperatureOnly', 'temperatureHumidity', 'commsLost',
            'notInstalled']
        """
        index = 4
        if self.is_sensor_present:
            index = int(self.__get(self.Q_SENSOR_TYPE))
        self._logger.info("Sensor type: %s", self.SENSOR_TYPES[index])
        return self.SENSOR_TYPES[index]

    @property
    def sensor_comm_status(self):
        """Communication status of the sensor.

        :return: communication status of the sensor
        """
        index = 1
        if self.is_sensor_present:
            index = int(self.__get(self.Q_SENSOR_COMM_STATUS))
        self._logger.info(
            "Sensor communication status: %s", self.SENSOR_STATUS_TYPES[index]
        )
        return self.SENSOR_STATUS_TYPES[index]

    @property
    def use_centigrade(self):
        """Select between centigrade and fahrenheit.

        :return: using centigrade or not
        """
        self._logger.info("Use centigrade: %s", str(self._use_centigrade))
        return self._use_centigrade

    @use_centigrade.setter
    def use_centigrade(self, value):
        """Select between centigrade and fahrenheit.

        :param value: use centrigrade or not
        :return:
        """
        self._logger.info("Updating use centigrade to: %s", value)
        self._use_centigrade = value

    @property
    def temperature(self):
        """Temperature.

        :return: temperature
        """
        temp = 0.00
        if self.sensor_supports_temperature:
            if self._use_centigrade:
                temp = float(self.__get(self.Q_SENSOR_TEMP_C) / 10)
            else:
                temp = float(self.__get(self.Q_SENSOR_TEMP_F) / 10)
        self._logger.info("Temperature: %.2f", temp)
        return temp

    @property
    def humidity(self):
        """Relative humidity.

        :return: relative humidity
        """
        humid = 0.00
        if self.sensor_supports_humidity:
            humid = float(self.__get(self.Q_SENSOR_HUMIDITY))
        self._logger.info("Relative humidity: %.2f", humid)
        return humid

    @property
    def temperature_status(self):
        """Determine the status of the temperature sensor.

        :return: The status of the temperature sensor
        """
        index = 1
        if self.sensor_supports_temperature:
            index = self.__get(self.Q_SENSOR_TEMP_STATUS)
        self._logger.info(
            "Temperature sensor status: %s", self.SENSOR_STATUS_TYPES[index]
        )
        return self.SENSOR_STATUS_TYPES[index]

    @property
    def humidity_status(self):
        """Determine the status of the humidity sensor.

        :return: status of the humidity sensor
        """
        index = 1
        if self.sensor_supports_humidity:
            index = self.__get(self.Q_SENSOR_HUMIDITY_STATUS)
        self._logger.info(
            "Relative humidity sensor status: %s",
            self.SENSOR_STATUS_TYPES[index],
        )
        return self.SENSOR_STATUS_TYPES[index]

    def get_outlet_name(self, outlet):
        """Name of an outlet in the PDU.

        :param outlet: outlet number
        :return: name of the outlet
        """
        if 1 <= outlet <= self._num_outlets:
            name = str(self.__get(self.Q_OUTLET_NAME + (outlet,)))
            self._logger.info("Outlet number %d has name %s", outlet, name)
            return name
        raise IndexError(
            'Only {} outlets exist. "{}" is an invalid outlet.'.format(
                self._num_outlets, str(outlet)
            )
        )

    def set_outlet_name(self, outlet, name):
        """Update the name of an outlet in the PDU.

        :param outlet: outlet number
        :param name: outlet name
        :return:
        """
        if 1 <= outlet <= self._num_outlets:
            self.__set(self.Q_OUTLET_NAME_RW + (outlet,), name)
            self._logger.info(
                "Updating outlet number %d to new name %s", outlet, name
            )
        raise IndexError(
            'Only {} outlets exist. "{}" is an invalid outlet.'.format(
                self._num_outlets, str(outlet)
            )
        )

    def outlet_status(self, outlet):
        """Determine the status of the outlet in the PDU.

        :param outlet: outlet number
        :return: status of the outlet, one of ['on', 'off']
        """
        if 1 <= outlet <= self._num_outlets:
            state = self.__get(self.Q_OUTLET_STATUS + (outlet,))
            self._logger.info(
                "Outlet number %d has status %s",
                outlet,
                self.OUTLET_STATUS_TYPES[state],
            )
            return self.OUTLET_STATUS_TYPES[state]
        raise IndexError(
            'Only {} outlets exist. "{}" is an invalid outlet.'.format(
                self._num_outlets, str(outlet)
            )
        )

    def outlet_command(self, outlet, operation):
        """Send command to an outlet in the PDU.

        :param outlet: outlet number
        :param operation: one of ['on', 'off', 'reboot']
        :return: did the operation complete successfully?
        """
        valid_operations = ["on", "off", "reboot"]
        if operation not in valid_operations:
            raise ValueError(
                '"{}" is an invalid operation. Valid operations are: {}'.format(
                    str(operation), str(valid_operations)
                )
            )

        operations = {"on": 1, "off": 2, "reboot": 3}

        if 1 <= outlet <= self._num_outlets:
            self._logger.info(
                "Setting outlet %d to %s state", outlet, operation
            )
            self.__set(
                self.Q_OUTLET_COMMAND_RW + (outlet,), operations[operation]
            )

            try:
                if operation in ("on", "reboot"):
                    success = self.__wait_for_state(outlet, "on")
                else:
                    success = self.__wait_for_state(outlet, "off")
            except RetryError:
                # If the operation timed out, no determination of the result
                # can be made.
                success = False

            return success
        raise IndexError(
            'Only {} outlets exist. "{}" is an invalid outlet.'.format(
                self._num_outlets, str(outlet)
            )
        )

    @property
    def sensor_supports_temperature(self):
        """Determine if the sensor supports temperature measurements.

        :return: does the sensor support temperature measurements?
        """
        return self.is_sensor_present and "temp" in self.sensor_type.lower()

    @property
    def sensor_supports_humidity(self):
        """Determine if the sensor supports relative humidity measurements.

        :return: does the sensor support relative humidity measurements?
        """
        return self.is_sensor_present and "humid" in self.sensor_type.lower()

    # pylint: disable=no-self-argument
    # In order to use this method within the @retry decorator, this method
    # must be defined as such.
    def __retry_if_not_state(result):
        """Only keep retrying if the state is not what is expected.

        :return: negation of input
        """
        return not result

    @retry(
        stop_max_delay=MAX_STOP_DELAY,
        wait_fixed=INTER_RETRY_WAIT,
        retry_on_result=__retry_if_not_state,
    )
    def __wait_for_state(self, outlet, state):
        """Wait until state is hit.

        This will wait for MAX_STOP_DELAY with a inter-try delay of
        INTER_RETRY_WAIT.

        :param outlet: outlet number
        :param state: state to wait for
        :return: was the state hit?
        """
        return self.outlet_status(outlet) is state

    def __get(self, oid):
        """Get a specific value from an OID in the SNMP tree.

        :param oid: OID to get
        :returns: value from the specified OID
        """
        (error_indication, _, _, var_binds) = cmdgen.CommandGenerator().getCmd(
            self._public, self._transport, oid
        )
        if error_indication:
            raise RuntimeError(self.ERROR_MSG.format("get", oid, self._host))

        return var_binds[0][1]

    def __set(self, oid, value):
        """Set a specific value to an OID in the SNMP tree.

        :param oid: OID to set
        :param value: value to set
        """
        initial_value = self.__get(oid)
        new_value = self.__coerce_value(initial_value, value)

        (error_indication, _, _, var_binds) = cmdgen.CommandGenerator().setCmd(
            self._private, self._transport, (oid, new_value)
        )
        if error_indication:
            raise RuntimeError(self.ERROR_MSG.format("set", oid, self._host))

        return var_binds[0][1]

    @staticmethod
    def __coerce_value(initial_value, new_value):
        """Coerce the new_value to the same type as the initial_value.

        Unfortunately this is a bit of a workaround for the more elegant
        version:
        `return initial_value.__init__(str(new_value))`
        Utilizing that more elegant version yields an SmiError:
        MIB object ObjectIdentity((...)) is not OBJECT-TYPE (MIB not loaded?)

        :param initial_value: initial value from the device
        :param new_value: new value to set, coerced into the right type
        :return: new value, coerced into the right type
        """
        if isinstance(initial_value, rfc1902.Counter32):
            set_value = rfc1902.Counter32(str(new_value))
        elif isinstance(initial_value, rfc1902.Counter64):
            set_value = rfc1902.Counter64(str(new_value))
        elif isinstance(initial_value, rfc1902.Gauge32):
            set_value = rfc1902.Gauge32(str(new_value))
        elif isinstance(initial_value, rfc1902.Integer):
            set_value = rfc1902.Integer(str(new_value))
        elif isinstance(initial_value, rfc1902.Integer32):
            set_value = rfc1902.Integer32(str(new_value))
        elif isinstance(initial_value, rfc1902.IpAddress):
            set_value = rfc1902.IpAddress(str(new_value))
        elif isinstance(initial_value, rfc1902.OctetString):
            set_value = rfc1902.OctetString(str(new_value))
        elif isinstance(initial_value, rfc1902.TimeTicks):
            set_value = rfc1902.TimeTicks(str(new_value))
        elif isinstance(initial_value, rfc1902.Unsigned32):
            set_value = rfc1902.Unsigned32(str(new_value))
        else:
            raise RuntimeError("Unknown type: {}".format(type(initial_value)))

        return set_value
