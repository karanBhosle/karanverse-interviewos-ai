from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

ALGORITHM_VERSION = "opencv-haar-v1"
DISALLOWED_LABELS = {
    "nervous",
    "anxiety",
    "dishonest",
    "honesty",
    "confidence",
    "emotion",
    "personality",
    "engagement",
}


def _load_cv2():
    import cv2

    return cv2


def _load_cascade():
    cv2 = _load_cv2()
    classifier = getattr(cv2, "CascadeClassifier", None)
    data = getattr(cv2, "data", None)
    if classifier is None or data is None:
        return None
    return classifier(data.haarcascades + "haarcascade_frontalface_default.xml")


CASCADE = _load_cascade()


@dataclass
class FrameObservation:
    timestamp_s: float
    face_count: int
    face_confidence: float
    face_box: tuple[int, int, int, int] | None
    brightness: float
    blur: float
    usable: bool
    quality_flags: list[str] = field(default_factory=list)
    yaw_proxy: float | None = None
    gaze_proxy: float | None = None


def _brightness(gray: np.ndarray) -> float:
    return float(np.mean(gray))


def _blur(gray: np.ndarray) -> float:
    cv2 = _load_cv2()
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def analyze_frame(image: np.ndarray, timestamp_s: float, max_width: int = 640) -> FrameObservation:
    cv2 = _load_cv2()
    if image is None or image.size == 0:
        return FrameObservation(timestamp_s, 0, 0.0, None, 0.0, 0.0, False, ["empty_frame"])
    if image.ndim == 2:
        bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        bgr = image
    height, width = bgr.shape[:2]
    if width > max_width:
        scale = max_width / width
        bgr = cv2.resize(bgr, (max_width, int(height * scale)))
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    brightness = _brightness(gray)
    blur = _blur(gray)
    flags: list[str] = []
    if brightness < 40:
        flags.append("too_dark")
    if brightness > 220:
        flags.append("too_bright")
    if blur < 20:
        flags.append("too_blurry")
    faces = []
    if CASCADE is not None:
        faces = CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
    elif not flags:
        flags.append("detector_unavailable")
    face_count = 0 if faces is None else len(faces)
    if face_count > 1:
        flags.append("multiple_faces")
    usable = not bool({"too_dark", "too_blurry", "empty_frame", "detector_unavailable"} & set(flags))
    box = None
    confidence = 0.0
    yaw_proxy = None
    gaze_proxy = None
    if face_count == 1:
        x, y, w, h = (int(v) for v in faces[0])
        box = (x, y, w, h)
        frame_w = gray.shape[1]
        center_offset = ((x + w / 2) - (frame_w / 2)) / (frame_w / 2)
        yaw_proxy = float(center_offset)
        gaze_proxy = float(center_offset)
        confidence = min(1.0, w / max(frame_w * 0.25, 1))
        if w < 50:
            flags.append("face_too_small")
            usable = False
    elif face_count == 0:
        flags.append("no_face")
    return FrameObservation(
        timestamp_s=timestamp_s,
        face_count=face_count,
        face_confidence=confidence,
        face_box=box,
        brightness=brightness,
        blur=blur,
        usable=usable and face_count == 1,
        quality_flags=flags,
        yaw_proxy=yaw_proxy,
        gaze_proxy=gaze_proxy,
    )


