import type {
	IDataObject,
	IExecuteFunctions,
	IHttpRequestMethods,
	IHttpRequestOptions,
	JsonObject,
} from 'n8n-workflow';
import { NodeApiError, NodeOperationError } from 'n8n-workflow';

export const AGENT_API_BASE_URL = 'https://agent.tinyfish.ai';
export const BROWSER_API_BASE_URL = 'https://api.browser.tinyfish.ai';
export const FETCH_API_BASE_URL = 'https://api.fetch.tinyfish.ai';
export const SEARCH_API_BASE_URL = 'https://api.search.tinyfish.ai';

/**
 * Map known TinyFish API error codes to actionable user messages.
 */
function getActionableMessage(error: unknown): string | undefined {
	const cause = (error as Record<string, unknown>)?.cause as Record<string, unknown> | undefined;
	const body = cause?.body as Record<string, unknown> | undefined;
	const errorObj = body?.error as Record<string, unknown> | undefined;

	if (!errorObj) return undefined;

	const code = errorObj.code as string | undefined;
	const message = errorObj.message as string | undefined;
	const details = errorObj.details as Record<string, string> | undefined;

	switch (code) {
		case 'MISSING_API_KEY':
			return 'API key is missing. Add your TinyFish API key in the node credentials.';
		case 'INVALID_API_KEY':
			return 'Invalid API key. Verify your key at https://agent.tinyfish.ai/api-keys or generate a new one.';
		case 'UNAUTHORIZED':
			return 'Authentication failed. Check your account status at https://agent.tinyfish.ai/api-keys.';
		case 'FORBIDDEN':
			return 'Insufficient credits or no active subscription. Check your account at https://agent.tinyfish.ai/api-keys.';
		case 'NOT_FOUND':
			return `${message || 'Resource not found'}. Verify the run ID is correct.`;
		case 'INVALID_INPUT': {
			if (details) {
				const detailStr = Object.entries(details)
					.map(([k, v]) => `${k}: ${v}`)
					.join(', ');
				return `Invalid input (${detailStr}). Check your URL and goal parameters.`;
			}
			return `Invalid input: ${message || 'Validation failed'}. Check your URL and goal parameters.`;
		}
		case 'RATE_LIMIT_EXCEEDED':
			return 'Rate limit exceeded. Wait a few minutes and try again, or reduce request frequency.';
		case 'INTERNAL_ERROR':
			return `TinyFish server error: ${message || 'An unexpected error occurred'}. Try again later.`;
		default:
			return undefined;
	}
}

/**
 * Make an authenticated request to the TinyFish API.
 */
export async function tinyfishApiRequest(
	this: IExecuteFunctions,
	method: IHttpRequestMethods,
	path: string,
	body: IDataObject = {},
	qs: IDataObject = {},
	options: Partial<IHttpRequestOptions> = {},
): Promise<IDataObject> {
	const requestOptions: IHttpRequestOptions = {
		method,
		url: path.startsWith('http') ? path : `${AGENT_API_BASE_URL}${path}`,
		qs,
		json: true,
		...options,
	};

	if (Object.keys(body).length > 0) {
		requestOptions.body = body;
	}

	try {
		const response = await this.helpers.httpRequestWithAuthentication.call(
			this,
			'tinyfishApi',
			requestOptions,
		);

		return (response ?? {}) as IDataObject;
	} catch (error) {
		const actionableMessage = getActionableMessage(error);
		if (actionableMessage) {
			throw new NodeApiError(this.getNode(), error as JsonObject, {
				message: actionableMessage,
			});
		}
		throw new NodeApiError(this.getNode(), error as JsonObject);
	}
}

/**
 * Build the automation payload from node parameters.
 * Mirrors dify/tools/base.py _build_automation_payload().
 */
export function buildAutomationPayload(this: IExecuteFunctions, itemIndex: number): IDataObject {
	const url = this.getNodeParameter('url', itemIndex) as string;
	const goal = this.getNodeParameter('goal', itemIndex) as string;
	const options = this.getNodeParameter('options', itemIndex, {}) as IDataObject;

	const payload: IDataObject = {
		url,
		goal,
		browser_profile: (options.browserProfile as string) || 'lite',
		api_integration: 'n8n',
	};

	if (options.proxyEnabled) {
		const proxyConfig: IDataObject = { enabled: true };
		if (options.proxyCountryCode) {
			proxyConfig.country_code = options.proxyCountryCode as string;
		}
		payload.proxy_config = proxyConfig;
	}

	return payload;
}

