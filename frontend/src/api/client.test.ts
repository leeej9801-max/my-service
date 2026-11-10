import { AxiosError, AxiosHeaders } from "axios";
import { expect, test, vi } from "vitest";
import { client } from "@/api/client";

test.each([
  ["error", "network_error", "Network error"],
  ["timeout", "timeout", "Request timed out"],
])("normalizes XHR %s failures", async (event, code, title) => {
  vi.spyOn(XMLHttpRequest.prototype, "send").mockImplementation(function (
    this: XMLHttpRequest,
  ) {
    this.dispatchEvent(new ProgressEvent(event));
  });
  await expect(client.get("/api/v1/health")).rejects.toMatchObject({
    type: "about:blank",
    status: 0,
    code,
    title,
    detail: event === "error" ? "Network Error" : "timeout of 10000ms exceeded",
  });
  expect(client.defaults.timeout).toBe(10_000);
});

test("normalizes an in-flight AbortController cancellation", async () => {
  const send = vi
    .spyOn(XMLHttpRequest.prototype, "send")
    .mockImplementation(() => undefined);
  const controller = new AbortController();
  const request = client.get("/api/v1/health", { signal: controller.signal });
  expect(send).toHaveBeenCalledOnce();
  controller.abort();
  await expect(request).rejects.toMatchObject({
    type: "about:blank",
    status: 0,
    code: "canceled",
    title: "Request canceled",
    detail: "canceled",
  });
});

test.each([
  [
    502,
    "<html>Bad Gateway</html>",
    { code: "http_error", detail: "Request failed" },
  ],
  [
    422,
    {
      type: "about:blank",
      title: "Unprocessable Content",
      detail: "Request validation failed.",
      instance: "/api/v1/items",
      code: "validation_error",
      errors: [{ loc: ["body", "name"], type: "missing" }],
    },
    {
      title: "Unprocessable Content",
      detail: "Request validation failed.",
      instance: "/api/v1/items",
      code: "validation_error",
      errors: [{ loc: ["body", "name"], type: "missing" }],
    },
  ],
])(
  "normalizes HTTP %s without exposing HTML or losing Problem fields",
  async (status, data, expected) => {
    await expect(
      client.get("/api/v1/items", {
        adapter: (config) =>
          Promise.reject(
            new AxiosError(
              "HTTP failure",
              "ERR_BAD_RESPONSE",
              config,
              undefined,
              {
                config,
                status,
                statusText: "Error",
                headers: new AxiosHeaders({ "x-request-id": "request-123" }),
                data,
              },
            ),
          ),
      }),
    ).rejects.toMatchObject({
      type: "about:blank",
      status,
      request_id: "request-123",
      ...expected,
    });
  },
);
