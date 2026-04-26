#!/usr/bin/env node
// af.mjs — Asset Factory CLI wrapper
//
// Why this exists:
//   Asset Factory의 모든 흐름(generate → poll → fetch image)을 한 명령으로 압축.
//   에이전트가 매번 curl/jq/base64 외울 필요 없게. 토큰 비용 0에 수렴.
//
// Usage:
//   af health
//   af catalog [models|loras]
//   af gen <project> <asset_key> <prompt> [--category sprite] [--size 64] [--negative "..."] [--wait]
//   af batch <project> <asset_key> --prompts "p1" "p2" --models m1 [--seeds 4] [--category character]
//   af workflow catalog
//   af workflow gen <category>/<variant> <project> <asset_key> "prompt"
//                   [--seed 42] [--candidates 4] [--workflow-params '{"pose_image":"..."}']
//                   [--negative "..."] [--steps 30] [--cfg 6.5] [--sampler dpmpp_2m] [--wait]
//   af status <job_id>
//   af wait <job_id> [--timeout 300]
//   af list <project> [--status approved]
//   af get <asset_id> [-o file.png]
//   af export <project> [--manifest]
//
// Env:
//   AF_HOST     base URL (default http://localhost:8000)
//   AF_API_KEY  x-api-key header (optional; required if server has API_KEY set)
//   AF_QUIET    suppress progress lines (output only final result)

import { writeFileSync } from "node:fs";

const HOST = process.env.AF_HOST || "http://localhost:8000";
const API_KEY = process.env.AF_API_KEY || "";
const QUIET = !!process.env.AF_QUIET;

function log(...args) { if (!QUIET) console.error(...args); }
function out(obj) { console.log(typeof obj === "string" ? obj : JSON.stringify(obj, null, 2)); }
function die(msg, code = 1) { console.error(`af: ${msg}`); process.exit(code); }

async function http(method, path, { body, raw = false } = {}) {
  const url = HOST.replace(/\/$/, "") + path;
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (API_KEY) headers["x-api-key"] = API_KEY;
  const init = { method, headers };
  if (body !== undefined) init.body = JSON.stringify(body);
  const r = await fetch(url, init);
  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    die(`HTTP ${r.status} ${method} ${path}\n${txt}`, 2);
  }
  if (raw) return r;
  if (r.headers.get("content-type")?.includes("application/json")) return r.json();
  return r.text();
}

// ── Args parsing (minimal, no deps) ──────────────────────
function parseArgs(argv) {
  const positional = [];
  const flags = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const key = a.slice(2);
      // greedy collect until next --flag or end
      const vals = [];
      while (i + 1 < argv.length && !argv[i + 1].startsWith("--") && !(argv[i + 1] === "-o")) {
        vals.push(argv[++i]);
      }
      flags[key] = vals.length === 0 ? true : vals.length === 1 ? vals[0] : vals;
    } else if (a === "-o") {
      flags.o = argv[++i];
    } else {
      positional.push(a);
    }
  }
  return { positional, flags };
}

// ── Commands ─────────────────────────────────────────────
async function cmdHealth() {
  const h = await http("GET", "/api/health");
  const sd = await http("GET", "/api/health/sd");
  out({ service: h, sd });
}

async function cmdCatalog(kind = "models") {
  if (!["models", "loras"].includes(kind)) die("catalog: kind must be 'models' or 'loras'");
  const data = await http("GET", `/api/sd/catalog/${kind}`);
  out(data);
}

async function pollJob(jobId, timeoutSec = 300) {
  const t0 = Date.now();
  let lastLine = "";
  while ((Date.now() - t0) / 1000 < timeoutSec) {
    const j = await http("GET", `/api/jobs/${jobId}`);
    const line = `[${Math.round((Date.now() - t0) / 1000)}s] status=${j.status} ${j.completed_count ?? 0}/${j.total_count ?? "?"} failed=${j.failed_count ?? 0}`;
    if (line !== lastLine) { log(line); lastLine = line; }
    if (j.status === "completed" || j.status === "failed") return j;
    await new Promise(r => setTimeout(r, 3000));
  }
  die(`poll timeout after ${timeoutSec}s for job ${jobId}`, 3);
}

async function cmdGen(args) {
  const { positional, flags } = args;
  const [project, asset_key, ...promptParts] = positional;
  const prompt = promptParts.join(" ");
  if (!project || !asset_key || !prompt) die("usage: af gen <project> <asset_key> <prompt> [--negative ...] [--size N] [--wait]");
  const body = {
    project,
    asset_key,
    category: flags.category || "sprite",
    prompt,
    negative_prompt: flags.negative || null,
    expected_size: flags.size ? Number(flags.size) : 64,
    max_colors: flags["max-colors"] ? Number(flags["max-colors"]) : 32,
  };
  if (flags.model) body.model_name = flags.model;
  if (flags.steps) body.steps = Number(flags.steps);
  if (flags.cfg) body.cfg = Number(flags.cfg);
  const r = await http("POST", "/api/generate", { body });
  log(`enqueued job_id=${r.job_id}`);
  if (flags.wait || flags.w) {
    const final = await pollJob(r.job_id, Number(flags.timeout) || 300);
    out(final);
  } else {
    out(r);
  }
}

