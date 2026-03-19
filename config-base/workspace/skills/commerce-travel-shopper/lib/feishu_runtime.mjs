import path from "node:path";
import fs from "node:fs";
import { randomUUID } from "node:crypto";
import { spawn, spawnSync } from "node:child_process";
import { STATES, assertTransition, nextState, TERMINAL_STATES } from "./workflow.mjs";
import { appendJsonLine, ensureDir, readJson, writeJson } from "./storage.mjs";

function nowIso() {
  return new Date().toISOString();
}

function urlEncode(v) {
  return encodeURIComponent(String(v || "").trim());
}

function parseCollectOutput(raw) {
  try {
    const parsed = JSON.parse(String(raw || "{}"));
    const files = Array.isArray(parsed?.results)
      ? parsed.results
          .flatMap((x) => {
            if (!x || !x.ok) return [];
            if (Array.isArray(x.files)) return x.files.map((f) => String(f));
            if (x.file) return [String(x.file)];
            return [];
          })
          .filter(Boolean)
      : [];
    return { parsed, files };
  } catch {
    return { parsed: { parse_error: true, raw: String(raw || "") }, files: [] };
  }
}

function toNum(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function runNodeScriptAsync(args = [], options = {}) {
  const timeoutMs = Math.max(1_000, Math.floor(toNum(options.timeoutMs, 300_000)));
  const maxBuffer = Math.max(256 * 1024, Math.floor(toNum(options.maxBuffer, 8 * 1024 * 1024)));
  return new Promise((resolve, reject) => {
    const child = spawn("node", args, {
      stdio: ["ignore", "pipe", "pipe"],
      env: process.env,
    });

    let stdout = "";
    let stderr = "";
    let stdoutTruncated = false;
    let stderrTruncated = false;
    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      reject(new Error(`collect failed: timeout after ${timeoutMs}ms`));
    }, timeoutMs);

    child.stdout.on("data", (chunk) => {
      const next = stdout.length + String(chunk).length;
      if (next > maxBuffer) {
        stdoutTruncated = true;
        const keep = Math.max(0, maxBuffer - stdout.length);
        if (keep > 0) stdout += String(chunk).slice(0, keep);
        return;
      }
      stdout += String(chunk);
    });

    child.stderr.on("data", (chunk) => {
      const next = stderr.length + String(chunk).length;
      if (next > maxBuffer) {
        stderrTruncated = true;
        const keep = Math.max(0, maxBuffer - stderr.length);
        if (keep > 0) stderr += String(chunk).slice(0, keep);
        return;
      }
      stderr += String(chunk);
    });

    child.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });

    child.on("close", (code) => {
      clearTimeout(timer);
      const finalStdout = stdoutTruncated ? `${stdout}\n...stdout truncated...` : stdout;
      const finalStderr = stderrTruncated ? `${stderr}\n...stderr truncated...` : stderr;
      if (code !== 0) {
        reject(new Error(`collect failed: ${(finalStderr || finalStdout || `exit code ${code}`).trim()}`));
        return;
      }
      resolve({ stdout: finalStdout, stderr: finalStderr, code: Number(code || 0) });
    });
  });
}

function sumPrice(offer) {
  return toNum(offer.final_price, toNum(offer.base_price) + toNum(offer.tax_fee) - toNum(offer.coupon));
}

function inferSourceByText(text) {
  const raw = String(text || "").toLowerCase();
  if (raw.includes("ctrip") || raw.includes("携程")) return "ctrip";
  if (raw.includes("qunar") || raw.includes("去哪儿")) return "qunar";
  if (raw.includes("feizhu") || raw.includes("飞猪") || raw.includes("fliggy")) return "feizhu";
  if (raw.includes("meituan") || raw.includes("美团")) return "meituan";
  if (raw.includes("taobao") || raw.includes("淘宝")) return "taobao";
  if (raw.includes("jd") || raw.includes("京东")) return "jd";
  return "unknown";
}

function normalizeInventoryHint(text) {
  const raw = String(text || "");
  if (/售罄|无票|无房|sold\s*out/i.test(raw)) return "sold_out_risk";
  if (/紧张|仅剩|少量/i.test(raw)) return "low_inventory";
  if (/有票|有房|充足|in\s*stock/i.test(raw)) return "in_stock";
  return "";
}

function extractPolicyText(text) {
  const lines = String(text || "")
    .split(/\r?\n/)
    .map((x) => x.trim())
    .filter(Boolean);
  const found = lines.find((x) => /退改|取消|refund|cancel/i.test(x));
  return found || "";
}

function uniqueStrings(arr = []) {
  return [...new Set(arr.map((x) => String(x || "").trim()).filter(Boolean))];
}

function jaccard(aTokens = [], bTokens = []) {
  const a = new Set(aTokens);
  const b = new Set(bTokens);
  if (!a.size && !b.size) return 1;
  let inter = 0;
  for (const t of a) {
    if (b.has(t)) inter += 1;
  }
  const union = new Set([...a, ...b]).size;
  return union > 0 ? inter / union : 0;
}

function scoreSameProduct(anchor, offer) {
  const anchorTitleTokens = uniqueStrings(tokenizeText(anchor.title || anchor.keyword));
  const offerTitleTokens = uniqueStrings(tokenizeText(offer.item_title || offer.normalized_title || ""));
  const titleScore = jaccard(anchorTitleTokens, offerTitleTokens);

  const anchorBrand = compactText(anchor.brand || "");
  const offerTitleRaw = compactText(`${offer.item_title || ""}${offer.raw_text || ""}`);
  const brandScore = anchorBrand && offerTitleRaw.includes(anchorBrand) ? 1 : anchorBrand ? 0 : 0.4;

  const anchorSpec = compactText(anchor.spec || "");
  const offerSpec = compactText(offer.normalized_spec || "");
  const specScore = anchorSpec && offerSpec
    ? anchorSpec === offerSpec
      ? 1
      : offerSpec.includes(anchorSpec) || anchorSpec.includes(offerSpec)
        ? 0.75
        : 0
    : anchorSpec || offerSpec
      ? 0.25
      : 0.6;

  const packScore = anchor.pack_count && offer.pack_count
    ? Math.max(0, 1 - Math.abs(Number(anchor.pack_count) - Number(offer.pack_count)) / Math.max(1, Number(anchor.pack_count)))
    : 0.5;

  const score = 0.4 * titleScore + 0.15 * brandScore + 0.35 * specScore + 0.1 * packScore;
  return Math.max(0, Math.min(1, Number(score.toFixed(4))));
}

