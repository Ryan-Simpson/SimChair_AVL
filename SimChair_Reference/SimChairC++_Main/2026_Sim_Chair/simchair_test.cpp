#include <cstdio>
#include "include\dboxLiveMotion.h"
#include <Windows.h>
#include <thread>
#include <iostream>
#include <chrono>

#pragma comment(lib, DBOX_LIVEMOTION_LIB)
#pragma comment(lib, "Shell32.lib")


#define APP_KEY "TestChair"
#define APP_BUILD 1000

namespace
{
 struct RaceTelemetry
 {
   dbox::XyzFloat32 Acceleration;
   dbox::XyzFloat32 Velocity;
   dbox::I32 EngineRpm;
   dbox::QuadFloat32 SuspensionTravel;
   dbox::QuadFloat32 SurfaceTypeId;
   dbox::F32 PitchRad;
   dbox::F32 RollRad;

   DBOX_STRUCTINFO_BEGIN()
 		DBOX_STRUCTINFO_FIELD(RaceTelemetry, Acceleration, dbox::FT_XYZ_FLOAT32, dbox::FM_ACCELERATION_XYZ)	
		DBOX_STRUCTINFO_FIELD(RaceTelemetry, Velocity, dbox::FT_XYZ_FLOAT32, dbox::FM_VELOCITY_XYZ)
		DBOX_STRUCTINFO_FIELD(RaceTelemetry, EngineRpm, dbox::FT_INT32, dbox::FM_ENGINE_RPM)
		DBOX_STRUCTINFO_FIELD(RaceTelemetry, SuspensionTravel, dbox::FT_QUAD_FLOAT32, dbox::FM_SUSPENSION_TRAVEL_QUAD)
		DBOX_STRUCTINFO_FIELD(RaceTelemetry, SurfaceTypeId, dbox::FT_QUAD_INT32, dbox::FM_SURFACE_TYPE_ID)
		DBOX_STRUCTINFO_FIELD(RaceTelemetry, PitchRad, dbox::FT_FLOAT32, dbox::FM_PITCH_RAD)
		DBOX_STRUCTINFO_FIELD(RaceTelemetry, RollRad, dbox::FT_FLOAT32, dbox::FM_ROLL_RAD)
  DBOX_STRUCTINFO_END()
 };

 enum AppEvents
 {
   RACE_TELEMETRY,
 };
}

int main()
{
  [[maybe_unused]] static constexpr float pi {3.1415};
  dbox::LiveMotion::Initialize(APP_KEY, APP_BUILD);
	dbox::LiveMotion::RegisterEvent(RACE_TELEMETRY, dbox::EM_FRAME_UPDATE, RaceTelemetry::GetStructInfo());

	dbox::LiveMotion::Open();
	{
	  std::cout << "Starting delay...\n";
	  using namespace std::chrono_literals;
	  dbox::LiveMotion::ResetState();

	  dbox::LiveMotion::Start();

	  RaceTelemetry oTelemetry;
	  oTelemetry.PitchRad = pi/6;
	  
	  dbox::LiveMotion::PostEvent(RACE_TELEMETRY, oTelemetry);
	  
	  std::this_thread::sleep_for(2s);

	  dbox::LiveMotion::Stop();

	  dbox::LiveMotion::Start();

	  dbox::LiveMotion::PostEvent(RACE_TELEMETRY, oTelemetry);
	  dbox::LiveMotion::Stop();

	}

	std::cout << "Task completed\n";

	return 0;
}
