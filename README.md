# HASS_template_REST_switch
simple home assistant RESTful switch core mod to handel TEMPLATEs in resource url (and update interval)

to use it :

1) download the folder "template_rest_switch" into your config/custom_components
2) add some configuration in your configuration.yaml ; this example is made to handle a switch managed by moonraker (klipper 3d printer API) on it's uncommon power api endpoint(s) :

```
  - platform: template_rest_switch
    name: "ngenLeds"
    # state_resource: http://192.168.1.14:7125/machine/device_power/status?LEDs
    is_on_template: '{{ value_json is not none and value_json.result.LEDs == "on" }}'
    resource: http://192.168.1.14:7125/machine/device_power/status?LEDs
    resource_template: >
      {% if is_state('switch.ngenLeds', 'on') %}
        http://192.168.1.14:7125/machine/device_power/off?LEDs
      {% else %}
        http://192.168.1.14:7125/machine/device_power/on?LEDs
      {% endif %}
    body_on: ""
    body_off: ""
    scan_interval: 2
```

[core REST switch documention](https://www.home-assistant.io/integrations/switch.rest/)  applies, unless specified here


* `resource` parameter is mandatory but won't be used to update the switch if resource_template is not null
* `state_resource` is optional ; if not set, it uses the "resource" parameter, so you better use the same url for resource and state_resource
* `scan_interval` has been added because I dislike things that are slow to switch, and by default on core RESTful switch, you CAN'T set scan_interval.

(BEWARE if the switch is a tasmota device : be sur to be on bleeding edge moonraker or it could not work because of a tasmota scecificity with 1 relay devices ; [see issue here](https://github.com/Arksine/moonraker/issues/134))