function extractPriceByKeyword(text, keywordRegex) {
  const src = String(text || "");
  const m = src.match(new RegExp(`${keywordRegex.source}[^0-9]{0,12}(\\d{2,6}(?:\\.\\d{1,2})?)`, "i"));
  return m ? toNum(m[1], 0) : 0;
}

function extractAllPrices(text) {
  const src = String(text || "");
  const nums = [];
  const re = /\d{2,6}(?:\.\d{1,2})?/g;
  let m;
  while ((m = re.exec(src))) {
    const n = toNum(m[0], 0);
    if (n > 0) nums.push(n);
  }
  return nums;
}

function compactText(v) {
  return String(v || "")
    .toLowerCase()
    .replace(/[\s\u3000]+/g, "")
    .replace(/[【】\[\]()（）,，。.!！?:：;；'"“”‘’`~·]/g, "");
}

function tokenizeText(v) {
  return compactText(v)
    .split(/[^a-z0-9\u4e00-\u9fa5]+/)
    .map((x) => x.trim())
    .filter(Boolean);
}

function parseSpecFromText(text) {
  const src = String(text || "");
  const volume = src.match(/(\d+(?:\.\d+)?)\s*(ml|l|g|kg)/i);
  const pack = src.match(/(?:\*|x|×)\s*(\d{1,3})/) || src.match(/(\d{1,3})\s*(盒|瓶|包|袋|支|听|罐|件|箱|罐装|盒装)/);
  const volumeValue = volume ? toNum(volume[1], 0) : 0;
  const volumeUnit = volume ? String(volume[2] || "").toLowerCase() : "";
  const packCount = pack ? Math.max(1, Math.floor(toNum(pack[1], 1))) : 1;
  const volumeMl = volumeUnit === "l" ? volumeValue * 1000 : volumeUnit === "kg" ? volumeValue * 1000 : volumeValue;
  const totalAmount = volumeMl > 0 ? volumeMl * packCount : 0;
  const normalizedSpec = volumeMl > 0 ? `${volumeMl}unit*${packCount}` : "";
  return {
    normalized_spec: normalizedSpec,
    unit_amount: volumeMl,
    pack_count: packCount,
    total_amount: totalAmount,
  };
}

function extractTitleFromText(text, query = {}) {
  const keyword = String(query.keyword || query.q || "").trim();
  const lines = String(text || "")
    .split(/\r?\n/)
    .map((x) => x.trim())
    .filter(Boolean);
  if (!lines.length) return keyword;
  const byKeyword = keyword ? lines.find((x) => compactText(x).includes(compactText(keyword))) : "";
  if (byKeyword) return byKeyword;
  const filtered = lines.filter((x) => !/(￥|¥|\d{2,6}(?:\.\d{1,2})?|销量|评价|月销|店铺|自营|退改|取消|包邮)/i.test(x));
  const best = (filtered.length ? filtered : lines).sort((a, b) => b.length - a.length)[0] || "";
  return best;
}

function extractShopNameFromText(text) {
  const lines = String(text || "")
    .split(/\r?\n/)
    .map((x) => x.trim())
    .filter(Boolean);
  const found = lines.find((x) => /(旗舰店|专营店|专卖店|自营|店铺|超市|官方)/.test(x));
  return found || "";
}

function offerFromEvidenceText(evidence, text, index, query = {}) {
  const source = inferSourceByText(`${evidence.file} ${text}`);
  const finalByKeyword = extractPriceByKeyword(text, /(总价|到手|合计|支付|final|price)/i);
  const base = extractPriceByKeyword(text, /(票价|房价|单价|base)/i);
  const tax = extractPriceByKeyword(text, /(税费|税|服务费|tax|fee)/i);
  const coupon = extractPriceByKeyword(text, /(优惠|券|立减|coupon|discount)/i);
  const all = extractAllPrices(text);
  const fallback = all.length ? Math.min(...all) : 0;
  const computed = toNum(base) + toNum(tax) - toNum(coupon);
  const finalPrice = finalByKeyword > 0 ? finalByKeyword : computed > 0 ? computed : fallback;
  const itemTitle = extractTitleFromText(text, query);
  const shopName = extractShopNameFromText(text);
  const spec = parseSpecFromText(`${itemTitle}\n${text}`);
  return {
    offer_id: `ocr_${index + 1}`,
    source,
    item_title: itemTitle,
    shop_name: shopName,
    normalized_title: compactText(itemTitle),
    ...spec,
    base_price: base,
    tax_fee: tax,
    coupon,
    final_price: finalPrice,
    policy_text: extractPolicyText(text),
    inventory_hint: normalizeInventoryHint(text),
    evidence_id: evidence.evidence_id,
    captured_at: evidence.captured_at,
    ocr_confidence: all.length > 0 ? 0.7 : 0.3,
    raw_text: String(text || "").slice(0, 2000),
  };
}

export class FeishuShopperRuntime {
  constructor(options = {}) {
    this.root = options.root || process.cwd();
    this.runtimeDir = options.runtimeDir || path.join(this.root, "runtime");
    this.tasksDir = path.join(this.runtimeDir, "tasks");
    this.logsDir = path.join(this.runtimeDir, "logs");
    this.statePath = path.join(this.runtimeDir, "state.json");
    this.allowedPath =
      options.allowedOperatorsPath || process.env.COMMERCE_ALLOWED_OPERATORS_FILE || path.join(this.root, "allowed_operators.json");
    ensureDir(this.tasksDir);
    ensureDir(this.logsDir);
    this._boot();
  }

  _boot() {
    const state = readJson(this.statePath, null);
    if (state && state.activeTaskId) {
      this.state = state;
      this._reconcileActiveTaskOnBoot();
      return;
    }
    this.state = { activeTaskId: null, updatedAt: nowIso() };
    writeJson(this.statePath, this.state);
  }

  _reconcileActiveTaskOnBoot() {
    const activeTaskId = String(this.state?.activeTaskId || "").trim();
    if (!activeTaskId) return;

    const task = readJson(this._taskPath(activeTaskId), null);
    if (!task || !task.task_id) {
      this.state.activeTaskId = null;
      this._saveState();
      return;
    }

    if (TERMINAL_STATES.has(task.state)) {
      this.state.activeTaskId = null;
      this._saveState();
      return;
    }

    const timeoutMinutes = Math.max(0, Math.floor(toNum(process.env.COMMERCE_ACTIVE_TASK_TIMEOUT_MIN, 360)));
    if (timeoutMinutes <= 0) return;

    const blockingStates = new Set([STATES.WAIT_CONFIRM_SUBMIT, STATES.WAIT_CONFIRM_PAY]);
    if (!blockingStates.has(String(task.state || ""))) return;

    const lastUpdatedAt = Date.parse(String(task.updated_at || task.created_at || ""));
    if (!Number.isFinite(lastUpdatedAt)) return;

    if (Date.now() - lastUpdatedAt < timeoutMinutes * 60 * 1000) return;

    task.execution = task.execution || {};
    task.execution.abort = true;
    task.state = STATES.ABORTED;
    task.updated_at = nowIso();
    task.audit = Array.isArray(task.audit) ? task.audit : [];
    task.audit.push({
      ts: task.updated_at,
      action: "AUTO_ABORT_STALE_ACTIVE_TASK",
      operator: "system",
      reason: `active_task_timeout_${timeoutMinutes}m`,
    });
    this._writeTask(task);
    this._emit(task.task_id, "AUTO_ABORT_STALE_ACTIVE_TASK", {
      operator: "system",
      reason: `active_task_timeout_${timeoutMinutes}m`,
    });
    this.state.activeTaskId = null;
    this._saveState();
  }

  _saveState() {
    this.state.updatedAt = nowIso();
    writeJson(this.statePath, this.state);
  }

  _taskPath(taskId) {
    return path.join(this.tasksDir, `${taskId}.json`);
  }

  _eventPath(taskId) {
    return path.join(this.logsDir, `${taskId}.events.jsonl`);
  }

  _evidenceDir(taskId) {
    return path.join(this.runtimeDir, "evidence", taskId);
  }

  _collectScriptPath() {
    return path.join(this.root, "scripts", "collect_screenshots.mjs");
  }

  _buildJobsFromTask(task) {
    const type = String(task.task_type || "").toLowerCase();
    const query = task.query || {};
    const platforms = Array.isArray(task.platforms) ? task.platforms : [];
    if (!platforms.length) return [];
    if (type === "product" || type === "shop") {
      const keyword = String(query.keyword || query.q || "").trim();
      if (!keyword) return [];
      return platforms
        .map((p) => String(p || "").toLowerCase())
        .map((p) => {
          if (p === "jd") return { source: "jd", url: `https://search.jd.com/Search?keyword=${urlEncode(keyword)}` };
          if (p === "taobao") return { source: "taobao", url: `https://s.taobao.com/search?q=${urlEncode(keyword)}` };
          return null;
        })
        .filter(Boolean);
    }
    if (type === "hotel") {
      const city = String(query.city || "").trim();
      if (!city) return [];
      return platforms
        .map((p) => String(p || "").toLowerCase())
        .map((p) => {
          if (p === "ctrip") return { source: "ctrip", url: `https://hotels.ctrip.com/hotels/list?cityName=${urlEncode(city)}` };
          if (p === "qunar") return { source: "qunar", url: `https://hotel.qunar.com/city/${urlEncode(city)}` };
          if (p === "meituan") return { source: "meituan", url: `https://www.meituan.com/s/${urlEncode(city)}酒店/` };
          if (p === "feizhu") return { source: "feizhu", url: `https://h5.m.taobao.com/trip/hotel/search/index?keyword=${urlEncode(city)}` };
          return null;
        })
        .filter(Boolean);
    }
    if (type === "flight") {
      return platforms
        .map((p) => String(p || "").toLowerCase())
        .map((p) => {
          if (p === "ctrip") return { source: "ctrip", url: "https://flights.ctrip.com/online/list/" };
          if (p === "qunar") return { source: "qunar", url: "https://flight.qunar.com/" };
          if (p === "meituan") return { source: "meituan", url: "https://www.meituan.com/" };
          if (p === "feizhu") return { source: "feizhu", url: "https://www.fliggy.com/" };
          return null;
        })
        .filter(Boolean);
    }
    return [];
  }

  _readTask(taskId) {
    const resolvedTaskId = String(taskId || "").trim();
    if (!resolvedTaskId) {
      throw new Error("no active task");
    }
    const task = readJson(this._taskPath(resolvedTaskId), null);
    if (!task) throw new Error(`task not found: ${resolvedTaskId}`);
    return task;
  }

  _writeTask(task, meta = {}) {
    const ts = nowIso();
    task.heartbeat = {
      last_heartbeat_at: ts,
      stage: String(meta.stage || task.state || "UNKNOWN"),
    };
    if (meta.note) {
      task.heartbeat.note = String(meta.note);
    }
    writeJson(this._taskPath(task.task_id), task);
  }

  _isBlockingState(state) {
    return new Set([STATES.WAIT_CONFIRM_SUBMIT, STATES.WAIT_CONFIRM_PAY]).has(String(state || ""));
  }

  _computeTaskAgeMinutes(task) {
    const from = Date.parse(String(task?.updated_at || task?.created_at || ""));
    if (!Number.isFinite(from)) return null;
    return Number(((Date.now() - from) / 60000).toFixed(1));
  }

  _allowedOperators() {
    const loaded = readJson(this.allowedPath, { users: [] });
    const fromEnv = (process.env.COMMERCE_ALLOWED_OPERATORS || "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    return new Set([...(loaded.users || []), ...fromEnv]);
  }

  _checkOperator(operator, task) {
    const allowed = this._allowedOperators();
    if (allowed.size === 0) return;
    if (!operator) throw new Error("operator is required in restricted mode");
    if (operator === task.created_by) return;
    if (allowed.has(operator)) return;
    throw new Error(`operator not allowed: ${operator}`);
  }

  _emit(taskId, event, payload = {}) {
    appendJsonLine(this._eventPath(taskId), {
      ts: nowIso(),
      task_id: taskId,
      event,
      ...payload,
    });
  }

  createTask({ type, query = {}, platforms = [], createdBy = "group_user", note = "" }) {
    if (!type) throw new Error("task type is required");
    if (this.state.activeTaskId) {
      const active = readJson(this._taskPath(this.state.activeTaskId), null);
      if (!active || !active.task_id) {
        this.state.activeTaskId = null;
        this._saveState();
      } else if (!TERMINAL_STATES.has(active.state)) {
        throw new Error(`active task exists: ${active.task_id}`);
      } else {
        this.state.activeTaskId = null;
        this._saveState();
      }
    }

    const taskId = `task_${new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14)}_${randomUUID().slice(0, 6)}`;
    const task = {
      task_id: taskId,
      task_type: type,
      query,
      platforms,
      note,
      created_by: createdBy,
      created_at: nowIso(),
      updated_at: nowIso(),
      state: STATES.COLLECTING,
      execution: {
        confirm_submit: false,
        confirm_pay: false,
        abort: false,
      },
      evidence: [],
      offers: [],
      ranking: { recommended_offer_id: null, reason: [], ranked_offer_ids: [] },
      checkout_draft: null,
      same_product: {
        anchor: null,
        threshold: 0.78,
        matched_offer_ids: [],
        report: null,
      },
      heartbeat: {
        last_heartbeat_at: nowIso(),
        stage: STATES.COLLECTING,
        note: "task_created",
      },
      audit: [],
    };
    this._writeTask(task);
    this.state.activeTaskId = taskId;
    this._saveState();
    this._emit(taskId, "TASK_CREATED", { state: task.state, operator: createdBy });
    return task;
  }

  getTask(taskId) {
    return this._readTask(taskId || this.state.activeTaskId);
  }

  getSelectedOfferSnapshot(taskId, offerId) {
    const task = this._readTask(taskId || this.state.activeTaskId);
    const chosenOfferId = String(offerId || task.checkout_draft?.offer_id || task.ranking?.recommended_offer_id || "");
    if (!chosenOfferId) {
      return {
        task_id: task.task_id,
        selected_offer_id: null,
        selected_offer: null,
        selected_evidence: [],
      };
    }
    const selected = task.offers.find((x) => x.offer_id === chosenOfferId) || null;
    const selectedEvidence = selected
      ? task.evidence.filter((x) => x.evidence_id === selected.evidence_id)
      : [];
    return {
      task_id: task.task_id,
      selected_offer_id: chosenOfferId,
      selected_offer: selected
        ? {
            offer_id: selected.offer_id,
            source: selected.source,
            final_price: selected.final_price,
            base_price: selected.base_price,
            tax_fee: selected.tax_fee,
            coupon: selected.coupon,
            policy_text: selected.policy_text,
            inventory_hint: selected.inventory_hint,
            evidence_id: selected.evidence_id,
            captured_at: selected.captured_at,
          }
        : null,
      selected_evidence: selectedEvidence,
    };
  }

  async collectScreenshots(taskId, jobs = [], operator = "system", options = {}) {
    const task = this._readTask(taskId || this.state.activeTaskId);
    this._checkOperator(operator, task);
    if (TERMINAL_STATES.has(task.state)) throw new Error("task is terminal");
    if (task.state !== STATES.COLLECTING) throw new Error(`state mismatch, expected ${STATES.COLLECTING}, got ${task.state}`);
    if (!Array.isArray(jobs) || jobs.length === 0) throw new Error("collect jobs required");

    const script = this._collectScriptPath();
    if (!fs.existsSync(script)) throw new Error(`collect script not found: ${script}`);
    const args = [
      script,
      "--task",
      task.task_id,
      "--urls",
      JSON.stringify(jobs),
      "--wait",
      String(toNum(options.wait, 3000)),
      "--scroll-count",
      String(toNum(options.scrollCount, 3)),
      "--scroll-step",
      String(toNum(options.scrollStep, 1200)),
      "--scroll-wait",
      String(toNum(options.scrollWait, 1000)),
    ];
    if (options.fullPage) args.push("--full-page");
    if (options.itemSelector) {
      args.push("--item-selector", String(options.itemSelector));
    }

    const child = await runNodeScriptAsync(args, {
      timeoutMs: 5 * 60 * 1000,
      maxBuffer: 8 * 1024 * 1024,
    });
    const { parsed, files } = parseCollectOutput(child.stdout);
    const updated = this.ingestScreenshots(task.task_id, files, operator);
    const now = nowIso();
    updated.updated_at = now;
    updated.audit.push({
      ts: now,
      action: "AUTO_COLLECT",
      operator,
      jobs: jobs.length,
      files: files.length,
    });
    this._writeTask(updated);
    this._emit(updated.task_id, "AUTO_COLLECT", { operator, jobs: jobs.length, files: files.length });
    return {
      task_id: updated.task_id,
      state: updated.state,
      collected_files: files,
      collect: parsed,
      task: updated,
    };
  }

  async autoCompare(taskId, jobs = [], operator = "system", options = {}) {
    const task = this._readTask(taskId || this.state.activeTaskId);
    const effectiveJobs = Array.isArray(jobs) && jobs.length > 0 ? jobs : this._buildJobsFromTask(task);
    if (!effectiveJobs.length) {
      throw new Error("no collect jobs; provide --urls or ensure task query/platforms can generate search URLs");
    }
    const collect = await this.collectScreenshots(task.task_id, effectiveJobs, operator, options);
    const afterOcr = this.ocrExtract(collect.task_id, operator);
    const afterRank = this.rankOffers(collect.task_id, operator);
    const afterDraft = this.buildCheckoutDraft(collect.task_id, options.offerId, operator);
    const selected = this.getSelectedOfferSnapshot(collect.task_id, options.offerId);
    return {
      task_id: collect.task_id,
      state: afterDraft.state,
      collected_count: collect.collected_files.length,
      offers_count: afterOcr.offers.length,
      recommended_offer_id: afterRank.ranking?.recommended_offer_id || null,
      selected,
      next_action: "CONFIRM_SUBMIT",
    };
  }

  setSameProductAnchor(taskId, anchor = {}, operator = "system") {
    const task = this._readTask(taskId || this.state.activeTaskId);
    this._checkOperator(operator, task);
    const query = task.query || {};
    const anchorTitle = String(anchor.title || anchor.name || query.keyword || query.q || "").trim();
    const normalizedSpec = parseSpecFromText(String(anchor.spec || "")).normalized_spec;
    const resolved = {
      keyword: String(anchor.keyword || query.keyword || query.q || "").trim(),
      brand: String(anchor.brand || "").trim(),
      title: anchorTitle,
      spec: String(anchor.spec || "").trim(),
      pack_count: Math.max(0, Math.floor(toNum(anchor.pack_count, 0))),
      normalized_title: compactText(anchorTitle),
      normalized_spec: normalizedSpec,
    };
    task.same_product = task.same_product || {};
    task.same_product.anchor = resolved;
    task.updated_at = nowIso();
    task.audit.push({ ts: task.updated_at, action: "SET_SAME_ANCHOR", operator, anchor: resolved });
    this._writeTask(task);
    this._emit(task.task_id, "SET_SAME_ANCHOR", { operator });
    return { task_id: task.task_id, anchor: resolved };
  }

  _resolveSameProductAnchor(task) {
    const stored = task.same_product?.anchor || null;
    if (stored && (stored.keyword || stored.title || stored.spec || stored.brand)) {
      return stored;
    }
    const query = task.query || {};
    const keyword = String(query.keyword || query.q || "").trim();
    if (!keyword) return null;
    return {
      keyword,
      brand: "",
      title: keyword,
      spec: "",
      pack_count: 0,
      normalized_title: compactText(keyword),
      normalized_spec: "",
    };
  }

  sameProductReport(taskId, operator = "system", options = {}) {
    const task = this._readTask(taskId || this.state.activeTaskId);
    this._checkOperator(operator, task);
    if (!Array.isArray(task.offers) || task.offers.length === 0) {
      throw new Error("no offers to build same-product report");
    }
    const anchor = this._resolveSameProductAnchor(task);
    if (!anchor) {
      throw new Error("same-product anchor missing; use query keyword or SHOP SET_ANCHOR");
    }

    const threshold = Number.isFinite(Number(options.threshold))
      ? Number(options.threshold)
      : toNum(task.same_product?.threshold, 0.78);
    const scored = task.offers.map((offer) => {
      const match_score = scoreSameProduct(anchor, offer);
      const matched = match_score >= threshold;
      const unit_price = toNum(offer.total_amount, 0) > 0 ? toNum(offer.final_price) / toNum(offer.total_amount) : 0;
      return {
        offer_id: offer.offer_id,
        source: offer.source,
        shop_name: offer.shop_name || "",
        item_title: offer.item_title || "",
        final_price: toNum(offer.final_price),
        normalized_spec: offer.normalized_spec || "",
        total_amount: toNum(offer.total_amount, 0),
        unit_price,
        evidence_id: offer.evidence_id,
        match_score,
        matched,
      };
    });
    const matched = scored.filter((x) => x.matched).sort((a, b) => a.final_price - b.final_price);
    if (!matched.length) {
      throw new Error(`no same-product offers matched threshold=${threshold}`);
    }

    const byPlatform = {};
    for (const row of matched) {
      byPlatform[row.source] = byPlatform[row.source] || [];
      byPlatform[row.source].push(row);
    }
    Object.keys(byPlatform).forEach((k) => {
      byPlatform[k] = byPlatform[k].sort((a, b) => a.final_price - b.final_price);
    });

    const crossPlatform = Object.entries(byPlatform)
      .map(([source, rows]) => ({ source, best: rows[0], offers: rows.length }))
      .sort((a, b) => a.best.final_price - b.best.final_price);

    const best = crossPlatform[0]?.best || matched[0];
    const second = crossPlatform[1]?.best || null;
    const gapPct =
      best && second && second.final_price > 0
        ? Number((((second.final_price - best.final_price) / second.final_price) * 100).toFixed(2))
        : 0;

    const report = {
      task_id: task.task_id,
      anchor,
      threshold,
      matched_count: matched.length,
      by_platform: byPlatform,
      cross_platform: crossPlatform,
      summary: {
        best_offer_id: best?.offer_id || null,
        best_platform: best?.source || null,
        best_price: best?.final_price || null,
        second_best_platform: second?.source || null,
        second_best_price: second?.final_price || null,
        best_gap_pct_vs_second: gapPct,
      },
    };

    task.same_product = task.same_product || {};
    task.same_product.anchor = anchor;
    task.same_product.threshold = threshold;
    task.same_product.matched_offer_ids = matched.map((x) => x.offer_id);
    task.same_product.report = report;
    task.updated_at = nowIso();
    task.audit.push({ ts: task.updated_at, action: "BUILD_SAME_PRODUCT_REPORT", operator, matched: matched.length, threshold });
    this._writeTask(task);
    this._emit(task.task_id, "BUILD_SAME_PRODUCT_REPORT", { operator, matched: matched.length, threshold });
    return report;
  }

  async autoCompareSameProduct(taskId, jobs = [], operator = "system", options = {}) {
    const task = this._readTask(taskId || this.state.activeTaskId);
    const effectiveJobs = Array.isArray(jobs) && jobs.length > 0 ? jobs : this._buildJobsFromTask(task);
    if (!effectiveJobs.length) {
      throw new Error("no collect jobs; provide --urls or ensure task query/platforms can generate search URLs");
    }

    if (options.anchor && typeof options.anchor === "object") {
      this.setSameProductAnchor(task.task_id, options.anchor, operator);
    }
    const collect = await this.collectScreenshots(task.task_id, effectiveJobs, operator, options);
    const afterOcr = this.ocrExtract(collect.task_id, operator);
    const report = this.sameProductReport(collect.task_id, operator, { threshold: options.threshold });
    return {
      task_id: collect.task_id,
      state: afterOcr.state,
      collected_count: collect.collected_files.length,
      offers_count: afterOcr.offers.length,
      matched_count: report.matched_count,
      report,
    };
  }

  _readEvidenceSidecarText(file) {
    const base = String(file || "");
    if (!base) return "";
    const ext = path.extname(base);
    const noExt = ext ? base.slice(0, -ext.length) : base;
    const candidates = [
      `${base}.json`,
      `${base}.txt`,
      `${noExt}.json`,
      `${noExt}.txt`,
    ];
    for (const p of candidates) {
      if (!fs.existsSync(p)) continue;
      if (p.endsWith(".json")) {
        const obj = readJson(p, null);
        if (obj) return JSON.stringify(obj);
      } else {
        const txt = fs.readFileSync(p, "utf8");
        if (txt.trim()) return txt;
      }
    }
    return "";
  }

  _visionReaderScriptPath() {
    return path.resolve(process.env.HOME || "", ".openclaw/workspace/skills/vision-reader/scripts/ocr_extract.py");
  }

  _extractTextWithVisionReader(imageFile) {
    const script = this._visionReaderScriptPath();
    if (!fs.existsSync(script)) return "";

    const bins = [process.env.PYTHON_BIN, "python3", "/usr/bin/python3"].filter(Boolean);
    for (const bin of bins) {
      const child = spawnSync(bin, [script, imageFile, "--json"], {
        encoding: "utf8",
        timeout: 60000,
        maxBuffer: 2 * 1024 * 1024,
      });
      if (child.error) continue;
      if (child.status !== 0) continue;

      const raw = String(child.stdout || "").trim();
      if (!raw) continue;
      try {
        const parsed = JSON.parse(raw);
        const txt = String(parsed?.text || "").trim();
        if (txt) return txt;
      } catch {
        // Ignore parse failure and try next python binary.
      }
    }
    return "";
  }

  ocrExtract(taskId, operator = "system") {
    const task = this._readTask(taskId || this.state.activeTaskId);
    this._checkOperator(operator, task);
    if (TERMINAL_STATES.has(task.state)) throw new Error("task is terminal");
    if (!Array.isArray(task.evidence) || task.evidence.length === 0) {
      throw new Error("no evidence for OCR extraction");
    }
    const offers = [];
    for (const [idx, ev] of task.evidence.entries()) {
      const sidecarText = this._readEvidenceSidecarText(ev.file);
      const visionText = sidecarText ? "" : this._extractTextWithVisionReader(ev.file);
      const payloadText = sidecarText || visionText;
      if (!String(payloadText || "").trim()) continue;
      const offer = offerFromEvidenceText(ev, payloadText, idx, task.query || {});
      if (offer.final_price > 0) offers.push(offer);
    }
    if (offers.length === 0) {
      throw new Error("OCR extraction produced no valid offers");
    }
    const updated = this.extractOffers(task.task_id, offers, operator);
    const now = nowIso();
    updated.updated_at = now;
    updated.audit.push({ ts: now, action: "OCR_EXTRACT", operator, count: offers.length });
    this._writeTask(updated);
    this._emit(updated.task_id, "OCR_EXTRACT", { operator, count: offers.length });
    return updated;
  }

  ingestScreenshots(taskId, files = [], operator = "system") {
    const task = this._readTask(taskId || this.state.activeTaskId);
    this._checkOperator(operator, task);
    if (TERMINAL_STATES.has(task.state)) throw new Error("task is terminal");
    if (task.state !== STATES.COLLECTING) throw new Error(`state mismatch, expected ${STATES.COLLECTING}, got ${task.state}`);
    const now = nowIso();
    const evidenceDir = this._evidenceDir(task.task_id);
    ensureDir(evidenceDir);
    const accepted = [];
    for (const f of files) {
      const abs = path.resolve(String(f));
      if (!fs.existsSync(abs)) continue;
      const ext = path.extname(abs).toLowerCase();
      if (![".png", ".jpg", ".jpeg", ".webp"].includes(ext)) continue;
      const id = `ev_${randomUUID().slice(0, 8)}`;
      accepted.push({ evidence_id: id, file: abs, captured_at: now });
    }
    task.evidence.push(...accepted);
    task.updated_at = now;
    task.audit.push({ ts: now, action: "INGEST_SCREENSHOTS", operator, count: accepted.length });
    this._writeTask(task);
    this._emit(task.task_id, "INGEST_SCREENSHOTS", { operator, count: accepted.length });
    return task;
  }

  extractOffers(taskId, offers = [], operator = "system") {
    const task = this._readTask(taskId || this.state.activeTaskId);
    this._checkOperator(operator, task);
    if (TERMINAL_STATES.has(task.state)) throw new Error("task is terminal");
    if (task.state !== STATES.COLLECTING && task.state !== STATES.ANALYZING) {
      throw new Error(`state mismatch, expected ${STATES.COLLECTING}/${STATES.ANALYZING}, got ${task.state}`);
    }
    if (task.state === STATES.COLLECTING) {
      assertTransition(task.state, STATES.ANALYZING);
      task.state = STATES.ANALYZING;
    }
    task.offers = offers.map((o, idx) => ({
      offer_id: String(o.offer_id || `offer_${idx + 1}`),
      source: String(o.source || "unknown"),
      item_title: String(o.item_title || ""),
      shop_name: String(o.shop_name || ""),
      normalized_title: String(o.normalized_title || compactText(o.item_title || "")),
      normalized_spec: String(o.normalized_spec || ""),
      unit_amount: toNum(o.unit_amount, 0),
      pack_count: Math.max(1, Math.floor(toNum(o.pack_count, 1))),
      total_amount: toNum(o.total_amount, 0),
      base_price: toNum(o.base_price),
      tax_fee: toNum(o.tax_fee),
      coupon: toNum(o.coupon),
      final_price: sumPrice(o),
      policy_text: String(o.policy_text || o.policy || ""),
      inventory_hint: String(o.inventory_hint || ""),
      evidence_id: String(o.evidence_id || ""),
      captured_at: String(o.captured_at || nowIso()),
      raw_text: String(o.raw_text || ""),
    }));
    task.updated_at = nowIso();
    task.audit.push({ ts: task.updated_at, action: "EXTRACT_OFFERS", operator, count: task.offers.length });
    this._writeTask(task);
    this._emit(task.task_id, "EXTRACT_OFFERS", { operator, count: task.offers.length });
    return task;
  }

  rankOffers(taskId, operator = "system") {
    const task = this._readTask(taskId || this.state.activeTaskId);
    this._checkOperator(operator, task);
    if (TERMINAL_STATES.has(task.state)) throw new Error("task is terminal");
    if (![STATES.ANALYZING, STATES.RANKED].includes(task.state)) {
      throw new Error(`state mismatch, expected ${STATES.ANALYZING}/${STATES.RANKED}, got ${task.state}`);
    }
    if (!task.offers.length) throw new Error("no offers to rank");
    const ranked = [...task.offers].sort((a, b) => sumPrice(a) - sumPrice(b));
    const best = ranked[0];
    task.ranking = {
      recommended_offer_id: best.offer_id,
      reason: ["final_price_min", "policy_checked_manually"],
      ranked_offer_ids: ranked.map((x) => x.offer_id),
    };
    if (task.state === STATES.ANALYZING) {
      assertTransition(STATES.ANALYZING, STATES.RANKED);
      task.state = STATES.RANKED;
    }
    task.updated_at = nowIso();
    task.audit.push({ ts: task.updated_at, action: "RANK_OFFERS", operator, recommended_offer_id: best.offer_id });
    this._writeTask(task);
    this._emit(task.task_id, "RANK_OFFERS", { operator, recommended_offer_id: best.offer_id });
    return task;
  }

  buildCheckoutDraft(taskId, offerId, operator = "system") {
    const task = this._readTask(taskId || this.state.activeTaskId);
    this._checkOperator(operator, task);
    if (TERMINAL_STATES.has(task.state)) throw new Error("task is terminal");
    if (![STATES.RANKED, STATES.DRAFT_READY].includes(task.state)) {
      throw new Error(`state mismatch, expected ${STATES.RANKED}/${STATES.DRAFT_READY}, got ${task.state}`);
    }
    const selectedId = String(offerId || task.ranking.recommended_offer_id || "");
    const selected = task.offers.find((x) => x.offer_id === selectedId);
    if (!selected) throw new Error(`offer not found: ${selectedId}`);
    task.checkout_draft = {
      offer_id: selected.offer_id,
      source: selected.source,
      expected_price: selected.final_price,
      created_at: nowIso(),
      note: "wait for CONFIRM_SUBMIT then CONFIRM_PAY",
    };
    if (task.state === STATES.RANKED) {
      assertTransition(STATES.RANKED, STATES.DRAFT_READY);
      task.state = STATES.DRAFT_READY;
      assertTransition(STATES.DRAFT_READY, STATES.WAIT_CONFIRM_SUBMIT);
      task.state = STATES.WAIT_CONFIRM_SUBMIT;
    }
    task.updated_at = nowIso();
    task.audit.push({ ts: task.updated_at, action: "BUILD_CHECKOUT_DRAFT", operator, offer_id: selected.offer_id });
    this._writeTask(task);
    this._emit(task.task_id, "BUILD_CHECKOUT_DRAFT", { operator, offer_id: selected.offer_id });
    return task;
  }

  riskCheck(taskId, operator = "system", options = {}) {
    const task = this._readTask(taskId || this.state.activeTaskId);
    this._checkOperator(operator, task);
    const tolerance = toNum(options.priceToleranceRatio, 0.05);
    const budget = toNum(options.budget, toNum(task.query?.budget, 0));
    const reasons = [];
    const warnings = [];
    const draft = task.checkout_draft;
    const checks = {
      has_offers: Array.isArray(task.offers) && task.offers.length > 0,
      has_draft: Boolean(draft),
      policy_present: true,
      inventory_safe: true,
      within_budget: true,
      draft_price_deviation_ok: true,
    };
    if (!checks.has_offers) reasons.push("no_offers");
    if (!checks.has_draft) reasons.push("checkout_draft_missing");
    const target = draft ? task.offers.find((x) => x.offer_id === draft.offer_id) : null;
    if (draft && !target) reasons.push("draft_offer_missing");
    if (target) {
      if (!String(target.policy_text || "").trim()) {
        checks.policy_present = false;
        reasons.push("policy_missing");
      }
      if (/sold_out|无票|无房|售罄/i.test(String(target.inventory_hint || ""))) {
        checks.inventory_safe = false;
        reasons.push("inventory_risk");
      }
      if (budget > 0 && toNum(target.final_price) > budget) {
        checks.within_budget = false;
        reasons.push("budget_exceeded");
      }
      const expected = toNum(draft?.expected_price, 0);
      if (expected > 0) {
        const deviation = Math.abs(toNum(target.final_price) - expected) / Math.max(1, expected);
        if (deviation > tolerance) {
          checks.draft_price_deviation_ok = false;
          reasons.push("price_deviation_exceeded");
          warnings.push(`deviation_ratio=${deviation.toFixed(4)}`);
        }
      }
    }
    const result = {
      task_id: task.task_id,
      pass: reasons.length === 0,
      reasons,
      warnings,
      checks,
      budget,
      price_tolerance_ratio: tolerance,
      checked_at: nowIso(),
    };
    this._emit(task.task_id, "RISK_CHECK", { operator, pass: result.pass, reasons });
    return result;
  }

  finalCheck(taskId, operator = "system") {
    const task = this._readTask(taskId || this.state.activeTaskId);
    this._checkOperator(operator, task);
    if (task.state !== STATES.WAIT_CONFIRM_PAY) {
      throw new Error(`state mismatch, expected ${STATES.WAIT_CONFIRM_PAY}, got ${task.state}`);
    }
    const draft = task.checkout_draft;
    if (!draft) throw new Error("checkout draft missing");
    const target = task.offers.find((x) => x.offer_id === draft.offer_id);
    if (!target) throw new Error(`draft offer missing: ${draft.offer_id}`);
    const risk = this.riskCheck(task.task_id, operator, {});
    const result = {
      task_id: task.task_id,
      pass: risk.pass,
      checks: {
        state_ok: true,
        draft_ok: true,
        price_non_negative: target.final_price >= 0,
        risk_pass: risk.pass,
      },
      expected_price: target.final_price,
      risk,
      message: risk.pass ? "ready for CONFIRM_PAY" : `blocked_by_risk: ${risk.reasons.join(",")}`,
    };
    this._emit(task.task_id, "FINAL_CHECK", { operator, pass: result.pass, expected_price: target.final_price });
    return result;
  }

  advanceTask(taskId, operator = "system") {
    const task = this._readTask(taskId || this.state.activeTaskId);
    this._checkOperator(operator, task);
    if (TERMINAL_STATES.has(task.state)) return task;
    const target = nextState(task.state);
    assertTransition(task.state, target);
    task.state = target;
    task.updated_at = nowIso();
    task.audit.push({ ts: task.updated_at, action: "ADVANCE", state: target, operator });
    this._writeTask(task);
    this._emit(task.task_id, "TASK_ADVANCED", { state: target, operator });
    return task;
  }

  confirmSubmit(taskId, operator) {
    const task = this._readTask(taskId || this.state.activeTaskId);
    this._checkOperator(operator, task);
    if (task.state !== STATES.WAIT_CONFIRM_SUBMIT) {
      throw new Error(`state mismatch, expected ${STATES.WAIT_CONFIRM_SUBMIT}, got ${task.state}`);
    }
    task.execution.confirm_submit = true;
    task.state = STATES.WAIT_CONFIRM_PAY;
    task.updated_at = nowIso();
    task.audit.push({ ts: task.updated_at, action: "CONFIRM_SUBMIT", operator });
    this._writeTask(task);
    this._emit(task.task_id, "CONFIRM_SUBMIT", { operator });
    return task;
  }

  confirmPay(taskId, operator) {
    const task = this._readTask(taskId || this.state.activeTaskId);
    this._checkOperator(operator, task);
    if (task.state !== STATES.WAIT_CONFIRM_PAY) {
      throw new Error(`state mismatch, expected ${STATES.WAIT_CONFIRM_PAY}, got ${task.state}`);
    }
    const risk = this.riskCheck(task.task_id, operator, {});
    if (!risk.pass) {
      throw new Error(`risk blocked: ${risk.reasons.join(",")}`);
    }
    task.execution.confirm_pay = true;
    task.state = STATES.DONE;
    task.updated_at = nowIso();
    task.audit.push({ ts: task.updated_at, action: "CONFIRM_PAY", operator });
    this._writeTask(task);
    this._emit(task.task_id, "CONFIRM_PAY", { operator });
    this.state.activeTaskId = null;
    this._saveState();
    return task;
  }

  abort(taskId, operator, reason = "manual_abort") {
    const task = this._readTask(taskId || this.state.activeTaskId);
    this._checkOperator(operator, task);
    if (task.state === STATES.ABORTED) return task;
    task.execution.abort = true;
    task.state = STATES.ABORTED;
    task.updated_at = nowIso();
    task.audit.push({ ts: task.updated_at, action: "ABORT", operator, reason });
    this._writeTask(task);
    this._emit(task.task_id, "ABORT", { operator, reason });
    if (this.state.activeTaskId === task.task_id) {
      this.state.activeTaskId = null;
      this._saveState();
    }
    return task;
  }

  forceReleaseActiveTask(taskId, operator = "system", reason = "manual_force_release") {
    const resolvedTaskId = String(taskId || this.state.activeTaskId || "").trim();
    if (!resolvedTaskId) {
      return { released: false, task_id: null, reason: "no_active_task" };
    }

    const task = readJson(this._taskPath(resolvedTaskId), null);
    if (task && task.task_id) {
      this._checkOperator(operator, task);
      if (!TERMINAL_STATES.has(task.state)) {
        task.execution = task.execution || {};
        task.execution.abort = true;
        task.state = STATES.ABORTED;
        task.updated_at = nowIso();
        task.audit = Array.isArray(task.audit) ? task.audit : [];
        task.audit.push({ ts: task.updated_at, action: "FORCE_RELEASE", operator, reason });
        this._writeTask(task);
        this._emit(task.task_id, "FORCE_RELEASE", { operator, reason });
      }
    }

    if (this.state.activeTaskId === resolvedTaskId) {
      this.state.activeTaskId = null;
      this._saveState();
    }

    return {
      released: true,
      task_id: resolvedTaskId,
      state: task?.state || "MISSING_TASK_FILE",
      reason,
    };
  }

  getDoctorSnapshot() {
    const activeTaskId = String(this.state?.activeTaskId || "").trim();
    const timeoutMinutes = Math.max(0, Math.floor(toNum(process.env.COMMERCE_ACTIVE_TASK_TIMEOUT_MIN, 360)));
    if (!activeTaskId) {
      return {
        active_task_id: null,
        active_task_state: null,
        active_task_age_min: null,
        heartbeat: null,
        stale_threshold_min: timeoutMinutes,
        is_stale_blocking_task: false,
        stale_reason: "no_active_task",
        suggested_action: "none",
      };
    }

    const task = readJson(this._taskPath(activeTaskId), null);
    if (!task || !task.task_id) {
      return {
        active_task_id: activeTaskId,
        active_task_state: "MISSING_TASK_FILE",
        active_task_age_min: null,
        heartbeat: null,
        stale_threshold_min: timeoutMinutes,
        is_stale_blocking_task: true,
        stale_reason: "active_task_file_missing",
        suggested_action: "SHOP FORCE_RELEASE",
      };
    }

    const ageMin = this._computeTaskAgeMinutes(task);
    const blocking = this._isBlockingState(task.state);
    const isStaleByTimeout = timeoutMinutes > 0 && Number.isFinite(ageMin) && ageMin >= timeoutMinutes;
    const isStaleBlockingTask = Boolean(blocking && isStaleByTimeout);
    const staleReason = isStaleBlockingTask
      ? `blocking_state_timeout_${timeoutMinutes}m`
      : blocking
        ? "blocking_state_but_within_timeout"
        : "active_task_not_blocking";

    return {
      active_task_id: activeTaskId,
      active_task_state: task.state,
      active_task_age_min: ageMin,
      active_task_updated_at: task.updated_at || null,
      heartbeat: task.heartbeat || null,
      stale_threshold_min: timeoutMinutes,
      is_stale_blocking_task: isStaleBlockingTask,
      stale_reason: staleReason,
      suggested_action: isStaleBlockingTask ? "SHOP FORCE_RELEASE" : "wait_or_continue_confirm",
    };
  }

  handleFeishuText(input, operator = "group_user") {
    const raw = String(input || "").trim();
    const [cmd, taskId, ...rest] = raw.split(/\s+/);
    const upper = (cmd || "").toUpperCase();
    if (upper === "CONFIRM_SUBMIT") {
      return this.confirmSubmit(taskId, operator);
    }
    if (upper === "CONFIRM_PAY") {
      return this.confirmPay(taskId, operator);
    }
    if (upper === "ABORT") {
      return this.abort(taskId, operator, "feishu_text_command");
    }
    if (upper === "SAME_REPORT") {
      const threshold = rest[0] ? Number(rest[0]) : undefined;
      return this.sameProductReport(taskId, operator, { threshold });
    }
    throw new Error(`unsupported command: ${raw}`);
  }
}
