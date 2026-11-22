import { defineEval } from "@grok/agent-sdk/evals";

export default defineEval({
  tags: ["smoke"],
  description: "Mute the living room TV by scanning then sending a command.",
  async test(t) {
    await t.send("Mute the living room TV.");
    t.succeeded();
    t.calledTool("send_command");
    t.notCalledTool("echo");
  },
});
