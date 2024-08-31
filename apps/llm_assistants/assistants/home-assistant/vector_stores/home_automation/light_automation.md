# Adaptive Lighting System

## Description
The Adaptive Lighting System is a system that automatically adjusts the lighting in the home based on the time of day,
current brightness, user iPhone focus modes, user preferences and room occupancy. The system is designed to provide the
right amount of light at the right time of day to ensure the user is comfortable and productive. The system is powered 
by Home-Assistant with AppDaemon and Pyscript for automation and logic.


### How it Works
The system initializes by setting off to trigger at any sign of occupancy in the home as well as non-occupancy after
a certain period of time. It is meant to control all lights holistically in the home so that no matter the brand and
feature capabilities this system should still be able to control it.

#### Default Behavior
The default behavior of the system is to turn on the lights in the home when the user enters the occupied room.
Depending on any user's iPhone Focus mode depends on the tone and hue of the lights as well. Typically, the lights are 
set to a warm white tone when users are in 'Personal' mode and a cool white tone when users are in 'Work' or 'Coding'
modes. The lights are set to a dimmed state when the user is in 'Do Not Disturb' mode. The lights are set to a bright
white tone when the user is in 'Fitness' mode. These user settings can be adjusted in the Home Assistant app.

## Master/Room Switch
This system has a master automation switch that turns off this automation entirely and leaves it to manual mode. In 
addition, this system has a room level switch that turns off the automation for a specific room. This is useful when
the user wants to manually control the lights in a specific room but not affect the entire home.

## User Preferences and Light Settings
This system has the following light and user settings available for each room in the home:
- **Inactivity Time**: The user can set how long the lights should stay on after the room is unoccupied.
- **Light Level Delta**: The user can set how much the light level should change when the room is occupied before the lights are adjusted.
- **Light Level Threshold**: The user can set the light level threshold that triggers the lights to turn on.
- **Light Scene Default**: The user can set the default light scene for the room. (e.g. 'Natural Light', 'Concentrate')

# Commands
## High-Level Commands

### Turn on the Lights
```python
run_master_on_automation(app='workstation', room='living_room') # Runs the light automation for the living room
```
### Turn off the Lights
```python
run_master_off_automation(app='lights',room='living_room', override=True) # Runs the light automation for the living room
```

### Fine-Tuned Commands
Fine-tuned commands involve controlling the lights in the home at a more granular level. These commands are useful when
the user wants to control the lights in a specific room or set of rooms.

For example, what if the user wants you to create a scene in the office that is conducive to productivity? You can
create a scene that turns on the lights in the office to a bright white tone and sets the light level to 100%. You can
try to combine tones and hues together in different sections of the same room to create a unique lighting experience.

#### Example: Create a Scene in the Office for Productivity

```python

# First, turn off the light automation for the office
# This allows for the room to be manually controlled by the user
control_user_overrides(app='lights', command='turn_off', area='bedroom')


# Next, group sets of lights together to create a unique lighting experience
lights = get_entities(room='office')

# OUTPUT: {
# 'light.office_gerardos_desk_light_1': 'on', 
# 'light.office_gerardos_desk_lamp_1': 'on',
# 'light.office_ceiling_light_1': 'on', 
# 'light.office_ceiling_light_2': 'on'
# 'light.office_evas_desk_light_1': 'on'
# 'light.office_evas_desk_lamp_1': 'on'
# }


command_matching_entities(
    hacs_commands='turn_on',
    domain='light',
    pattern='light_.*\d$',
    exclude_pattern=['desk'], # You can come up with the ideal groupings in ReGeX
    area='office',
    xy_color=[0.5, 0.5], # Bright white tone
    brightness=100, # 100% brightness
    )
command_matching_entities(
    hacs_commands='turn_on',
    domain='light',
    pattern='light_.*\d$',
    exclude_pattern=['ceiling_light'], # You can come up with the ideal groupings in ReGeX
    area='office',
    xy_color=[0.401, 0.358], # Bright white tone
    brightness=255, # 100% brightness
    )
command_matching_entities(
    hacs_commands='turn_on',
    domain='light',
    pattern='light_.*\d$',
    exclude_pattern=['desk'], # You can come up with the ideal groupings in ReGeX
    area='office',
    xy_color=[0.329, 0.334], # Natural light tone
    brightness=255, # 100% brightness
    )



```
Here are some examples of color coordination for the lights in the home:
```yaml
adaptive_lighting:
energize: 
  time_window: 
    - "6:00"  # 6:00 AM
    - "10:00" # 10:00 AM
  hs_color:   # Choice 2
    - 41.14
    - 2.841
  xy_color: # Choice 1
    - 0.329 
    - 0.334
  rgb_color: # Choice 3
    - 255
    - 252
    - 247
  color_temp_kelvin: 6410 # Choice 4
  color_temp: 156  # Choice 5
  brightness: 255 # Choice 6

concentrate: 
  time_window: 
    - "10:00"
    - "16:00"
  hs_color: 
    - 26.722
    - 28.925
  xy_color: 
    - 0.401 
    - 0.359
  rgb_color: 
    - 255 
    - 214
    - 181
  color_temp_kelvin: 4347
  color_temp: 230
  brightness: 255

read: 
  time_window: 
    - "16:00"
    - "22:00"
  hs_color: 
    - 28.016
    - 59.968
  xy_color: 
    - 0.507 
    - 0.384
  rgb_color: 
    - 255
    - 173
    - 102
  color_temp_kelvin: 2890
  brightness: 255

relax: 
  time_window: 
    - "22:00"
    - "23:00"
  hs_color: 
    - 29.667
    - 82.994
  xy_color: 
    - 0.575 
    - 0.389
  rgb_color: 
    - 255
    - 148
    - 43
  color_temp_kelvin: 2237
  color_temp: 447
  brightness: 144

rest: 
  time_window: 
    - "23:00"
    - "0:00"
  hs_color: 
    - 33.767
    - 84.314
  xy_color: 
    - 0.561
    - 0.4042
  rgb_color: 
    - 255
    - 161
    - 40
  color_temp_kelvin: None
  color_temp: None
  brightness: 89

night_light: 
  time_window: 
    - "0:00"
    - "6:00"
  hs_color: 
    - 33.767
    - 84.314
  xy_color: 
    - 0.561
    - 0.4042
  rgb_color: 
    - 255
    - 161
    - 40
  color_temp_kelvin: None
  color_temp: None
  brightness: 1
```