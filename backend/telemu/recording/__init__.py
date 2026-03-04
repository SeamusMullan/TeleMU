"""Recording subsystem — binary serialisation and .tmu file format."""

from telemu.recording.channels import ALL_CHANNELS, DEFAULT_CHANNELS
from telemu.recording.channels import ChannelDef as SerializerChannelDef
from telemu.recording.serializer import FrameSerializer
from telemu.recording.tmu_format import (
    CHANNEL_DEF_SIZE,
    FOOTER_SIZE,
    FORMAT_VERSION,
    HEADER_FIXED_SIZE,
    MAGIC,
    ChannelDef,
    ChannelType,
    TMUCorruptionError,
    TMUFooter,
    TMUHeader,
    VerifyResult,
    build_minimal_tmu,
    compute_channel_offsets,
    frame_payload_size,
    pack_frame,
    repair_file,
    repair_tmu,
    unpack_frame,
    verify_file,
    verify_tmu,
)

__all__ = [
    "ALL_CHANNELS",
    "CHANNEL_DEF_SIZE",
    "ChannelDef",
    "ChannelType",
    "DEFAULT_CHANNELS",
    "FOOTER_SIZE",
    "FORMAT_VERSION",
    "FrameSerializer",
    "HEADER_FIXED_SIZE",
    "MAGIC",
    "SerializerChannelDef",
    "TMUCorruptionError",
    "TMUFooter",
    "TMUHeader",
    "VerifyResult",
    "build_minimal_tmu",
    "compute_channel_offsets",
    "frame_payload_size",
    "pack_frame",
    "repair_file",
    "repair_tmu",
    "unpack_frame",
    "verify_file",
    "verify_tmu",
]
