import { defineTool } from "@grok/agent-sdk/tools";
import * as z from "zod/v4";

import { hubPost, type HubResult } from "../lib/hub";

export default defineTool({
  description:
    "Send a remote command to one device id from list_devices or discover_devices. Actions: power_on, power_off, power_toggle, volume_up, volume_down, volume_set, mute, home, back, up, down, left, right, select, play, pause, launch, input.",
  execution: "server",
  effect: "write",
  inputSchema: z.object({
    device_id: z.string(),
    action: z.string(),
    value: z.union([z.string(), z.number()]).optional(),
  }),
  dryRunResult: ({ device_id, action, value }) => ({
    ok: false,
    message: `Dry run: would send ${action} to ${device_id}`,
    device_id,
    value: value ?? null,
  }),
  async execute({ device_id, action, value }, ctx): Promise<HubResult> {
    if (ctx.session.purpose === "eval") {
      return {
        ok: true,
        message: `Eval: ${action} on ${device_id}`,
        device_id,
      };
    }
    return hubPost<HubResult>(`/api/devices/${encodeURIComponent(device_id)}/command`, {
      action,
      value: value ?? null,
    });
  },
});
