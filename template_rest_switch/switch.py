import asyncio
import logging

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchEntity
from homeassistant.const import (
    CONF_HEADERS,
    CONF_METHOD,
    CONF_NAME,
    CONF_PARAMS,
    CONF_PASSWORD,
    CONF_RESOURCE,
    CONF_RESOURCE_TEMPLATE,
    CONF_TIMEOUT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    HTTP_BAD_REQUEST,
    HTTP_OK,
    CONF_SCAN_INTERVAL,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from homeassistant.helpers.entity_component import DEFAULT_SCAN_INTERVAL


from homeassistant.components.rest.switch import (
    RestSwitch,
    CONF_BODY_OFF,
    CONF_BODY_ON,
    CONF_IS_ON_TEMPLATE,
    CONF_STATE_RESOURCE,
    DEFAULT_METHOD,
    DEFAULT_BODY_OFF,
    DEFAULT_BODY_ON,
    DEFAULT_NAME,
    DEFAULT_TIMEOUT,
    DEFAULT_VERIFY_SSL,
)

from homeassistant.exceptions import HomeAssistantError, PlatformNotReady

_LOGGER = logging.getLogger(__name__)
SUPPORT_REST_METHODS = ["post", "put", "patch"]
CONF_STATE_TEMPLATE = "state_template"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_RESOURCE): cv.url,
        vol.Optional(CONF_RESOURCE_TEMPLATE): cv.template,
        vol.Optional(CONF_STATE_RESOURCE): cv.url,
        # vol.Optional(CONF_STATE_TEMPLATE): cv.template,
        vol.Optional(CONF_HEADERS): {cv.string: cv.string},
        vol.Optional(CONF_PARAMS): {cv.string: cv.string},
        vol.Optional(CONF_BODY_OFF, default=DEFAULT_BODY_OFF): cv.template,
        vol.Optional(CONF_BODY_ON, default=DEFAULT_BODY_ON): cv.template,
        vol.Optional(CONF_IS_ON_TEMPLATE): cv.template,
        vol.Optional(CONF_METHOD, default=DEFAULT_METHOD): vol.All(
            vol.Lower, vol.In(SUPPORT_REST_METHODS)
        ),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
        vol.Inclusive(CONF_USERNAME, "authentication"): cv.string,
        vol.Inclusive(CONF_PASSWORD, "authentication"): cv.string,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the RESTful switch."""
    body_off = config.get(CONF_BODY_OFF)
    body_on = config.get(CONF_BODY_ON)
    is_on_template = config.get(CONF_IS_ON_TEMPLATE)
    method = config.get(CONF_METHOD)
    headers = config.get(CONF_HEADERS)
    params = config.get(CONF_PARAMS)
    name = config.get(CONF_NAME)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    resource = config.get(CONF_RESOURCE)
    resource_template = config.get(CONF_RESOURCE_TEMPLATE)
    state_resource = config.get(CONF_STATE_RESOURCE) or resource
    # state_resource_template = config.get(CONF_STATE_TEMPLATE)
    verify_ssl = config.get(CONF_VERIFY_SSL)

    auth = None
    if username:
        auth = aiohttp.BasicAuth(username, password=password)

    if is_on_template is not None:
        is_on_template.hass = hass

    if resource_template is not None:
        resource_template.hass = hass

    # if state_resource_template is not None:
    #     state_resource_template.hass = hass

    if body_on is not None:
        body_on.hass = hass
    if body_off is not None:
        body_off.hass = hass
    timeout = config.get(CONF_TIMEOUT)

    try:
        switch = TemplateRestSwitch(
            name=name,
            resource=resource,
            resource_template=resource_template,
            state_resource=state_resource,
            # state_resource_template,
            method=method,
            headers=headers,
            params=params,
            auth=auth,
            body_on=body_on,
            body_off=body_off,
            is_on_template=is_on_template,
            timeout=timeout,
            verify_ssl=verify_ssl,
        )

        req = await switch.get_device_state(hass)
        if req.status >= HTTP_BAD_REQUEST:
            _LOGGER.error("Got non-ok response from resource: %s", req.status)
        else:
            async_add_entities([switch])
    except (TypeError, ValueError):
        _LOGGER.error(
            "Missing resource or schema in configuration. "
            "Add http:// or https:// to your URL"
        )
    except (asyncio.TimeoutError, aiohttp.ClientError):
        _LOGGER.warning("No route to resource/endpoint: %s", resource)
        raise PlatformNotReady()


class TemplateRestSwitch(RestSwitch):
    """Representation of a switch that can be toggled using REST, but as template resource."""

    def __init__(
        self,
        name,
        resource,
        resource_template,
        state_resource,
        # state_template,
        method,
        headers,
        params,
        auth,
        body_on,
        body_off,
        is_on_template,
        timeout,
        verify_ssl,
    ):
        RestSwitch.__init__(
            self,
            name=name,
            resource=resource,
            state_resource=state_resource,
            method=method,
            headers=headers,
            params=params,
            auth=auth,
            body_on=body_on,
            body_off=body_off,
            is_on_template=is_on_template,
            timeout=timeout,
            verify_ssl=verify_ssl,
        )
        self._resource_template = resource_template

    async def set_device_state(self, body):
        """Send a state update to the device."""
        websession = async_get_clientsession(self.hass, self._verify_ssl)

        if self._resource_template is not None:
            self._resource = (
                self._resource_template.async_render_with_possible_json_value(
                    self._resource_template, "http://no_resource_computed_error"
                )
            )

        with async_timeout.timeout(self._timeout):
            req = await getattr(websession, self._method)(
                self._resource,
                auth=self._auth,
                data=bytes(body, "utf-8"),
                headers=self._headers,
                params=self._params,
            )
            return req