def aggregate_observations(observations: list[FrameObservation]) -> dict[str, Any]:
    if not observations:
        return {
            "processing_status": "insufficient_data",
            "usable_frames": 0,
            "features": [],
            "feedback": ["No frames were available for visual analysis."],
            "algorithm_version": ALGORITHM_VERSION,
        }
    usable = [obs for obs in observations if obs.usable]
    total = len(observations)
    face_visible = sum(1 for obs in observations if obs.face_count == 1) / total
    out_of_frame = sum(1 for obs in observations if obs.face_count == 0) / total
    multi = sum(1 for obs in observations if obs.face_count > 1) / total
    dark = sum(1 for obs in observations if "too_dark" in obs.quality_flags) / total
    blurry = sum(1 for obs in observations if "too_blurry" in obs.quality_flags) / total
    yaw_values = [obs.yaw_proxy for obs in usable if obs.yaw_proxy is not None]
    movement = float(np.std(yaw_values)) if len(yaw_values) >= 2 else None
    away = (
        sum(1 for value in yaw_values if abs(value) > 0.35) / len(yaw_values) if yaw_values else None
    )
    status = "ok" if usable else "insufficient_data"
    features = [
        _feature("face_visibility", face_visible, total, status),
        _feature("out_of_frame_fraction", out_of_frame, total, status),
        _feature("multiple_faces_fraction", multi, total, status),
        _feature("dark_frame_fraction", dark, total, "quality"),
        _feature("blurry_frame_fraction", blurry, total, "quality"),
        _feature("head_orientation_variation", movement, len(usable), status if movement is not None else "unavailable"),
        _feature("head_facing_away_fraction", away, len(usable), status if away is not None else "unavailable"),
        _feature("mean_brightness", float(np.mean([obs.brightness for obs in observations])), total, "quality"),
    ]
    feedback = _feedback(features, status)
    return {
        "processing_status": status,
        "usable_frames": len(usable),
        "sampled_frames": total,
        "algorithm_version": ALGORITHM_VERSION,
        "features": features,
        "feedback": feedback,
        "limitations": [
            "Head-orientation and gaze values are geometric proxies from a face bounding box, not validated attention or honesty measures.",
            "Low-quality or missing frames are not treated as negative behavior.",
            "Visual observations are separate from technical answer scores.",
        ],
    }


def _feature(feature_type: str, value: float | None, usable_frames: int, status: str) -> dict[str, Any]:
    return {
        "feature_type": feature_type,
        "value": None if value is None else round(float(value), 4),
        "usable_frames": usable_frames,
        "algorithm_version": ALGORITHM_VERSION,
        "processing_status": status if value is not None else "unavailable",
    }


def _feedback(features: list[dict[str, Any]], status: str) -> list[str]:
    by_type = {item["feature_type"]: item["value"] for item in features}
    messages: list[str] = []
    if status == "insufficient_data":
        messages.append("There were not enough usable frames for reliable visual analysis.")
        return messages
    if (by_type.get("out_of_frame_fraction") or 0) > 0.25:
        messages.append("Your face was outside the frame during several portions of this answer.")
    if (by_type.get("head_orientation_variation") or 0) > 0.2:
        messages.append("Head orientation varied considerably during this response.")
    if (by_type.get("dark_frame_fraction") or 0) > 0.3:
        messages.append("The recording was too dark for reliable analysis during parts of this answer.")
    if (by_type.get("head_facing_away_fraction") or 0) > 0.3:
        messages.append("Your gaze estimate frequently shifted away from the camera.")
    if (by_type.get("multiple_faces_fraction") or 0) > 0.1:
        messages.append("More than one face was detected in some frames, so those frames were not treated as a stable self-view.")
    if not messages:
        messages.append("Face visibility was stable enough for descriptive presentation metrics.")
    return messages


def presentation_checklist(features: list[dict[str, Any]], enabled: bool) -> dict[str, Any] | None:
    if not enabled:
        return None
    by_type = {item["feature_type"]: item for item in features}
    visibility_row = by_type.get("face_visibility")
    if visibility_row and visibility_row.get("processing_status") in {"insufficient_data", "unavailable"}:
        return {
            "enabled": True,
            "available": False,
            "score": None,
            "explanation": "Checklist score withheld because visual data were insufficient. This is not a poor score.",
        }
    visibility = (visibility_row or {}).get("value") or 0
    quality_penalty = (by_type.get("dark_frame_fraction", {}).get("value") or 0) + (
        by_type.get("blurry_frame_fraction", {}).get("value") or 0
    )
    score = max(0.0, min(100.0, visibility * 100 - quality_penalty * 20))
    return {
        "enabled": True,
        "available": True,
        "score": round(score, 1),
        "explanation": (
            "Optional presentation checklist from face visibility and recording quality only. "
            "It is not a technical score and does not measure confidence or honesty."
        ),
        "components": {
            "face_visibility": visibility,
            "recording_quality_penalty": quality_penalty,
        },
    }


def validate_no_affective_language(text: str) -> None:
    lowered = text.lower()
    for label in DISALLOWED_LABELS:
        if label in lowered:
            raise ValueError(f"Disallowed affective label in visual feedback: {label}")
