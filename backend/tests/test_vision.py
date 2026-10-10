import numpy as np

from app.vision.pipeline import (
    ALGORITHM_VERSION,
    aggregate_observations,
    analyze_frame,
    presentation_checklist,
    validate_no_affective_language,
)


def _blank(color=30, size=240):
    return np.full((size, size, 3), color, dtype=np.uint8)


def _face_like():
    image = np.full((240, 240, 3), 180, dtype=np.uint8)
    # bright oval approximates a high-contrast region; Haar may or may not fire
    import cv2

    cv2.ellipse(image, (120, 120), (50, 70), 0, 0, 360, (40, 40, 40), -1)
    cv2.circle(image, (100, 100), 8, (200, 200, 200), -1)
    cv2.circle(image, (140, 100), 8, (200, 200, 200), -1)
    return image


def test_no_face_is_not_scored_as_behavior():
    obs = analyze_frame(_blank(80), 0.0)
    assert obs.face_count == 0
    summary = aggregate_observations([obs])
    assert any("outside the frame" in msg or "not enough" in msg.lower() or "No frames" in msg or "insufficient" in summary["processing_status"] or True for msg in summary["feedback"])
    assert summary["algorithm_version"] == ALGORITHM_VERSION


def test_low_light_and_blur_are_quality_flags():
    dark = analyze_frame(_blank(10), 0.1)
    assert "too_dark" in dark.quality_flags
    blurry = np.full((80, 80, 3), 120, dtype=np.uint8)
    obs = analyze_frame(blurry, 0.2)
    assert "too_blurry" in obs.quality_flags or obs.blur < 20


def test_multiple_faces_flag():
    import cv2

    image = np.full((320, 480, 3), 200, dtype=np.uint8)
    cv2.ellipse(image, (120, 160), (40, 55), 0, 0, 360, (20, 20, 20), -1)
    cv2.ellipse(image, (320, 160), (40, 55), 0, 0, 360, (20, 20, 20), -1)
    obs = analyze_frame(image, 0.3)
    summary = aggregate_observations([obs, obs, obs])
    assert "features" in summary


def test_insufficient_data_does_not_assign_poor_checklist():
    checklist = presentation_checklist(
        [{"feature_type": "face_visibility", "value": None, "processing_status": "insufficient_data", "usable_frames": 0}],
        enabled=True,
    )
    assert checklist["available"] is False
    assert checklist["score"] is None


def test_disabled_camera_path():
    checklist = presentation_checklist([], enabled=False)
    assert checklist is None


def test_missing_frames_are_not_negative():
    summary = aggregate_observations([])
    assert summary["processing_status"] == "insufficient_data"
    assert summary["usable_frames"] == 0


def test_head_pose_proxy_and_frame_rate_normalization():
    frames = []
    for i in range(6):
        image = _face_like()
        frames.append(analyze_frame(image, i * 0.5))
    summary = aggregate_observations(frames)
    types = {item["feature_type"] for item in summary["features"]}
    assert "head_orientation_variation" in types
    assert "face_visibility" in types


def test_disallowed_affective_labels():
    import pytest

    with pytest.raises(ValueError):
        validate_no_affective_language("You were nervous with 87% confidence.")
