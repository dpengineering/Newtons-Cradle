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


## End of year 2023

### Bugs
After running Newton's Cradle for a while the UI will not update as intended, the cursor will not move but updates the values correctly. The reset widgets method should rn on its own thread or the main thread to guarantee it re draws correctly.
