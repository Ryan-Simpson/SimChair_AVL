// Client code for receiving IMU data from IMU on car
// Data is then converted into motion of the simulator chair to "simulate" what the car experiences

// Edited by CW 4/26/2022
//

#undef UNICODE


#include <cstdio>
#include <conio.h>
#include "C:\Users\VRX 226\Desktop\2022 Autonomous Vehicle Lab\Demo\IMUClient_AGV\LiveMotionB10767\dboxLiveMotion.h"
#include <math.h> // For sin
#include <string>
#include <iostream>
#include <sstream>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <stdlib.h>
#include <stdio.h>
#include <iostream>
#include <Windows.h>
#include <vector>


//#define DEFAULT_ADDRESS "166.203.181.152" for connecting without VPN
#define DEFAULT_ADDRESS "127.0.0.1"
#define DEFAULT_PORT "9999"
#define DEFAULT_BUFLEN 32



#pragma comment (lib, "Ws2_32.lib")
#pragma comment(lib, DBOX_LIVEMOTION_LIB)

const char* const APP_KEY = "CalPolyPomonaDevSim";
const dbox::U32 APP_BUILD = 1000;
const double PI = 3.141592654f;
using std::string;
using std::basic_istream;

struct SimConfig {
	dbox::F32 MasterGain;
	dbox::F32 MasterSpectrum;

	DBOX_STRUCTINFO_BEGIN()
		DBOX_STRUCTINFO_FIELD(SimConfig, MasterGain, dbox::FT_FLOAT32, dbox::FM_MASTER_GAIN_DB)
		DBOX_STRUCTINFO_FIELD(SimConfig, MasterSpectrum, dbox::FT_FLOAT32, dbox::FM_MASTER_SPECTRUM_DB)
		DBOX_STRUCTINFO_END()
};

struct MotionConfig {
	dbox::F32 EngineRpmIdle;
	dbox::F32 EngineRpmMax;
	dbox::F32 EngineTorqueMax;

	DBOX_STRUCTINFO_BEGIN()
		DBOX_STRUCTINFO_FIELD(MotionConfig, EngineRpmIdle, dbox::FT_FLOAT32, dbox::FM_ENGINE_RPM_IDLE)
		DBOX_STRUCTINFO_FIELD(MotionConfig, EngineRpmMax, dbox::FT_FLOAT32, dbox::FM_ENGINE_RPM_MAX)
		DBOX_STRUCTINFO_FIELD(MotionConfig, EngineTorqueMax, dbox::FT_FLOAT32, dbox::FM_ENGINE_TORQUE_MAX)
		DBOX_STRUCTINFO_END()
};

struct MotionData {
	dbox::F32 Roll;  // -1.0 to 1.0
	dbox::F32 Pitch;  // -1.0 to 1.0
	dbox::F32 Heave;  // -1.0 to 1.0
	dbox::F32 EngineRpm; // Depends on MotionConfig EngineRpmIdle and EngineRpmMax
	dbox::F32 EngineTorque; // Depends on MotionConfig EngineTorqueMax

	DBOX_STRUCTINFO_BEGIN()
		DBOX_STRUCTINFO_FIELD(MotionData, Roll, dbox::FT_FLOAT32, dbox::FM_RAW_ROLL)
		DBOX_STRUCTINFO_FIELD(MotionData, Pitch, dbox::FT_FLOAT32, dbox::FM_RAW_PITCH)
		DBOX_STRUCTINFO_FIELD(MotionData, Heave, dbox::FT_FLOAT32, dbox::FM_RAW_HEAVE)
		DBOX_STRUCTINFO_FIELD(MotionData, EngineRpm, dbox::FT_FLOAT32, dbox::FM_ENGINE_RPM)
		DBOX_STRUCTINFO_FIELD(MotionData, EngineTorque, dbox::FT_FLOAT32, dbox::FM_ENGINE_TORQUE)
		DBOX_STRUCTINFO_END()
};


/// These are your unique event ids that you'll use when calling PostEvent.
enum AppEvents {
	SIM_CONFIG = 1000,
	MOTION_CONFIG = 2000,
	MOTION_DATA = 3000,
};

/// This function is used to prevent possible error when the application ends before the normal execution.
/// This includes Closing the console window, CTRL-C, Windows Shutdown, Log Off...
bool WINAPI OnAbnormalTerminate(DWORD /*dwCtrlType*/) {
	dbox::LiveMotion::Terminate();
	return true;
}

