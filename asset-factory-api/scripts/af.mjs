#!/usr/bin/env node
// af.mjs — Asset Factory CLI wrapper
//
// ⚠️  PARTIAL DEPRECATION (2026-04, post PR sunghere/asset-factory#18):
//   - `af workflow {catalog,describe,gen,upload}` 는 asset-factory 레포의
//     Python typer CLI (`python -m cli workflow ...`) 가 정식 채택됐다.
//     동일 동작이며, 신규 기능(--input, --bypass-approval 등)은 Python 쪽에 먼저 들어간다.
//     스크립트/스킬 신규 작성 시 `python -m cli workflow ...` 사용 권장.
//   - `af health` / `af list` / `af get` / `af export` 는 Python 포팅 전이라
//     본 스크립트가 계속 운영용 유일 진입점이다.
//   완전 제거 시점은 위 명령들이 Python CLI 로 포팅된 이후.
//
// Why this exists:
//   Asset Factory의 모든 흐름(generate → poll → fetch image)을 한 명령으로 압축.
//   에이전트가 매번 curl/jq/base64 외울 필요 없게. 토큰 비용 0에 수렴.
//
// Usage:
//   af health
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
//   AF_HOST     base URL (default http://localhost:47823 — Asset Factory 운영 메인)
//                기본값을 운영 포트로 박은 이유: 에이전트가 default 호출 시 dev
//                인스턴스 (8000) 로 가서 메인 DB / 큐와 다른 곳에 작업하는 사고
//                방지. 테스트 인스턴스 호출은 명시적으로 AF_HOST=http://localhost:8000
//   AF_API_KEY  x-api-key header (optional; required if server has API_KEY set)
//   AF_QUIET    suppress progress lines (output only final result)

import { writeFileSync } from "node:fs";

const HOST = process.env.AF_HOST || "http://localhost:47823";
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
  out(h);
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
  if (sub === "upload") return cmdWorkflowUpload(rest);
  die("usage: af workflow {catalog|gen|upload} ...");
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
    log(`cherry-pick UI: ${r.cherry_pick_url ?? `${HOST}/cherry-pick?run=${r.job_id}`}`);
  }
  if (flags.wait || flags.w) {
    const timeoutSec = Number(flags.timeout) || Math.max(120, r.candidates_total * 60);
    const final = await pollJob(r.job_id, timeoutSec);
    out({ ...final, workflow_category: r.workflow_category, workflow_variant: r.workflow_variant });
  } else {
    out(r);
  }
}

