import { defineTool } from "@grok/agent-sdk/tools";
import * as z from "zod/v4";

import { evalDevices, hubGet } from "../lib/hub";

type ListResult = { devices: typeof evalDevices; source: string };

export default defineTool({
  description: "List devices the local Room hub already knows about. Use after a scan, or to see the current roster.",
  execution: "server",
  effect: "read",
  inputSchema: z.object({}),
  async execute(_input, ctx): Promise<ListResult> {
    if (ctx.session.purpose === "eval") {
      return { devices: evalDevices, source: "eval" };
    }
    const data = await hubGet<{ devices: typeof evalDevices }>("/api/devices");
    return { devices: data.devices ?? [], source: "hub" };
  },
});
