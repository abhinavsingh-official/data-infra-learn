"use client";

import { useEffect, useState } from "react";
import { PageHero } from "@/components/shared/page-hero";
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getInterviewQuestions } from "@/lib/api";
import { PHASE_THEME, type PhaseSlug } from "@/lib/phase-theme";
import { cn } from "@/lib/utils";
import type { InterviewQuestionsPage } from "@/lib/types";

// Maps each backend topic label to the phase accent it reads closest to -
// same idea as track-skill-tree-view.tsx's PARADIGM_ACCENT, just kept
// local since this page is the only place these exact labels appear.
const TOPIC_SLUG: Record<string, PhaseSlug> = {
  SQL: "postgres",
  "Data Modeling & Warehousing": "warehouse",
  "NoSQL & Document Databases": "nosql",
  "Data Lake & Lakehouse": "lake",
  "ETL / Pipeline Architecture": "pipeline-architecture",
};

export default function InterviewQuestionsRoute() {
  const [data, setData] = useState<InterviewQuestionsPage | null>(null);
  const [failed, setFailed] = useState(false);
  const [topicIndex, setTopicIndex] = useState(0);

  useEffect(() => {
    getInterviewQuestions()
      .then(setData)
      .catch(() => setFailed(true));
  }, []);

  if (failed) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Backend unreachable</AlertTitle>
        <AlertDescription>
          Could not load interview questions from the API. Make sure the backend is running and
          reachable at the configured API base URL.
        </AlertDescription>
      </Alert>
    );
  }

  if (!data) {
    return <p className="text-sm text-muted-foreground">Loading...</p>;
  }

  const activeTopic = data.topics[topicIndex];
  const slug = TOPIC_SLUG[activeTopic.topic] ?? "postgres";
  const theme = PHASE_THEME[slug];

  return (
    <div className="space-y-8">
      <PageHero
        title="Interview Questions"
        description="Commonly-asked, publicly-known data engineering interview questions, grouped by topic - straight answers, no fluff."
        showBack
        backHref="/learn"
      />

      <div className="flex flex-wrap gap-2">
        {data.topics.map((topic, i) => {
          const isActive = i === topicIndex;
          const t = PHASE_THEME[TOPIC_SLUG[topic.topic] ?? "postgres"];
          return (
            <Button
              key={topic.topic}
              size="sm"
              variant={isActive ? "default" : "outline"}
              onClick={() => setTopicIndex(i)}
              className={cn(!isActive && t.text, isActive && "retro-box")}
            >
              <span className={cn("mr-1.5 size-2 rounded-full", t.bgSolid)} />
              {topic.topic}
            </Button>
          );
        })}
      </div>

      <Card className={cn("border-l-4", theme.border)}>
        <CardContent className="pt-6">
          <Accordion>
            {activeTopic.questions.map((item, i) => (
              <AccordionItem key={i} value={`q-${i}`}>
                <AccordionTrigger className="text-base">{item.q}</AccordionTrigger>
                <AccordionContent className="text-sm leading-relaxed text-muted-foreground">
                  {item.a}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </CardContent>
      </Card>
    </div>
  );
}