// ── workflow upload ──────────────────────────────────────
//
// 동적 입력 이미지를 ComfyUI input/<subfolder>/ 에 업로드한다.
// 응답의 name 을 후속 `af workflow gen` 의 --workflow-params 의
// load_images.<label> 에 박아 사용. SKILL.md 의 chain 패턴 참고.
//
// 두 가지 출처:
//   1) 로컬 파일:    af workflow upload ./pose.png
//   2) 기존 에셋:    af workflow upload --from-asset <asset_id>
//
// (P0-3 1차 — 멍멍이 합의한 단순 형태. P0-1/P0-2 가 머지된 후
//  --from-run / --output / --bypass-approval 통합은 follow-up PR.)
async function cmdWorkflowUpload(args) {
  const { positional, flags } = args;
  // parseArgs 가 `--from-asset abc /some/file.png` 같이 뒤따르는 positional 까지
  // 배열로 슬러프할 수 있다. fromAsset 은 단일 string 으로 강제하고, 잉여는
  // 명시적으로 거부.
  let fromAsset = flags["from-asset"];
  if (Array.isArray(fromAsset)) {
    if (fromAsset.length > 1) {
      die(`--from-asset 은 값 1개만 받음 (받음: ${JSON.stringify(fromAsset)})`);
    }
    fromAsset = fromAsset[0];
  }
  const subfolder = flags.subfolder || "";
  const localPath = positional[0];

  // 출처 검증 — 정확히 하나만
  if (fromAsset && localPath) {
    die("--from-asset 과 로컬 파일 경로는 동시 사용 불가");
  }
  if (!fromAsset && !localPath) {
    die(
      "usage: af workflow upload <local-file>\n" +
      "       af workflow upload --from-asset <asset_id>\n" +
      "  optional: --subfolder <name>  (default: asset-factory)\n" +
      "\n" +
      "  응답의 .name 을 --workflow-params 의 load_images.<label> 에 박아 사용.\n" +
      "  예) af workflow upload ./pose.png  →  { \"name\": \"asset-factory_abc_pose.png\" }\n" +
      "      af workflow gen sprite/pixel_alpha pj k \"...\" \\\n" +
      "        --workflow-params '{\"load_images\":{\"pose_image\":\"asset-factory_abc_pose.png\"}}'"
    );
  }

  if (fromAsset) {
    // 기존 에셋 → 입력으로 chain
    const body = { asset_id: fromAsset };
    if (subfolder) body.subfolder = subfolder;
    const r = await http("POST", "/api/workflows/inputs/from-asset", { body });
    log(`uploaded from asset ${fromAsset} → name=${r.name}`);
    out(r);
    return;
  }

  // 로컬 파일 → multipart upload
  // Node 18+ 의 native FormData / Blob / fetch 사용 (의존성 0).
  const { readFileSync, statSync } = await import("node:fs");
  const { basename } = await import("node:path");

  let stat;
  try {
    stat = statSync(localPath);
  } catch (e) {
    die(`파일 없음: ${localPath}`);
  }
  if (!stat.isFile()) die(`파일이 아님: ${localPath}`);

  const buf = readFileSync(localPath);
  const fname = basename(localPath);

  // content-type 추정 — 서버가 PNG/JPEG/WEBP 만 허용 (asset-factory server.py).
  // 잘못된 확장자면 서버에서 415 — 호출자에게 명확히 알리는 게 낫다.
  const ext = fname.toLowerCase().match(/\.(png|jpe?g|webp)$/);
  const contentType = !ext ? null
    : ext[1] === "png" ? "image/png"
    : ext[1] === "webp" ? "image/webp"
    : "image/jpeg";
  if (!contentType) {
    die(`지원 안 되는 확장자: ${fname} (.png/.jpg/.jpeg/.webp 만)`);
  }

  // FormData + Blob — Node 18+ native
  const fd = new FormData();
  fd.append("file", new Blob([buf], { type: contentType }), fname);
  if (subfolder) fd.append("subfolder", subfolder);

  // http() 헬퍼는 JSON body 전용이라 fetch 직접 호출.
  const url = HOST.replace(/\/$/, "") + "/api/workflows/inputs";
  const headers = {};
  if (API_KEY) headers["x-api-key"] = API_KEY;
  // Content-Type 은 fetch 가 boundary 포함해 자동 설정 — 직접 박지 마라.

  const r = await fetch(url, { method: "POST", headers, body: fd });
  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    die(`HTTP ${r.status} POST /api/workflows/inputs\n${txt}`, 2);
  }
  const j = await r.json();
  log(`uploaded ${fname} (${stat.size}B, ${contentType}) → name=${j.name}`);
  out(j);
}

function usage() {
  console.error(`af — Asset Factory CLI (host: ${HOST})

Commands:
  af health                            # 서버 + ComfyUI 연결 점검

  af workflow catalog                  # ComfyUI 워크플로우 카탈로그 (sprite/illustration/...)
  af workflow gen <category>/<variant> <project> <key> "prompt"
        [--seed 42] [--candidates 4] [--workflow-params '{"pose_image":"x.png"}']
        [--negative "..."] [--steps 30] [--cfg 6.5] [--sampler dpmpp_2m] [--wait]
                                       # ComfyUI 변형 호출. multi-output 변형은 1슬롯에 N장 저장됨
  af workflow upload <local-file> [--subfolder name]
  af workflow upload --from-asset <asset_id> [--subfolder name]
                                       # 동적 입력 이미지 업로드 (PoseExtract/ControlNet)
                                       # 응답의 .name 을 --workflow-params 의 load_images.<label> 에 사용

  af status <job_id>                   # 잡 상태 단발 조회
  af wait <job_id> [--timeout 300]     # 폴링 (3초 간격)
  af list <project> [--status approved]
  af get <asset_id> [-o file.png]      # 에셋 이미지 다운로드
  af export <project> [--manifest]

Examples:
  af workflow catalog | jq '.categories | keys'
  af workflow gen sprite/pixel_alpha myproj hero "1girl, silver hair, school uniform" --seed 42 --wait
  af workflow gen illustration/hyphoria_hires myproj cover_v1 "fantasy landscape, masterpiece" --candidates 4

  # 동적 입력 chain — 사용자 사진 → pose extract → 캐릭터 합성
  POSE_NAME=$(af workflow upload ./user_pose.png | jq -r .name)
  af workflow gen sprite/pixel_alpha myproj knight "1girl, blue armor, ..." \\
      --workflow-params "{\\"load_images\\":{\\"pose_image\\":\\"$POSE_NAME\\"}}" --wait

Env: AF_HOST (default http://localhost:47823 — 운영 메인. 테스트는 :8000), AF_API_KEY, AF_QUIET=1
`);
  process.exit(0);
}

// ── Dispatch ──────────────────────────────────────────────
const [, , cmd, ...rest] = process.argv;
if (!cmd || cmd === "-h" || cmd === "--help" || cmd === "help") usage();
const args = parseArgs(rest);

const handlers = {
  health: cmdHealth,
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
