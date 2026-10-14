// udp_sender_win.h
// WinSock2 UDP sender for the Windows D-BOX version.
// Functionally identical to udp_sender.h but uses WinSock2 instead of POSIX.
#ifndef SIMCHAIR_UDP_SENDER_WIN_H_
#define SIMCHAIR_UDP_SENDER_WIN_H_

#include <string>

#include "simchair/input_processor.h"

namespace simchair {

class UdpSenderWin {
 public:
    UdpSenderWin(std::string destination_ip, int destination_port);
    ~UdpSenderWin();

    UdpSenderWin(const UdpSenderWin&) = delete;
    UdpSenderWin& operator=(const UdpSenderWin&) = delete;

    [[nodiscard]] bool Open();
    bool Send(const VehicleCommand& cmd);

 private:
    std::string destination_ip_;
    int         destination_port_;
    // SOCKET is typedef'd as uintptr_t on Windows; use uintptr_t to avoid
    // pulling in <winsock2.h> in the header.
    uintptr_t   sock_ = ~uintptr_t{0};  // INVALID_SOCKET equivalent
    bool        wsa_started_ = false;
};

}  // namespace simchair

#endif  // SIMCHAIR_UDP_SENDER_WIN_H_
