const fs = require("fs/promises");
const path = require("path");
const crypto = require("crypto");
const { parentPort, workerData } = require("worker_threads");

const CHUNK_LINES = Number(workerData?.chunkLines) || 60;
const CHUNK_OVERLAP = Number(workerData?.chunkOverlap) || 10;

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

async function parseBatch(items) {
	const results = [];
	for (const item of items) {
		let text;
		try {
			text = await fs.readFile(item.abs, "utf8");
		} catch {
			results.push({ order: item.order, skipped: true });
			continue;
		}

		const parsed = parseTextForIndex(item.rel, text);
		if (!parsed) {
			results.push({ order: item.order, skipped: true });
			continue;
		}

		results.push({
			order: item.order,
			relativePath: item.rel,
			mtimeMs: item.mtimeMs,
			sizeBytes: item.sizeBytes,
			...parsed,
		});
	}
	return results;
}

(async () => {
	const items = Array.isArray(workerData?.items) ? workerData.items : [];
	const results = await parseBatch(items);
	parentPort.postMessage({ results });
})();
