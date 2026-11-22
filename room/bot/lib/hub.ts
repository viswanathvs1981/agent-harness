export type HubDevice = {
  id: string;
  name: string;
  kind: string;
  protocol: string;
  address: string;
  reachable: boolean;
};

export type HubResult = {
  ok: boolean;
  message: string;
  device_id?: string | null;
};

const DEFAULT_HUB = "http://127.0.0.1:8787";

export function hubUrl(): string {
  return process.env.HOME_HUB_URL?.replace(/\/$/, "") || DEFAULT_HUB;
}

export async function hubGet<T>(path: string): Promise<T> {
  const response = await fetch(`${hubUrl()}${path}`);
  if (!response.ok) {
    throw new Error(`Hub ${response.status} on ${path}`);
  }
  return (await response.json()) as T;
}

export async function hubPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${hubUrl()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  const data = (await response.json().catch(() => ({}))) as T & { detail?: string; message?: string };
  if (!response.ok) {
    throw new Error(data.detail || data.message || `Hub ${response.status} on ${path}`);
  }
  return data;
}

export const evalDevices: HubDevice[] = [
  {
    id: "roku-192-168-1-40",
    name: "Living Room Roku",
    kind: "tv",
    protocol: "roku",
    address: "192.168.1.40",
    reachable: true,
  },
];