int main(int, char* []) {
	SetConsoleCtrlHandler((PHANDLER_ROUTINE)OnAbnormalTerminate, true);

	float pitchd;

	// Create a sample sinus signal
	float adSinusSignal[1000]; // 1000 samples
	for (int nIndex = 0; nIndex < 1000; nIndex++) {
		adSinusSignal[nIndex] = static_cast<float>(sin(2.0f * PI * nIndex / 1000.0f));
	}

	// Initialization and registration should be done only once.
	dbox::LiveMotion::Initialize(APP_KEY, APP_BUILD);
	dbox::LiveMotion::RegisterEvent(SIM_CONFIG, dbox::EM_CONFIG_UPDATE, SimConfig::GetStructInfo());
	dbox::LiveMotion::RegisterEvent(MOTION_CONFIG, dbox::EM_CONFIG_UPDATE, MotionConfig::GetStructInfo());
	dbox::LiveMotion::RegisterEvent(MOTION_DATA, dbox::EM_FRAME_UPDATE, MotionData::GetStructInfo());

	// Registration completed, open motion output device.
	// Open can be called once, after end of registration.
	dbox::LiveMotion::Open();
	{
		// Motion System initialization
		Sleep(100);

		// Sim Start
		// It is always good to ResetState before each session.
		dbox::LiveMotion::ResetState();

		SimConfig oSimConfig;
		oSimConfig.MasterGain = 0; // 0dB
		oSimConfig.MasterSpectrum = 0; // 0dB
		dbox::LiveMotion::PostEvent(SIM_CONFIG, oSimConfig);

		MotionConfig oMotionConfig;
		oMotionConfig.EngineRpmIdle = 750.4f;
		oMotionConfig.EngineRpmMax = 3420.2f;
		oMotionConfig.EngineTorqueMax = 447.42f;
		dbox::LiveMotion::PostEvent(MOTION_CONFIG, oMotionConfig);

		MotionData oMotionData;
		oMotionData.Roll = -0.3f;
		oMotionData.Pitch = 0.2f;
		oMotionData.Heave = 0.3f;
		oMotionData.EngineRpm = 1000;
		oMotionData.EngineTorque = 175;
		dbox::LiveMotion::PostEvent(MOTION_DATA, oMotionData);
		// ...
		dbox::LiveMotion::PostEvent(MOTION_DATA, oMotionData);
		// ...
		dbox::LiveMotion::PostEvent(MOTION_DATA, oMotionData);
		// ...
		dbox::LiveMotion::PostEvent(MOTION_DATA, oMotionData);

		// Start of sim, this will fade-in actual motion.
		dbox::LiveMotion::Start();

		oMotionData.Roll = 0;
		oMotionData.Pitch = 0;
		oMotionData.Heave = 0;
		oMotionData.EngineRpm = 0; // Mute RPM
		oMotionData.EngineTorque = 0;
		dbox::LiveMotion::PostEvent(MOTION_DATA, oMotionData);

		// ...
		dbox::LiveMotion::PostEvent(MOTION_DATA, oMotionData);
		// ...
		dbox::LiveMotion::PostEvent(MOTION_DATA, oMotionData);

		Sleep(50);

		///
		WSADATA wsaData;
		SOCKET ConnectSocket = INVALID_SOCKET;
		struct addrinfo* result = NULL,
			* ptr = NULL,
			hints;
		char sendbuf[4] = "134";
		int sendbuflen = 4;
		char recvbuf[DEFAULT_BUFLEN];
		int iResult;
		int iSendResult;
		int recvbuflen = DEFAULT_BUFLEN;


		// Initialize Winsock
		iResult = WSAStartup(MAKEWORD(2, 2), &wsaData);
		if (iResult != 0) {
			printf("WSAStartup failed with error: %d\n", iResult);
			return 1;
		}

		ZeroMemory(&hints, sizeof(hints));
		hints.ai_family = AF_INET;
		hints.ai_socktype = SOCK_STREAM;
		hints.ai_protocol = IPPROTO_TCP;

		// Resolve the server address and port
		iResult = getaddrinfo(DEFAULT_ADDRESS, DEFAULT_PORT, &hints, &result);
		if (iResult != 0) {
			printf("getaddrinfo failed with error: %d\n", iResult);
			WSACleanup();
			return 1;
		}

		// Attempt to connect to an address until one succeeds
		for (ptr = result; ptr != NULL; ptr = ptr->ai_next) {

			// Create a SOCKET for connecting to server
			ConnectSocket = socket(ptr->ai_family, ptr->ai_socktype,
				ptr->ai_protocol);
			if (ConnectSocket == INVALID_SOCKET) {
				printf("socket failed with error: %ld\n", WSAGetLastError());
				WSACleanup();
				return 1;
			}

			// Connect to server.
			iResult = connect(ConnectSocket, ptr->ai_addr, (int)ptr->ai_addrlen);
			if (iResult == SOCKET_ERROR) {
				closesocket(ConnectSocket);
				ConnectSocket = INVALID_SOCKET;
				continue;
			}
			break;
		}

		freeaddrinfo(result);

		if (ConnectSocket == INVALID_SOCKET) {
			printf("Unable to connect to server!\n");
			WSACleanup();
			return 1;
		}

		// Send an initial buffer
		//iResult = send(ConnectSocket, sendbuf, (int)strlen(sendbuf), 0);
		if (iResult == SOCKET_ERROR) {
			printf("send failed with error: %d\n", WSAGetLastError());
			closesocket(ConnectSocket);
			WSACleanup();
			return 1;
		}

		// shutdown the connection since no more data will be sent
		iResult = shutdown(ConnectSocket, SD_SEND);
		if (iResult == SOCKET_ERROR) {
			printf("shutdown failed with error: %d\n", WSAGetLastError());
			closesocket(ConnectSocket);
			WSACleanup();
			return 1;
		}

		// Receive until the peer closes the connection
		while (true) {
			//connect(ConnectSocket, ptr->ai_addr, (int)ptr->ai_addrlen);
			//iSendResult = send(ConnectSocket, sendbuf, sendbuflen, 0);
			//std::cout << sendbuf << std::endl;
			memset(recvbuf, 0, recvbuflen);

			iResult = recv(ConnectSocket, recvbuf, recvbuflen, 0);
			system("cls");
			std::string data(recvbuf);
			std::string delim = "/";

			if (!data.empty())
			{

				std::vector<std::string> words{};

				size_t pos = 0;
				while ((pos = data.find(delim)) != std::string::npos)
				{
					words.push_back(data.substr(0, pos));
					data.erase(0, pos + delim.length());
				}

				try
				{
					float pitch = (std::stof(words[0])) * (1.78 / 45.0);
					if (pitch > 1.0)
					{
						pitch = 1.0;
					}
					if (pitch < -1.0)
					{
						pitch = -1.0;
					}
					float roll = (std::stof(words[1])) * (-2.38 / 45.0);
					if (roll > 1.0)
					{
						roll = 1.0;
					}
					if (roll < -1.0)
					{
						roll = -1.0;
					}

					oMotionData.Roll = roll; // Simulate Roll
					oMotionData.Pitch = pitch; // Simulate Pitch
					dbox::LiveMotion::PostEvent(MOTION_DATA, oMotionData);

					std::cout << "Pitch: " << pitch << std::endl;
					std::cout << "Roll: " << roll << std::endl;
					words.clear();
				}
				catch (const std::invalid_argument& ia)
				{
					std::cerr << "Invalid Argument: " << ia.what() << '\n';
					words.clear();
					continue;
				}
				if (iResult > 0)
				{
					printf("Bytes received: %d\n", iResult);
				}
				else if (iResult == 0) {
					printf("Connection closed\n");
				}
				else {
					printf("recv failed with error: %d\n", WSAGetLastError());
				}
			}
			Sleep(50);
		}

		// ???
		dbox::   LiveMotion::PostEvent(MOTION_DATA, oMotionData);
		// ...
		dbox::LiveMotion::PostEvent(MOTION_DATA, oMotionData);
		// ...
		dbox::LiveMotion::PostEvent(MOTION_DATA, oMotionData);
		// ...
		dbox::LiveMotion::PostEvent(MOTION_DATA, oMotionData);

		Sleep(5000);


		// End of level, this will fade-out motion.
		dbox::LiveMotion::Stop();

		// Level End

	}

	// Close motion output device.
	dbox::LiveMotion::Close();
	// Terminate
	dbox::LiveMotion::Terminate();

	printf("\nEnded, press any key...\n");
	_getch();
	return 0;
}