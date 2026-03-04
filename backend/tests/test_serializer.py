"""Tests for the binary frame serializer."""

import math
import struct

import pytest

from telemu.recording.channels import ALL_CHANNELS, DEFAULT_CHANNELS, ChannelDef, _K2C, _RAD2DEG
from telemu.recording.serializer import FrameSerializer
from telemu.sharedmem.lmu_data import LMUVehicleScoring, LMUVehicleTelemetry


# ── Helpers ───────────────────────────────────────────────────────────


def _make_telemetry(**overrides) -> LMUVehicleTelemetry:
    """Create an LMUVehicleTelemetry instance with optional field overrides."""
    t = LMUVehicleTelemetry()
    for key, val in overrides.items():
        setattr(t, key, val)
    return t


def _make_scoring(**overrides) -> LMUVehicleScoring:
    """Create an LMUVehicleScoring instance with optional field overrides."""
    s = LMUVehicleScoring()
    for key, val in overrides.items():
        setattr(s, key, val)
    return s


# ── Channel definition tests ─────────────────────────────────────────


class TestChannelDefinitions:
    def test_all_channels_non_empty(self):
        assert len(ALL_CHANNELS) > 0

    def test_default_channels_subset_of_all(self):
        for name in DEFAULT_CHANNELS:
            assert name in ALL_CHANNELS, f"Default channel '{name}' not in ALL_CHANNELS"

    def test_channel_def_fields(self):
        ch = ALL_CHANNELS["speed"]
        assert ch.name == "speed"
        assert ch.fmt == "d"
        assert ch.unit == "km/h"
        assert ch.source == "computed"
        assert callable(ch.extract)

    def test_channel_names_match_keys(self):
        for key, ch in ALL_CHANNELS.items():
            assert ch.name == key, f"Key '{key}' != channel name '{ch.name}'"

    def test_valid_format_characters(self):
        valid_fmts = {"d", "f", "i", "h", "b", "B", "?"}
        for name, ch in ALL_CHANNELS.items():
            assert ch.fmt in valid_fmts, f"Channel '{name}' has invalid fmt '{ch.fmt}'"

    def test_all_four_wheels_present(self):
        for pos in ("fl", "fr", "rl", "rr"):
            assert f"wheel_{pos}_temp" in ALL_CHANNELS

    def test_telemetry_and_scoring_channels_exist(self):
        sources = {ch.source for ch in ALL_CHANNELS.values()}
        assert "telemetry" in sources
        assert "scoring" in sources


# ── Serializer construction tests ─────────────────────────────────────


class TestSerializerConstruction:
    def test_default_channels(self):
        ser = FrameSerializer()
        assert ser.channel_names == DEFAULT_CHANNELS

    def test_custom_channels(self):
        names = ["speed", "rpm", "gear"]
        ser = FrameSerializer(names)
        assert ser.channel_names == names

    def test_unknown_channel_raises(self):
        with pytest.raises(ValueError, match="Unknown channel"):
            FrameSerializer(["speed", "nonexistent_channel"])

    def test_empty_channels_raises(self):
        with pytest.raises(ValueError, match="At least one channel"):
            FrameSerializer([])

    def test_frame_size_matches_format(self):
        ser = FrameSerializer(["speed", "rpm", "gear"])
        assert ser.frame_size == struct.calcsize(ser.format_string)

    def test_frame_size_includes_timestamp(self):
        # timestamp (8 bytes) + speed (8) + gear (4) = 20
        ser = FrameSerializer(["speed", "gear"])
        assert ser.frame_size == 8 + 8 + 4


# ── Serialization roundtrip tests ─────────────────────────────────────


class TestSerializationRoundtrip:
    def test_roundtrip_basic(self):
        t = _make_telemetry(mEngineRPM=7500.0, mGear=4)
        t.mLocalVel.x = 30.0
        t.mLocalVel.y = 0.0
        t.mLocalVel.z = 5.0
        s = _make_scoring()

        ser = FrameSerializer(["speed", "rpm", "gear"])
        frame = ser.serialize(12.345, t, s)
        result = ser.deserialize(frame)

        assert result["timestamp"] == pytest.approx(12.345)
        expected_speed = math.sqrt(30.0**2 + 5.0**2) * 3.6
        assert result["speed"] == pytest.approx(expected_speed)
        assert result["rpm"] == pytest.approx(7500.0)
        assert result["gear"] == 4

    def test_roundtrip_all_default_channels(self):
        t = _make_telemetry(mEngineRPM=6000.0, mFuel=50.0)
        s = _make_scoring(mPlace=3, mBestLapTime=92.5)

        ser = FrameSerializer()  # default channels
        frame = ser.serialize(100.0, t, s)
        result = ser.deserialize(frame)

        assert result["timestamp"] == pytest.approx(100.0)
        assert result["rpm"] == pytest.approx(6000.0)
        assert result["fuel"] == pytest.approx(50.0)
        assert result["place"] == 3
        assert result["best_lap_time"] == pytest.approx(92.5)

    def test_frame_size_is_exact(self):
        ser = FrameSerializer(["speed", "rpm"])
        t = _make_telemetry()
        s = _make_scoring()
        frame = ser.serialize(0.0, t, s)
        assert len(frame) == ser.frame_size


