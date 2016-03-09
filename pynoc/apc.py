"""APC Power Distribution Unit control object."""

import logging
from datetime import datetime
from os import getcwd, path
from snmpy import Snmpy


class APC(object):
    """APC Power Distribution Unit."""

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods
    # This class requires more attributes and public methods to cover the
    # functionality of the device.

    PREFIX = 'PowerNet-MIB'

    # Static readonly data
    Q_NAME = 'rPDU2IdentName.1'
    Q_LOCATION = 'rPDU2IdentLocation.1'
    Q_HARDWARE_REV = 'rPDU2IdentHardwareRev.1'
    Q_FIRMWARE_REV = 'rPDU2IdentFirmwareRev.1'
    Q_MANUFACTURE_DATE = 'rPDU2IdentDateOfManufacture.1'
    Q_MODEL_NUMBER = 'rPDU2IdentModelNumber.1'
    Q_SERIAL_NUMBER = 'rPDU2IdentSerialNumber.1'
    Q_NUM_OUTLETS = 'rPDU2DevicePropertiesNumOutlets.1'
    Q_NUM_SWITCHED_OUTLETS = 'rPDU2DevicePropertiesNumSwitchedOutlets.1'
    Q_NUM_METERED_OUTLETS = 'rPDU2DevicePropertiesNumMeteredOutlets.1'
    Q_MAX_CURRENT_RATING = 'rPDU2DevicePropertiesMaxCurrentRating.1'
    Q_PHASE_VOLTAGE = 'rPDU2PhaseStatusVoltage.1'

    # Dynamic readonly data
    Q_PHASE_LOAD_STATE = 'rPDU2PhaseStatusLoadState.1'
    Q_PHASE_CURRENT = 'rPDU2PhaseStatusCurrent.1'
    Q_POWER = 'rPDU2DeviceStatusPower.1'
    Q_SENSOR_TYPE = 'rPDU2SensorTempHumidityStatusType.1'
    Q_SENSOR_NAME = 'rPDU2SensorTempHumidityStatusName.1'
    Q_SENSOR_COMM_STATUS = 'rPDU2SensorTempHumidityStatusCommStatus.1'
    Q_SENSOR_TEMP_F = 'rPDU2SensorTempHumidityStatusTempF.1'
    Q_SENSOR_TEMP_C = 'rPDU2SensorTempHumidityStatusTempC.1'
    Q_SENSOR_TEMP_STATUS = 'rPDU2SensorTempHumidityStatusTempStatus.1'
    Q_SENSOR_HUMIDITY = 'rPDU2SensorTempHumidityStatusRelativeHumidity.1'
    Q_SENSOR_HUMIDITY_STATUS = 'rPDU2SensorTempHumidityStatusHumidityStatus.1'
    Q_OUTLET_NAME = 'rPDU2OutletSwitchedStatusName.{0}'
    Q_OUTLET_STATUS = 'rPDU2OutletSwitchedStatusState.{0}'

    # Dynamic readwrite data
    Q_SENSOR_NAME_RW = 'rPDU2SensorTempHumidityConfigName.1'
    Q_OUTLET_NAME_RW = 'rPDU2OutletSwitchedConfigName.{0}'
    Q_OUTLET_COMMAND_RW = 'rPDU2OutletSwitchedControlCommand.{0}'

    # Lookups
    LOAD_STATES = ['', 'lowLoad', 'normal', 'nearOverload', 'overload']
    SENSOR_TYPES = ['',
                    'temperatureOnly',
                    'temperatureHumidity',
                    'commsLost',
                    'notInstalled']
    COMM_STATUS_TYPES = ['', 'notInstalled', 'commsOK', 'commsLost']
    SENSOR_STATUS_TYPES = ['',
                           'notPresent',
                           'belowMin',
                           'belowLow',
                           'normal',
                           'aboveHigh',
                           'aboveMax']
    OUTLET_STATUS_TYPES = ['', 'off', 'on']

    def _get_query_string(self, query, param=None):
        """Generate a well-formatted SNMP query string.

        :param query: which query to use
        :param param: additional parameter, usually outlet number
        :return: well-formatted SNMP query string
        """
        if param:
            query = query.format(param)
        return '{0}::{1}'.format(self.PREFIX, query)

    def __init__(self, hostname_or_ip_address,
                 public_community, private_community):
        """Create an APC object.

        :param hostname_or_ip_address: hostname or ip address of PDU
        :param public_community: public community string
        :param private_community: private community string
        :return: APC object
        """
        self._host = hostname_or_ip_address
        self._vendor = 'APC'

        self._snmp_public_auth = public_community
        self._snmp_private_auth = private_community

        self._connection = Snmpy(self._host,
                                 self._snmp_public_auth,
                                 self._snmp_private_auth,
                                 timeout=1.5,
                                 retries=2)
        self._connection.add_mib_path(getcwd())
        self._connection.add_mib_path(path.dirname(path.abspath(__file__)))
        self._connection.load_mibs(self.PREFIX)

        # Generic information (static)
        self._identification = self._connection.get(
            self._get_query_string(self.Q_NAME))
        self._location = self._connection.get(
            self._get_query_string(self.Q_LOCATION))
        self._hardware_rev = self._connection.get(
            self._get_query_string(self.Q_HARDWARE_REV))
        self._firmware_rev = self._connection.get(
            self._get_query_string(self.Q_FIRMWARE_REV))
        self._manufacture_date = datetime.strptime(str(self._connection.get(
            self._get_query_string(self.Q_MANUFACTURE_DATE))), "%m/%d/%Y")
        self._model_number = self._connection.get(
            self._get_query_string(self.Q_MODEL_NUMBER))
        self._serial_number = self._connection.get(
            self._get_query_string(self.Q_SERIAL_NUMBER))

        # Device status (static)
        self._num_outlets = self._connection.get(
            self._get_query_string(self.Q_NUM_OUTLETS))
        self._num_switched_outlets = self._connection.get(
            self._get_query_string(self.Q_NUM_SWITCHED_OUTLETS))
        self._num_metered_outlets = self._connection.get(
            self._get_query_string(self.Q_NUM_METERED_OUTLETS))
        self._max_current = self._connection.get(
            self._get_query_string(self.Q_MAX_CURRENT_RATING))

        # Phase status (static)
        self._power_factor = 100
        self._current_factor = 10
        self._phase_voltage = int(self._connection.get(
            self._get_query_string(self.Q_PHASE_VOLTAGE)))

        self._use_centigrade = False

        self._logger = logging.getLogger(__name__)
        self._logger.addHandler(logging.NullHandler())

    @property
    def host(self):
        """Hostname or IP Address of PDU.

        :return: PDU hostname or ip address
        """
        self._logger.info('Host: %s', self._host)
        return self._host

    @property
    def vendor(self):
        """Vendor/Manufacturer of PDU.

        :return: PDU vendor/manufacturer
        """
        self._logger.info('Vendor: %s', self._vendor)
        return self._vendor

    @property
    def identification(self):
        """Identification string.

        :return: PDU identification
        """
        self._logger.info('Identification: %s', self._identification)
        return self._identification

    @property
    def location(self):
        """Location of the PDU.

        :return: PDU location
        """
        self._logger.info('Location: %s', self._location)
        return self._location

    @property
    def hardware_revision(self):
        """Hardware revision.

        :return: PDU hardware revision
        """
        revision = str(self._hardware_rev)
        self._logger.info('Hardware revision: %s', revision)
        return revision

    @property
    def firmware_revision(self):
        """Firmware revision.

        :return: PDU firmware revision
        """
        revision = str(self._firmware_rev)
        self._logger.info('Firmware revision: %s', revision)
        return revision

    @property
    def date_of_manufacture(self):
        """Date of manufacture.

        :return: PDU date of manufacture
        """
        self._logger.info('Date of Manufacre: %s', str(self._manufacture_date))
        return self._manufacture_date

    @property
    def model_number(self):
        """Model number.

        :return: PDU model number
        """
        model = str(self._model_number)
        self._logger.info('Model number: %s', model)
        return model

    @property
    def serial_number(self):
        """Serial number.

        :return: PDU serial number
        """
        serial = str(self._serial_number)
        self._logger.info('Serial number: %s', serial)
        return serial

    @property
    def num_outlets(self):
        """Number of outlets in the PDU.

        :return: total number of outlets in the PDU
        """
        num = int(self._num_outlets)
        self._logger.info('Number of outlets: %d', num)
        return num

    @property
    def num_switched_outlets(self):
        """Number of switched outlets in the PDU.

        :return: number of switched outlets in the PDU
        """
        num = int(self._num_switched_outlets)
        self._logger.info('Number of switched outlets: %d', num)
        return num

    @property
    def num_metered_outlets(self):
        """Number of metered outlets in the PDU.

        :return: number of metered outlets in the PDU
        """
        num = int(self._num_metered_outlets)
        self._logger.info('Number of metered outlets: %d', num)
        return num

    @property
    def max_current(self):
        """Maximum current for the PDU.

        :return: maximum current for the PDU
        """
        current = int(self._max_current)
        self._logger.info('Maximum current: %d', current)
        return current

    @property
    def voltage(self):
        """Line voltage of the PDU.

        :return: PDU line voltage
        """
        voltage = int(self._phase_voltage)
        self._logger.info('Line voltage: %d', voltage)
        return voltage

    @property
    def load_state(self):
        """Load state of the PDU.

        :return: one of ['lowLoad', 'normal', 'nearOverload', overload']
        """
        state = int(self._connection.get(
            self._get_query_string(self.Q_PHASE_LOAD_STATE)))
        self._logger.info('Load state: %s', self.LOAD_STATES[state])
        return self.LOAD_STATES[state]

    @property
    def current(self):
        """The current utilization of the PDU.

        :return: current, in amps
        """
        current = float(self._connection.get(
            self._get_query_string(
                self.Q_PHASE_CURRENT)) / self._current_factor)
        self._logger.info('Current: %.2f', current)
        return current

    @property
    def power(self):
        """The power utilization of the PDU.

        :return: power, in kW
        """
        power = float(self._connection.get(
            self._get_query_string(
                self.Q_POWER)) / self._power_factor)
        self._logger.info('Power: %.2f', power)
        return power

    @property
    def is_sensor_present(self):
        """Determine if a sensor is present on the PDU.

        :return: Is the sensor present?
        """
        state = self._connection.get(
            self._get_query_string(self.Q_SENSOR_TYPE))
        present = 1 < int(state) < 3
        self._logger.info('Sensor present: %s', str(present))
        return present

    @property
    def sensor_name(self):
        """Name of the sensor.

        :return: name of the sensor
        """
        name = None
        if self.is_sensor_present:
            name = str(self._connection.get(self._get_query_string(
                self.Q_SENSOR_NAME)))
        self._logger.info('Sensor name: %s', name)
        return name

    @sensor_name.setter
    def _set_sensor_name(self, name):
        """Name of the sensor.

        :param name: name of the sensor
        :return:
        """
        if self.is_sensor_present:
            self._connection.set(
                self._get_query_string(self.Q_SENSOR_NAME_RW),
                name)
            self._logger.info('Updating sensor name to: %s', name)

    @property
    def sensor_type(self):
        """Type of sensor.

        :return: type of sensor, one of
        ['temperatureOnly', 'temperatureHumidity', 'commsLost', 'notInstalled']
        """
        index = 4
        if self.is_sensor_present:
            index = int(self._connection.get(self._get_query_string(
                self.Q_SENSOR_TYPE)))
        self._logger.info('Sensor type: %s', self.SENSOR_TYPES[index])
        return self.SENSOR_TYPES[index]

    @property
    def sensor_comm_status(self):
        """Communication status of the sensor.

        :return: communication status of the sensor
        """
        index = 1
        if self.is_sensor_present:
            index = int(self._connection.get(self._get_query_string(
                self.Q_SENSOR_COMM_STATUS)))
        self._logger.info('Sensor communication status: %s',
                          self.SENSOR_STATUS_TYPES[index])
        return self.SENSOR_STATUS_TYPES[index]

    @property
    def use_centigrade(self):
        """Select between centigrade and fahrenheit.

        :return: using centigrade or not
        """
        self._logger.info('Use centigrade: %s', str(self._use_centigrade))
        return self._use_centigrade

    @use_centigrade.setter
    def use_centigrade(self, value):
        """Select between centigrade and fahrenheit.

        :param value: use centrigrade or not
        :return:
        """
        self._logger.info('Updating use centigrade to: %s', value)
        self._use_centigrade = value

    @property
    def temperature(self):
        """Temperature.

        :return: temperature
        """
        temp = 0.00
        if self.sensor_supports_temperature:
            if self._use_centigrade:
                temp = float(self._connection.get(self._get_query_string(
                    self.Q_SENSOR_TEMP_C)) / 10)
            else:
                temp = float(self._connection.get(self._get_query_string(
                    self.Q_SENSOR_TEMP_F)) / 10)
        self._logger.info('Temperature: %.2f', temp)
        return temp

    @property
    def humidity(self):
        """Relative humidity.

        :return: relative humidity
        """
        humid = 0.00
        if self.sensor_supports_humidity:
            humid = float(self._connection.get(self._get_query_string(
                self.Q_SENSOR_HUMIDITY)))
        self._logger.info('Relative humidity: %.2f', humid)
        return humid

    @property
    def temperature_status(self):
        """Determine the status of the temperature sensor.

        :return: The status of the temperature sensor
        """
        index = 1
        if self.sensor_supports_temperature:
            index = self._connection.get(self._get_query_string(
                self.Q_SENSOR_TEMP_STATUS))
        self._logger.info('Temperature sensor status: %s',
                          self.SENSOR_STATUS_TYPES[index])
        return self.SENSOR_STATUS_TYPES[index]

    @property
    def humidity_status(self):
        """Determine the status of the humidity sensor.

        :return: status of the humidity sensor
        """
        index = 1
        if self.sensor_supports_humidity:
            index = self._connection.get(self._get_query_string(
                self.Q_SENSOR_HUMIDITY_STATUS))
        self._logger.info('Relative humidity sensor status: %s',
                          self.SENSOR_STATUS_TYPES[index])
        return self.SENSOR_STATUS_TYPES[index]

    def get_outlet_name(self, outlet):
        """Name of an outlet in the PDU.

        :param outlet: outlet number
        :return: name of the outlet
        """
        if 1 <= outlet <= self._num_outlets:
            name = str(self._connection.get(self._get_query_string(
                self.Q_OUTLET_NAME, outlet)))
            self._logger.info('Outlet number %d has name %s', outlet, name)
            return name
        else:
            raise IndexError()

    def set_outlet_name(self, outlet, name):
        """Update the name of an outlet in the PDU.

        :param outlet: outlet number
        :param name: outlet name
        :return:
        """
        if 1 <= outlet <= self._num_outlets:
            self._connection.set(
                self._get_query_string(self.Q_OUTLET_NAME_RW, outlet),
                name)
            self._logger.info('Updating outlet number %d to new name %s',
                              outlet,
                              name)
        else:
            raise IndexError()

    def outlet_status(self, outlet):
        """Determine the status of the outlet in the PDU.

        :param outlet: outlet number
        :return: status of the outlet, one of ['on', 'off']
        """
        if 1 <= outlet <= self._num_outlets:
            state = self._connection.get(self._get_query_string(
                self.Q_OUTLET_STATUS, outlet))
            self._logger.info('Outlet number %d has status %s',
                              outlet,
                              self.OUTLET_STATUS_TYPES[state])
            return self.OUTLET_STATUS_TYPES[state]
        else:
            raise IndexError()

    def outlet_command(self, outlet, operation):
        """Send command to an outlet in the PDU.

        :param outlet: outlet number
        :param operation: one of ['on', 'off', 'reboot']
        :return:
        """
        if operation not in ['on', 'off', 'reboot']:
            raise ValueError()

        operations = {'on': 1,
                      'off': 2,
                      'reboot': 3}

        if 1 <= outlet <= self._num_outlets:
            self._logger.info('Setting outlet %d to %s state',
                              outlet,
                              operation)
            self._connection.set(
                self._get_query_string(self.Q_OUTLET_COMMAND_RW, outlet),
                operations[operation])
        else:
            raise IndexError()

    @property
    def sensor_supports_temperature(self):
        """Determine if the sensor supports temperature measurements.

        :return: does the sensor support temperature measurements?
        """
        return self.is_sensor_present and self.sensor_type.find('temp') > -1

    @property
    def sensor_supports_humidity(self):
        """Determine if the sensor supports relative humidity measurements.

        :return: does the sensor support relative humidity measurements?
        """
        return self.is_sensor_present and self.sensor_type.find('Humid') > -1
