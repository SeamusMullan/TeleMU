"""Tests for the TMU binary serializer."""

import math
import struct
import types

import pytest

from lmupi.sharedmem.tmu_serializer import (
    ALL_CHANNELS,
    KELVIN_OFFSET,
    MAGIC,
    FORMAT_VERSION,
    ChannelDescriptor,
    TMUSerializer,
    _kelvin_to_celsius,
    _rad_to_deg,
    _speed_from_local_vel,
)


# ---------------------------------------------------------------------------
# Lightweight stubs that mimic the ctypes structs
# ---------------------------------------------------------------------------

def _make_vec3(x=0.0, y=0.0, z=0.0):
    return types.SimpleNamespace(x=x, y=y, z=z)


def _make_wheel(**overrides):
    defaults = dict(
        mSuspensionDeflection=0.01,
        mRideHeight=0.05,
        mSuspForce=5000.0,
        mBrakeTemp=350.0,
        mBrakePressure=0.8,
        mRotation=50.0,          # rad/s
        mLateralPatchVel=0.0,
        mLongitudinalPatchVel=0.0,
        mLateralGroundVel=0.0,
        mLongitudinalGroundVel=0.0,
        mCamber=-0.05,           # radians
        mLateralForce=3000.0,
        mLongitudinalForce=1500.0,
        mTireLoad=4000.0,
        mGripFract=0.95,
        mPressure=180.0,         # kPa
        mTemperature=[350.0, 360.0, 355.0],  # Kelvin
        mWear=0.9,
        mFlat=False,
        mDetached=False,
        mToe=0.002,              # radians
        mTireCarcassTemperature=340.0,  # Kelvin
        mTireInnerLayerTemperature=[338.0, 339.0, 340.0],
    )
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_telemetry(**overrides):
    """Return a stub that looks like ``LMUVehicleTelemetry``."""
    defaults = dict(
        mID=0,
        mDeltaTime=0.016,
        mElapsedTime=123.456,
        mLapNumber=3,
        mLapStartET=100.0,
        mVehicleName=b"TestCar",
        mTrackName=b"TestTrack",
        mPos=_make_vec3(100.0, 2.0, 200.0),
        mLocalVel=_make_vec3(10.0, 0.5, 1.0),   # ~36.2 km/h
        mLocalAccel=_make_vec3(1.0, 0.0, 0.5),
        mLocalRot=_make_vec3(0.1, 0.2, 0.05),   # rad/s
        mLocalRotAccel=_make_vec3(0.01, 0.02, 0.005),
        mGear=3,
        mEngineRPM=7500.0,
        mEngineWaterTemp=90.0,
        mEngineOilTemp=110.0,
        mClutchRPM=7200.0,
        mUnfilteredThrottle=0.85,
        mUnfilteredBrake=0.0,
        mUnfilteredSteering=0.12,
        mUnfilteredClutch=0.0,
        mFilteredThrottle=0.83,
        mFilteredBrake=0.0,
        mFilteredSteering=0.12,
        mFilteredClutch=0.0,
        mSteeringShaftTorque=4.5,
        mFront3rdDeflection=0.002,
        mRear3rdDeflection=0.003,
        mFrontWingHeight=0.06,
        mFrontRideHeight=0.04,
        mRearRideHeight=0.05,
        mDrag=500.0,
        mFrontDownforce=3000.0,
        mRearDownforce=3200.0,
        mFuel=50.0,
        mEngineMaxRPM=9000.0,
        mOverheating=False,
        mDetached=False,
        mHeadlights=False,
        mLastImpactMagnitude=0.0,
        mEngineTorque=400.0,
        mCurrentSector=1,
        mSpeedLimiter=0,
        mMaxGears=7,
        mFuelCapacity=110.0,
        mPhysicalSteeringWheelRange=900.0,
        mDeltaBest=-0.5,
        mTurboBoostPressure=0.0,
        mBatteryChargeFraction=0.0,
        mElectricBoostMotorTorque=0.0,
        mElectricBoostMotorRPM=0.0,
        mElectricBoostMotorTemperature=0.0,
        mElectricBoostWaterTemperature=0.0,
        mElectricBoostMotorState=0,
        mRearBrakeBias=0.55,
        mWheels=[_make_wheel() for _ in range(4)],
    )
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_scoring(**overrides):
    """Return a stub that looks like ``LMUVehicleScoring``."""
    defaults = dict(
        mID=0,
        mTotalLaps=2,
        mSector=1,
        mFinishStatus=0,
        mLapDist=1234.5,
        mBestSector1=25.1,
        mBestSector2=52.3,
        mBestLapTime=78.5,
        mLastSector1=25.5,
        mLastSector2=53.0,
        mLastLapTime=79.2,
        mCurSector1=24.8,
        mCurSector2=0.0,
        mNumPitstops=1,
        mNumPenalties=0,
        mIsPlayer=True,
        mControl=0,
        mInPits=False,
        mPlace=3,
        mTimeBehindNext=1.2,
        mLapsBehindNext=0,
        mTimeBehindLeader=3.5,
        mLapsBehindLeader=0,
        mLapStartET=100.0,
        mHeadlights=0,
        mPitState=0,
        mFlag=0,
        mDRSState=False,
        mTimeIntoLap=23.456,
        mEstimatedLapTime=79.0,
    )
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_kelvin_to_celsius(self):
        assert _kelvin_to_celsius(373.15) == pytest.approx(100.0)
        assert _kelvin_to_celsius(273.15) == pytest.approx(0.0)
        assert _kelvin_to_celsius(0.0) == pytest.approx(-273.15)

    def test_rad_to_deg(self):
        assert _rad_to_deg(math.pi) == pytest.approx(180.0)
        assert _rad_to_deg(0.0) == pytest.approx(0.0)
        assert _rad_to_deg(math.pi / 2) == pytest.approx(90.0)

    def test_speed_from_local_vel(self):
        vel = _make_vec3(10.0, 0.0, 0.0)
        assert _speed_from_local_vel(vel) == pytest.approx(36.0)  # 10 m/s * 3.6

        vel = _make_vec3(0.0, 0.0, 0.0)
        assert _speed_from_local_vel(vel) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# TMUSerializer tests
