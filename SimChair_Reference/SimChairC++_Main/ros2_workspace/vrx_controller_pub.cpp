#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <WS2tcpip.h>
#include <string>
#include <windows.h>
#include <basetsd.h>
#include <dinput.h>
#include <stdio.h>
#include <iostream>
#include <cmath>
#include <iostream>
#include <iomanip>

#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"

#pragma comment (lib, "ws2_32.lib")
#pragma comment(lib, "dinput8.lib")
#pragma comment(lib, "dxguid.lib")


using namespace std;

/////////////////////////////////////////////////////////////////////////////////////////
// DIRECTINPUT INITIALIZATION/////
// INITIALIZATION CODE WAS TAKEN FROM Jon Parise <jparise@cmu.edu/////
/////////////////////////////////////////////////////////////////////////////////////////
class Joystick
{
private:
	unsigned int            id;
	unsigned int            device_counter;
	LPDIRECTINPUT8          di;
	LPDIRECTINPUTDEVICE8    joystick;

public:
	Joystick(unsigned int id);
	~Joystick();

	HRESULT deviceName(char* name);

	HRESULT open();
	HRESULT close();

	HRESULT poll(DIJOYSTATE2* js);

	BOOL CALLBACK enumCallback(const DIDEVICEINSTANCE* instance, VOID* context);

	// Device Querying
	static unsigned int deviceCount();
};

BOOL CALLBACK enumCallback(const DIDEVICEINSTANCE* instance, VOID* context);
BOOL CALLBACK countCallback(const DIDEVICEINSTANCE* instance, VOID* counter);


#define SAFE_RELEASE(p)     { if(p) { (p)->Release(); (p) = NULL; } }

Joystick::Joystick(unsigned int id)
{
	this->id = id;
	device_counter = 0;

	di = NULL;
	joystick = NULL;
}

Joystick::~Joystick()
{
	close();
}

HRESULT
Joystick::deviceName(char* name)
{
	HRESULT hr;
	DIDEVICEINSTANCE device;

	ZeroMemory(&device, sizeof(device));
	device.dwSize = sizeof(device);

	if (!di || !joystick) {
		return E_INVALIDARG;
	}

	if (FAILED(hr = joystick->GetDeviceInfo(&device))) {
		return hr;
	}


	return hr;
}

HRESULT
Joystick::open()
{
	HRESULT hr;

	// Create a DirectInput device
	if (FAILED(hr = DirectInput8Create(GetModuleHandle(NULL),
		DIRECTINPUT_VERSION,
		IID_IDirectInput8,
		(VOID * *)& di, NULL))) {
		return hr;
	}

	// Look for the first simple joystick we can find.
	if (FAILED(hr = di->EnumDevices(DI8DEVCLASS_GAMECTRL, ::enumCallback,
		(LPVOID)this, DIEDFL_ATTACHEDONLY))) {
		return hr;
	}

	// Make sure we got a joystick
	if (joystick == NULL) {
		return E_FAIL;
	}

	// Set the data format to "simple joystick" - a predefined data format 
	//
	// A data format specifies which controls on a device we are interested in,
	// and how they should be reported. This tells DInput that we will be
	// passing a DIJOYSTATE2 structure to IDirectInputDevice::GetDeviceState().
	if (FAILED(hr = joystick->SetDataFormat(&c_dfDIJoystick2))) {
		return hr;
	}

	// Set the cooperative level to let DInput know how this device should
	// interact with the system and with other DInput applications.
	if (FAILED(hr = joystick->SetCooperativeLevel(NULL, DISCL_EXCLUSIVE | DISCL_FOREGROUND))) {
		return hr;
	}

	return S_OK;
}

HRESULT
Joystick::close()
{
	if (joystick) {
		joystick->Unacquire();
	}

	SAFE_RELEASE(joystick);
	SAFE_RELEASE(di);

	return S_OK;
}

HRESULT
Joystick::poll(DIJOYSTATE2* js)
{
	HRESULT hr;

	if (joystick == NULL) {
		return S_OK;
	}

	// Poll the device to read the current state
	hr = joystick->Poll();
	if (FAILED(hr)) {

		// DirectInput is telling us that the input stream has been
		// interrupted.  We aren't tracking any state between polls, so we
		// don't have any special reset that needs to be done.  We just
		// re-acquire and try again.
		hr = joystick->Acquire();
		while (hr == DIERR_INPUTLOST) {
			hr = joystick->Acquire();
		}

		// If we encounter a fatal error, return failure.
		if ((hr == DIERR_INVALIDPARAM) || (hr == DIERR_NOTINITIALIZED)) {
			return E_FAIL;
		}

		// If another application has control of this device, return success.
		// We'll just have to wait our turn to use the joystick.
		if (hr == DIERR_OTHERAPPHASPRIO) {
			return S_OK;
		}
	}

	// Get the input's device state
	if (FAILED(hr = joystick->GetDeviceState(sizeof(DIJOYSTATE2), js))) {
		return hr;
	}

	return S_OK;
}

