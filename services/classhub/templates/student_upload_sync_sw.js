self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

const broadcastFlushRequest = async () => {
  const allClients = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
  for (const client of allClients) {
    client.postMessage({ type: "classhub-flush-upload-queue" });
  }
};

self.addEventListener("sync", (event) => {
  if (event.tag !== "classhub-upload-queue") return;
  event.waitUntil(broadcastFlushRequest());
});

self.addEventListener("message", (event) => {
  const payload = event.data || {};
  if (payload.type === "classhub-request-sync") {
    event.waitUntil(broadcastFlushRequest());
  }
});