# ── Type conversion tests ─────────────────────────────────────────────


class TestTypeConversions:
    def test_kelvin_to_celsius(self):
        """Tyre temps are stored in Kelvin, should be converted to °C."""
        t = _make_telemetry()
        # Set FL centre temperature to 363.15K (= 90°C)
        t.mWheels[0].mTemperature[1] = 363.15
        s = _make_scoring()

        ser = FrameSerializer(["wheel_fl_temp"])
        frame = ser.serialize(0.0, t, s)
        result = ser.deserialize(frame)

        assert result["wheel_fl_temp"] == pytest.approx(90.0)

    def test_radians_to_degrees(self):
        """Rotation values are stored in rad/s, should be converted to °/s."""
        t = _make_telemetry()
        t.mLocalRot.x = math.pi  # 180 °/s
        s = _make_scoring()

        ser = FrameSerializer(["local_rot_x"])
        frame = ser.serialize(0.0, t, s)
        result = ser.deserialize(frame)

        assert result["local_rot_x"] == pytest.approx(180.0)

    def test_throttle_percent(self):
        """Throttle 0.0–1.0 should be converted to 0–100%."""
        t = _make_telemetry(mUnfilteredThrottle=0.75)
        s = _make_scoring()

        ser = FrameSerializer(["throttle"])
        frame = ser.serialize(0.0, t, s)
        result = ser.deserialize(frame)

        assert result["throttle"] == pytest.approx(75.0)

    def test_speed_from_velocity(self):
        """Speed should be computed as |velocity| * 3.6 km/h."""
        t = _make_telemetry()
        # 10 m/s in each axis → |v| = sqrt(300) m/s
        t.mLocalVel.x = 10.0
        t.mLocalVel.y = 10.0
        t.mLocalVel.z = 10.0
        s = _make_scoring()

        ser = FrameSerializer(["speed"])
        frame = ser.serialize(0.0, t, s)
        result = ser.deserialize(frame)

        expected = math.sqrt(300.0) * 3.6
        assert result["speed"] == pytest.approx(expected)

    def test_camber_radians_to_degrees(self):
        """Wheel camber should be converted from radians to degrees."""
        t = _make_telemetry()
        t.mWheels[0].mCamber = math.radians(-3.5)  # -3.5°
        s = _make_scoring()

        ser = FrameSerializer(["wheel_fl_camber"])
        frame = ser.serialize(0.0, t, s)
        result = ser.deserialize(frame)

        assert result["wheel_fl_camber"] == pytest.approx(-3.5)

    def test_battery_charge_percent(self):
        """Battery charge 0.0–1.0 should be converted to 0–100%."""
        t = _make_telemetry(mBatteryChargeFraction=0.42)
        s = _make_scoring()

        ser = FrameSerializer(["battery_charge"])
        frame = ser.serialize(0.0, t, s)
        result = ser.deserialize(frame)

        assert result["battery_charge"] == pytest.approx(42.0)


# ── Boolean channel tests ─────────────────────────────────────────────


class TestBooleanChannels:
    def test_bool_true(self):
        t = _make_telemetry(mOverheating=True)
        s = _make_scoring()

        ser = FrameSerializer(["overheating"])
        frame = ser.serialize(0.0, t, s)
        result = ser.deserialize(frame)

        assert result["overheating"] is True

    def test_bool_false(self):
        t = _make_telemetry(mOverheating=False)
        s = _make_scoring()

        ser = FrameSerializer(["overheating"])
        frame = ser.serialize(0.0, t, s)
        result = ser.deserialize(frame)

        assert result["overheating"] is False

    def test_scoring_bool_drs(self):
        t = _make_telemetry()
        s = _make_scoring(mDRSState=True)

        ser = FrameSerializer(["drs"])
        frame = ser.serialize(0.0, t, s)
        result = ser.deserialize(frame)

        assert result["drs"] is True


# ── Per-wheel channel tests ───────────────────────────────────────────


