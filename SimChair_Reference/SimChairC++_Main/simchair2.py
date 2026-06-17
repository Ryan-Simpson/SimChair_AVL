import pygame
import time

# Steering is Axis 0
# Brake is Axis 1
# Throttle is Axis 6

# Left shifter is Btn 0
# Right shifter is Btn 1

# Initialize
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("No controller found!")
    exit()

controller = pygame.joystick.Joystick(0)
controller.init()
print(f"Connected to: {controller.get_name()}")
print(f"Total axes: {controller.get_numaxes()}")
print("\nMove each control and watch which axis changes:")
print("=" * 50)

while True:
    pygame.event.pump()
    
    print("\r", end="")  # Clear line

    for i in range(controller.get_numbuttons()):
        pressed = controller.get_button(i)
        print(f"Btn{i}: {pressed}  ", end="")
    
    print('\n')
    
    # Show ALL axes
    for i in range(controller.get_numaxes()):
        value = controller.get_axis(i)
        print(f"Axis{i}: {value:+.2f}  ", end="")

    print('\n')
    
    time.sleep(0.1)