BOOL CALLBACK
Joystick::enumCallback(const DIDEVICEINSTANCE* instance, VOID* context)
{
	// If this is the requested device ID ...
	if (device_counter == this->id) {

		// Obtain an interface to the enumerated joystick.  Stop the enumeration
		// if the requested device was created successfully.
		if (SUCCEEDED(di->CreateDevice(instance->guidInstance, &joystick, NULL))) {
			return DIENUM_STOP;
		}
	}

	// Otherwise, increment the device counter and continue with
	// the device enumeration.
	device_counter++;

	return DIENUM_CONTINUE;
}

BOOL CALLBACK
enumCallback(const DIDEVICEINSTANCE* instance, VOID* context)
{
	if (context != NULL) {
		return ((Joystick*)context)->enumCallback(instance, context);
	}
	else {
		return DIENUM_STOP;
	}
}

unsigned int
Joystick::deviceCount()
{
	unsigned int counter = 0;
	LPDIRECTINPUT8 di = NULL;
	HRESULT hr;

	if (SUCCEEDED(hr = DirectInput8Create(GetModuleHandle(NULL),
		DIRECTINPUT_VERSION,
		IID_IDirectInput8,
		(VOID * *)& di, NULL))) {
		di->EnumDevices(DI8DEVCLASS_GAMECTRL, ::countCallback,
			&counter, DIEDFL_ATTACHEDONLY);
	}

	return counter;
}

BOOL CALLBACK
countCallback(const DIDEVICEINSTANCE* instance, VOID* counter)
{
	if (counter != NULL) {
		unsigned int* tmpCounter = (unsigned int*)counter;
		(*tmpCounter)++;
		counter = tmpCounter;
	}

	return DIENUM_CONTINUE;
}
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//END OF THE INITALIZATION /////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////


// ROS2 NODE

using namespace std::chrono_literals;

class VRXControllerPublisher : public rclcpp::Node
{
  public:
    VRXControllerPublisher()
    : Node("vrxcontroller_publisher")
    {
      publisher_ = this->create_publisher<geometry_msgs::msg::Twist>("/simulator_chair/cmd_vel", 10);
      timer_= this->create_wall_timer(
        50ms, std::bind(&VRXControllerPublisher::timer_callback, this));
      // Joystick Defined
      unsigned int i;
      unsigned int numJoysticks = Joystick::deviceCount();
      printf("Found %d joysticks.\n", numJoysticks);

      // Initialize all of the joysticks on the system.
      for (i = 0; i < numJoysticks; i++) {
        joysticks[i] = new Joystick(i);
        joysticks[i]->open();

      }


    }

  private:
    void timer_callback()
    {
      auto message = geometry_msgs::msg::Twist();
      joysticks[1]->poll(&js0); // Steering wheel and pedals
	  joysticks[0]->poll(&js1); // Shifter

      //STEERING
		  double tempSteer = (double)js0.lX;

		  tempSteer = (((65600 - tempSteer) / 65600.0)-.5)*2.0;  // 0 - 1, .5 in middle -> -1, 1, 0 in middle

      //ACCELERATION
		  double tempAccel = (double)js0.lRz;
		  tempAccel = round((65600 - tempAccel) / 65600.00 * 100.0)/100.0;

      //BRAKING
      double tempBraking = (double)js0.lY;
      tempBraking = round((65600 - tempBraking) / 65600.00 * 100);

      // Forward or Reverse using Shifter
      int fwd = js1.rgbButtons[0]; // Forward Shifter -- any non-'R' position works
		  int rvs = js1.rgbButtons[7]; // Reverse Shifter


      if (rvs == 128)
      {
        message.linear.x = -1.0*tempAccel;
        message.angular.z = tempSteer;
        // Convert twist to negative
      }
      else
      {
        message.linear.x = tempAccel;
        message.angular.z = tempSteer;
        // We're assuming all non 'R' positions of the shifter are forward
        // TODO: Add varying velocities based on shifter locations  1-7

      }

      // message->header.frame_id = "CarEgo";
      // message->header.stamp = this->now();
	  RCLCPP_INFO_ONCE(this->get_logger(), "Before publishing!");
	  RCLCPP_INFO_ONCE(node->get_logger(), message);
      publisher_->publish(message);
	  


    }
    DIJOYSTATE2 js0;
    DIJOYSTATE2 js1;
    rclcpp::TimerBase::SharedPtr timer_;
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr publisher_;
    Joystick* joysticks[4]{};

};


int main(int argc, char * argv[])
{

  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<VRXControllerPublisher>());
  rclcpp::shutdown();
  return 0;
}