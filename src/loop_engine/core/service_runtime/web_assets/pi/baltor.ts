/**
 * Baltor for Pi.
 *
 * Pi has no built-in Model Context Protocol client, so this extension calls
 * the Baltor service's REST routes directly. It adds:
 *
 *   baltor_search    search the Baltor library; returns references only, never file bodies
 *   baltor_download  download one published skill and install it in .pi/skills/<name>/
 *   /baltor          in a session, or `pi -p --baltor-check` from a shell: a connection check
 *
 * The service token is read from the environment variable named in the
 * configuration (BALTOR_SERVICE_TOKEN by default). It is sent only in the
 * Authorization header to the configured service origin. It is never written
 * to a file and never returned to the model, and an exact copy of it is
 * removed from every tool result before the model or the session sees it.
 *
 * Configuration (optional): .pi/baltor.json in the project, or baltor.json in
 * Pi's agent folder, holding {"baltor": {"url": "...", "token_env": "..."}}.
 * Without one, the extension uses https://baltor.ai and BALTOR_SERVICE_TOKEN.
 *
 * Record: baltor_pi_extension/v1. Licence: MIT.
 */
import { createHash, randomUUID } from "node:crypto";
import { existsSync, lstatSync, mkdirSync, readdirSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import * as path from "node:path";
import { getAgentDir, loadSkillsFromDir, parseFrontmatter, type ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";

export const EXTENSION_RECORD = "baltor_pi_extension/v1";
export const INSTALL_RECORD = "baltor_pi_install/v1";
const DEFAULT_SERVICE_URL = "https://baltor.ai/mcp";
const DEFAULT_TOKEN_VARIABLE = "BALTOR_SERVICE_TOKEN";
const CONFIG_FILE = "baltor.json";
const RESULT_RECORD = "service_http_result/v1";
const ERROR_RECORD = "service_http_error/v1";
const CAPABILITIES_RECORD = "service_capabilities/v1";
const RETRIEVAL_RESULT_RECORD = "service_retrieval_result/v1";
// Version 2, like the search: the manifest and the download ask with the same default step effects and library
// setting as the search that found the item, so an item the search offered is not refused. Version 1 was refused
// for every item that reads files (September 25, 2026). A version 2 manifest answers as provisioning_manifest/v3.
const PROVISIONING_REQUEST = "service_provisioning_request/v2";
const MANIFEST_RECORD = "provisioning_manifest/v3";
const DOWNLOAD_RECORD = "service_download/v1";
const DIGEST_HEADER = "x-content-sha256";
const RECORD_TYPE_HEADER = "x-loop-engine-record-type";
// A release that does not declare its search request version accepts version 1.
// A release that declares one is held to it, and an unknown one is refused.
const UNDECLARED_RETRIEVAL_REQUEST = "service_retrieval_request/v1";
const SUPPORTED_RETRIEVAL_REQUESTS = ["service_retrieval_request/v1", "service_retrieval_request/v2"];
const SEARCH_MODE = "hybrid";
const SKILL_KIND = "skill";
const SKILL_FILE = "SKILL.md";
// The same two renderings as the repository's native placement tool. Pi drops a
// SKILL.md without a description, so a body without one gets a generated header.
export const RENDER_UNCHANGED = "served_bytes_unchanged";
export const RENDER_HEADER = "generated_frontmatter_then_served_body";
const DIGEST = /^[0-9a-f]{64}$/;
const IDENTITY = /^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$/;
const NATIVE_NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const VARIABLE = /^[A-Z][A-Z0-9_]{2,63}$/;
const PATH_SEGMENT = /^[A-Za-z0-9_][A-Za-z0-9._-]{0,127}$/;
const MAX_JSON_BYTES = 2_000_000;
const MAX_FILE_BYTES_CEILING = 16 * 1024 * 1024;
const DEFAULT_FILE_BYTES = 1_048_576;
const MAX_PACKAGE_FILES = 64;
const MAX_PATH_DEPTH = 6;
const MAX_DESCRIPTION = 1024;
const REQUEST_TIMEOUT_MS = 30_000;
const STAGING_PREFIX = ".baltor-staging-";

export class BaltorError extends Error {
	code: string;
	transport: boolean;
	constructor(code: string, message: string, transport = false) {
		super(message);
		this.code = code;
		this.transport = transport;
	}
}

type Settings = { serviceUrl: string; origin: string; tokenVariable: string; source: string };
type Capabilities = { retrievalRequest: string; retrievalDeclared: boolean; fileBytes: number; searchLimit: number };
type PackageFile = { path: string; digest: string; size_bytes: number; role?: string };
type SearchHit = {
	identity: string;
	kind: string;
	purpose: string;
	digest: string;
	size_bytes: number;
	license: string;
	body_allowed: boolean;
	files: PackageFile[] | null;
	catalogue_release: string | null;
};
type InstalledFile = {
	path: string;
	published_digest: string;
	header_bytes: number;
	file_sha256: string;
	size_bytes: number;
	response: { record_type: string; content_sha256: string };
};

const isTable = (value: unknown): value is Record<string, any> =>
	value !== null && typeof value === "object" && !Array.isArray(value);
const sha256 = (bytes: Buffer | Uint8Array) => createHash("sha256").update(bytes).digest("hex");

// ---------------------------------------------------------------- settings

export function readSettings(cwd: string): Settings {
	for (const file of [path.join(cwd, ".pi", CONFIG_FILE), path.join(getAgentDir(), CONFIG_FILE)]) {
		if (!existsSync(file)) continue;
		let parsed: unknown;
		try {
			parsed = JSON.parse(readFileSync(file, "utf8"));
		} catch {
			throw new BaltorError("configuration_unreadable", `${file} is not valid JSON.`);
		}
		return settingsFrom(parsed, file);
	}
	return settingsFrom({ baltor: { url: DEFAULT_SERVICE_URL, token_env: DEFAULT_TOKEN_VARIABLE } }, "built-in default");
}

function settingsFrom(value: unknown, source: string): Settings {
	if (!isTable(value) || Object.keys(value).length !== 1 || !isTable(value.baltor)) {
		throw new BaltorError("configuration_invalid", `${source} must hold exactly one "baltor" table.`);
	}
	const table = value.baltor;
	const unknown = Object.keys(table).filter((key) => key !== "url" && key !== "token_env");
	if (unknown.length) {
		throw new BaltorError("configuration_invalid", `${source} has settings this extension does not read: ${unknown.join(", ")}.`);
	}
	const url = table.url ?? DEFAULT_SERVICE_URL;
	const tokenVariable = table.token_env ?? DEFAULT_TOKEN_VARIABLE;
	if (typeof tokenVariable !== "string" || !VARIABLE.test(tokenVariable)) {
		throw new BaltorError("configuration_invalid", `${source}: token_env must name an environment variable, such as BALTOR_SERVICE_TOKEN. It never holds the token itself.`);
	}
	return { serviceUrl: String(url), origin: serviceOrigin(url, source), tokenVariable, source };
}

function serviceOrigin(url: unknown, source: string): string {
	let parsed: URL;
	try {
		parsed = new URL(String(url));
	} catch {
		throw new BaltorError("configuration_invalid", `${source}: url is not an address.`);
	}
	if (parsed.username || parsed.password) {
		throw new BaltorError("configuration_invalid", `${source}: url must not carry a user name or password.`);
	}
	const loopback = ["127.0.0.1", "localhost", "[::1]"].includes(parsed.hostname);
	if (parsed.protocol !== "https:" && !(parsed.protocol === "http:" && loopback)) {
		throw new BaltorError("configuration_invalid", `${source}: url must use https.`);
	}
	// The address the website shows ends in /mcp. The REST routes live under the same origin.
	return parsed.origin;
}

function tokenFrom(settings: Settings): string {
	const value = (process.env[settings.tokenVariable] ?? "").trim();
	if (!value) {
		throw new BaltorError("token_missing", `${settings.tokenVariable} is not set in the environment that started pi. Set it in your shell; the extension never reads a token from a file.`);
	}
	if (/\s/.test(value)) {
		throw new BaltorError("token_invalid", `${settings.tokenVariable} holds white space, so it cannot be a service token.`);
	}
	return value;
}

// ---------------------------------------------------------------- HTTP

type Exchange = { status: number; headers: Headers; bytes: Buffer };

async function readCapped(response: Response, maxBytes: number, route: string): Promise<Buffer> {
	const declared = Number(response.headers.get("content-length") ?? "NaN");
	const tooLarge = () => new BaltorError("response_too_large", `The answer to ${route} is larger than ${maxBytes} bytes, so it was not read.`);
	if (Number.isFinite(declared) && declared > maxBytes) {
		await response.body?.cancel().catch(() => undefined);
		throw tooLarge();
	}
	const reader = response.body?.getReader();
	if (!reader) return Buffer.alloc(0);
	const chunks: Buffer[] = [];
	let total = 0;
	for (;;) {
		const { done, value } = await reader.read();
		if (done) break;
		total += value.byteLength;
		if (total > maxBytes) {
			await reader.cancel().catch(() => undefined);
			throw tooLarge();
		}
		chunks.push(Buffer.from(value));
	}
	return Buffer.concat(chunks);
}

async function exchange(
	settings: Settings,
	route: string,
	options: { method: "GET" | "POST"; body?: unknown; token?: string; maxBytes: number; signal?: AbortSignal },
): Promise<Exchange> {
	const signals = [AbortSignal.timeout(REQUEST_TIMEOUT_MS)];
	if (options.signal) signals.push(options.signal);
	const headers: Record<string, string> = { Accept: "application/json, application/octet-stream" };
	if (options.token) headers.Authorization = `Bearer ${options.token}`;
	if (options.body !== undefined) headers["Content-Type"] = "application/json";
	let response: Response;
	try {
		response = await fetch(settings.origin + route, {
			method: options.method,
			headers,
			body: options.body === undefined ? undefined : JSON.stringify(options.body),
			// A redirect is refused, so the token is only ever sent to the configured origin.
			redirect: "manual",
			signal: AbortSignal.any(signals),
		});
	} catch (error) {
		const reason = error instanceof Error ? (error.cause instanceof Error ? error.cause.message : error.message) : String(error);
		throw new BaltorError("service_unreachable", `Could not reach ${settings.origin}${route}: ${reason}`, true);
	}
	if (response.status >= 300 && response.status < 400) {
		await response.body?.cancel().catch(() => undefined);
		throw new BaltorError("redirect_refused", `The service answered ${route} with a redirect (${response.status}). The extension does not follow redirects, so the token is never sent to another address.`);
	}
	return { status: response.status, headers: response.headers, bytes: await readCapped(response, options.maxBytes, route) };
}

function refusal(status: number, record: any): BaltorError {
	const error = isTable(record?.error) ? record.error : {};
	const code = typeof error.code === "string" ? error.code : `http_${status}`;
	const parts = [`Baltor refused the request (${status} ${code}).`];
	if (typeof error.message === "string") parts.push(error.message);
	if (typeof error.next_action === "string") parts.push(`Next: ${error.next_action}`);
	if (typeof record?.request_reference === "string") parts.push(`Reference: ${record.request_reference}.`);
	return new BaltorError(code, parts.join(" "));
}

function serviceResult(reply: Exchange, operation: string): any {
	let record: any;
	try {
		record = JSON.parse(reply.bytes.toString("utf8"));
	} catch {
		throw new BaltorError("response_unreadable", `The service answered ${operation} with status ${reply.status} and a body that is not JSON.`);
	}
	if (reply.status !== 200 || record?.record_type === ERROR_RECORD) throw refusal(reply.status, record);
	if (record?.record_type !== RESULT_RECORD || !isTable(record.result)) {
		throw new BaltorError("response_unsupported", `The service answered ${operation} with a record this extension does not read (${String(record?.record_type)}).`);
	}
	return record.result;
}

// ---------------------------------------------------------------- service calls

const capabilityCache = new Map<string, Capabilities>();

export async function capabilitiesFor(settings: Settings, signal?: AbortSignal): Promise<Capabilities> {
	const cached = capabilityCache.get(settings.origin);
	if (cached) return cached;
	const value = serviceResult(
		await exchange(settings, "/api/v1/capabilities", { method: "GET", maxBytes: MAX_JSON_BYTES, signal }),
		"capabilities",
	);
	if (value.record_type !== CAPABILITIES_RECORD || value.api_version !== "v1") {
		throw new BaltorError("service_version_unsupported", `The service reports ${String(value.record_type)} with interface ${String(value.api_version)}; this extension reads ${CAPABILITIES_RECORD} with interface v1.`);
	}
	const declared = value.retrieval?.request_record_type;
	const retrievalRequest = declared === undefined ? UNDECLARED_RETRIEVAL_REQUEST : declared;
	if (!SUPPORTED_RETRIEVAL_REQUESTS.includes(retrievalRequest)) {
		throw new BaltorError("search_version_unsupported", `The service asks for search request ${String(retrievalRequest)}; this extension sends ${SUPPORTED_RETRIEVAL_REQUESTS.join(" or ")}. Update the extension.`);
	}
	const delivery = isTable(value.delivery) ? value.delivery : {};
	if (delivery.download_endpoint !== "/api/v1/download" || delivery.body_format !== "utf8_text") {
		throw new BaltorError("delivery_unsupported", "The service describes a download route or body format this extension does not read.");
	}
	const limit = Number(delivery.download_bytes);
	const result: Capabilities = {
		retrievalRequest,
		retrievalDeclared: declared !== undefined,
		fileBytes: Number.isInteger(limit) && limit > 0 ? Math.min(limit, MAX_FILE_BYTES_CEILING) : DEFAULT_FILE_BYTES,
		searchLimit: Number.isInteger(value.limits?.search_results) ? value.limits.search_results : 10,
	};
	capabilityCache.set(settings.origin, result);
	return result;
}

// Search results of this session, so a download is bound to the digest the model saw.
const searchCache = new Map<string, SearchHit>();

function packageFiles(value: unknown): PackageFile[] | null {
	if (!isTable(value) || !Array.isArray(value.files)) return null;
	return value.files.map((file: any) => ({
		path: String(file?.path),
		digest: String(file?.digest),
		size_bytes: Number(file?.size_bytes),
		role: typeof file?.role === "string" ? file.role : undefined,
	}));
}

async function searchOnce(settings: Settings, token: string, capabilities: Capabilities, query: string, limit: number, signal?: AbortSignal) {
	const topN = Math.max(1, Math.min(limit, capabilities.searchLimit));
	return serviceResult(
		await exchange(settings, "/api/v1/retrieval", {
			method: "POST",
			token,
			signal,
			maxBytes: MAX_JSON_BYTES,
			body: { record_type: capabilities.retrievalRequest, query, mode: SEARCH_MODE, top_n: topN },
		}),
		"search",
	);
}

export async function search(settings: Settings, query: string, limit: number, signal?: AbortSignal) {
	const token = tokenFrom(settings);
	let capabilities = await capabilitiesFor(settings, signal);
	let result: any;
	try {
		result = await searchOnce(settings, token, capabilities, query, limit, signal);
	} catch (error) {
		// The service can be upgraded while a long session runs. After a version refusal the
		// extension asks the service again, once, and repeats the search only if the version changed.
		if (!(error instanceof BaltorError) || error.code !== "unsupported_version") throw error;
		capabilityCache.delete(settings.origin);
		const previous = capabilities.retrievalRequest;
		capabilities = await capabilitiesFor(settings, signal);
		if (capabilities.retrievalRequest === previous) throw error;
		result = await searchOnce(settings, token, capabilities, query, limit, signal);
	}
	if (result.record_type !== RETRIEVAL_RESULT_RECORD || !Array.isArray(result.hits)) {
		throw new BaltorError("response_unsupported", `The search answer is ${String(result.record_type)}, not ${RETRIEVAL_RESULT_RECORD}.`);
	}
	const release = typeof result.catalogue_release === "string" ? result.catalogue_release : null;
	const hits: SearchHit[] = result.hits.map((hit: any) => ({
		identity: String(hit?.reference?.identity),
		kind: String(hit?.kind),
		purpose: String(hit?.purpose ?? ""),
		digest: String(hit?.reference?.body_digest),
		size_bytes: Number(hit?.size_bytes),
		license: String(hit?.license ?? "unknown"),
		body_allowed: hit?.body_allowed === true,
		files: packageFiles(hit?.package),
		catalogue_release: release,
	}));
	for (const hit of hits) if (IDENTITY.test(hit.identity) && DIGEST.test(hit.digest)) searchCache.set(hit.identity, hit);
	return { hits, release, request: capabilities.retrievalRequest };
}

async function manifest(settings: Settings, token: string, identity: string, signal?: AbortSignal) {
	const value = serviceResult(
		await exchange(settings, "/api/v1/provisioning", {
			method: "POST",
			token,
			signal,
			maxBytes: MAX_JSON_BYTES,
			body: { record_type: PROVISIONING_REQUEST, operation: "manifest", identity },
		}),
		"manifest",
	);
	if (value.record_type !== MANIFEST_RECORD || value.identity !== identity || !DIGEST.test(String(value.digest))) {
		throw new BaltorError("response_unsupported", `The manifest for ${identity} is not a ${MANIFEST_RECORD} record for that identity.`);
	}
	return value;
}

async function downloadFile(
	settings: Settings,
	token: string,
	request: { identity: string; requestId: string; itemDigest: string; path?: string },
	expected: PackageFile,
	maxBytes: number,
	signal?: AbortSignal,
): Promise<{ bytes: Buffer; recordType: string; header: string }> {
	const body: Record<string, string> = {
		record_type: PROVISIONING_REQUEST,
		operation: "read",
		identity: request.identity,
		request_id: request.requestId,
		expected_digest: request.itemDigest,
	};
	if (request.path !== undefined) body.path = request.path;
	let reply: Exchange;
	try {
		reply = await exchange(settings, "/api/v1/download", { method: "POST", token, signal, maxBytes, body });
	} catch (error) {
		// One repeat after a transport failure. It reuses the same request identity,
		// which the service records once, so a repeat is never counted twice.
		if (!(error instanceof BaltorError) || !error.transport || signal?.aborted) throw error;
		reply = await exchange(settings, "/api/v1/download", { method: "POST", token, signal, maxBytes, body });
	}
	if (reply.status !== 200) {
		let record: any = null;
		try {
			record = JSON.parse(reply.bytes.toString("utf8"));
		} catch {}
		throw refusal(reply.status, record);
	}
	const recordType = reply.headers.get(RECORD_TYPE_HEADER);
	const header = reply.headers.get(DIGEST_HEADER) ?? "";
	const actual = sha256(reply.bytes);
	if (recordType !== DOWNLOAD_RECORD) {
		throw new BaltorError("response_unsupported", `The download answer is ${String(recordType)}, not ${DOWNLOAD_RECORD}. Nothing was written.`);
	}
	if (!DIGEST.test(header) || header !== expected.digest || actual !== expected.digest || reply.bytes.length !== expected.size_bytes) {
		throw new BaltorError("digest_mismatch", `The downloaded ${expected.path} does not match its published digest (published ${expected.digest}, header ${header || "missing"}, bytes ${actual}, ${reply.bytes.length} of ${expected.size_bytes} bytes). Nothing was written.`);
	}
	return { bytes: reply.bytes, recordType, header };
}

// ---------------------------------------------------------------- placement

export function nativeName(identity: string): string {
	if (identity.length > 200 || !IDENTITY.test(identity)) {
		throw new BaltorError("identity_invalid", `${JSON.stringify(identity)} is not a Baltor identity. Use an identity exactly as baltor_search returned it.`);
	}
	const name = identity.toLowerCase().replace(/[._]/g, "-");
	if (name.length > 64 || !NATIVE_NAME.test(name)) {
		throw new BaltorError("identity_has_no_skill_name", `${identity} does not map to a Pi skill name.`);
	}
	return name;
}

function checkRelativePath(value: string): string[] {
	const parts = value.split("/");
	if (!value || value.length > 200 || parts.length > MAX_PATH_DEPTH || !parts.every((part) => PATH_SEGMENT.test(part) && part !== "." && part !== "..")) {
		throw new BaltorError("package_path_refused", `The package names the file ${JSON.stringify(value)}, which is not a plain relative path. Nothing was written.`);
	}
	return parts;
}

function realDirectory(directory: string) {
	mkdirSync(directory, { recursive: true });
	const stat = lstatSync(directory);
	if (stat.isSymbolicLink() || !stat.isDirectory()) {
		throw new BaltorError("placement_refused", `${directory} is a link or not a folder, so nothing is written there.`);
	}
}

function exists(target: string) {
	try {
		lstatSync(target);
		return true;
	} catch {
		return false;
	}
}

function singleLine(text: string) {
	return text.replace(/\p{C}/gu, " ").split(/\s+/).filter(Boolean).join(" ");
}

// The header the repository's native placement tool writes: JSON strings are also YAML scalars.
export function skillHeader(name: string, purpose: string): Buffer {
	const description = singleLine(purpose).slice(0, MAX_DESCRIPTION).trimEnd();
	if (!description) throw new BaltorError("purpose_empty", "The published item has no purpose text to use as the skill description.");
	return Buffer.from(`---\nname: ${JSON.stringify(name)}\ndescription: ${JSON.stringify(description)}\n---\n`, "utf8");
}

function servedDescription(bytes: Buffer): string | null {
	try {
		const { frontmatter } = parseFrontmatter(bytes.toString("utf8"));
		return typeof frontmatter.description === "string" && frontmatter.description.trim() ? frontmatter.description : null;
	} catch {
		return null;
	}
}

function paths(cwd: string, name: string) {
	const pi = path.join(cwd, ".pi");
	return {
		pi,
		skills: path.join(pi, "skills"),
		target: path.join(pi, "skills", name),
		records: path.join(pi, "baltor", "installed"),
		record: path.join(pi, "baltor", "installed", `${name}.json`),
	};
}

export function verifyInstall(cwd: string, name: string): { ok: boolean; record: any; problems: string[] } {
	const where = paths(cwd, name);
	const problems: string[] = [];
	let record: any = null;
	try {
		if (lstatSync(where.record).isSymbolicLink()) throw new Error("link");
		record = JSON.parse(readFileSync(where.record, "utf8"));
	} catch {
		return { ok: false, record: null, problems: [`no install record at .pi/baltor/installed/${name}.json`] };
	}
	if (record?.record_type !== INSTALL_RECORD || record.native_name !== name || !Array.isArray(record.files)) {
		return { ok: false, record, problems: ["the install record is not one this extension wrote"] };
	}
	for (const file of record.files as InstalledFile[]) {
		try {
			const full = path.join(where.target, ...checkRelativePath(String(file.path)));
			if (lstatSync(full).isSymbolicLink()) throw new Error("link");
			const bytes = readFileSync(full);
			if (sha256(bytes) !== file.file_sha256) problems.push(`${file.path} changed since it was installed`);
			else if (sha256(bytes.subarray(file.header_bytes)) !== file.published_digest) problems.push(`${file.path} does not hold the published bytes`);
		} catch {
			problems.push(`${file.path} is missing`);
		}
	}
	return { ok: problems.length === 0, record, problems };
}

function piLoaderCheck(directory: string, skillFile: string) {
	const loaded = loadSkillsFromDir({ dir: directory, source: "baltor-install-check" });
	const skill = loaded.skills.find((item) => path.resolve(item.filePath) === path.resolve(skillFile));
	const warnings = loaded.diagnostics.filter((item) => path.resolve(item.path ?? "") === path.resolve(skillFile)).map((item) => item.message);
	return { loaded: Boolean(skill), name: skill?.name ?? null, warnings };
}

// One install at a time for each skill name, so parallel calls never download twice.
const installLocks = new Map<string, Promise<unknown>>();

export async function install(settings: Settings, cwd: string, identity: string, signal?: AbortSignal) {
	const name = nativeName(identity);
	const previous = installLocks.get(name) ?? Promise.resolve();
	const run = previous.catch(() => undefined).then(() => installOnce(settings, cwd, identity, name, signal));
	installLocks.set(name, run);
	try {
		return await run;
	} finally {
		if (installLocks.get(name) === run) installLocks.delete(name);
	}
}

async function installOnce(settings: Settings, cwd: string, identity: string, name: string, signal?: AbortSignal) {
	const where = paths(cwd, name);
	const relativeTarget = path.join(".pi", "skills", name);
	const token = tokenFrom(settings);
	const capabilities = await capabilitiesFor(settings, signal);
	const item = await manifest(settings, token, identity, signal);
	if (item.kind !== SKILL_KIND) {
		throw new BaltorError("kind_has_no_pi_location", `${identity} is a ${String(item.kind)} item. This version of the extension installs skills only, so nothing was downloaded.`);
	}
	if (item.body_allowed !== true) {
		throw new BaltorError("download_not_allowed", `Your Baltor account can see ${identity} but not download it, so nothing was downloaded.`);
	}
	// Already installed with the same published digest: nothing to download. A record
	// whose folder was removed is replaced by the new install.
	if (exists(where.target)) {
		const check = verifyInstall(cwd, name);
		if (check.ok && check.record.identity === identity && check.record.published_digest === item.digest) {
			return { downloaded: false, name, identity, target: relativeTarget, record: check.record, loader: piLoaderCheck(where.skills, path.join(where.target, SKILL_FILE)) };
		}
		throw new BaltorError("placement_conflict", `${relativeTarget} already exists and is not the published ${identity} (${check.problems.join("; ") || "different item or digest"}). Move that folder away to install this item. Nothing was downloaded.`);
	}

	// The package listing comes from a search result, so every file of the package is
	// installed. An identity not searched in this session is searched for once.
	let seen = searchCache.get(identity);
	if (!seen) {
		await search(settings, identity, 10, signal);
		seen = searchCache.get(identity);
	}
	if (!seen?.files?.length) {
		throw new BaltorError("package_listing_missing", `baltor_search did not return the file listing for ${identity}, so the extension cannot install every file of it. Nothing was downloaded.`);
	}
	if (seen.digest !== item.digest) {
		throw new BaltorError("item_changed", `${identity} changed after it was searched (searched ${seen.digest}, now ${item.digest}). Search again before downloading.`);
	}
	const files = seen.files;
	if (files.length > MAX_PACKAGE_FILES) throw new BaltorError("package_too_large", `${identity} holds ${files.length} files; this extension installs at most ${MAX_PACKAGE_FILES}.`);
	const seenPaths = new Set<string>();
	for (const file of files) {
		checkRelativePath(file.path);
		if (seenPaths.has(file.path)) throw new BaltorError("package_path_refused", `The package names ${file.path} twice. Nothing was written.`);
		seenPaths.add(file.path);
		if (!DIGEST.test(file.digest) || !Number.isInteger(file.size_bytes) || file.size_bytes < 0 || file.size_bytes > capabilities.fileBytes) {
			throw new BaltorError("package_invalid", `The package entry ${file.path} has no usable digest or size. Nothing was written.`);
		}
	}
	const skillEntry = files.find((file) => file.path === SKILL_FILE);
	if (!skillEntry) throw new BaltorError("package_invalid", `${identity} is a skill package without ${SKILL_FILE}. Nothing was written.`);
	// A package with one SKILL.md whose digest is the item's digest is the item body itself.
	const bodyOnly = files.length === 1 && skillEntry.digest === item.digest;

	realDirectory(where.pi);
	realDirectory(where.skills);
	const stagingRoot = path.join(where.skills, `${STAGING_PREFIX}${randomUUID()}`);
	const staged = path.join(stagingRoot, name);
	const requestId = `pi-${randomUUID()}`;
	try {
		mkdirSync(staged, { recursive: true });
		const installed: InstalledFile[] = [];
		let rendering = RENDER_UNCHANGED;
		for (const file of files) {
			const { bytes, recordType, header: digestHeader } = await downloadFile(
				settings,
				token,
				{ identity, requestId, itemDigest: item.digest, path: bodyOnly ? undefined : file.path },
				file,
				capabilities.fileBytes,
				signal,
			);
			let header = Buffer.alloc(0);
			if (file.path === SKILL_FILE && servedDescription(bytes) === null) {
				header = skillHeader(name, String(item.purpose ?? ""));
				rendering = RENDER_HEADER;
			}
			const content = Buffer.concat([header, bytes]);
			const full = path.join(staged, ...checkRelativePath(file.path));
			mkdirSync(path.dirname(full), { recursive: true });
			writeFileSync(full, content, { flag: "wx", mode: 0o644 });
			installed.push({
				path: file.path,
				published_digest: file.digest,
				header_bytes: header.length,
				file_sha256: sha256(content),
				size_bytes: bytes.length,
				response: { record_type: recordType, content_sha256: digestHeader },
			});
		}
		// Pi's own skill loader decides whether this folder is a skill before it is moved into place.
		const loader = piLoaderCheck(stagingRoot, path.join(staged, SKILL_FILE));
		if (!loader.loaded) {
			throw new BaltorError("pi_would_not_load", `Pi's skill loader does not accept the downloaded ${SKILL_FILE} (${loader.warnings.join("; ") || "no reason given"}). Nothing was installed.`);
		}
		if (exists(where.target)) {
			throw new BaltorError("placement_conflict", `${relativeTarget} appeared while the item was downloading. Nothing was installed.`);
		}
		renameSync(staged, where.target);
		const record = {
			record_type: INSTALL_RECORD,
			extension: EXTENSION_RECORD,
			identity,
			native_name: name,
			kind: item.kind,
			service_origin: settings.origin,
			catalogue_release: seen?.catalogue_release ?? null,
			request_id: requestId,
			installed_at: new Date().toISOString(),
			published_digest: item.digest,
			license: item.license ?? null,
			rendering,
			files: installed,
			pi_loader: { loaded: loader.loaded, name: loader.name, warnings: loader.warnings },
		};
		realDirectory(path.join(where.pi, "baltor"));
		realDirectory(where.records);
		writeFileSync(where.record, `${JSON.stringify(record, null, 2)}\n`, { mode: 0o644 });
		return { downloaded: true, name, identity, target: relativeTarget, record, loader };
	} finally {
		rmSync(stagingRoot, { recursive: true, force: true });
	}
}

// ---------------------------------------------------------------- status

export async function statusLines(cwd: string, signal?: AbortSignal): Promise<{ ready: boolean; lines: string[] }> {
	const lines = [`Baltor extension for Pi (${EXTENSION_RECORD})`];
	let ready = true;
	let settings: Settings;
	try {
		settings = readSettings(cwd);
	} catch (error) {
		return { ready: false, lines: [...lines, `Configuration: refused. ${(error as Error).message}`, "Result: not ready"] };
	}
	lines.push(`Configuration: ${settings.source} (service ${settings.origin}, token variable ${settings.tokenVariable})`);
	const tokenSet = Boolean((process.env[settings.tokenVariable] ?? "").trim());
	lines.push(`Token variable: ${tokenSet ? "set (the value is never shown)" : "not set"}`);
	if (!tokenSet) ready = false;
	try {
		const capabilities = await capabilitiesFor(settings, signal);
		lines.push(`Service: reachable, interface v1, search request ${capabilities.retrievalRequest}${capabilities.retrievalDeclared ? "" : " (the release does not declare one)"}`);
		if (tokenSet) {
			const session = serviceResult(await exchange(settings, "/api/v1/session", { method: "GET", token: tokenFrom(settings), maxBytes: MAX_JSON_BYTES, signal }), "session");
			const principal = isTable(session.principal) ? session.principal : {};
			const scopes = Array.isArray(principal.scopes) ? principal.scopes.join(", ") : "unknown";
			lines.push(`Token: accepted for account ${String(principal.tenant_id)} with scopes ${scopes}`);
			try {
				const usage = serviceResult(await exchange(settings, "/api/v1/usage", { method: "GET", token: tokenFrom(settings), maxBytes: MAX_JSON_BYTES, signal }), "usage");
				lines.push(`Downloads counted on this account: ${JSON.stringify(usage.totals ?? {})}`);
			} catch (error) {
				lines.push(`Usage: not shown. ${(error as Error).message}`);
			}
		}
	} catch (error) {
		ready = false;
		lines.push(`Service: ${(error as Error).message}`);
	}
	const skills = path.join(cwd, ".pi", "skills");
	const records = path.join(cwd, ".pi", "baltor", "installed");
	const names = exists(records) ? readdirSync(records).filter((file) => file.endsWith(".json")).map((file) => file.slice(0, -5)) : [];
	lines.push(`Installed Baltor skills: ${names.length}`);
	for (const name of names) {
		const check = verifyInstall(cwd, name);
		const loader = exists(path.join(skills, name, SKILL_FILE)) ? piLoaderCheck(skills, path.join(skills, name, SKILL_FILE)) : { loaded: false, warnings: [] };
		lines.push(`  ${name}: item ${String(check.record?.identity)}, published digest ${check.ok ? "verified" : `not verified (${check.problems.join("; ")})`}, Pi skill loader ${loader.loaded ? "accepts it" : "does not accept it"}`);
		if (!check.ok || !loader.loaded) ready = false;
	}
	lines.push(`Result: ${ready ? "ready" : "not ready"}`);
	return { ready, lines };
}

// ---------------------------------------------------------------- Pi wiring

function redact(text: string, secret: string, variable: string) {
	return secret && text.includes(secret) ? text.split(secret).join(`[${variable} hidden]`) : text;
}

export default function baltor(pi: ExtensionAPI) {
	pi.registerFlag("baltor-check", {
		description: "Print the Baltor configuration, connection and install check (use with -p)",
		type: "boolean",
		default: false,
	});

	pi.registerTool({
		name: "baltor_search",
		label: "Baltor search",
		description:
			"Search the Baltor library of harness files (skills, instructions, tools) by what they do. Returns references only: identity, kind, purpose, size, licence and published digest. It never returns file bodies and never downloads anything.",
		promptSnippet: "Search the Baltor library for published skills that fit the task",
		promptGuidelines: [
			"Use baltor_search to look for a published Baltor skill before writing a procedure for a task from scratch.",
			"Use baltor_download with an identity returned by baltor_search to install that skill into .pi/skills; each download counts as usage on the Baltor account, so download only what the task needs.",
		],
		parameters: Type.Object({
			query: Type.String({ description: "What the skill should do, in plain words", minLength: 1, maxLength: 1000 }),
			limit: Type.Optional(Type.Integer({ description: "How many references to return, 1 to 20 (default 5)", minimum: 1, maximum: 20 })),
		}),
		async execute(_toolCallId, params, signal, _onUpdate, ctx) {
			const settings = readSettings(ctx.cwd);
			const found = await search(settings, params.query, params.limit ?? 5, signal);
			const lines = [
				`Baltor search for ${JSON.stringify(params.query)}: ${found.hits.length} reference(s)${found.release ? ` from catalogue release ${found.release.slice(0, 12)}` : ""}. Nothing was downloaded.`,
			];
			found.hits.forEach((hit, index) => {
				lines.push(`${index + 1}. ${hit.identity}`);
				lines.push(`   ${hit.kind}, ${hit.size_bytes} bytes, licence ${hit.license}, digest ${hit.digest.slice(0, 12)}, ${hit.body_allowed ? "you may download it" : "search only for your account"}`);
				lines.push(`   ${hit.purpose}`);
				if (hit.files?.length) lines.push(`   files: ${hit.files.map((file) => file.path).join(", ")}`);
			});
			if (found.hits.length) lines.push("To install one, call baltor_download with its identity.");
			return { content: [{ type: "text", text: lines.join("\n") }], details: { release: found.release, request: found.request, hits: found.hits } };
		},
	});

	pi.registerTool({
		name: "baltor_download",
		label: "Baltor download",
		description:
			"Download one published Baltor skill by its identity and install it in this project's .pi/skills/<name>/ folder. The published SHA-256 digest is checked against the manifest, the response header and the bytes before anything is written. An item that is already installed with the same digest is not downloaded again.",
		promptSnippet: "Install a skill found with baltor_search into .pi/skills",
		parameters: Type.Object({
			identity: Type.String({ description: "The identity exactly as baltor_search returned it", minLength: 1, maxLength: 200 }),
		}),
		async execute(_toolCallId, params, signal, _onUpdate, ctx) {
			const settings = readSettings(ctx.cwd);
			const result = await install(settings, ctx.cwd, params.identity.trim(), signal);
			const file = path.join(result.target, SKILL_FILE);
			const record = result.record;
			const lines = [
				result.downloaded
					? `Installed Baltor item ${result.identity} as the Pi skill ${result.name}.`
					: `${result.identity} is already installed as the Pi skill ${result.name} with the same published digest. Nothing was downloaded.`,
				`Pi skill name: ${result.name}`,
				`Folder: ${result.target}${path.sep}`,
				`Published SHA-256 digest: ${record.published_digest}. It matched the manifest, the response header and the downloaded bytes.`,
				record.rendering === RENDER_HEADER
					? `${SKILL_FILE} holds a generated name and description header, which Pi needs, followed by the published file byte for byte.`
					: `${SKILL_FILE} is the published file byte for byte.`,
				`Pi's skill loader ${result.loader.loaded ? "accepts" : "does not accept"} the installed skill. Pi lists it from the next session; to use it now, read ${file}.`,
			];
			return {
				content: [{ type: "text", text: lines.join("\n") }],
				details: { downloaded: result.downloaded, name: result.name, identity: result.identity, file, request_id: record.request_id, published_digest: record.published_digest, rendering: record.rendering },
			};
		},
	});

	pi.registerCommand("baltor", {
		description: "Show the Baltor configuration, connection and installed skills",
		handler: async (_args, ctx) => {
			const report = await statusLines(ctx.cwd);
			if (ctx.hasUI) ctx.ui.notify(report.lines.join("\n"), report.ready ? "info" : "warning");
			else process.stderr.write(`${report.lines.join("\n")}\n`);
		},
	});

	pi.on("session_start", async (event, ctx) => {
		if (event.reason !== "startup" || pi.getFlag("baltor-check") !== true) return;
		const report = await statusLines(ctx.cwd);
		if (ctx.hasUI) ctx.ui.notify(report.lines.join("\n"), report.ready ? "info" : "warning");
		else process.stderr.write(`${report.lines.join("\n")}\n`);
	});

	// An exact copy of the token never reaches the model or the session through a tool result,
	// for example from a shell command that prints the environment. A transformed copy is not caught.
	pi.on("tool_result", async (event, ctx) => {
		let variable = DEFAULT_TOKEN_VARIABLE;
		try {
			variable = readSettings(ctx.cwd).tokenVariable;
		} catch {}
		const secret = (process.env[variable] ?? "").trim();
		if (!secret) return;
		let changed = false;
		const content = event.content.map((part: any) => {
			if (part?.type !== "text" || typeof part.text !== "string" || !part.text.includes(secret)) return part;
			changed = true;
			return { ...part, text: redact(part.text, secret, variable) };
		});
		let details = event.details;
		try {
			const text = details === undefined ? "" : JSON.stringify(details);
			if (text && text.includes(secret)) {
				details = JSON.parse(redact(text, secret, variable));
				changed = true;
			}
		} catch {
			details = { note: "details removed because they could not be checked for the token" };
			changed = true;
		}
		if (changed) return { content, details };
	});
}
