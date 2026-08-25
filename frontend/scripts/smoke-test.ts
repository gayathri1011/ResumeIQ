import { checkHealth } from "../services/health.service";

async function main(): Promise<void> {
  console.log("Running ResumeIQ frontend → backend smoke test...");
  const health = await checkHealth();
  console.log("Health check response:", health);

  if (health.status !== "ok") {
    throw new Error(`Unexpected health status: ${health.status}`);
  }

  console.log("Smoke test passed.");
}

main().catch((error: unknown) => {
  console.error("Smoke test failed:", error);
  process.exit(1);
});
