"use client";

import { AppShell } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import { usePlans } from "@/lib/api/hooks";

export default function LearningPlanPage() {
  const plans = usePlans();
  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Learning roadmap</h1>
          <p className="text-sm text-muted-foreground">
            Only verified URLs are linked. Everything else is a search suggestion, not an invented citation.
          </p>
        </div>
        {plans.data?.map((plan) => (
          <Card key={plan.id}>
            <CardHeader>
              <CardTitle className="flex items-center justify-between text-base">
                <span>{plan.summary}</span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => api.post(`/api/v1/learning-plans/${plan.id}/reassess`).then(() => plans.refetch())}
                >
                  Mark reassessed
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {plan.tasks.map((task) => (
                <div key={task.id} className="rounded-md border border-border p-4 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <strong>{task.skill}</strong>
                    <Badge>{task.priority}</Badge>
                    <Badge variant="secondary">{task.status}</Badge>
                  </div>
                  <p className="mt-2 text-muted-foreground">{task.why_it_matters}</p>
                  {task.recommended_reading ? (
                    <a className="mt-2 block underline" href={task.recommended_reading} target="_blank" rel="noreferrer">
                      {task.recommended_reading}
                    </a>
                  ) : (
                    <p className="mt-2">Search suggestion: {task.search_suggestion}</p>
                  )}
                  <p className="mt-2">Practice: {task.practice_question}</p>
                  {task.coding_exercise ? <p>Exercise: {task.coding_exercise}</p> : null}
                  <p className="text-muted-foreground">Reassess when: {task.reassessment_criteria}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
        {!plans.data?.length ? (
          <p className="text-sm text-muted-foreground">A plan is generated when you complete a session.</p>
        ) : null}
      </div>
    </AppShell>
  );
}
