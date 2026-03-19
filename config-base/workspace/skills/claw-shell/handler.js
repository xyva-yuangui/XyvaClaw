const { execSync } = require("node:child_process");

function ensureSession() {
  try {
    execSync('tmux has-session -t claw', { stdio: "ignore" });
  } catch {
    execSync('tmux new -s claw -d');
  }
}

function sendCommand(cmd) {
  const escaped = cmd.replace(/"/g, '\\"');
  execSync(`tmux send-keys -t claw "${escaped}" C-m`);
}

function readOutput() {
  try {
    const buf = execSync('tmux capture-pane -t claw -p -S -200');
    return buf.toString("utf8");
  } catch (e) {
    return `ERROR READING TMUX OUTPUT: ${e.message}`;
  }
}

function isDangerous(cmd) {
  const lower = ` ${cmd.toLowerCase()} `;
  const bad = ["sudo", " rm ", " rm-", "reboot", "shutdown", "mkfs", "dd ",
    "chmod 777", "> /dev/", "curl|bash", "curl | bash", "wget|bash", "wget | bash",
    ":(){ ", "fork bomb", " --force-delete", "format ", "deltree"];
  if (bad.some(k => lower.includes(k))) return true;
  if (/>\s*\/dev\/sd[a-z]/.test(cmd)) return true;
  if (/rm\s+(-[rf]+\s+)*(\/|~\/?\s*$)/.test(cmd)) return true;
  return false;
}

async function waitForStableOutput(maxWaitMs = 5000, intervalMs = 200) {
  let prevOutput = "";
  let stableCount = 0;
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    await new Promise(r => setTimeout(r, intervalMs));
    const output = readOutput();
    if (output === prevOutput) {
      stableCount++;
      if (stableCount >= 2) break;
    } else {
      stableCount = 0;
      prevOutput = output;
    }
  }
  return readOutput();
}

// MAIN ENTRYPOINT
// OpenClaw will call this function when using the skill tool
async function claw_shell_run(input) {
  const { command } = input;
  if (!command || typeof command !== "string") {
    return { error: "command is required" };
  }

  if (isDangerous(command)) {
    return {
      error: "dangerous_command",
      message: `Command looks dangerous. Ask the user for explicit approval before running: ${command}`
    };
  }

  ensureSession();
  sendCommand(command);

  const output = await waitForStableOutput();
  return { command, output };
}

module.exports = {
  claw_shell_run,
};