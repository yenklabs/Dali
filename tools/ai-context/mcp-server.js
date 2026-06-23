const fs = require("fs/promises");
const path = require("path");
const crypto = require("crypto");
const os = require("os");
const { execSync } = require("child_process");
const { Worker } = require("worker_threads");

const { Server } = require("@modelcontextprotocol/sdk/server/index.js");
const {
	StdioServerTransport,
} = require("@modelcontextprotocol/sdk/server/stdio.js");
const {
	CallToolRequestSchema,
	ListToolsRequestSchema,
} = require("@modelcontextprotocol/sdk/types.js");

let DatabaseSync = null;
try {
	({ DatabaseSync } = require("node:sqlite"));
} catch {
	DatabaseSync = null;
}

const INDEX_VERSION = 2;
const MAX_FILES = 12000;
const MAX_FILE_BYTES = 200_000;
const CHUNK_LINES = 60;
const CHUNK_OVERLAP = 10;
const DEFAULT_TOKEN_BUDGET = 1400;
const MAX_PIVOT_FILES = 6;
const MAX_NEIGHBOR_SKELETONS = 10;
const MAX_RETRIEVAL_CANDIDATES = 1500;
const MAX_FALLBACK_SCAN_FILES = 600;
const MAX_CACHE_AGE_MS = 1000 * 60 * 60 * 8;
const RETRIEVAL_CACHE_VERSION = 10;
const CACHE_DIR_NAME = ".ai-context";
const LATENCY_SAMPLE_WINDOW = 200;
const SNAPSHOT_STALE_MS = 1000 * 60 * 5;
const MIN_FILES_FOR_WORKERS = 24;
const MAX_INDEX_WORKERS = 8;
const MIN_BYTES_FOR_WORKERS = 600_000;
const TARGET_BYTES_PER_WORKER = 2_000_000;
const WORKER_COUNT_OVERRIDE = Number.parseInt(
	process.env.AI_CONTEXT_INDEX_WORKERS || "",
	10,
);

const TEXT_EXTENSIONS = new Set([
	".js",
	".jsx",
	".ts",
	".tsx",
	".json",
	".md",
	".txt",
	".yml",
	".yaml",
	".toml",
	".xml",
	".html",
	".css",
	".scss",
	".py",
	".java",
	".go",
	".rs",
	".c",
	".h",
	".cpp",
	".hpp",
	".cs",
	".php",
	".rb",
	".sh",
	".zsh",
	".sql",
	".graphql",
]);

const SKIP_DIRS = new Set([
	"node_modules",
	".git",
	"dist",
	"build",
	".next",
	"out",
	"coverage",
	".nyc_output",
	"playwright-report",
	"test-results",
	"allure-results",
	".vscode",
	".idea",
	".turbo",
	".cache",
	CACHE_DIR_NAME,
]);

const SOURCE_PATH_HINTS = new Set([
	"src",
	"app",
	"apps",
	"lib",
	"libs",
	"packages",
	"services",
	"service",
	"server",
	"client",
	"modules",
	"components",
]);

const GENERATED_ARTIFACT_PATH_HINTS = new Set([
	"coverage",
	".nyc_output",
	"playwright-report",
	"test-results",
	"allure-results",
	"report",
	"reports",
	"junit",
	"lcov",
	"snapshot",
	"snapshots",
]);

const GENERATED_QUERY_TERMS = new Set([
	"coverage",
	"report",
	"reports",
	"junit",
	"lcov",
	"nyc",
	"allure",
	"playwright",
	"snapshot",
	"snapshots",
]);

const TEST_PATH_HINTS = new Set([
	"test",
	"tests",
	"__tests__",
	"spec",
	"specs",
	"e2e",
	"integration",
]);

const TEST_QUERY_TERMS = new Set([
	"test",
	"tests",
	"testing",
	"spec",
	"jest",
	"vitest",
	"unit",
	"integration",
	"e2e",
]);

const TARGETED_QUERY_TERMS = new Set([
	"implementation",
	"implement",
	"definition",
	"body",
	"source",
	"code",
]);

const DOC_PATH_HINTS = new Set([
	"docs",
	"doc",
	"readme",
	"changelog",
	"license",
	"adr",
]);

const DOC_QUERY_TERMS = new Set([
	"docs",
	"documentation",
	"readme",
	"changelog",
	"design",
	"adr",
]);

const NEIGHBOR_QUERY_TERMS = new Set([
	"related",
	"impact",
	"touches",
	"dependencies",
	"callers",
	"usage",
	"where else",
]);

const TOKEN_FIRST_MODE = process.env.AI_CONTEXT_TOKEN_FIRST !== "0";
const TOKEN_FIRST_SINGLE_PIVOT =
	process.env.AI_CONTEXT_TOKEN_FIRST_SINGLE_PIVOT !== "0";

const dbStateByWorkspace = new Map();
const indexByWorkspace = new Map();
const metricsByWorkspace = new Map();
const refreshStateByWorkspace = new Map();
const indexPerfByWorkspace = new Map();

function getMetrics(workspaceRoot) {
	if (!metricsByWorkspace.has(workspaceRoot)) {
		metricsByWorkspace.set(workspaceRoot, {
			totalQueries: 0,
			cacheHits: 0,
			cacheMisses: 0,
			lastQueryLatencyMs: null,
			latencySamplesMs: [],
			totalLatencyMs: 0,
			averageLatencyMs: null,
			lastUsedTokens: null,
			totalTokenReductionPct: 0,
			averageTokenReductionPct: null,
			lastTokenReductionPct: null,
			lastCandidateMode: null,
			modeBreakdown: {
				debug: {
					queries: 0,
					cacheHits: 0,
					cacheMisses: 0,
					totalLatencyMs: 0,
					averageLatencyMs: null,
				},
				refactor: {
					queries: 0,
					cacheHits: 0,
					cacheMisses: 0,
					totalLatencyMs: 0,
					averageLatencyMs: null,
				},
				feature: {
					queries: 0,
					cacheHits: 0,
					cacheMisses: 0,
					totalLatencyMs: 0,
					averageLatencyMs: null,
				},
				explore: {
					queries: 0,
					cacheHits: 0,
					cacheMisses: 0,
					totalLatencyMs: 0,
					averageLatencyMs: null,
				},
			},
		});
	}
	return metricsByWorkspace.get(workspaceRoot);
}

function percentile(values, p) {
	if (!values || values.length === 0) {
		return null;
	}
	const sorted = [...values].sort((a, b) => a - b);
	const idx = Math.min(
		sorted.length - 1,
		Math.max(0, Math.ceil((p / 100) * sorted.length) - 1),
	);
	return sorted[idx];
}

function inferTaskMode(task) {
	const t = (task || "").toLowerCase();
	if (/bug|fix|error|exception|crash|failing|failure|stack/.test(t)) {
		return "debug";
	}
	if (/refactor|rename|extract|cleanup|restructure|modular/.test(t)) {
		return "refactor";
	}
	if (/add|implement|feature|new endpoint|create|build/.test(t)) {
		return "feature";
	}
	return "explore";
}

function snapshotMetrics(workspaceRoot) {
	const m = getMetrics(workspaceRoot);
	const cacheHitRate =
		m.totalQueries > 0
			? Number(((m.cacheHits / m.totalQueries) * 100).toFixed(2))
			: 0;
	const p50LatencyMs = percentile(m.latencySamplesMs, 50);
	const p95LatencyMs = percentile(m.latencySamplesMs, 95);

	const modeBreakdown = Object.fromEntries(
		Object.entries(m.modeBreakdown).map(([mode, stats]) => {
			const hitRate =
				stats.queries > 0
					? Number(((stats.cacheHits / stats.queries) * 100).toFixed(2))
					: 0;
			return [
				mode,
				{
					queries: stats.queries,
					cacheHits: stats.cacheHits,
					cacheMisses: stats.cacheMisses,
					cacheHitRate: hitRate,
					averageLatencyMs: stats.averageLatencyMs,
				},
			];
		}),
	);

	return {
		totalQueries: m.totalQueries,
		cacheHits: m.cacheHits,
		cacheMisses: m.cacheMisses,
		cacheHitRate,
		lastQueryLatencyMs: m.lastQueryLatencyMs,
		averageLatencyMs: m.averageLatencyMs,
		p50LatencyMs,
		p95LatencyMs,
		lastUsedTokens: m.lastUsedTokens,
		lastTokenReductionPct: m.lastTokenReductionPct,
		averageTokenReductionPct: m.averageTokenReductionPct,
		lastCandidateMode: m.lastCandidateMode,
		modeBreakdown,
	};
}

function snapshotIndexerMetrics(workspaceRoot) {
	return (
		indexPerfByWorkspace.get(workspaceRoot) || {
			lastBuildAt: null,
			totalBuildMs: null,
			walkMs: null,
			statMs: null,
			parseMs: null,
			dbWriteMs: null,
			graphMs: null,
			queueFiles: 0,
			queueBytes: 0,
			parsedFiles: 0,
			workerMode: "none",
			workerCount: 0,
			workerBatchCount: 0,
			workerBatchTargetBytes: 0,
		}
	);
}

function recordQueryMetrics(
	workspaceRoot,
	{ cache, latencyMs, usedTokens, candidateMode, taskMode, tokenReductionPct },
) {
	const m = getMetrics(workspaceRoot);
	m.totalQueries += 1;
	if (cache === "hit") {
		m.cacheHits += 1;
	} else {
		m.cacheMisses += 1;
	}
	m.lastQueryLatencyMs = latencyMs;
	m.latencySamplesMs.push(latencyMs);
	if (m.latencySamplesMs.length > LATENCY_SAMPLE_WINDOW) {
		m.latencySamplesMs.shift();
	}
	m.totalLatencyMs += latencyMs;
	m.averageLatencyMs = Number((m.totalLatencyMs / m.totalQueries).toFixed(2));
	m.lastUsedTokens = usedTokens;
	m.lastTokenReductionPct = tokenReductionPct;
	m.totalTokenReductionPct += tokenReductionPct;
	m.averageTokenReductionPct = Number(
		(m.totalTokenReductionPct / m.totalQueries).toFixed(2),
	);
	m.lastCandidateMode = candidateMode || null;

	const mode = taskMode && m.modeBreakdown[taskMode] ? taskMode : "explore";
	const mm = m.modeBreakdown[mode];
	mm.queries += 1;
	if (cache === "hit") {
		mm.cacheHits += 1;
	} else {
		mm.cacheMisses += 1;
	}
	mm.totalLatencyMs += latencyMs;
	mm.averageLatencyMs = Number((mm.totalLatencyMs / mm.queries).toFixed(2));
}

