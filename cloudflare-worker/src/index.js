export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Health check for the Worker itself
    if (url.pathname === "/gateway-health") {
      return new Response(
        JSON.stringify({
          status: "ok",
          service: "RecoverAI API Gateway",
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      );
    }

    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods":
            "GET,POST,PUT,PATCH,DELETE,OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
      });
    }

    if (!env.BACKEND_URL) {
      return new Response(
        JSON.stringify({
          status: "error",
          message: "BACKEND_URL is not configured",
        }),
        {
          status: 500,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
          },
        },
      );
    }

    // Forward the request to the FastAPI backend
    const backendUrl = `${env.BACKEND_URL}${url.pathname}${url.search}`;

    const headers = new Headers(request.headers);
    headers.delete("host");

    const backendRequest = new Request(backendUrl, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method)
        ? undefined
        : request.body,
      redirect: "follow",
    });

    const response = await fetch(backendRequest);

    // Add CORS headers for the frontend
    const responseHeaders = new Headers(response.headers);
    responseHeaders.set("Access-Control-Allow-Origin", "*");
    responseHeaders.set(
      "Access-Control-Allow-Methods",
      "GET,POST,PUT,PATCH,DELETE,OPTIONS",
    );
    responseHeaders.set(
      "Access-Control-Allow-Headers",
      "Content-Type, Authorization",
    );

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  },
};
