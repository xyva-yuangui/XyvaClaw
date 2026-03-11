import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { emptyPluginConfigSchema } from "openclaw/plugin-sdk";
import { registerFeishuBitableTools } from "./src/bitable.js";
import { feishuPlugin } from "./src/channel.js";
import { registerFeishuDocTools } from "./src/docx.js";
import { registerFeishuDriveTools } from "./src/drive.js";
import { registerFeishuPermTools } from "./src/perm.js";
import { setFeishuRuntime } from "./src/runtime.js";
import { registerFeishuImageTool } from "./src/image-tool.js";
import { registerFeishuCalendarTools } from "./src/calendar.js";
import { registerFeishuApprovalTools } from "./src/approval.js";
import { registerFeishuSearchTools } from "./src/search.js";
import { registerFeishuGroupTools } from "./src/group.js";
import { registerFeishuTaskTools } from "./src/task.js";
import { registerFeishuForwardTools } from "./src/forward.js";
import { registerFeishuWebhookTools } from "./src/webhook.js";
import { registerFeishuVcTools } from "./src/vc.js";
import { registerFeishuAttendanceTools } from "./src/attendance.js";
import { registerFeishuAppTools } from "./src/app.js";
import { registerFeishuWikiTools } from "./src/wiki.js";

export { monitorFeishuProvider } from "./src/monitor.js";
export {
  sendMessageFeishu,
  sendCardFeishu,
  updateCardFeishu,
  editMessageFeishu,
  getMessageFeishu,
} from "./src/send.js";
export {
  uploadImageFeishu,
  uploadFileFeishu,
  sendImageFeishu,
  sendFileFeishu,
  sendMediaFeishu,
} from "./src/media.js";
export { probeFeishu } from "./src/probe.js";
export {
  addReactionFeishu,
  removeReactionFeishu,
  listReactionsFeishu,
  FeishuEmoji,
} from "./src/reactions.js";
export {
  extractMentionTargets,
  extractMessageBody,
  isMentionForwardRequest,
  formatMentionForText,
  formatMentionForCard,
  formatMentionAllForText,
  formatMentionAllForCard,
  buildMentionedMessage,
  buildMentionedCardContent,
  type MentionTarget,
} from "./src/mention.js";
export { feishuPlugin } from "./src/channel.js";

const plugin = {
  id: "feishu_local",
  name: "Feishu",
  description: "Feishu/Lark channel plugin",
  configSchema: emptyPluginConfigSchema(),
  register(api: OpenClawPluginApi) {
    setFeishuRuntime(api.runtime);
    api.registerChannel({ plugin: feishuPlugin });
    registerFeishuDocTools(api);
    registerFeishuWikiTools(api);
    registerFeishuDriveTools(api);
    registerFeishuPermTools(api);
    registerFeishuBitableTools(api);
    registerFeishuImageTool(api);
    registerFeishuCalendarTools(api);
    registerFeishuApprovalTools(api);
    registerFeishuSearchTools(api);
    registerFeishuGroupTools(api);
    registerFeishuTaskTools(api);
    registerFeishuForwardTools(api);
    registerFeishuWebhookTools(api);
    registerFeishuVcTools(api);
    registerFeishuAttendanceTools(api);
    registerFeishuAppTools(api);
  },
};

export default plugin;