# ---------------------------------------------------------------------------

class TestTMUSerializer:
    def test_default_all_channels(self):
        ser = TMUSerializer()
        assert len(ser.channels) == len(ALL_CHANNELS)

    def test_subset_channels(self):
        sel = ["speed", "throttle", "gear"]
        ser = TMUSerializer(channels=sel)
        assert ser.channel_names == sel

    def test_unknown_channel_raises(self):
        with pytest.raises(ValueError, match="Unknown channel"):
            TMUSerializer(channels=["nonexistent_channel"])

    def test_frame_size_consistency(self):
        ser = TMUSerializer(channels=["speed", "gear", "in_pits"])
        # timestamp(8) + speed(d=8) + gear(i=4) + in_pits(?=1) = 21
        assert ser.frame_size == 8 + 8 + 4 + 1

    def test_encode_decode_frame_roundtrip(self):
        channels = ["speed", "throttle", "gear", "engine_rpm", "in_pits"]
        ser = TMUSerializer(channels=channels)
        tele = _make_telemetry()
        scor = _make_scoring()

        frame = ser.encode_frame(tele, scor)
        assert len(frame) == ser.frame_size

        decoded = ser.decode_frame(frame)
        assert decoded["timestamp"] == pytest.approx(tele.mElapsedTime)
        expected_speed = _speed_from_local_vel(tele.mLocalVel)
        assert decoded["speed"] == pytest.approx(expected_speed)
        assert decoded["throttle"] == pytest.approx(85.0)
        assert decoded["gear"] == 3
        assert decoded["engine_rpm"] == pytest.approx(7500.0)
        assert decoded["in_pits"] is False

    def test_explicit_timestamp(self):
        ser = TMUSerializer(channels=["speed"])
        tele = _make_telemetry()
        scor = _make_scoring()

        frame = ser.encode_frame(tele, scor, timestamp=999.0)
        decoded = ser.decode_frame(frame)
        assert decoded["timestamp"] == pytest.approx(999.0)

    def test_kelvin_conversion_in_tire_temp(self):
        ser = TMUSerializer(channels=["tire_temp_fl"])
        tele = _make_telemetry()
        scor = _make_scoring()

        frame = ser.encode_frame(tele, scor)
        decoded = ser.decode_frame(frame)
        expected = 360.0 - KELVIN_OFFSET  # centre temperature
        assert decoded["tire_temp_fl"] == pytest.approx(expected)

    def test_radian_conversion_in_rotation(self):
        ser = TMUSerializer(channels=["local_rot_x"])
        tele = _make_telemetry(mLocalRot=_make_vec3(math.pi, 0.0, 0.0))
        scor = _make_scoring()

        frame = ser.encode_frame(tele, scor)
        decoded = ser.decode_frame(frame)
        assert decoded["local_rot_x"] == pytest.approx(180.0)

    def test_steering_uses_physical_range(self):
        ser = TMUSerializer(channels=["steering"])
        tele = _make_telemetry(mUnfilteredSteering=0.5, mPhysicalSteeringWheelRange=900.0)
        scor = _make_scoring()

        frame = ser.encode_frame(tele, scor)
        decoded = ser.decode_frame(frame)
        assert decoded["steering"] == pytest.approx(450.0)

    def test_encode_header_structure(self):
        ser = TMUSerializer(channels=["speed", "gear"])
        header = ser.encode_header(
            track="Monza", car="Porsche 963", driver="Player", sample_rate=60.0,
        )

        # Magic bytes
        assert header[:4] == MAGIC

        # Version
        (version,) = struct.unpack_from("<H", header, 4)
        assert version == FORMAT_VERSION

        # Channel count
        (num_ch,) = struct.unpack_from("<H", header, 6)
        assert num_ch == 2

    def test_header_decode_roundtrip(self):
        ser = TMUSerializer(channels=["speed", "throttle", "gear"])
        header = ser.encode_header(
            track="Spa", car="BMW M4 GT3", driver="TestDriver", sample_rate=120.0,
        )

        meta, ch_list, offset = TMUSerializer.decode_header(header)
        assert meta["track"] == "Spa"
        assert meta["car"] == "BMW M4 GT3"
        assert meta["driver"] == "TestDriver"
        assert meta["sample_rate"] == 120.0
        assert len(ch_list) == 3
        assert ch_list[0].name == "speed"
        assert ch_list[0].type_code == "d"
        assert ch_list[0].unit == "km/h"
        assert ch_list[1].name == "throttle"
        assert ch_list[2].name == "gear"
        assert ch_list[2].type_code == "i"
        assert offset == len(header)

    def test_decode_header_bad_magic(self):
        with pytest.raises(ValueError, match="Invalid magic"):
            TMUSerializer.decode_header(b"BAD\x00" + b"\x00" * 20)

    def test_available_channels(self):
        names = TMUSerializer.available_channels()
        assert isinstance(names, list)
        assert "speed" in names
        assert "gear" in names
        assert "tire_temp_fl" in names
        assert names == sorted(names)  # should be sorted

    def test_repr(self):
        ser = TMUSerializer(channels=["speed"])
        r = repr(ser)
        assert "TMUSerializer" in r
        assert "channels=1" in r

    def test_full_frame_all_channels(self):
        """Encode and decode a frame with ALL channels to verify nothing crashes."""
        ser = TMUSerializer()  # all channels
        tele = _make_telemetry()
        scor = _make_scoring()

        frame = ser.encode_frame(tele, scor)
        assert len(frame) == ser.frame_size

        decoded = ser.decode_frame(frame)
        assert "timestamp" in decoded
        assert len(decoded) == len(ALL_CHANNELS) + 1  # +1 for timestamp

    def test_scoring_channels(self):
        ser = TMUSerializer(channels=["total_laps", "best_lap_time", "place", "drs_state"])
        tele = _make_telemetry()
        scor = _make_scoring(mTotalLaps=5, mBestLapTime=78.5, mPlace=2, mDRSState=True)

        frame = ser.encode_frame(tele, scor)
        decoded = ser.decode_frame(frame)
        assert decoded["total_laps"] == 5
        assert decoded["best_lap_time"] == pytest.approx(78.5)
        assert decoded["place"] == 2
        assert decoded["drs_state"] is True

    def test_multiple_frames_sequential(self):
        """Multiple frames can be concatenated and decoded sequentially."""
        ser = TMUSerializer(channels=["speed", "gear"])
        tele = _make_telemetry()
        scor = _make_scoring()

        frames = bytearray()
        for i in range(5):
            frames += ser.encode_frame(tele, scor, timestamp=float(i))

        for i in range(5):
            decoded = ser.decode_frame(bytes(frames), offset=i * ser.frame_size)
            assert decoded["timestamp"] == pytest.approx(float(i))
