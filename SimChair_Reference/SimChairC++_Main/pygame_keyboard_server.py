import pygame
import socket

pygame.init()
screen = pygame.display.set_mode((400, 300))
clock = pygame.time.Clock()

# Replace 'localhost' with the IP address or hostname of your Linux machine
ROS2_IP = '172.17.0.1'
ROS2_PORT = 8002

pygame_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
pygame_socket.connect((ROS2_IP, ROS2_PORT))

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                input_data = "w"
            elif event.key == pygame.K_a:
                input_data = "a"
            elif event.key == pygame.K_s:
                input_data = "s"
            elif event.key == pygame.K_d:
                input_data = "d"
            else:
                input_data = ""

            if input_data:
                # Send input_data to ROS2 node over the network
                pygame_socket.send(input_data.encode())

    pygame.display.flip()
    clock.tick(30)

pygame_socket.close()
pygame.quit()
