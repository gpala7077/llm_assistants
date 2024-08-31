# Adaptive Workstation

## Description
The Adaptive Workstation is a system that automatically adjusts a user's desk and office environment based on 
occupancy, user preferences, and Apple focus mode. The system is designed to provide the right amount of light at the
right time of day to ensure the user is comfortable and productive. The system is powered by Home-Assistant with
AppDaemon and Pyscript for automation and logic.

### How it Works
The system initializes by setting off to trigger only when the user is present at their desk. It uses a bluetooth connection
to determine if the user is present at their desk in addition to other presence/occupancy sensors. Combined, these sensors
ensure that the system only triggers when the user is present at their desk.



#### Default Behavior
The default behavior of the system is to turn on the lights at the user's desk when the user is present. Depending on the
user's iPhone Focus mode, the lights are set to a warm white tone when the user is in 'Personal' mode and a cool white tone
when the user is in 'Work' or 'Coding' modes. The lights are set to a dimmed state when the user is in 'Do Not Disturb' mode.


## Master/Room Switch
This system has a master automation switch that turns off this automation entirely and leaves it to manual mode. In
addition, this system has a user level switch that turns off the automation for a specific user. This is useful when
the user wants to manually control the lights at their desk but not affect the entire home.


## User Preferences and Light Settings
This system has the following light and user settings available for each user in the home:
- **Inactivity Time**: The user can set how long the lights should stay on after the room is unoccupied.
- **Lamp Darkness Threshold**: The user can set the light level threshold that triggers the lights to turn on.


# Commands
## High-Level Commands

### Turn on the Desk
```python
toggle_desk(room='office', user='gerardo') # Turn on Gerardo's desk
```
### Turn off the Desk
```python
toggle_desk(room='office', user='eva') # Turn on Eva's desk
```

### Fine-Tuned Commands

#### Example: Create a Scene in the Office for Productivity

```python

```
Here are some examples of color coordination for the lights in the home:
```yaml

```