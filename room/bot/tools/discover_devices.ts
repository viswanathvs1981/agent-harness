import { defineTool } from "@grok/agent-sdk/tools";
import * as z from "zod/v4";

import { evalDevices, hubPost } from "../lib/hub";

type DiscoverResult = { devices: typeof evalDevices; deep: boolean; source: string };

export default defineTool({
  description:
    "Scan the local Wi-Fi via the Room hub (mDNS + SSDP). Set deep=true to also probe common ports on the /24. Only works when the hub runs on the same LAN as the TV.",
  execution: "server",
  effect: "idempotent",
  inputSchema: z.object({
    deep: z.boolean().optional(),
  }),
  async execute({ deep }, ctx): Promise<DiscoverResult> {
    if (ctx.session.purpose === "eval") {
      return { devices: evalDevices, deep: Boolean(deep), source: "eval" };
    }
    const data = await hubPost<{ devices: typeof evalDevices; deep: boolean }>("/api/scan", {
      deep: Boolean(deep),
    });
    return { devices: data.devices ?? [], deep: Boolean(data.deep), source: "hub" };
  },
});