async function cmdBatch(args) {
  const { positional, flags } = args;
  const [project, asset_key] = positional;
  if (!project || !asset_key) die("usage: af batch <project> <asset_key> --prompts \"p1\" \"p2\" --models m1 [--seeds 4] [--category character]");
  const prompts = flags.prompts;
  if (!prompts) die("--prompts required (one or more strings)");
  const promptsArr = Array.isArray(prompts) ? prompts : [prompts];
  const models = flags.models ? (Array.isArray(flags.models) ? flags.models : [flags.models]) : [];
  if (models.length === 0) die("--models required (one or more model names from `af catalog models`)");
  const lorasArg = flags.loras; // simple: comma-separated "name:weight,name:weight"
  let lorasMatrix = [];
  if (lorasArg) {
    const groups = (Array.isArray(lorasArg) ? lorasArg : [lorasArg]);
    lorasMatrix = groups.map(g => g.split(",").map(item => {
      const [name, w] = item.split(":");
      return { name, weight: w ? Number(w) : 0.7 };
    }));
  }
  const body = {
    project,
    asset_key,
    category: flags.category || "character",
    prompts: promptsArr,
    models,
    loras: lorasMatrix,
    seeds_per_combo: flags.seeds ? Number(flags.seeds) : 4,
    common: {
      steps: flags.steps ? Number(flags.steps) : 28,
      cfg: flags.cfg ? Number(flags.cfg) : 7.0,
      sampler: flags.sampler || "DPM++ 2M",
      expected_size: flags.size ? Number(flags.size) : 64,
      max_colors: flags["max-colors"] ? Number(flags["max-colors"]) : 32,
      max_retries: 3,
    },
  };
  if (flags.negative) body.common.negative_prompt = flags.negative;
  const r = await http("POST", "/api/mcp/design_asset", { body });
  log(`enqueued batch_id=${r.batch_id} job_id=${r.job_id} expanded=${r.expanded_count} eta=${r.estimated_eta_seconds}s`);
  log(`cherry-pick UI: ${HOST}/cherry-pick?batch=${r.batch_id}`);
  if (flags.wait || flags.w) {
    const final = await pollJob(r.job_id, Number(flags.timeout) || (r.expanded_count * 15));
    out({ ...final, batch_id: r.batch_id, cherry_pick_url: `${HOST}/cherry-pick?batch=${r.batch_id}` });
  } else {
    out(r);
  }
}

async function cmdStatus(args) {
  const [job_id] = args.positional;
  if (!job_id) die("usage: af status <job_id>");
  out(await http("GET", `/api/jobs/${job_id}`));
}

async function cmdWait(args) {
  const [job_id] = args.positional;
  if (!job_id) die("usage: af wait <job_id> [--timeout 300]");
  out(await pollJob(job_id, Number(args.flags.timeout) || 300));
}

async function cmdList(args) {
  const [project] = args.positional;
  const qs = new URLSearchParams();
  if (project) qs.set("project", project);
  if (args.flags.status) qs.set("status", args.flags.status);
  if (args.flags.category) qs.set("category", args.flags.category);
  if (args.flags["validation-status"]) qs.set("validation_status", args.flags["validation-status"]);
  out(await http("GET", `/api/assets?${qs}`));
}

async function cmdGet(args) {
  const [asset_id] = args.positional;
  if (!asset_id) die("usage: af get <asset_id> [-o file.png]");
  const r = await http("GET", `/api/assets/${asset_id}/image`, { raw: true });
  const buf = Buffer.from(await r.arrayBuffer());
  const dest = args.flags.o || `${asset_id}.png`;
  writeFileSync(dest, buf);
  log(`wrote ${buf.length} bytes -> ${dest}`);
  out({ asset_id, path: dest, bytes: buf.length });
}

async function cmdExport(args) {
  const [project] = args.positional;
  const body = {
    project,
    save_manifest: !!args.flags.manifest || true,
  };
  if (args.flags.category) body.category = args.flags.category;
  out(await http("POST", "/api/export", { body }));
}

// ── workflow (ComfyUI 백엔드) ──────────────────────────────
async function cmdWorkflow(args) {
  const sub = args.positional[0];
  const rest = { positional: args.positional.slice(1), flags: args.flags };
  if (sub === "catalog") return cmdWorkflowCatalog();
  if (sub === "gen") return cmdWorkflowGen(rest);
  die("usage: af workflow {catalog|gen} ...");
}

async function cmdWorkflowCatalog() {
  // /api/workflows/catalog 응답 그대로 — 카테고리/변형/available/outputs/defaults
  out(await http("GET", "/api/workflows/catalog"));
}