function sha1(text) {
	return crypto.createHash("sha1").update(text).digest("hex");
}

function toWords(text) {
	return (text.toLowerCase().match(/[a-z0-9_]+/g) || []).filter(
		w => w.length > 1,
	);
}

function toTermFrequency(text) {
	const tf = {};
	for (const word of toWords(text)) {
		tf[word] = (tf[word] || 0) + 1;
	}
	return tf;
}

function estimateTokens(text) {
	return Math.ceil(text.length / 4);
}

function isLikelyTextPath(relativePath) {
	if (isLikelyGeneratedArtifactPath(relativePath)) {
		return false;
	}

	const ext = path.extname(relativePath).toLowerCase();
	if (!ext) {
		return true;
	}
	return TEXT_EXTENSIONS.has(ext);
}

function splitPathSegments(relativePath) {
	return relativePath.toLowerCase().split("/").filter(Boolean);
}

function isLikelyGeneratedArtifactPath(relativePath) {
	const segments = splitPathSegments(relativePath);
	for (const segment of segments) {
		if (GENERATED_ARTIFACT_PATH_HINTS.has(segment)) {
			return true;
		}
	}

	const basename = path.posix.basename(relativePath.toLowerCase());
	if (
		/^(lcov(\.info)?|coverage(-final)?|junit|test-results|playwright-report|allure-results)/.test(
			basename,
		)
	) {
		return true;
	}

	return false;
}

function queryWantsGeneratedArtifacts(querySet) {
	for (const term of GENERATED_QUERY_TERMS) {
		if (querySet.has(term)) {
			return true;
		}
	}
	return false;
}

function queryWantsTests(querySet) {
	for (const term of TEST_QUERY_TERMS) {
		if (querySet.has(term)) {
			return true;
		}
	}
	return false;
}

function queryWantsDocs(querySet) {
	for (const term of DOC_QUERY_TERMS) {
		if (querySet.has(term)) {
			return true;
		}
	}
	return false;
}

function queryWantsNeighbors(querySet) {
	for (const term of NEIGHBOR_QUERY_TERMS) {
		if (querySet.has(term)) {
			return true;
		}
	}
	return false;
}

function isLikelyTestPath(relativePath) {
	const segments = splitPathSegments(relativePath);
	for (const segment of segments) {
		if (TEST_PATH_HINTS.has(segment)) {
			return true;
		}
	}

	const basename = path.posix.basename(relativePath.toLowerCase());
	return /\.(test|spec)\.[a-z0-9]+$/.test(basename);
}

function isLikelyDocPath(relativePath) {
	const segments = splitPathSegments(relativePath);
	for (const segment of segments) {
		if (DOC_PATH_HINTS.has(segment)) {
			return true;
		}
	}

	const ext = path.extname(relativePath).toLowerCase();
	if ([".md", ".txt", ".rst", ".adoc"].includes(ext)) {
		return true;
	}

	const basename = path.posix.basename(relativePath.toLowerCase());
	return /^(readme|changelog|license|contributing)/.test(basename);
}

function getPathQualityScore(relativePath, querySet) {
	const segments = splitPathSegments(relativePath);
	let score = 0;

	for (const segment of segments) {
		if (SOURCE_PATH_HINTS.has(segment)) {
			score += 0.8;
		}
	}

	if (isJsTsPath(relativePath)) {
		score += 1.1;
	}

	if (
		isLikelyGeneratedArtifactPath(relativePath) &&
		!queryWantsGeneratedArtifacts(querySet)
	) {
		score -= 8;
	}

	if (isLikelyTestPath(relativePath) && !queryWantsTests(querySet)) {
		score -= 4;
	}

	if (isLikelyDocPath(relativePath) && !queryWantsDocs(querySet)) {
		score -= 7;
	}

	return score;
}

function extractQuerySymbols(query) {
	const matches = String(query || "").match(/[A-Za-z_][A-Za-z0-9_]*/g) || [];
	const symbols = new Set();

	for (const token of matches) {
		if (token.length < 4) {
			continue;
		}
		const looksLikeSymbol =
			/[A-Z]/.test(token) ||
			token.includes("_") ||
			/^[a-z]+(?:[A-Z][a-z0-9]*)+$/.test(token);
		if (looksLikeSymbol) {
			symbols.add(token);
		}
	}

	return Array.from(symbols);
}

function extractQueryFileHints(query) {
	const matches =
		String(query || "").match(
			/[A-Za-z0-9_./-]+\.(?:ts|tsx|js|jsx|py|java|go|rs|cs|cpp|c|h)/g,
		) || [];

	return Array.from(new Set(matches.map(m => m.toLowerCase())));
}

function queryLooksImplementationFocused(query, querySet) {
	const q = String(query || "").toLowerCase();
	if (
		/\b(function body|implementation|definition|source code|show code|show implementation)\b/.test(
			q,
		)
	) {
		return true;
	}

	for (const term of TARGETED_QUERY_TERMS) {
		if (querySet.has(term)) {
			return true;
		}
	}

	return false;
}

function matchesFileHints(relativePath, fileHints) {
	if (!fileHints || fileHints.length === 0) {
		return false;
	}

	const rp = String(relativePath || "").toLowerCase();
	const basename = path.posix.basename(rp);

	for (const hint of fileHints) {
		const normalizedHint = hint.replace(/\\/g, "/").toLowerCase();
		const hintBase = path.posix.basename(normalizedHint);
		if (rp.includes(normalizedHint) || basename === hintBase) {
			return true;
		}
	}

	return false;
}

function getFileHintBoost(relativePath, fileHints) {
	return matchesFileHints(relativePath, fileHints) ? 18 : 0;
}

function scoreDefinitionBoost(chunkText, querySymbols) {
	if (!querySymbols || querySymbols.length === 0) {
		return 0;
	}

	let boost = 0;
	for (const symbol of querySymbols) {
		const escaped = symbol.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
		const definitionPatterns = [
			new RegExp(`\\b(?:async\\s+)?function\\s+${escaped}\\b`, "i"),
			new RegExp(
				`\\b(?:const|let|var)\\s+${escaped}\\s*=\\s*(?:async\\s*)?\\(`,
				"i",
			),
			new RegExp(`\\bclass\\s+${escaped}\\b`, "i"),
			new RegExp(`\\b${escaped}\\s*:\\s*(?:async\\s*)?\\(`, "i"),
		];
		const usagePattern = new RegExp(`\\b${escaped}\\s*\\(`, "i");

		if (definitionPatterns.some(rx => rx.test(chunkText))) {
			boost += 24;
			continue;
		}

		if (usagePattern.test(chunkText)) {
			boost += 3;
		}
	}

	return boost;
}

function isJsTsPath(relativePath) {
	const ext = path.extname(relativePath).toLowerCase();
	return ext === ".js" || ext === ".jsx" || ext === ".ts" || ext === ".tsx";
}

function chunkByLines(text) {
	const lines = text.split(/\r?\n/);
	const chunks = [];

	let lineStart = 0;
	let chunkIndex = 0;
	while (lineStart < lines.length) {
		const lineEndExclusive = Math.min(lines.length, lineStart + CHUNK_LINES);
		const chunkText = lines
			.slice(lineStart, lineEndExclusive)
			.join("\n")
			.trim();
		if (chunkText) {
			chunks.push({
				chunkIndex,
				startLine: lineStart + 1,
				endLine: lineEndExclusive,
				text: chunkText,
				tf: toTermFrequency(chunkText),
			});
			chunkIndex += 1;
		}

		if (lineEndExclusive === lines.length) {
			break;
		}
		lineStart = Math.max(lineStart + 1, lineEndExclusive - CHUNK_OVERLAP);
	}

	return chunks;
}

function scoreChunk(
	queryTerms,
	querySet,
	querySymbols,
	queryFileHints,
	chunk,
	relativePath,
) {
	let keywordHits = 0;
	for (const term of queryTerms) {
		keywordHits += chunk.tf[term] || 0;
	}

	const chunkTerms = Object.keys(chunk.tf);
	let overlap = 0;
	for (const term of chunkTerms) {
		if (querySet.has(term)) {
			overlap += 1;
		}
	}

	const denominator = Math.max(1, querySet.size + chunkTerms.length - overlap);
	const jaccard = overlap / denominator;

	const filePathWords = new Set(toWords(relativePath));
	let pathMatches = 0;
	for (const term of querySet) {
		if (filePathWords.has(term)) {
			pathMatches += 1;
		}
	}

	const pathQuality = getPathQualityScore(relativePath, querySet);
	const definitionBoost = scoreDefinitionBoost(chunk.text, querySymbols);
	const fileHintBoost = getFileHintBoost(relativePath, queryFileHints);
	return (
		keywordHits * 1.8 +
		jaccard * 12 +
		pathMatches * 2.5 +
		pathQuality +
		definitionBoost +
		fileHintBoost
	);
}

function compactSnippet(text, maxLines = 48) {
	const normalized = text.replace(/\r\n/g, "\n");
	const lines = normalized.split("\n");

	let importLines = 0;
	while (
		importLines < lines.length &&
		/^\s*(import|export)\b/.test(lines[importLines])
	) {
		importLines += 1;
	}

	let compacted = lines;
	if (importLines > 10) {
		const keptHead = lines.slice(0, 6);
		const rest = lines.slice(importLines);
		compacted = [
			...keptHead,
			`// ... ${importLines - 6} import/export lines omitted ...`,
			...rest,
		];
	}

	const noExtraBlanks = [];
	let lastBlank = false;
	for (const line of compacted) {
		const isBlank = line.trim().length === 0;
		if (isBlank && lastBlank) {
			continue;
		}
		noExtraBlanks.push(line);
		lastBlank = isBlank;
	}

	let limited = noExtraBlanks;
	if (limited.length > maxLines) {
		const removed = limited.length - maxLines;
		limited = [
			...limited.slice(0, maxLines - 1),
			`// ... ${removed} lines omitted ...`,
		];
	}

	return limited.join("\n").trim();
}

