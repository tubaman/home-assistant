"""
Interfaces with http://alarmdealer.com website control panel.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/alarm_control_panel.alarmdealer/
"""
import logging

import voluptuous as vol

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.components.alarm_control_panel import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_PASSWORD, CONF_USERNAME, STATE_UNKNOWN, CONF_CODE, CONF_NAME,
    STATE_ALARM_DISARMED, STATE_ALARM_ARMED_HOME, STATE_ALARM_ARMED_AWAY,
    EVENT_HOMEASSISTANT_STOP)
import homeassistant.helpers.config_validation as cv
import homeassistant.loader as loader

REQUIREMENTS = ['alarmdealerscrape']

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'AlarmDealer'
DOMAIN = 'alarmdealer'
NOTIFICATION_ID = 'alarmdealer_notification'
NOTIFICATION_TITLE = 'AlarmDealer Setup'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Optional(CONF_CODE): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Alarm Dealer platform."""
    from alarmdealerscrape import AlarmDealerClient
    name = config.get(CONF_NAME)
    code = config.get(CONF_CODE)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    persistent_notification = loader.get_component('persistent_notification')
    alarmdealer = AlarmDealerClient()

    try:
        alarmdealer.login(username, password)
    except:
        message = 'Failed to log into alarmdealer.com. Check credentials.'
        _LOGGER.error(message)
        persistent_notification.create(
            hass, message,
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID)
        return False
    else:
        hass.data[DOMAIN] = alarmdealer
        add_devices([AlarmDealerAlarm(alarmdealer, name, code)])

    def logout(event):
        """Logout of the Alarm Dealer API."""
        hass.data[DOMAIN].logout()

    hass.bus.listen(EVENT_HOMEASSISTANT_STOP, logout)


class AlarmDealerAlarm(alarm.AlarmControlPanel):
    """Representation a AlarmDealer alarm."""

    def __init__(self, alarmdealer, name, code):
        """Initialize the AlarmDealer alarm."""
        self.alarmdealer = alarmdealer
        self._name = name
        self._code = str(code) if code else None
        self._status = None

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def code_format(self):
        """One or more characters if code is defined."""
        # TODO: change to 4 digits
        return None if self._code is None else '.+'

    @property
    def state(self):
        """Return the state of the device."""
        if self._status == 'System is Ready to Arm':
            state = STATE_ALARM_DISARMED
        elif self._status == 'System Armed in Stay Mode':
            state = STATE_ALARM_ARMED_HOME
        elif self._status == 'System Armed in Away Mode':
            state = STATE_ALARM_ARMED_AWAY
        else:
            state = STATE_UNKNOWN
        return state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            'status': self._status,
        }

    def update(self):
        """Update alarm status."""
        self._status = self.alarmdealer.get_status()

    def alarm_disarm(self, code=None):
        """Send disarm command."""
        if not self._validate_code(code, 'disarming'):
            return
        self.alarmdealer.disarm(code)
        _LOGGER.info("Alarm Dealer alarm disarming")

    def alarm_arm_home(self, code=None):
        """Send arm home command."""
        if not self._validate_code(code, 'arming home'):
            return
        self.alarmdealer.arm_stay()
        _LOGGER.info("Alarm Dealer alarm arming home")

    def alarm_arm_away(self, code=None):
        """Send arm away command."""
        if not self._validate_code(code, 'arming away'):
            return
        self.alarmdealer.arm_away()
        _LOGGER.info("Alarm Dealer alarm arming away")

    def _validate_code(self, code, state):
        """Validate given code."""
        check = self._code is None or code == self._code
        if not check:
            _LOGGER.warning("Wrong code entered for %s", state)
        return check
