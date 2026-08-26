"use client";

import { useEffect, useState } from "react";

import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { loadTargetRole, saveTargetRole } from "@/features/dashboard/utils";

interface TargetRoleFieldProps {
  resumeId: string;
}

export function TargetRoleField({ resumeId }: TargetRoleFieldProps) {
  const [role, setRole] = useState("");

  useEffect(() => {
    setRole(loadTargetRole(resumeId));
  }, [resumeId]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Target role</CardTitle>
        <CardDescription>
          Saved locally — used when improving bullets for a target role
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Input
          placeholder="e.g. Senior Software Engineer"
          value={role}
          onChange={(event) => {
            const value = event.target.value;
            setRole(value);
            saveTargetRole(resumeId, value);
          }}
        />
      </CardContent>
    </Card>
  );
}