class TestWheelChannels:
    def test_all_wheel_positions(self):
        """Each wheel position should extract from the correct index."""
        t = _make_telemetry()
        temps_k = [350.0, 355.0, 345.0, 348.0]  # Kelvin
        for i, temp in enumerate(temps_k):
            t.mWheels[i].mTemperature[1] = temp
        s = _make_scoring()

        channels = ["wheel_fl_temp", "wheel_fr_temp", "wheel_rl_temp", "wheel_rr_temp"]
        ser = FrameSerializer(channels)
        frame = ser.serialize(0.0, t, s)
        result = ser.deserialize(frame)

        for i, name in enumerate(channels):
            assert result[name] == pytest.approx(temps_k[i] - _K2C)

    def test_left_center_right_temps(self):
        """Left/center/right surface temperatures should all convert K→°C."""
        t = _make_telemetry()
        t.mWheels[0].mTemperature[0] = 340.0  # left
        t.mWheels[0].mTemperature[1] = 350.0  # center
        t.mWheels[0].mTemperature[2] = 345.0  # right
        s = _make_scoring()

        ser = FrameSerializer(["wheel_fl_temp_l", "wheel_fl_temp", "wheel_fl_temp_r"])
        frame = ser.serialize(0.0, t, s)
        result = ser.deserialize(frame)

        assert result["wheel_fl_temp_l"] == pytest.approx(340.0 - _K2C)
        assert result["wheel_fl_temp"] == pytest.approx(350.0 - _K2C)
        assert result["wheel_fl_temp_r"] == pytest.approx(345.0 - _K2C)


# ── Mixed-type frame tests ────────────────────────────────────────────


class TestMixedTypes:
    def test_mixed_double_int_bool(self):
        """Frames can mix doubles, ints, and bools."""
        t = _make_telemetry(mEngineRPM=5000.0, mGear=3, mOverheating=True)
        s = _make_scoring(mPlace=5)

        ser = FrameSerializer(["rpm", "gear", "overheating", "place"])
        frame = ser.serialize(1.0, t, s)
        result = ser.deserialize(frame)

        assert result["rpm"] == pytest.approx(5000.0)
        assert result["gear"] == 3
        assert result["overheating"] is True
        assert result["place"] == 5

    def test_negative_gear_reverse(self):
        t = _make_telemetry(mGear=-1)
        s = _make_scoring()

        ser = FrameSerializer(["gear"])
        frame = ser.serialize(0.0, t, s)
        result = ser.deserialize(frame)

        assert result["gear"] == -1


# ── Edge cases ────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_zero_values(self):
        """Default-initialised structs should produce all zeros."""
        t = _make_telemetry()
        s = _make_scoring()

        ser = FrameSerializer(["speed", "rpm", "throttle", "fuel"])
        frame = ser.serialize(0.0, t, s)
        result = ser.deserialize(frame)

        assert result["speed"] == pytest.approx(0.0)
        assert result["rpm"] == pytest.approx(0.0)
        assert result["throttle"] == pytest.approx(0.0)
        assert result["fuel"] == pytest.approx(0.0)

    def test_single_channel(self):
        t = _make_telemetry(mEngineRPM=8000.0)
        s = _make_scoring()

        ser = FrameSerializer(["rpm"])
        frame = ser.serialize(5.0, t, s)
        result = ser.deserialize(frame)

        assert len(result) == 2  # timestamp + rpm
        assert result["timestamp"] == pytest.approx(5.0)
        assert result["rpm"] == pytest.approx(8000.0)

    def test_deserialize_wrong_size_raises(self):
        ser = FrameSerializer(["speed", "rpm"])
        with pytest.raises(struct.error):
            ser.deserialize(b"\x00" * 3)

    def test_channel_defs_property(self):
        ser = FrameSerializer(["speed", "gear"])
        defs = ser.channel_defs
        assert len(defs) == 2
        assert all(isinstance(d, ChannelDef) for d in defs)

    def test_multiple_serializers_independent(self):
        """Different serializers should not interfere with each other."""
        ser1 = FrameSerializer(["speed"])
        ser2 = FrameSerializer(["rpm", "gear"])

        t = _make_telemetry(mEngineRPM=6000.0, mGear=5)
        s = _make_scoring()

        frame1 = ser1.serialize(1.0, t, s)
        frame2 = ser2.serialize(2.0, t, s)

        r1 = ser1.deserialize(frame1)
        r2 = ser2.deserialize(frame2)

        assert "speed" in r1
        assert "speed" not in r2
        assert "rpm" in r2
        assert "rpm" not in r1

    def test_max_channels_roundtrip(self):
        """Serializer with all available channels should round-trip without error."""
        t = _make_telemetry(mEngineRPM=5500.0, mGear=4, mFuel=60.0)
        s = _make_scoring(mPlace=2, mLapDist=1234.5)

        all_names = list(ALL_CHANNELS.keys())
        ser = FrameSerializer(all_names)

        # Frame size should match the struct format
        assert ser.frame_size == struct.calcsize(ser.format_string)
        assert len(ser.channel_names) == len(all_names)

        frame = ser.serialize(99.0, t, s)
        assert len(frame) == ser.frame_size

        result = ser.deserialize(frame)
        assert result["timestamp"] == pytest.approx(99.0)
        assert result["rpm"] == pytest.approx(5500.0)
        assert result["gear"] == 4
        assert result["fuel"] == pytest.approx(60.0)
        assert result["place"] == 2
        assert result["lap_dist"] == pytest.approx(1234.5)

        # Every channel name must be present in result
        for name in all_names:
            assert name in result
