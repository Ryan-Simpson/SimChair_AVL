#include "simchair/udp_sender_win.h"

// WinSock2 must be included before <windows.h>
#include <WinSock2.h>
#include <WS2tcpip.h>
#pragma comment(lib, "ws2_32.lib")

#include <cstdio>
#include <cstring>

namespace simchair {

UdpSenderWin::UdpSenderWin(std::string destination_ip, int destination_port)
    : destination_ip_(std::move(destination_ip)),
      destination_port_(destination_port) {}

UdpSenderWin::~UdpSenderWin() {
    if (sock_ != ~uintptr_t{0}) {
        closesocket(static_cast<SOCKET>(sock_));
    }
    if (wsa_started_) {
        WSACleanup();
    }
}

bool UdpSenderWin::Open() {
    WSADATA wsa_data{};
    if (WSAStartup(MAKEWORD(2, 2), &wsa_data) != 0) {
        fprintf(stderr, "WSAStartup failed: %d\n", WSAGetLastError());
        return false;
    }
    wsa_started_ = true;

    SOCKET s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (s == INVALID_SOCKET) {
        fprintf(stderr, "socket() failed: %d\n", WSAGetLastError());
        return false;
    }

    sockaddr_in probe{};
    probe.sin_family = AF_INET;
    if (inet_pton(AF_INET, destination_ip_.c_str(), &probe.sin_addr) != 1) {
        fprintf(stderr, "Invalid destination IP: %s\n", destination_ip_.c_str());
        closesocket(s);
        return false;
    }

    sock_ = static_cast<uintptr_t>(s);
    return true;
}

bool UdpSenderWin::Send(const VehicleCommand& cmd) {
    sockaddr_in dest{};
    dest.sin_family = AF_INET;
    dest.sin_port   = htons(static_cast<u_short>(destination_port_));
    inet_pton(AF_INET, destination_ip_.c_str(), &dest.sin_addr);

    char buf[64];
    snprintf(buf, sizeof(buf), "%.2f,%.2f,%.2f,%d",
             cmd.steering, cmd.throttle, cmd.brake, cmd.driving_mode);

    int sent = sendto(static_cast<SOCKET>(sock_), buf, static_cast<int>(strlen(buf)),
                      0, reinterpret_cast<const sockaddr*>(&dest), sizeof(dest));
    if (sent == SOCKET_ERROR) {
        fprintf(stderr, "sendto() failed: %d\n", WSAGetLastError());
        return false;
    }
    return true;
}

}  // namespace simchair
