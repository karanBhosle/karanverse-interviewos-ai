"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { api } from "@/lib/api/client";
import { useMe } from "@/lib/api/hooks";

export default function SettingsPage() {
  const me = useMe();
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (me.error) setMessage(me.error instanceof Error ? me.error.message : "Could not load privacy settings.");
  }, [me.error]);

  async function update(field: string, value: boolean) {
    await api.patch("/api/v1/auth/me/privacy", { [field]: value });
    await me.refetch();
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Privacy settings</h1>
          <p className="text-sm text-muted-foreground">
            Control retention, camera consent, optional media storage, and account deletion.
          </p>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Data controls</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Toggle
              label="Keep resume files"
              checked={Boolean(me.data?.resume_retention_enabled)}
              onChange={(value) => update("resume_retention_enabled", value)}
            />
            <Toggle
              label="Keep session history"
              checked={Boolean(me.data?.session_history_enabled)}
              onChange={(value) => update("session_history_enabled", value)}
            />
            <Toggle
              label="Camera consent for future sessions"
              checked={Boolean(me.data?.camera_consent)}
              onChange={(value) => update("camera_consent", value)}
            />
            <Toggle
              label="Allow optional raw media storage (off by default)"
              checked={Boolean(me.data?.media_storage_consent)}
              onChange={(value) => update("media_storage_consent", value)}
            />
            <Toggle
              label="Enable optional presentation checklist score"
              checked={Boolean(me.data?.visual_checklist_enabled)}
              onChange={(value) => update("visual_checklist_enabled", value)}
            />
            <Toggle
              label="Consent to server-side visual analysis if separately enabled"
              checked={Boolean(me.data?.visual_analysis_opt_in)}
              onChange={(value) => update("visual_analysis_opt_in", value)}
            />
          </CardContent>
        </Card>
        <Alert>
          <AlertTitle>Data leaving the browser</AlertTitle>
          <AlertDescription>
            Resume text, job descriptions, and answers are stored in the InterviewOS API. If an LLM API key is
            configured on the server, those texts may be sent to that provider. Review the provider privacy terms. Webcam
            frames are not uploaded unless you consent to server-side analysis. API keys never enter the browser.
          </AlertDescription>
        </Alert>
        <Button
          variant="destructive"
          onClick={async () => {
            await api.delete("/api/v1/users/me/data");
            setMessage("Resumes, sessions, media, and derived indexes were deleted.");
          }}
        >
          Delete my resumes, sessions, and optional media
        </Button>
        {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
      </div>
    </AppShell>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-4 text-sm">
      <span>{label}</span>
      <Switch checked={checked} onCheckedChange={onChange} />
    </label>
  );
}
