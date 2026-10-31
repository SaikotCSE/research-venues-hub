import { ApiError, api, setCsrfToken, toQuery } from "./api";

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("api client", () => {
  afterEach(() => vi.restoreAllMocks());

  it("serialises query params, skipping empty values and repeating arrays", () => {
    expect(toQuery({ q: "vision", core: ["A*", "A"], oa: true, empty: "", none: null, off: false })).toBe("q=vision&core=A*&core=A&oa=1");
  });

  it("sends JSON with the CSRF token on writes", async () => {
    setCsrfToken("tok-1");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, { starred: true }));
    await expect(api.post("/venues/cvpr/star/", { starred: true })).resolves.toEqual({ starred: true });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/app/venues/cvpr/star/");
    expect(init?.method).toBe("POST");
    expect((init?.headers as Record<string, string>)["X-CSRFToken"]).toBe("tok-1");
    expect(init?.body).toBe('{"starred":true}');
  });

  it("raises ApiError with field errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(400, { error: "Please correct the highlighted fields.", fields: { email: ["Taken."] } }));
    const error = (await api.post("/auth/signup/", {}).catch((e: unknown) => e)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(400);
    expect(error.fields).toEqual({ email: ["Taken."] });
  });

  it("refreshes the CSRF token once and retries", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(403, { error: "CSRF verification failed. Refresh the page and try again." }))
      .mockResolvedValueOnce(jsonResponse(200, { csrf_token: "fresh" }))
      .mockResolvedValueOnce(jsonResponse(200, { ok: true }));
    await expect(api.post("/me/email/", { email: "a@b.c" })).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect((fetchMock.mock.calls[2][1]?.headers as Record<string, string>)["X-CSRFToken"]).toBe("fresh");
  });

  it("reports network failures as offline", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(api.get("/session/")).rejects.toMatchObject({ status: 0 });
  });
});