function normalizeTask(task) {
	return task.toLowerCase().replace(/\s+/g, " ").trim();
}

function extractJsTsModuleRefs(text) {
	const refs = new Set();
	const importExportRegex =
		/(?:import|export)\s+(?:[^'";]+\s+from\s+)?['"]([^'"]+)['"]/g;
	const requireRegex = /require\(\s*['"]([^'"]+)['"]\s*\)/g;

	let m;
	while ((m = importExportRegex.exec(text)) !== null) {
		refs.add(m[1]);
	}
	while ((m = requireRegex.exec(text)) !== null) {
		refs.add(m[1]);
	}
	return Array.from(refs);
}

function extractTopLevelSymbols(text) {
	const symbols = [];
	const regexes = [
		/export\s+(?:async\s+)?function\s+([A-Za-z0-9_]+)/g,
		/(?:^|\n)\s*(?:async\s+)?function\s+([A-Za-z0-9_]+)/g,
		/export\s+class\s+([A-Za-z0-9_]+)/g,
		/(?:^|\n)\s*class\s+([A-Za-z0-9_]+)/g,
		/export\s+(?:const|let|var)\s+([A-Za-z0-9_]+)/g,
		/(?:^|\n)\s*(?:const|let|var)\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\(/g,
	];

	for (const rx of regexes) {
		let m;
		while ((m = rx.exec(text)) !== null) {
			symbols.push(m[1]);
		}
	}

	return Array.from(new Set(symbols)).slice(0, 30);
}

function buildFileSkeleton(relativePath, symbols) {
	if (!symbols || symbols.length === 0) {
		return `file ${relativePath}\n(no extracted top-level symbols)`;
	}
	const lines = [`file ${relativePath}`];
	for (const symbol of symbols.slice(0, 20)) {
		lines.push(`- ${symbol}()`);
	}
	return lines.join("\n");
}

function normalizeModuleSpecifier(specifier) {
	if (!specifier) {
		return null;
	}
	if (!specifier.startsWith(".") && !specifier.startsWith("/")) {
		return null;
	}
	return specifier;
}

function resolveInternalImport(sourceFile, specifier, fileSet) {
	const normalizedSpecifier = normalizeModuleSpecifier(specifier);
	if (!normalizedSpecifier) {
		return null;
	}

	const sourceDir = path.posix.dirname(sourceFile.replace(/\\/g, "/"));
	const base = path.posix.normalize(
		path.posix.join(sourceDir, normalizedSpecifier),
	);
	const candidates = [
		base,
		`${base}.ts`,
		`${base}.tsx`,
		`${base}.js`,
		`${base}.jsx`,
		`${base}.mjs`,
		`${base}.cjs`,
		`${base}/index.ts`,
		`${base}/index.tsx`,
		`${base}/index.js`,
		`${base}/index.jsx`,
	];

	for (const candidate of candidates) {
		if (fileSet.has(candidate)) {
			return candidate;
		}
	}
	return null;
}

function buildDependencyGraph(files) {
	const fileSet = new Set(files.map(f => f.relativePath));
	const outgoing = {};
	const incoming = {};

	for (const file of files) {
		outgoing[file.relativePath] = [];
		incoming[file.relativePath] = [];
	}

	for (const file of files) {
		if (!isJsTsPath(file.relativePath) || !Array.isArray(file.rawImports)) {
			continue;
		}

		const deps = new Set();
		for (const specifier of file.rawImports) {
			const target = resolveInternalImport(
				file.relativePath,
				specifier,
				fileSet,
			);
			if (target && target !== file.relativePath) {
				deps.add(target);
			}
		}

		outgoing[file.relativePath] = Array.from(deps);
		for (const dep of deps) {
			incoming[dep].push(file.relativePath);
		}
	}

	return { outgoing, incoming };
}

function getGitHead(workspaceRoot) {
	try {
		return execSync("git rev-parse HEAD", {
			cwd: workspaceRoot,
			stdio: ["ignore", "pipe", "ignore"],
			encoding: "utf8",
		}).trim();
	} catch {
		return null;
	}
}

function getWorkspaceFingerprint(workspaceRoot) {
	const gitHead = getGitHead(workspaceRoot);
	if (gitHead) {
		try {
			const trackedChanges = execSync(
				"git status --porcelain --untracked-files=no",
				{
					cwd: workspaceRoot,
					stdio: ["ignore", "pipe", "ignore"],
					encoding: "utf8",
				},
			).trim();
			return `git:${sha1(`${gitHead}\n${trackedChanges}`)}`;
		} catch {
			return `git:${sha1(gitHead)}`;
		}
	}

	try {
		const names = execSync("ls -1A", {
			cwd: workspaceRoot,
			stdio: ["ignore", "pipe", "ignore"],
			encoding: "utf8",
		})
			.split("\n")
			.filter(Boolean)
			.filter(n => !SKIP_DIRS.has(n))
			.sort();

		const sample = names.slice(0, 300).join("\n");
		return `fs:${sha1(sample)}`;
	} catch {
		return "fs:unknown";
	}
}

async function walkWorkspace(rootDir) {
	const stack = [rootDir];
	const files = [];

	while (stack.length > 0 && files.length < MAX_FILES) {
		const current = stack.pop();
		const entries = await fs.readdir(current, { withFileTypes: true });

		for (const entry of entries) {
			const abs = path.join(current, entry.name);
			const rel = path.relative(rootDir, abs).replace(/\\/g, "/");

			if (entry.isDirectory()) {
				if (!SKIP_DIRS.has(entry.name)) {
					stack.push(abs);
				}
				continue;
			}

			if (!entry.isFile()) {
				continue;
			}

			if (!isLikelyTextPath(rel)) {
				continue;
			}

			files.push({ abs, rel });
			if (files.length >= MAX_FILES) {
				break;
			}
		}
	}

	return files;
}

async function ensureSqliteState(workspaceRoot) {
	if (!DatabaseSync) {
		return null;
	}

	if (dbStateByWorkspace.has(workspaceRoot)) {
		return dbStateByWorkspace.get(workspaceRoot);
	}

	const dataDir = path.join(workspaceRoot, CACHE_DIR_NAME);
	await fs.mkdir(dataDir, { recursive: true });
	const dbPath = path.join(dataDir, "index.db");

	const db = new DatabaseSync(dbPath);
	db.exec("PRAGMA journal_mode = WAL;");
	db.exec("PRAGMA synchronous = NORMAL;");
	db.exec("PRAGMA temp_store = MEMORY;");

	db.exec(`
CREATE TABLE IF NOT EXISTS files (
  relative_path TEXT PRIMARY KEY,
  mtime_ms INTEGER NOT NULL,
  size_bytes INTEGER NOT NULL,
  content_hash TEXT NOT NULL,
  symbols_json TEXT NOT NULL,
  raw_imports_json TEXT NOT NULL,
  skeleton TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chunks (
  relative_path TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  start_line INTEGER NOT NULL,
  end_line INTEGER NOT NULL,
  text TEXT NOT NULL,
  tf_json TEXT NOT NULL,
  PRIMARY KEY (relative_path, chunk_index)
);
CREATE TABLE IF NOT EXISTS edges (
  src TEXT NOT NULL,
  dst TEXT NOT NULL,
  PRIMARY KEY (src, dst)
);
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS query_cache (
  cache_key TEXT PRIMARY KEY,
  created_at INTEGER NOT NULL,
  index_signature TEXT NOT NULL,
  git_head TEXT,
  result_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_query_cache_created_at ON query_cache(created_at);
`);

	let hasFts = true;
	try {
		db.exec(`
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  relative_path UNINDEXED,
  chunk_index UNINDEXED,
  start_line UNINDEXED,
  end_line UNINDEXED,
  text
);
`);
	} catch {
		hasFts = false;
	}

	const state = { db, hasFts };
	dbStateByWorkspace.set(workspaceRoot, state);
	return state;
}

function loadFileChunksFromDb(db, relativePath) {
	const rows = db
		.prepare(
			"SELECT chunk_index, start_line, end_line, text, tf_json FROM chunks WHERE relative_path = ? ORDER BY chunk_index ASC",
		)
		.all(relativePath);

	return rows.map(row => ({
		chunkIndex: row.chunk_index,
		startLine: row.start_line,
		endLine: row.end_line,
		text: row.text,
		tf: JSON.parse(row.tf_json),
	}));
}

function loadGraphFromDb(db, files) {
	const outgoing = {};
	const incoming = {};

	for (const file of files) {
		outgoing[file.relativePath] = [];
		incoming[file.relativePath] = [];
	}

	const edgeRows = db.prepare("SELECT src, dst FROM edges").all();
	for (const row of edgeRows) {
		if (outgoing[row.src]) {
			outgoing[row.src].push(row.dst);
		}
		if (incoming[row.dst]) {
			incoming[row.dst].push(row.src);
		}
	}

	return { outgoing, incoming };
}

function loadMetaValue(db, key, fallback = null) {
	const row = db.prepare("SELECT value FROM meta WHERE key = ?").get(key);
	return row ? row.value : fallback;
}

async function loadIndexFromSqliteSnapshot(workspaceRoot) {
	const sqliteState = await ensureSqliteState(workspaceRoot);
	if (!sqliteState) {
		return null;
	}

	const db = sqliteState.db;
	const rows = db.prepare("SELECT * FROM files").all();
	if (!rows || rows.length === 0) {
		return null;
	}

	const files = rows.map(row => ({
		relativePath: row.relative_path,
		mtimeMs: row.mtime_ms,
		sizeBytes: row.size_bytes,
		contentHash: row.content_hash,
		chunks: [],
		symbols: JSON.parse(row.symbols_json),
		rawImports: JSON.parse(row.raw_imports_json),
		skeleton: row.skeleton,
	}));

	const graph = loadGraphFromDb(db, files);
	const indexSignature = loadMetaValue(
		db,
		"indexSignature",
		computeIndexSignature(files),
	);
	const generatedAt = loadMetaValue(
		db,
		"generatedAt",
		new Date(0).toISOString(),
	);
	const workspaceFingerprint = loadMetaValue(db, "workspaceFingerprint", null);

	return {
		version: INDEX_VERSION,
		generatedAt,
		workspaceRoot,
		files,
		graph,
		indexSignature,
		workspaceFingerprint,
		sqlite: { enabled: true, hasFts: Boolean(sqliteState.hasFts) },
	};
}

function computeIndexSignature(files) {
	const pairs = files
		.map(file => `${file.relativePath}:${file.contentHash}`)
		.sort()
		.join("\n");
	return sha1(pairs);
}

function persistEdges(db, graph) {
	db.prepare("DELETE FROM edges").run();
	const insert = db.prepare(
		"INSERT OR REPLACE INTO edges(src, dst) VALUES(?, ?)",
	);
	for (const [src, deps] of Object.entries(graph.outgoing || {})) {
		for (const dst of deps) {
			insert.run(src, dst);
		}
	}
}

function parseTextForIndex(relativePath, text) {
	if (!text || text.includes("\u0000")) {
		return null;
	}

	const chunks = chunkByLines(text);
	if (chunks.length === 0) {
		return null;
	}

	const symbols = extractTopLevelSymbols(text);
	const rawImports = isJsTsPath(relativePath)
		? extractJsTsModuleRefs(text)
		: [];
	const skeleton = buildFileSkeleton(relativePath, symbols);

	return {
		contentHash: sha1(text),
		chunks,
		symbols,
		rawImports,
		skeleton,
	};
}

async function parseFileInProcess(item) {
	let text;
	try {
		text = await fs.readFile(item.abs, "utf8");
	} catch {
		return { order: item.order, skipped: true };
	}

	const parsed = parseTextForIndex(item.rel, text);
	if (!parsed) {
		return { order: item.order, skipped: true };
	}

	return {
		order: item.order,
		relativePath: item.rel,
		mtimeMs: item.mtimeMs,
		sizeBytes: item.sizeBytes,
		...parsed,
	};
}

function getWorkerCount(fileCount, totalBytes) {
	const cpuCount =
		typeof os.availableParallelism === "function"
			? os.availableParallelism()
			: os.cpus().length;
	const cpuBound =
		Number.isFinite(WORKER_COUNT_OVERRIDE) && WORKER_COUNT_OVERRIDE > 0
			? Math.min(MAX_INDEX_WORKERS, WORKER_COUNT_OVERRIDE)
			: Math.max(1, Math.min(MAX_INDEX_WORKERS, cpuCount - 1));
	const byteBound = Math.max(
		1,
		Math.ceil(totalBytes / TARGET_BYTES_PER_WORKER),
	);
	const target = Math.min(cpuBound, byteBound);
	return Math.max(1, Math.min(target, fileCount));
}

function splitParseQueueByBytes(parseQueue, batchCount) {
	if (batchCount <= 1 || parseQueue.length <= 1) {
		return [parseQueue];
	}

	const totalBytes = parseQueue.reduce((sum, item) => sum + item.sizeBytes, 0);
	const targetBytes = Math.max(1, Math.ceil(totalBytes / batchCount));
	const batches = [];
	let current = [];
	let currentBytes = 0;

	for (let i = 0; i < parseQueue.length; i += 1) {
		const item = parseQueue[i];
		const remainingItems = parseQueue.length - i - 1;
		const remainingBatches = batchCount - batches.length - 1;

		current.push(item);
		currentBytes += item.sizeBytes;

		const shouldCloseByBytes = currentBytes >= targetBytes;
		const shouldCloseByShape = remainingItems >= remainingBatches;
		if (shouldCloseByBytes && shouldCloseByShape) {
			batches.push(current);
			current = [];
			currentBytes = 0;
		}
	}

	if (current.length > 0) {
		batches.push(current);
	}

	return batches.length > 0 ? batches : [parseQueue];
}

function runParseWorkerBatch(batch) {
	const workerPath = path.join(__dirname, "index-worker.js");

	return new Promise((resolve, reject) => {
		const worker = new Worker(workerPath, {
			workerData: {
				items: batch,
				chunkLines: CHUNK_LINES,
				chunkOverlap: CHUNK_OVERLAP,
			},
		});

		let settled = false;
		worker.once("message", message => {
			if (settled) {
				return;
			}
			settled = true;
			if (message && Array.isArray(message.results)) {
				resolve(message.results);
				return;
			}
			reject(new Error("worker returned invalid payload"));
		});

		worker.once("error", error => {
			if (!settled) {
				settled = true;
				reject(error);
			}
		});

		worker.once("exit", code => {
			if (!settled && code !== 0) {
				settled = true;
				reject(new Error(`worker exited with code ${code}`));
			}
		});
	});
}

async function parseFilesForIndex(parseQueue) {
	if (parseQueue.length === 0) {
		return {
			results: [],
			stats: {
				mode: "none",
				queueFiles: 0,
				queueBytes: 0,
				workerCount: 0,
				workerBatchCount: 0,
				workerBatchTargetBytes: 0,
				durationMs: 0,
			},
		};
	}

	const queueBytes = parseQueue.reduce((sum, item) => sum + item.sizeBytes, 0);
	const parseStart = Date.now();

	if (
		parseQueue.length < MIN_FILES_FOR_WORKERS &&
		queueBytes < MIN_BYTES_FOR_WORKERS
	) {
		const results = await Promise.all(parseQueue.map(parseFileInProcess));
		results.sort((a, b) => a.order - b.order);
		return {
			results,
			stats: {
				mode: "in-process",
				queueFiles: parseQueue.length,
				queueBytes,
				workerCount: 0,
				workerBatchCount: 0,
				workerBatchTargetBytes: 0,
				durationMs: Date.now() - parseStart,
			},
		};
	}

	const workerCount = getWorkerCount(parseQueue.length, queueBytes);
	const batches = splitParseQueueByBytes(parseQueue, workerCount);
	const workerBatchTargetBytes = Math.max(
		1,
		Math.ceil(queueBytes / workerCount),
	);

	try {
		const batchResults = await Promise.all(
			batches.map(batch => runParseWorkerBatch(batch)),
		);
		const results = batchResults.flat();
		results.sort((a, b) => a.order - b.order);
		return {
			results,
			stats: {
				mode: "workers",
				queueFiles: parseQueue.length,
				queueBytes,
				workerCount,
				workerBatchCount: batches.length,
				workerBatchTargetBytes,
				durationMs: Date.now() - parseStart,
			},
		};
	} catch {
		const results = await Promise.all(parseQueue.map(parseFileInProcess));
		results.sort((a, b) => a.order - b.order);
		return {
			results,
			stats: {
				mode: "worker-fallback",
				queueFiles: parseQueue.length,
				queueBytes,
				workerCount,
				workerBatchCount: batches.length,
				workerBatchTargetBytes,
				durationMs: Date.now() - parseStart,
			},
		};
	}
}

async function buildIndex(workspaceRoot) {
	const buildStart = Date.now();
	const workspaceFingerprint = getWorkspaceFingerprint(workspaceRoot);
	const sqliteState = await ensureSqliteState(workspaceRoot);
	const db = sqliteState?.db || null;
	const hasFts = sqliteState?.hasFts || false;

	const walkStart = Date.now();
	const items = await walkWorkspace(workspaceRoot);
	const walkMs = Date.now() - walkStart;

	const files = [];
	const activePaths = new Set();
	const parseQueue = [];

	let existing = new Map();
	if (db) {
		const rows = db.prepare("SELECT * FROM files").all();
		existing = new Map(rows.map(row => [row.relative_path, row]));
	}

	const statStart = Date.now();
	let order = 0;
	for (const item of items) {
		let stat;
		try {
			stat = await fs.stat(item.abs);
		} catch {
			continue;
		}

		if (stat.size > MAX_FILE_BYTES) {
			continue;
		}

		activePaths.add(item.rel);
		const existingRow = existing.get(item.rel);

		if (
			existingRow &&
			existingRow.mtime_ms === Math.floor(stat.mtimeMs) &&
			existingRow.size_bytes === stat.size
		) {
			files.push({
				relativePath: item.rel,
				mtimeMs: Math.floor(stat.mtimeMs),
				sizeBytes: stat.size,
				contentHash: existingRow.content_hash,
				chunks: db ? [] : loadFileChunksFromDb(db, item.rel),
				symbols: JSON.parse(existingRow.symbols_json),
				rawImports: JSON.parse(existingRow.raw_imports_json),
				skeleton: existingRow.skeleton,
			});
			continue;
		}

		parseQueue.push({
			order,
			abs: item.abs,
			rel: item.rel,
			mtimeMs: Math.floor(stat.mtimeMs),
			sizeBytes: stat.size,
		});
		order += 1;
	}
	const statMs = Date.now() - statStart;

	const { results: parsedFiles, stats: parseStats } =
		await parseFilesForIndex(parseQueue);

	const dbWriteStart = Date.now();
	for (const parsed of parsedFiles) {
		if (parsed.skipped) {
			continue;
		}

		const existingRow = existing.get(parsed.relativePath);
		if (existingRow && existingRow.content_hash === parsed.contentHash && db) {
			db.prepare(
				"UPDATE files SET mtime_ms = ?, size_bytes = ? WHERE relative_path = ?",
			).run(parsed.mtimeMs, parsed.sizeBytes, parsed.relativePath);

			files.push({
				relativePath: parsed.relativePath,
				mtimeMs: parsed.mtimeMs,
				sizeBytes: parsed.sizeBytes,
				contentHash: existingRow.content_hash,
				chunks: [],
				symbols: JSON.parse(existingRow.symbols_json),
				rawImports: JSON.parse(existingRow.raw_imports_json),
				skeleton: existingRow.skeleton,
			});
			continue;
		}

		if (db) {
			db.prepare(
				`INSERT OR REPLACE INTO files(
          relative_path, mtime_ms, size_bytes, content_hash, symbols_json, raw_imports_json, skeleton
        ) VALUES(?, ?, ?, ?, ?, ?, ?)`,
			).run(
				parsed.relativePath,
				parsed.mtimeMs,
				parsed.sizeBytes,
				parsed.contentHash,
				JSON.stringify(parsed.symbols),
				JSON.stringify(parsed.rawImports),
				parsed.skeleton,
			);

			db.prepare("DELETE FROM chunks WHERE relative_path = ?").run(
				parsed.relativePath,
			);
			if (hasFts) {
				db.prepare("DELETE FROM chunks_fts WHERE relative_path = ?").run(
					parsed.relativePath,
				);
			}

			const insertChunk = db.prepare(
				"INSERT INTO chunks(relative_path, chunk_index, start_line, end_line, text, tf_json) VALUES(?, ?, ?, ?, ?, ?)",
			);
			const insertFts = hasFts
				? db.prepare(
						"INSERT INTO chunks_fts(relative_path, chunk_index, start_line, end_line, text) VALUES(?, ?, ?, ?, ?)",
					)
				: null;

			for (const chunk of parsed.chunks) {
				insertChunk.run(
					parsed.relativePath,
					chunk.chunkIndex,
					chunk.startLine,
					chunk.endLine,
					chunk.text,
					JSON.stringify(chunk.tf),
				);
				if (insertFts) {
					insertFts.run(
						parsed.relativePath,
						chunk.chunkIndex,
						chunk.startLine,
						chunk.endLine,
						chunk.text,
					);
				}
			}
		}

		files.push({
			relativePath: parsed.relativePath,
			mtimeMs: parsed.mtimeMs,
			sizeBytes: parsed.sizeBytes,
			contentHash: parsed.contentHash,
			chunks: db ? [] : parsed.chunks,
			symbols: parsed.symbols,
			rawImports: parsed.rawImports,
			skeleton: parsed.skeleton,
		});
	}

	if (db) {
		for (const relPath of existing.keys()) {
			if (activePaths.has(relPath)) {
				continue;
			}
			db.prepare("DELETE FROM files WHERE relative_path = ?").run(relPath);
			db.prepare("DELETE FROM chunks WHERE relative_path = ?").run(relPath);
			if (hasFts) {
				db.prepare("DELETE FROM chunks_fts WHERE relative_path = ?").run(
					relPath,
				);
			}
		}
	}
	const dbWriteMs = Date.now() - dbWriteStart;

	const graphStart = Date.now();
	const graph = buildDependencyGraph(files);
	if (db) {
		persistEdges(db, graph);
	}
	const graphMs = Date.now() - graphStart;

	const indexSignature = computeIndexSignature(files);
	const index = {
		version: INDEX_VERSION,
		generatedAt: new Date().toISOString(),
		workspaceRoot,
		files,
		graph,
		indexSignature,
		workspaceFingerprint,
		sqlite: { enabled: Boolean(db), hasFts },
	};

	if (db) {
		db.prepare(
			"INSERT OR REPLACE INTO meta(key, value) VALUES('indexVersion', ?)",
		).run(String(INDEX_VERSION));
		db.prepare(
			"INSERT OR REPLACE INTO meta(key, value) VALUES('indexSignature', ?)",
		).run(indexSignature);
		db.prepare(
			"INSERT OR REPLACE INTO meta(key, value) VALUES('generatedAt', ?)",
		).run(index.generatedAt);
		db.prepare(
			"INSERT OR REPLACE INTO meta(key, value) VALUES('workspaceFingerprint', ?)",
		).run(workspaceFingerprint);
	}

	indexPerfByWorkspace.set(workspaceRoot, {
		lastBuildAt: index.generatedAt,
		totalBuildMs: Date.now() - buildStart,
		walkMs,
		statMs,
		parseMs: parseStats.durationMs,
		dbWriteMs,
		graphMs,
		queueFiles: parseStats.queueFiles,
		queueBytes: parseStats.queueBytes,
		parsedFiles: parsedFiles.filter(p => !p.skipped).length,
		workerMode: parseStats.mode,
		workerCount: parseStats.workerCount,
		workerBatchCount: parseStats.workerBatchCount,
		workerBatchTargetBytes: parseStats.workerBatchTargetBytes,
	});

	indexByWorkspace.set(workspaceRoot, index);
	return index;
}

async function ensureIndex(workspaceRoot) {
	if (indexByWorkspace.has(workspaceRoot)) {
		return indexByWorkspace.get(workspaceRoot);
	}

	const snapshot = await loadIndexFromSqliteSnapshot(workspaceRoot);
	if (snapshot) {
		if (!snapshot.workspaceFingerprint) {
			const fp = getWorkspaceFingerprint(workspaceRoot);
			snapshot.workspaceFingerprint = fp;
			const db = dbStateByWorkspace.get(workspaceRoot)?.db;
			if (db) {
				db.prepare(
					"INSERT OR REPLACE INTO meta(key, value) VALUES('workspaceFingerprint', ?)",
				).run(fp);
			}
		}

		indexByWorkspace.set(workspaceRoot, snapshot);

		const generatedAtMs = Date.parse(snapshot.generatedAt);
		const isStale =
			!Number.isFinite(generatedAtMs) ||
			Date.now() - generatedAtMs > SNAPSHOT_STALE_MS;
		if (isStale && !refreshStateByWorkspace.get(workspaceRoot)) {
			const currentFingerprint = getWorkspaceFingerprint(workspaceRoot);
			const unchanged =
				snapshot.workspaceFingerprint &&
				currentFingerprint === snapshot.workspaceFingerprint;
			if (unchanged) {
				return snapshot;
			}

			refreshStateByWorkspace.set(workspaceRoot, true);
			buildIndex(workspaceRoot)
				.catch(() => {
					// Keep serving stale-but-fast snapshot if background refresh fails.
				})
				.finally(() => {
					refreshStateByWorkspace.set(workspaceRoot, false);
				});
		}

		return snapshot;
	}

	return buildIndex(workspaceRoot);
}

function getFallbackChunksFromDb(index, queryTerms) {
	const sqliteState = dbStateByWorkspace.get(index.workspaceRoot);
	if (!sqliteState || !sqliteState.db) {
		return [];
	}

	const db = sqliteState.db;
	const terms = queryTerms.filter(t => t.length >= 3).slice(0, 6);
	if (terms.length === 0) {
		return [];
	}

	const where = terms
		.map(() => "(text LIKE ? OR relative_path LIKE ?)")
		.join(" OR ");
	const params = [];
	for (const term of terms) {
		const like = `%${term}%`;
		params.push(like, like);
	}

	try {
		const sql = `SELECT relative_path, chunk_index, start_line, end_line, text FROM chunks WHERE ${where} LIMIT ?`;
		const rows = db.prepare(sql).all(...params, MAX_RETRIEVAL_CANDIDATES);
		return rows.map(row => ({
			relativePath: row.relative_path,
			chunkIndex: row.chunk_index,
			startLine: row.start_line,
			endLine: row.end_line,
			text: row.text,
			tf: toTermFrequency(row.text),
		}));
	} catch {
		return [];
	}
}

function getSymbolMatchedFiles(index, querySymbols) {
	if (!Array.isArray(querySymbols) || querySymbols.length === 0) {
		return [];
	}

	const symbolSet = new Set(querySymbols.map(s => s.toLowerCase()));
	const matches = [];

	for (const file of index.files) {
		if (!Array.isArray(file.symbols) || file.symbols.length === 0) {
			continue;
		}
		if (
			file.symbols.some(symbol => symbolSet.has(String(symbol).toLowerCase()))
		) {
			matches.push(file.relativePath);
		}
	}

	return matches.slice(0, 12);
}

function getChunksForFilesFromDb(index, relativePaths, perFileLimit = 8) {
	if (!Array.isArray(relativePaths) || relativePaths.length === 0) {
		return [];
	}

	const sqliteState = dbStateByWorkspace.get(index.workspaceRoot);
	if (!sqliteState || !sqliteState.db) {
		return [];
	}

	const db = sqliteState.db;
	const all = [];

	try {
		const stmt = db.prepare(
			"SELECT relative_path, chunk_index, start_line, end_line, text FROM chunks WHERE relative_path = ? ORDER BY chunk_index ASC LIMIT ?",
		);
		for (const relPath of relativePaths) {
			const rows = stmt.all(relPath, perFileLimit);
			for (const row of rows) {
				all.push({
					relativePath: row.relative_path,
					chunkIndex: row.chunk_index,
					startLine: row.start_line,
					endLine: row.end_line,
					text: row.text,
					tf: toTermFrequency(row.text),
				});
			}
		}
		return all;
	} catch {
		return [];
	}
}

function getChunkWindowFromDb(
	index,
	relativePath,
	startChunkIndex,
	endChunkIndex,
) {
	const sqliteState = dbStateByWorkspace.get(index.workspaceRoot);
	if (!sqliteState || !sqliteState.db) {
		return [];
	}

	try {
		const rows = sqliteState.db
			.prepare(
				"SELECT relative_path, chunk_index, start_line, end_line, text FROM chunks WHERE relative_path = ? AND chunk_index >= ? AND chunk_index <= ? ORDER BY chunk_index ASC",
			)
			.all(relativePath, startChunkIndex, endChunkIndex);

		return rows.map(row => ({
			relativePath: row.relative_path,
			chunkIndex: row.chunk_index,
			startLine: row.start_line,
			endLine: row.end_line,
			text: row.text,
			tf: toTermFrequency(row.text),
		}));
	} catch {
		return [];
	}
}

function getChunkWindow(index, fileMap, hit, before = 0, after = 1) {
	if (!hit || !Number.isInteger(hit.chunkIndex)) {
		return [];
	}

	const startIdx = Math.max(0, hit.chunkIndex - before);
	const endIdx = Math.max(startIdx, hit.chunkIndex + after);

	const file = fileMap[hit.relativePath];
	if (file && Array.isArray(file.chunks) && file.chunks.length > 0) {
		const fromMemory = file.chunks
			.filter(
				chunk =>
					Number.isInteger(chunk.chunkIndex) &&
					chunk.chunkIndex >= startIdx &&
					chunk.chunkIndex <= endIdx,
			)
			.sort((a, b) => a.chunkIndex - b.chunkIndex);

		if (fromMemory.length > 0) {
			return fromMemory;
		}
	}

	return getChunkWindowFromDb(index, hit.relativePath, startIdx, endIdx);
}

function mergeChunkWindowTexts(window) {
	if (!Array.isArray(window) || window.length === 0) {
		return "";
	}

	let merged = [];
	for (const chunk of window) {
		const lines = String(chunk?.text || "").split("\n");
		if (merged.length === 0) {
			merged = lines;
			continue;
		}

		const maxOverlap = Math.min(CHUNK_LINES, merged.length, lines.length);
		let overlap = 0;
		for (let size = maxOverlap; size >= 1; size -= 1) {
			const mergedTail = merged.slice(merged.length - size).join("\n");
			const nextHead = lines.slice(0, size).join("\n");
			if (mergedTail === nextHead) {
				overlap = size;
				break;
			}
		}

		merged.push(...lines.slice(overlap));
	}

	return merged.join("\n");
}

function findBalancedBraceEnd(text, openBraceIdx) {
	let depth = 0;
	let inSingle = false;
	let inDouble = false;
	let inTemplate = false;
	let inLineComment = false;
	let inBlockComment = false;
	let escaped = false;

	for (let i = openBraceIdx; i < text.length; i += 1) {
		const ch = text[i];
		const next = i + 1 < text.length ? text[i + 1] : "";

		if (inLineComment) {
			if (ch === "\n") {
				inLineComment = false;
			}
			continue;
		}

		if (inBlockComment) {
			if (ch === "*" && next === "/") {
				inBlockComment = false;
				i += 1;
			}
			continue;
		}

		if (inSingle) {
			if (!escaped && ch === "'") {
				inSingle = false;
			}
			escaped = !escaped && ch === "\\";
			continue;
		}

		if (inDouble) {
			if (!escaped && ch === '"') {
				inDouble = false;
			}
			escaped = !escaped && ch === "\\";
			continue;
		}

		if (inTemplate) {
			if (!escaped && ch === "`") {
				inTemplate = false;
			}
			escaped = !escaped && ch === "\\";
			continue;
		}

		escaped = false;

		if (ch === "/" && next === "/") {
			inLineComment = true;
			i += 1;
			continue;
		}

		if (ch === "/" && next === "*") {
			inBlockComment = true;
			i += 1;
			continue;
		}

		if (ch === "'") {
			inSingle = true;
			continue;
		}

		if (ch === '"') {
			inDouble = true;
			continue;
		}

		if (ch === "`") {
			inTemplate = true;
			continue;
		}

		if (ch === "{") {
			depth += 1;
		} else if (ch === "}") {
			depth -= 1;
			if (depth === 0) {
				return i + 1;
			}
		}
	}
	return -1;
}

function findDefinitionBodyStart(text, startIdx) {
	const windowSize = 2400;
	const source = text.slice(startIdx, startIdx + windowSize);
	const patterns = [
		/function\b[^{]*\{/i,
		/=\s*(?:async\s*)?function\b[^{]*\{/i,
		/=\s*(?:async\s*)?<[^>]+>\s*\([^)]*\)\s*=>\s*\{/i,
		/=\s*(?:async\s*)?\([^)]*\)\s*=>\s*\{/i,
		/=\s*(?:async\s*)?[A-Za-z_$][A-Za-z0-9_$]*\s*=>\s*\{/i,
		/class\b[^{]*\{/i,
	];

	let best = -1;
	for (const rx of patterns) {
		const m = rx.exec(source);
		if (!m) {
			continue;
		}
		const rel = m.index + m[0].lastIndexOf("{");
		if (rel < 0) {
			continue;
		}
		const abs = startIdx + rel;
		if (best < 0 || abs < best) {
			best = abs;
		}
	}

	if (best >= 0) {
		return best;
	}

	return text.indexOf("{", startIdx);
}

function trimToSymbolDefinition(text, querySymbols) {
	if (!text || !Array.isArray(querySymbols) || querySymbols.length === 0) {
		return null;
	}

	for (const symbol of querySymbols) {
		const escaped = symbol.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
		const definitionPatterns = [
			new RegExp(
				`(?:^|\\n)\\s*(?:export\\s+)?(?:async\\s+)?function\\s+${escaped}\\b`,
				"i",
			),
			new RegExp(
				`(?:^|\\n)\\s*(?:export\\s+)?(?:const|let|var)\\s+${escaped}\\s*=`,
				"i",
			),
			new RegExp(`(?:^|\\n)\\s*(?:export\\s+)?class\\s+${escaped}\\b`, "i"),
			new RegExp(
				`(?:^|\\n)\\s*(?:export\\s+)?(?:const|let|var)\\s+${escaped}\\s*:\\s*[^=]+=`,
				"i",
			),
		];

		let startIdx = -1;
		for (const rx of definitionPatterns) {
			const m = rx.exec(text);
			if (m) {
				startIdx = m.index + (m[0].startsWith("\n") ? 1 : 0);
				break;
			}
		}
		if (startIdx < 0) {
			continue;
		}

		const openBraceIdx = findDefinitionBodyStart(text, startIdx);
		if (openBraceIdx < 0) {
			continue;
		}

		const endIdx = findBalancedBraceEnd(text, openBraceIdx);
		if (endIdx < 0 || endIdx <= startIdx) {
			continue;
		}

		return {
			startIdx,
			endIdx,
			text: text.slice(startIdx, endIdx),
		};
	}

	return null;
}

function expandHitForTargetedSnippet(
	index,
	fileMap,
	hit,
	strictTokenMode,
	querySymbols,
) {
	if (!strictTokenMode || !TOKEN_FIRST_SINGLE_PIVOT) {
		return hit;
	}

	const window = getChunkWindow(index, fileMap, hit, 0, 1);
	if (!window || window.length <= 1) {
		return hit;
	}

	const mergedText = mergeChunkWindowTexts(window);
	const baseStartLine = window[0].startLine;
	const baseEndLine = window[window.length - 1].endLine;

	const trimmed = trimToSymbolDefinition(mergedText, querySymbols);
	if (!trimmed || !trimmed.text) {
		return {
			...hit,
			startLine: baseStartLine,
			endLine: baseEndLine,
			text: mergedText,
		};
	}

	const before = mergedText.slice(0, trimmed.startIdx);
	const startOffsetLines = before.split("\n").length - 1;
	const trimmedLineCount = trimmed.text.split("\n").length;

	return {
		...hit,
		startLine: baseStartLine + startOffsetLines,
		endLine: baseStartLine + startOffsetLines + trimmedLineCount - 1,
		text: trimmed.text,
	};
}

function choosePivotFiles(scoredChunks) {
	const pivots = [];
	const seen = new Set();

	for (const chunk of scoredChunks) {
		if (seen.has(chunk.relativePath)) {
			continue;
		}
		seen.add(chunk.relativePath);
		pivots.push(chunk.relativePath);
		if (pivots.length >= MAX_PIVOT_FILES) {
			break;
		}
	}

	return pivots;
}

function buildGraphBoost(index, pivotFiles) {
	const boost = {};
	const outgoing = index.graph?.outgoing || {};
	const incoming = index.graph?.incoming || {};
	const queue = [];
	const seen = new Set();

	for (const pivot of pivotFiles) {
		queue.push({ file: pivot, depth: 0 });
		seen.add(`${pivot}:0`);
		boost[pivot] = Math.max(boost[pivot] || 0, 3.5);
	}

	while (queue.length > 0) {
		const next = queue.shift();
		if (!next || next.depth >= 2) {
			continue;
		}

		const neighbors = new Set([
			...(outgoing[next.file] || []),
			...(incoming[next.file] || []),
		]);
		for (const neighbor of neighbors) {
			const depth = next.depth + 1;
			const key = `${neighbor}:${depth}`;
			if (seen.has(key)) {
				continue;
			}
			seen.add(key);
			queue.push({ file: neighbor, depth });
			boost[neighbor] = Math.max(boost[neighbor] || 0, depth === 1 ? 2.1 : 1.0);
		}
	}

	return boost;
}

function getCandidateChunks(index, queryTerms) {
	const normalizedTerms = queryTerms.filter(Boolean);
	if (normalizedTerms.length === 0) {
		return null;
	}

	const sqliteState = dbStateByWorkspace.get(index.workspaceRoot);
	if (!sqliteState || !sqliteState.hasFts) {
		return null;
	}

	try {
		const ftsQuery = normalizedTerms.map(term => `${term}*`).join(" OR ");
		const rows = sqliteState.db
			.prepare(
				"SELECT relative_path, chunk_index, start_line, end_line, text FROM chunks_fts WHERE chunks_fts MATCH ? LIMIT ?",
			)
			.all(ftsQuery, MAX_RETRIEVAL_CANDIDATES);

		if (!rows || rows.length === 0) {
			return null;
		}

		return rows.map(row => ({
			relativePath: row.relative_path,
			chunkIndex: row.chunk_index,
			startLine: row.start_line,
			endLine: row.end_line,
			text: row.text,
			tf: toTermFrequency(row.text),
		}));
	} catch {
		return null;
	}
}

function runRetrieval(index, query, tokenBudget) {
	const queryTerms = toWords(query);
	const querySet = new Set(queryTerms);
	const querySymbols = extractQuerySymbols(query);
	const queryFileHints = extractQueryFileHints(query);
	const targetedMode =
		queryLooksImplementationFocused(query, querySet) ||
		querySymbols.length > 0 ||
		queryFileHints.length > 0;
	const strictTokenMode = TOKEN_FIRST_MODE && targetedMode;
	const wantNeighbors = queryWantsNeighbors(querySet);
	const minimumCandidateHits = strictTokenMode ? 4 : 8;
	if (queryTerms.length === 0) {
		return {
			pivots: [],
			neighbors: [],
			usedTokens: 0,
			queryTerms,
		};
	}

	const fileMap = Object.fromEntries(index.files.map(f => [f.relativePath, f]));
	const candidateChunks = getCandidateChunks(index, queryTerms);
	const dbFallbackChunks = getFallbackChunksFromDb(index, queryTerms);
	const symbolMatchedPaths = getSymbolMatchedFiles(index, querySymbols);
	const symbolFastChunks =
		targetedMode && symbolMatchedPaths.length > 0
			? getChunksForFilesFromDb(index, symbolMatchedPaths, 10)
			: [];
	const baseline = [];
	const targetedBaseline = [];
	let usedSymbolFastPath = false;

	function addBaselineEntry(entry) {
		if (
			targetedMode &&
			symbolMatchedPaths.length > 0 &&
			symbolMatchedPaths.includes(entry.relativePath)
		) {
			targetedBaseline.push(entry);
			return;
		}

		if (targetedMode && queryFileHints.length > 0) {
			if (matchesFileHints(entry.relativePath, queryFileHints)) {
				targetedBaseline.push(entry);
				return;
			}
		}
		baseline.push(entry);
	}

	if (symbolFastChunks.length > 0) {
		usedSymbolFastPath = true;
		for (const chunk of symbolFastChunks) {
			const score =
				scoreChunk(
					queryTerms,
					querySet,
					querySymbols,
					queryFileHints,
					chunk,
					chunk.relativePath,
				) + 6;
			if (score <= 0) {
				continue;
			}
			addBaselineEntry({
				relativePath: chunk.relativePath,
				chunkIndex: chunk.chunkIndex,
				startLine: chunk.startLine,
				endLine: chunk.endLine,
				text: chunk.text,
				score,
			});
		}
	}

	if (
		!(strictTokenMode && usedSymbolFastPath) &&
		candidateChunks &&
		candidateChunks.length > 0
	) {
		for (const chunk of candidateChunks) {
			const score = scoreChunk(
				queryTerms,
				querySet,
				querySymbols,
				queryFileHints,
				chunk,
				chunk.relativePath,
			);
			if (score <= 0) {
				continue;
			}
			addBaselineEntry({
				relativePath: chunk.relativePath,
				chunkIndex: chunk.chunkIndex,
				startLine: chunk.startLine,
				endLine: chunk.endLine,
				text: chunk.text,
				score,
			});
		}
	}

	if (
		!usedSymbolFastPath &&
		baseline.length + targetedBaseline.length < minimumCandidateHits
	) {
		for (const chunk of dbFallbackChunks) {
			const score = scoreChunk(
				queryTerms,
				querySet,
				querySymbols,
				queryFileHints,
				chunk,
				chunk.relativePath,
			);
			if (score <= 0) {
				continue;
			}
			addBaselineEntry({
				relativePath: chunk.relativePath,
				chunkIndex: chunk.chunkIndex,
				startLine: chunk.startLine,
				endLine: chunk.endLine,
				text: chunk.text,
				score,
			});
		}
	}

	if (
		!usedSymbolFastPath &&
		baseline.length + targetedBaseline.length < minimumCandidateHits
	) {
		const filesForScan = index.files.slice(0, MAX_FALLBACK_SCAN_FILES);
		for (const file of filesForScan) {
			if (!file.chunks || file.chunks.length === 0) {
				continue;
			}
			for (const chunk of file.chunks) {
				const score = scoreChunk(
					queryTerms,
					querySet,
					querySymbols,
					queryFileHints,
					chunk,
					file.relativePath,
				);
				if (score <= 0) {
					continue;
				}
				addBaselineEntry({
					relativePath: file.relativePath,
					chunkIndex: chunk.chunkIndex,
					startLine: chunk.startLine,
					endLine: chunk.endLine,
					text: chunk.text,
					score,
				});
			}
		}
	}

	const effectiveBaseline =
		targetedBaseline.length > 0 ? targetedBaseline : baseline;

	effectiveBaseline.sort((a, b) => b.score - a.score);
	const initialPivots = choosePivotFiles(effectiveBaseline);
	const graphBoost = buildGraphBoost(index, initialPivots);

	const scored = effectiveBaseline
		.map(entry => ({
			...entry,
			score: entry.score + (graphBoost[entry.relativePath] || 0),
		}))
		.sort((a, b) => b.score - a.score);

	const pivots = [];
	const pivotFileSet = new Set();
	const chunkDedupe = new Set();
	const snippetDedupe = new Set();
	const pivotBudget = strictTokenMode
		? Math.min(360, Math.max(160, Math.floor(tokenBudget * 0.28)))
		: targetedMode
			? Math.min(650, Math.max(220, Math.floor(tokenBudget * 0.45)))
			: Math.max(300, Math.floor(tokenBudget * 0.8));
	const maxPivots = strictTokenMode
		? TOKEN_FIRST_SINGLE_PIVOT
			? 1
			: 2
		: targetedMode
			? 10
			: 20;
	const maxPivotFiles = strictTokenMode
		? TOKEN_FIRST_SINGLE_PIVOT
			? 1
			: 2
		: targetedMode
			? 3
			: MAX_PIVOT_FILES;
	const maxNeighbors = strictTokenMode
		? wantNeighbors
			? 1
			: 0
		: targetedMode
			? 3
			: MAX_NEIGHBOR_SKELETONS;
	let usedTokens = 0;
	let rawPivotTokens = 0;
	let compactedPivotTokens = 0;

	for (const hit of scored) {
		const expandedHit = expandHitForTargetedSnippet(
			index,
			fileMap,
			hit,
			strictTokenMode,
			querySymbols,
		);
		const key = `${expandedHit.relativePath}:${expandedHit.startLine}:${expandedHit.endLine}`;
		if (chunkDedupe.has(key)) {
			continue;
		}

		const compacted = compactSnippet(
			expandedHit.text,
			strictTokenMode && TOKEN_FIRST_SINGLE_PIVOT ? 140 : 48,
		);
		if (!compacted) {
			continue;
		}
		const compactHash = sha1(compacted);
		if (snippetDedupe.has(compactHash)) {
			continue;
		}

		const snippetTokens = estimateTokens(compacted);
		const rawTokens = estimateTokens(expandedHit.text);
		if (pivots.length > 0 && usedTokens + snippetTokens > pivotBudget) {
			continue;
		}

		pivots.push({
			...expandedHit,
			text: compacted,
		});
		chunkDedupe.add(key);
		snippetDedupe.add(compactHash);
		pivotFileSet.add(hit.relativePath);
		usedTokens += snippetTokens;
		rawPivotTokens += rawTokens;
		compactedPivotTokens += snippetTokens;

		if (
			usedTokens >= pivotBudget ||
			pivots.length >= maxPivots ||
			pivotFileSet.size >= maxPivotFiles
		) {
			break;
		}
	}

	const outgoing = index.graph?.outgoing || {};
	const incoming = index.graph?.incoming || {};
	const neighborPaths = new Set();

	for (const pivotPath of pivotFileSet) {
		for (const p of outgoing[pivotPath] || []) {
			if (!pivotFileSet.has(p)) {
				neighborPaths.add(p);
			}
		}
		for (const p of incoming[pivotPath] || []) {
			if (!pivotFileSet.has(p)) {
				neighborPaths.add(p);
			}
		}
	}

	const neighbors = [];
	const sortedNeighborPaths = Array.from(neighborPaths).sort((a, b) => {
		const boostDiff = (graphBoost[b] || 0) - (graphBoost[a] || 0);
		return boostDiff !== 0 ? boostDiff : a.localeCompare(b);
	});

	for (const neighborPath of sortedNeighborPaths) {
		if (neighbors.length >= maxNeighbors) {
			break;
		}

		const file = fileMap[neighborPath];
		if (!file || !file.skeleton) {
			continue;
		}

		const compactSkeleton = compactSnippet(file.skeleton, 24);
		if (!compactSkeleton) {
			continue;
		}
		const skeletonHash = sha1(compactSkeleton);
		if (snippetDedupe.has(skeletonHash)) {
			continue;
		}

		const skeletonTokens = estimateTokens(compactSkeleton);
		if (usedTokens + skeletonTokens > tokenBudget) {
			continue;
		}

		neighbors.push({
			relativePath: neighborPath,
			text: compactSkeleton,
			score: graphBoost[neighborPath] || 0,
		});
		snippetDedupe.add(skeletonHash);
		usedTokens += skeletonTokens;
	}

	return {
		pivots,
		neighbors,
		usedTokens,
		tokenReductionPct:
			rawPivotTokens > 0
				? Number(
						(
							((rawPivotTokens - compactedPivotTokens) / rawPivotTokens) *
							100
						).toFixed(2),
					)
				: 0,
		queryTerms,
		stats: {
			totalFiles: index.files.length,
			pivots: pivots.length,
			neighbors: neighbors.length,
			tokenFirstMode: strictTokenMode,
			tokenFirstSinglePivot: strictTokenMode && TOKEN_FIRST_SINGLE_PIVOT,
			retrievalMode: targetedMode ? "targeted-impl" : "hybrid",
			candidateMode: usedSymbolFastPath
				? "symbol-fast+fts"
				: candidateChunks
					? "fts+db+limited-scan"
					: dbFallbackChunks.length > 0
						? "db+limited-scan"
						: "limited-scan",
		},
	};
}

function buildCapsuleText(query, tokenBudget, index, result) {
	if (result?.stats?.tokenFirstMode) {
		const lines = [
			"# AI Context Capsule (Token-First)",
			"",
			`Query: ${query}`,
			"",
		];

		if (result.pivots.length === 0) {
			lines.push("No matching pivot snippets found.");
			return lines.join("\n");
		}

		for (const hit of result.pivots) {
			lines.push(`### ${hit.relativePath}:${hit.startLine}-${hit.endLine}`);
			lines.push("```");
			lines.push(hit.text);
			lines.push("```");
			lines.push("");
		}

		if (result.neighbors.length > 0) {
			for (const neighbor of result.neighbors) {
				lines.push(`### ${neighbor.relativePath}`);
				lines.push("```");
				lines.push(neighbor.text);
				lines.push("```");
				lines.push("");
			}
		}

		return lines.join("\n");
	}

	const lines = [];
	const edgeCount = Object.values(index.graph?.outgoing || {}).reduce(
		(acc, deps) => acc + deps.length,
		0,
	);

	lines.push("# AI Context Capsule");
	lines.push("");
	lines.push(`Query: ${query}`);
	lines.push(`Token budget: ${tokenBudget}`);
	lines.push(`Index generated: ${index.generatedAt}`);
	lines.push(`Graph edges: ${edgeCount}`);
	lines.push(`Index signature: ${index.indexSignature}`);
	lines.push("");
	lines.push("## Pivot Snippets");
	lines.push("");

	if (result.pivots.length === 0) {
		lines.push("No matching pivot snippets found.");
	} else {
		for (const hit of result.pivots) {
			lines.push(
				`### ${hit.relativePath}:${hit.startLine}-${hit.endLine} (score ${hit.score.toFixed(2)})`,
			);
			lines.push("```");
			lines.push(hit.text);
			lines.push("```");
			lines.push("");
		}
	}

	lines.push("## Neighbor Skeletons");
	lines.push("");
	if (result.neighbors.length === 0) {
		lines.push("No neighbor skeletons fit within budget.");
	} else {
		for (const neighbor of result.neighbors) {
			lines.push(
				`### ${neighbor.relativePath} (graph score ${neighbor.score.toFixed(2)})`,
			);
			lines.push("```");
			lines.push(neighbor.text);
			lines.push("```");
			lines.push("");
		}
	}

	return lines.join("\n");
}

function readQueryCache(db, cacheKey, indexSignature, gitHead) {
	if (!db) {
		return null;
	}

	const row = db
		.prepare(
			"SELECT result_json, created_at FROM query_cache WHERE cache_key = ? AND index_signature = ? AND (git_head IS ? OR git_head = ?)",
		)
		.get(cacheKey, indexSignature, gitHead, gitHead);

	if (!row) {
		return null;
	}

	if (Date.now() - row.created_at > MAX_CACHE_AGE_MS) {
		db.prepare("DELETE FROM query_cache WHERE cache_key = ?").run(cacheKey);
		return null;
	}

	try {
		return JSON.parse(row.result_json);
	} catch {
		return null;
	}
}

function writeQueryCache(db, cacheKey, indexSignature, gitHead, payload) {
	if (!db) {
		return;
	}

	db.prepare(
		"INSERT OR REPLACE INTO query_cache(cache_key, created_at, index_signature, git_head, result_json) VALUES(?, ?, ?, ?, ?)",
	).run(cacheKey, Date.now(), indexSignature, gitHead, JSON.stringify(payload));

	db.prepare("DELETE FROM query_cache WHERE created_at < ?").run(
		Date.now() - MAX_CACHE_AGE_MS,
	);
}

async function runPipelineCore({ workspaceRoot, task, tokenBudget }) {
	const start = Date.now();
	const taskMode = inferTaskMode(task);
	const index = await ensureIndex(workspaceRoot);
	const normalized = normalizeTask(task);
	const gitHead = getGitHead(workspaceRoot);
	const cacheKey = sha1(
		`${workspaceRoot}\n${normalized}\n${tokenBudget}\n${gitHead || "nogit"}\nrv:${RETRIEVAL_CACHE_VERSION}`,
	);
	const db = dbStateByWorkspace.get(workspaceRoot)?.db || null;

	const cached = readQueryCache(db, cacheKey, index.indexSignature, gitHead);
	if (cached) {
		const latencyMs = Date.now() - start;
		recordQueryMetrics(workspaceRoot, {
			cache: "hit",
			latencyMs,
			usedTokens: cached.usedTokens,
			candidateMode: cached?.stats?.candidateMode || "cache",
			taskMode,
			tokenReductionPct: cached.tokenReductionPct || 0,
		});
		return {
			...cached,
			cache: "hit",
			latencyMs,
			metrics: snapshotMetrics(workspaceRoot),
		};
	}

	const result = runRetrieval(index, task, tokenBudget);
	const capsule = buildCapsuleText(task, tokenBudget, index, result);

	const payload = {
		ok: true,
		workspaceRoot,
		task,
		tokenBudget,
		workspaceFingerprint: index.workspaceFingerprint || null,
		usedTokens: result.usedTokens,
		pivots: result.pivots.length,
		neighbors: result.neighbors.length,
		tokenReductionPct: result.tokenReductionPct,
		capsule,
		stats: result.stats,
		indexVersion: index.version,
		indexSignature: index.indexSignature,
		sqlite: index.sqlite,
	};

	writeQueryCache(db, cacheKey, index.indexSignature, gitHead, payload);
	const latencyMs = Date.now() - start;
	recordQueryMetrics(workspaceRoot, {
		cache: "miss",
		latencyMs,
		usedTokens: payload.usedTokens,
		candidateMode: payload?.stats?.candidateMode,
		taskMode,
		tokenReductionPct: payload.tokenReductionPct || 0,
	});
	return {
		...payload,
		cache: "miss",
		latencyMs,
		metrics: snapshotMetrics(workspaceRoot),
	};
}

async function toolIndexWorkspace(args) {
	const workspaceRoot = path.resolve(args?.workspaceRoot || process.cwd());
	const index = await buildIndex(workspaceRoot);
	const edgeCount = Object.values(index.graph?.outgoing || {}).reduce(
		(acc, deps) => acc + deps.length,
		0,
	);

	return {
		content: [
			{
				type: "text",
				text: JSON.stringify(
					{
						ok: true,
						workspaceRoot,
						generatedAt: index.generatedAt,
						workspaceFingerprint: index.workspaceFingerprint || null,
						files: index.files.length,
						edges: edgeCount,
						indexSignature: index.indexSignature,
						sqlite: index.sqlite,
						indexer: snapshotIndexerMetrics(workspaceRoot),
					},
					null,
					2,
				),
			},
		],
	};
}

async function toolIndexStatus(args) {
	const workspaceRoot = path.resolve(args?.workspaceRoot || process.cwd());
	const index = await ensureIndex(workspaceRoot);
	const edgeCount = Object.values(index.graph?.outgoing || {}).reduce(
		(acc, deps) => acc + deps.length,
		0,
	);

	return {
		content: [
			{
				type: "text",
				text: JSON.stringify(
					{
						ok: true,
						workspaceRoot,
						generatedAt: index.generatedAt,
						workspaceFingerprint: index.workspaceFingerprint || null,
						files: index.files.length,
						edges: edgeCount,
						indexVersion: index.version,
						indexSignature: index.indexSignature,
						sqlite: index.sqlite,
						metrics: snapshotMetrics(workspaceRoot),
						indexer: snapshotIndexerMetrics(workspaceRoot),
					},
					null,
					2,
				),
			},
		],
	};
}

async function toolGetContextCapsule(args) {
	const workspaceRoot = path.resolve(args?.workspaceRoot || process.cwd());
	const query = String(args?.query || "").trim();
	const tokenBudgetRaw = Number(args?.tokenBudget ?? DEFAULT_TOKEN_BUDGET);
	const tokenBudget = Number.isFinite(tokenBudgetRaw)
		? Math.max(200, Math.min(10000, Math.floor(tokenBudgetRaw)))
		: DEFAULT_TOKEN_BUDGET;

	if (!query) {
		return {
			content: [{ type: "text", text: "query is required" }],
			isError: true,
		};
	}

	const payload = await runPipelineCore({
		workspaceRoot,
		task: query,
		tokenBudget,
	});

	return {
		content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
	};
}

async function toolRunPipeline(args) {
	const workspaceRoot = path.resolve(args?.workspaceRoot || process.cwd());
	const task = String(args?.task || args?.query || "").trim();
	const tokenBudgetRaw = Number(args?.tokenBudget ?? DEFAULT_TOKEN_BUDGET);
	const tokenBudget = Number.isFinite(tokenBudgetRaw)
		? Math.max(200, Math.min(10000, Math.floor(tokenBudgetRaw)))
		: DEFAULT_TOKEN_BUDGET;

	if (!task) {
		return {
			content: [{ type: "text", text: "task is required" }],
			isError: true,
		};
	}

	const payload = await runPipelineCore({ workspaceRoot, task, tokenBudget });
	return {
		content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
	};
}

function createServer() {
	const server = new Server(
		{
			name: "ai-context-mcp",
			version: "0.2.0",
		},
		{
			capabilities: {
				tools: {},
			},
		},
	);

	server.setRequestHandler(ListToolsRequestSchema, async () => ({
		tools: [
			{
				name: "run_pipeline",
				description:
					"Single-call context pipeline with incremental index, query cache, and token-compacted capsule output.",
				inputSchema: {
					type: "object",
					properties: {
						workspaceRoot: {
							type: "string",
							description:
								"Absolute or relative workspace root path. Defaults to current working directory.",
						},
						task: {
							type: "string",
							description: "Natural-language task query from the user prompt.",
						},
						tokenBudget: {
							type: "number",
							description:
								"Token budget for packed context, between 200 and 10000.",
							default: DEFAULT_TOKEN_BUDGET,
						},
					},
					required: ["task"],
				},
			},
			{
				name: "index_workspace",
				description:
					"Build or rebuild local repository index and dependency graph.",
				inputSchema: {
					type: "object",
					properties: {
						workspaceRoot: {
							type: "string",
							description:
								"Absolute or relative workspace root path. Defaults to current working directory.",
						},
					},
				},
			},
			{
				name: "index_status",
				description: "Return index status and counts for the workspace.",
				inputSchema: {
					type: "object",
					properties: {
						workspaceRoot: {
							type: "string",
							description:
								"Absolute or relative workspace root path. Defaults to current working directory.",
						},
					},
				},
			},
			{
				name: "get_context_capsule",
				description:
					"Return token-budgeted context capsule with pivot snippets and neighbor skeletons.",
				inputSchema: {
					type: "object",
					properties: {
						workspaceRoot: {
							type: "string",
							description:
								"Absolute or relative workspace root path. Defaults to current working directory.",
						},
						query: {
							type: "string",
							description:
								"Task/query text used to retrieve relevant code context.",
						},
						tokenBudget: {
							type: "number",
							description:
								"Token budget for packed context, between 200 and 10000.",
							default: DEFAULT_TOKEN_BUDGET,
						},
					},
					required: ["query"],
				},
			},
		],
	}));

	server.setRequestHandler(CallToolRequestSchema, async request => {
		const { name, arguments: args } = request.params;

		if (name === "run_pipeline") {
			return toolRunPipeline(args || {});
		}

		if (name === "index_workspace") {
			return toolIndexWorkspace(args || {});
		}
		if (name === "index_status") {
			return toolIndexStatus(args || {});
		}
		if (name === "get_context_capsule") {
			return toolGetContextCapsule(args || {});
		}

		return {
			isError: true,
			content: [{ type: "text", text: `Unknown tool: ${name}` }],
		};
	});

	return server;
}

async function main() {
	const server = createServer();
	const transport = new StdioServerTransport();
	await server.connect(transport);
}

main().catch(error => {
	process.stderr.write(
		`ai-context-mcp fatal error: ${error?.stack || error}\n`,
	);
	process.exit(1);
});