export function buildSearchQuery(this: IExecuteFunctions, itemIndex: number): IDataObject {
	const query = this.getNodeParameter('searchQuery', itemIndex) as string;
	const options = this.getNodeParameter('searchOptions', itemIndex, {}) as IDataObject;

	const qs: IDataObject = { query };

	if (options.location) {
		qs.location = options.location as string;
	}
	if (options.language) {
		qs.language = options.language as string;
	}
	if (options.page !== undefined) {
		qs.page = options.page as number;
	}

	return qs;
}

export function buildFetchPayload(this: IExecuteFunctions, itemIndex: number): IDataObject {
	const fetchUrls = this.getNodeParameter('fetchUrls', itemIndex) as string;
	const options = this.getNodeParameter('fetchOptions', itemIndex, {}) as IDataObject;
	const urls = fetchUrls
		.split(/[\n,]/)
		.map((url) => url.trim())
		.filter(Boolean);

	if (urls.length === 0) {
		throw new NodeOperationError(this.getNode(), 'At least one URL is required', {
			itemIndex,
		});
	}

	if (urls.length > 10) {
		throw new NodeOperationError(this.getNode(), 'Fetch Content accepts a maximum of 10 URLs', {
			itemIndex,
		});
	}

	const payload: IDataObject = {
		urls,
		format: (options.format as string) || 'markdown',
		links: Boolean(options.links),
		image_links: Boolean(options.imageLinks),
	};

	if (options.proxyCountryCode) {
		payload.proxy_config = {
			country_code: options.proxyCountryCode as string,
		};
	}

	return payload;
}

export function buildBrowserSessionPayload(
	this: IExecuteFunctions,
	itemIndex: number,
): IDataObject {
	const url = this.getNodeParameter('browserUrl', itemIndex, '') as string;
	const options = this.getNodeParameter('browserOptions', itemIndex, {}) as IDataObject;
	const payload: IDataObject = {};

	if (url.trim()) {
		payload.url = url.trim();
	}

	if (options.timeoutSeconds !== undefined) {
		payload.timeout_seconds = options.timeoutSeconds as number;
	}

	return payload;
}

/**
 * Consume an SSE stream from the TinyFish run-sse endpoint.
 * Uses native fetch() for streaming support.
 * Returns the final COMPLETE result as structured JSON.
 */
export async function consumeSseStream(
	this: IExecuteFunctions,
	payload: IDataObject,
): Promise<IDataObject> {
	const credentials = await this.getCredentials('tinyfishApi');
	const apiKey = credentials.apiKey as string;

	let lastProgress = '';

	const response = await fetch(`${AGENT_API_BASE_URL}/v1/automation/run-sse`, {
		method: 'POST',
		headers: {
			'X-API-Key': apiKey,
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(payload),
	});

	if (!response.ok) {
		const errorText = await response.text();
		throw new NodeOperationError(
			this.getNode(),
			`API request failed with status ${response.status}: ${errorText}`,
		);
	}

	if (!response.body) {
		throw new NodeOperationError(this.getNode(), 'Response body is empty');
	}

	const reader = response.body.getReader();
	const decoder = new TextDecoder();
	let buffer = '';
	let finalResult: IDataObject | null = null;
	let runId = '';
	let streamingUrl = '';

	while (true) {
		const { done, value } = await reader.read();

		buffer += decoder.decode(value, { stream: true });
		if (done) {
			buffer += decoder.decode();
		}
		const lines = buffer.split('\n');
		buffer = lines.pop() ?? '';

		for (const line of lines) {
			if (!line.startsWith('data: ')) continue;

			let eventData: IDataObject;
			try {
				eventData = JSON.parse(line.slice(6)) as IDataObject;
			} catch {
				continue;
			}

			const eventType = eventData.type as string;

			if (eventType === 'STARTED') {
				runId = (eventData.run_id as string) || (eventData.runId as string) || '';
			} else if (eventType === 'STREAMING_URL') {
				streamingUrl =
					(eventData.streaming_url as string) || (eventData.streamingUrl as string) || '';
			} else if (eventType === 'PROGRESS') {
				lastProgress = (eventData.purpose as string) || '';
			} else if (eventType === 'COMPLETE') {
				const status = eventData.status as string;
				if (status === 'COMPLETED') {
					finalResult = {
						status: 'COMPLETED',
						runId,
						streamingUrl,
						lastProgress,
						result: eventData.result || eventData.resultJson || {},
					};
				} else {
					finalResult = {
						status: status || 'FAILED',
						runId,
						lastProgress,
						error: eventData.error || 'Unknown error',
					};
				}
			}
		}

		if (done) break;
	}

	if (!finalResult) {
		throw new NodeOperationError(this.getNode(), 'SSE stream ended without a COMPLETE event');
	}

	return finalResult;
}
