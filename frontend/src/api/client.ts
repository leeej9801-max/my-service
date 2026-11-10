import axios from "axios";

export const client = axios.create({
  timeout: 10_000,
});

client.interceptors.response.use(undefined, (error: unknown) => {
  const response = axios.isAxiosError<unknown>(error)
    ? error.response
    : undefined;
  const code = axios.isCancel(error)
    ? "canceled"
    : axios.isAxiosError(error) &&
        (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT")
      ? "timeout"
      : response
        ? "http_error"
        : "network_error";
  const fallback = {
    canceled: "Request canceled",
    timeout: "Request timed out",
    http_error: "Request failed",
    network_error: "Network error",
  }[code];
  const data: unknown = response?.data;
  const body = data && typeof data === "object" ? data : {};
  const status = response?.status ?? 0;
  const title =
    "title" in body && typeof body.title === "string" ? body.title : fallback;
  const detail =
    "detail" in body && typeof body.detail === "string"
      ? body.detail
      : !response && error instanceof Error
        ? error.message
        : title;
  const header: unknown = response?.headers["x-request-id"];
  const problem = Object.assign(new Error(detail), {
    type:
      "type" in body && typeof body.type === "string"
        ? body.type
        : "about:blank",
    title,
    status,
    detail,
    code: "code" in body && typeof body.code === "string" ? body.code : code,
    ...("instance" in body && typeof body.instance === "string"
      ? { instance: body.instance }
      : {}),
    ...("errors" in body && Array.isArray(body.errors)
      ? { errors: body.errors }
      : {}),
    ...("request_id" in body && typeof body.request_id === "string"
      ? { request_id: body.request_id }
      : typeof header === "string"
        ? { request_id: header }
        : {}),
  });
  // 401 hook: handle problem.status === 401 here when authentication is added.
  return Promise.reject(problem);
});
