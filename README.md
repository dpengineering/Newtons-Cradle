# NewtonsCradle Documentation :

## Main Methods

### scoop
Scoops desired numbers of balls simultaneously if the sum of the balls being scooped is less than 5.
Must be called in a thread to ensure the UI and hardware function as intended.

### scoopFiveBalls
Scoops left side first then right side. this is necessary to prevent a collision.
Must be called in a thread to ensure the UI and hardware function as intended.

### stop_balls
Is called before scooping balls after the initial scoop to stop the momentum of balls to ensure a successful scoop.
Must be called in a thread to ensure the UI and hardware function as intended.

## UI Features
* Sliders will change the value of opposite slider to prevent a collision. 
  * It will not allow the user to select more than five balls for scooping.

* Images of balls will change color based on ho many balls are being picked up on each side.

### Admin Button
* The Admin button is located in the bottom right corner, but is invisible.
* Password to enter the Admin Scene is "7266"

### Quit
Quits execution of the program and exits to the desktop

### Home
Homes the steppers and brings transitions back to the main screen

### Double Home
Homes 2 steppers at a time letting each arm home it's vertical and horizontal motor at the same time

### Mother-Function.py file
This function was used as a fix to a bug which made the motors and UI break after spamming the touch screen, adding a extra file allows for the main function to quit itself before creating a new thread which prevents kivy from breaking due to input overload the function then continuously runs main.py through a while True loop

## End of year 2024

### Bugs Fixed
I fixed a bug which broke the motors and UI when anybody spammed the screen when the UI was running. There haven't been any errors since that I've noticed.

### Going Forward
Most additions to the Newton's Cradle project to this point should be stylistic and to make the functions run smoother (QUADRA HOME FUNCTION!?!?), 
* Please note that use of threading breaks kivy so try to refrain from using Threading in main.py, also threading won't work for moving two motors in unison
* Possibly main.py could work without Mother-Function if threading is removed, previous software developers used threading as a way to keep the code running without breaking, however it could be possible with enough testing. 

