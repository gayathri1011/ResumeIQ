import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { JobAnalysisResult } from "@/types/job";

interface JobExtractionResultsProps {
  result: JobAnalysisResult;
}

function TagList({ items, emptyLabel }: { items: string[]; emptyLabel: string }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyLabel}</p>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <Badge key={item} variant="secondary">
          {item}
        </Badge>
      ))}
    </div>
  );
}

function BulletList({ items, emptyLabel }: { items: string[]; emptyLabel: string }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyLabel}</p>;
  }
  return (
    <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export function JobExtractionResults({ result }: JobExtractionResultsProps) {
  const experience = result.experience_requirements;

  return (
    <div className="space-y-4">
      {result.cached ? (
        <Alert variant="info">
          This job description was analyzed before — showing stored extraction (no new AI call).
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{result.job_title ?? "Untitled role"}</CardTitle>
          {result.company && (
            <CardDescription>{result.company}</CardDescription>
          )}
        </CardHeader>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Required skills</CardTitle>
          </CardHeader>
          <CardContent>
            <TagList items={result.required_skills} emptyLabel="None extracted" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Preferred skills</CardTitle>
          </CardHeader>
          <CardContent>
            <TagList items={result.preferred_skills} emptyLabel="None extracted" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Experience</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            {!experience ? (
              <p>Not specified in the posting</p>
            ) : (
              <>
                {(experience.years_min !== null || experience.years_max !== null) && (
                  <p>
                    Years:{" "}
                    {experience.years_min ?? "?"}–{experience.years_max ?? "+"}
                  </p>
                )}
                {experience.seniority_level && (
                  <p>Level: {experience.seniority_level}</p>
                )}
                {experience.description && <p>{experience.description}</p>}
                {!experience.years_min &&
                  !experience.years_max &&
                  !experience.seniority_level &&
                  !experience.description && <p>Not specified in the posting</p>}
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Education</CardTitle>
          </CardHeader>
          <CardContent>
            <BulletList
              items={result.education_requirements}
              emptyLabel="Not specified in the posting"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tools</CardTitle>
          </CardHeader>
          <CardContent>
            <TagList items={result.tools} emptyLabel="None extracted" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Technologies</CardTitle>
          </CardHeader>
          <CardContent>
            <TagList items={result.technologies} emptyLabel="None extracted" />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Responsibilities</CardTitle>
        </CardHeader>
        <CardContent>
          <BulletList
            items={result.responsibilities}
            emptyLabel="None extracted"
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Keywords</CardTitle>
          <CardDescription>
            Important terms for later matching and gap analysis
          </CardDescription>
        </CardHeader>
        <CardContent>
          <TagList items={result.keywords} emptyLabel="None extracted" />
        </CardContent>
      </Card>
    </div>
  );
}
