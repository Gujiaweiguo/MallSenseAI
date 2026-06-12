"""ROI type definitions — scene types, zone purposes, and metadata."""

from __future__ import annotations

import enum
from typing import Literal, TypedDict


class SceneType(str, enum.Enum):
    """Physical scene / location type for a camera's field of view."""

    corridor = "corridor"
    entrance = "entrance"
    stairwell = "stairwell"
    elevator = "elevator"
    parking = "parking"
    plaza = "plaza"
    other = "other"


class ZonePurpose(str, enum.Enum):
    """Functional purpose of a zone within a scene."""

    passable = "passable"          # area that must remain clear for passage
    forbidden = "forbidden"        # area where objects must never appear
    monitoring = "monitoring"      # general observation zone
    buffer = "buffer"              # transition zone between regions


class ROIMetadata(TypedDict, total=False):
    """Metadata describing an ROI's role in a scene.

    All fields are optional — consumers should use ``.get()`` or
    ``dict.get()`` to handle missing keys gracefully.
    """

    scene_type: SceneType
    zone_purpose: ZonePurpose
    description: str
    direction: Literal["horizontal", "vertical", "omnidirectional"]
