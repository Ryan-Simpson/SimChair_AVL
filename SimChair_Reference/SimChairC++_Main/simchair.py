import pygame
import time

# Initialize
pygame.init()
pygame.joystick.init()

# Check for controller
if pygame.joystick.get_count() == 0:
    print("No controller found!")
    exit()

# Connect to first controller
controller = pygame.joystick.Joystick(0)
controller.init()
print(f"Connected to: {controller.get_name()}")

driving_mode = 0

# Read controls
while True:
    pygame.event.pump()

    left_shifter = controller.get_button(0)
    right_shifter = controller.get_button(1)
    
    steering = controller.get_axis(0)   # Steering wheel
    throttle = controller.get_axis(6)   # Gas pedal
    brake = controller.get_axis(1)      # Brake pedal

    if left_shifter or right_shifter:
        driving_mode = max(min(driving_mode, driving_mode - left_shifter),0)
        driving_mode = min(max(driving_mode, driving_mode + right_shifter),3)
        time.sleep(0.25)



    throttle_norm = min(-throttle + 1, 1)
    brake_norm = min(-brake + 1, 1)

    

    
    print(f"S: {steering:.2f} T: {throttle_norm:.2f} B: {brake_norm:.2f} M: {driving_mode:.2f}")
    
    time.sleep(0.2)