async function cmdWorkflowGen(args) {
  const { positional, flags } = args;
  const [variantSpec, project, asset_key, ...promptParts] = positional;
  if (!variantSpec || !project || !asset_key || promptParts.length === 0) {
    die(
      "usage: af workflow gen <category>/<variant> <project> <asset_key> \"prompt\"\n" +
      "  e.g. af workflow gen sprite/pixel_alpha myproj hero \"1girl, silver hair\"\n" +
      "  options: --seed N --candidates N --workflow-params '{\"key\":\"val\"}'\n" +
      "           --negative \"...\" --steps N --cfg N --sampler s --wait"
    );
  }
  if (!variantSpec.includes("/")) {
    die("variant 는 'category/name' 형식 (예: sprite/pixel_alpha)");
  }
  const [workflow_category, workflow_variant] = variantSpec.split("/", 2);
  const prompt = promptParts.join(" ");

  const body = {
    project,
    asset_key,
    category: flags.category || "sprite",
    workflow_category,
    workflow_variant,
    prompt,
    candidates_total: flags.candidates ? Number(flags.candidates) : 1,
  };
  if (flags.seed !== undefined) body.seed = Number(flags.seed);
  if (flags.negative) body.negative_prompt = flags.negative;
  if (flags.steps) body.steps = Number(flags.steps);
  if (flags.cfg) body.cfg = Number(flags.cfg);
  if (flags.sampler) body.sampler = flags.sampler;
  if (flags["expected-size"]) body.expected_size = Number(flags["expected-size"]);
  if (flags["max-colors"]) body.max_colors = Number(flags["max-colors"]);

  // --workflow-params '{"pose_image":"...","controlnet_strength":0.9,"lora_strengths":{"x":0.5}}'
  if (flags["workflow-params"]) {
    try {
      body.workflow_params = JSON.parse(flags["workflow-params"]);
    } catch (e) {
      die(`--workflow-params 가 JSON 이 아님: ${e.message}`);
    }
  }

  const r = await http("POST", "/api/workflows/generate", { body });
  log(`enqueued job_id=${r.job_id} variant=${r.workflow_category}/${r.workflow_variant} ` +
      `candidates=${r.candidates_total} primary=${r.primary_output ?? "?"}`);
  if (r.candidates_total > 1) {
    log(`(cherry-pick UI 는 나중에 GET /api/jobs/${r.job_id} 의 batch_id 를 통해)`);
  }
  if (flags.wait || flags.w) {
    const timeoutSec = Number(flags.timeout) || Math.max(120, r.candidates_total * 60);
    const final = await pollJob(r.job_id, timeoutSec);
    out({ ...final, workflow_category: r.workflow_category, workflow_variant: r.workflow_variant });
  } else {
    out(r);
  }
}

function usage() {
  console.error(`af — Asset Factory CLI (host: ${HOST})

Commands:
  af health                            # 서버 + SD/ComfyUI 연결 점검 (양 백엔드)
  af catalog [models|loras]            # A1111 모델/LoRA 목록
  af gen <project> <key> <prompt> [--size 64] [--negative "..."] [--model m] [--wait]
                                       # A1111 단일 에셋 생성
  af batch <project> <key> --prompts "p1" ["p2"...] --models m1 [m2...] [--seeds 4]
           [--loras "name:w,name:w" "..."] [--size 64] [--wait]
                                       # A1111 디자인 배치 (cherry-pick)

  af workflow catalog                  # ComfyUI 워크플로우 카탈로그 (sprite/illustration/...)
  af workflow gen <category>/<variant> <project> <key> "prompt"
        [--seed 42] [--candidates 4] [--workflow-params '{"pose_image":"x.png"}']
        [--negative "..."] [--steps 30] [--cfg 6.5] [--sampler dpmpp_2m] [--wait]
                                       # ComfyUI 변형 호출. multi-output 변형은 1슬롯에 N장 저장됨

  af status <job_id>                   # 잡 상태 단발 조회
  af wait <job_id> [--timeout 300]     # 폴링 (3초 간격)
  af list <project> [--status approved]
  af get <asset_id> [-o file.png]      # 에셋 이미지 다운로드
  af export <project> [--manifest]

Examples:
  af workflow catalog | jq '.categories | keys'
  af workflow gen sprite/pixel_alpha myproj hero "1girl, silver hair, school uniform" --seed 42 --wait
  af workflow gen illustration/hyphoria_hires myproj cover_v1 "fantasy landscape, masterpiece" --candidates 4

Env: AF_HOST (default http://localhost:8000), AF_API_KEY, AF_QUIET=1
`);
  process.exit(0);
}

// ── Dispatch ──────────────────────────────────────────────
const [, , cmd, ...rest] = process.argv;
if (!cmd || cmd === "-h" || cmd === "--help" || cmd === "help") usage();
const args = parseArgs(rest);

const handlers = {
  health: cmdHealth,
  catalog: () => cmdCatalog(args.positional[0] || "models"),
  gen: () => cmdGen(args),
  batch: () => cmdBatch(args),
  workflow: () => cmdWorkflow(args),
  status: () => cmdStatus(args),
  wait: () => cmdWait(args),
  list: () => cmdList(args),
  get: () => cmdGet(args),
  export: () => cmdExport(args),
};

const handler = handlers[cmd];
if (!handler) die(`unknown command: ${cmd}\nrun 'af --help'`);
await handler();
