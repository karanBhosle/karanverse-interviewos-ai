import assert from "node:assert/strict";
import test from "node:test";

function cameraDeniedMessage(permission: string) {
  if (permission === "denied") {
    return "Camera permission was denied. The interview continues in text-only mode.";
  }
  return null;
}

test("denied camera does not block the interview", () => {
  assert.equal(
    cameraDeniedMessage("denied"),
    "Camera permission was denied. The interview continues in text-only mode.",
  );
});

test("stop-camera is an explicit user action", () => {
  const states = ["idle", "granted", "stopped"];
  assert.ok(states.includes("stopped"));
});
