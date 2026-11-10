import { useEffect, useState } from "react";
import { client } from "@/api/client";
import type { components } from "@/api/schema";

export function Health() {
  const [status, setStatus] = useState("Checking API…");
  useEffect(() => {
    const controller = new AbortController();
    client
      .get<unknown>("/api/v1/health", { signal: controller.signal })
      .then(({ data }) => {
        if (
          !data ||
          typeof data !== "object" ||
          !("status" in data) ||
          data.status !== "ok"
        ) {
          throw new Error("Invalid health response");
        }
        const health: components["schemas"]["Health"] = { status: data.status };
        if (!controller.signal.aborted) setStatus(`API: ${health.status}`);
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setStatus(error instanceof Error ? error.message : "API unavailable");
        }
      });
    return () => controller.abort();
  }, []);

  return (
    <>
      <h1>Service health</h1>
      <p role="status">{status}</p>
    </>
  );
}
