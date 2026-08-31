import type { INodeProperties } from 'n8n-workflow';

export const operationField: INodeProperties = {
	displayName: 'Operation',
	name: 'operation',
	type: 'options',
	noDataExpression: true,
	default: 'runSse',
	options: [
		{
			name: 'Create Browser Session',
			value: 'createBrowserSession',
			action: 'Create browser session',
			description: 'Create a remote browser session and return CDP connection details',
		},
		{
			name: 'Fetch Content',
			value: 'fetchContent',
			action: 'Fetch and extract content from urls',
			description: 'Render up to 10 URLs and return clean extracted page content',
		},
		{
			name: 'Get Run',
			value: 'getRun',
			action: 'Get run details',
			description: 'Retrieve the status and result of a previously started async run by its ID',
		},
		{
			name: 'List Runs',
			value: 'listRuns',
			action: 'List automation runs',
			description:
				'List past automation runs with optional status filter. Useful for monitoring or retrieving results.',
		},
		{
			name: 'Run (Async)',
			value: 'runAsync',
			action: 'Run automation asynchronously',
			description:
				'Returns a run ID immediately without waiting. Use with Get Run to poll for results. Best for batch processing multiple URLs in parallel.',
		},
		{
			name: 'Run (SSE Streaming)',
			value: 'runSse',
			action: 'Run automation with SSE streaming',
			description:
				'Recommended for most tasks. Streams real-time progress events and returns the final result. Best for tasks that may take 30+ seconds.',
		},
		{
			name: 'Run (Sync)',
			value: 'runSync',
			action: 'Run automation synchronously',
			description:
				'Execute and wait for the complete result in a single response. Use for quick extractions under 60 seconds.',
		},
		{
			name: 'Search Web',
			value: 'searchWeb',
			action: 'Search web',
			description: 'Search the web and return structured results with titles, snippets, and URLs',
		},
		{
			name: 'Terminate Browser Session',
			value: 'terminateBrowserSession',
			action: 'Terminate browser session',
			description: 'Terminate a remote browser session by session ID',
		},
	],
};

export const runFields: INodeProperties[] = [
	{
		displayName: 'URL',
		name: 'url',
		type: 'string',
		default: '',
		required: true,
		validateType: 'url',
		placeholder: 'https://example.com',
		description:
			'The website URL to navigate to. Must include https://. The AI browser will load this page and execute the goal.',
		displayOptions: {
			show: {
				operation: ['runSse', 'runSync', 'runAsync'],
			},
		},
	},
	{
		displayName: 'Goal',
		name: 'goal',
		type: 'string',
		typeOptions: { rows: 4 },
		default: '',
		required: true,
		placeholder:
			'Extract all product names and prices. Return as JSON array with keys: name, price.',
		description:
			'Natural language instruction for what to accomplish on the website. For best results: specify the exact JSON schema you want returned, include termination conditions (e.g., stop after 20 items), and handle edge cases explicitly (e.g., if price shows Contact Us, set to null). Use numbered steps for multi-step workflows.',
		displayOptions: {
			show: {
				operation: ['runSse', 'runSync', 'runAsync'],
			},
		},
	},
	{
		displayName: 'Options',
		name: 'options',
		type: 'collection',
		placeholder: 'Add Option',
		default: {},
		displayOptions: {
			show: {
				operation: ['runSse', 'runSync', 'runAsync'],
			},
		},
		options: [
			{
				displayName: 'Browser Profile',
				name: 'browserProfile',
				type: 'options',
				default: 'lite',
				description:
					'Browser profile to use for execution. Start with Lite for speed; switch to Stealth if you get blocked.',
				options: [
					{
						name: 'Lite (Standard)',
						value: 'lite',
						description: 'Fast standard browser for sites without bot protection',
					},
					{
						name: 'Stealth (Anti-Detection)',
						value: 'stealth',
						description:
							'Anti-detection browser for sites with Cloudflare, DataDome, or CAPTCHAs. Slower but bypasses bot detection. Pair with proxy for best results.',
					},
				],
			},
			{
				displayName: 'Enable Proxy',
				name: 'proxyEnabled',
				type: 'boolean',
				default: false,
				description:
					'Whether to route the browser through a geographic proxy. Recommended when using Stealth mode for geo-restricted or bot-protected sites.',
			},
			{
				displayName: 'Proxy Country',
				name: 'proxyCountryCode',
				type: 'options',
				default: 'US',
				description:
					"Geographic location for the proxy. Choose the country closest to the target site's expected region.",
				displayOptions: {
					show: {
						proxyEnabled: [true],
					},
				},
				options: [
					{ name: 'Australia', value: 'AU' },
					{ name: 'Canada', value: 'CA' },
					{ name: 'France', value: 'FR' },
					{ name: 'Germany', value: 'DE' },
					{ name: 'Japan', value: 'JP' },
					{ name: 'United Kingdom', value: 'GB' },
					{ name: 'United States', value: 'US' },
				],
			},
		],
	},
];

export const getRunFields: INodeProperties[] = [
	{
		displayName: 'Run ID',
		name: 'runId',
		type: 'string',
		default: '',
		required: true,
		placeholder: 'run_abc123',
		description: 'The ID of the automation run to retrieve',
		displayOptions: {
			show: {
				operation: ['getRun'],
			},
		},
	},
];

export const listRunsFields: INodeProperties[] = [
	{
		displayName: 'Return All',
		name: 'returnAll',
		type: 'boolean',
		default: false,
		description: 'Whether to return all results or only up to a given limit',
		displayOptions: {
			show: {
				operation: ['listRuns'],
			},
		},
	},
	{
		displayName: 'Limit',
		name: 'limit',
		type: 'number',
		default: 50,
		description: 'Max number of results to return',
		typeOptions: {
			minValue: 1,
			maxValue: 100,
		},
		displayOptions: {
			show: {
				operation: ['listRuns'],
				returnAll: [false],
			},
		},
	},
	{
		displayName: 'Filters',
		name: 'filters',
		type: 'collection',
		placeholder: 'Add Filter',
		default: {},
		displayOptions: {
			show: {
				operation: ['listRuns'],
			},
		},
		options: [
			{
				displayName: 'Status',
				name: 'status',
				type: 'options',
				default: '',
				description: 'Filter runs by status',
				options: [
					{ name: 'All', value: '' },
					{ name: 'Cancelled', value: 'CANCELLED' },
					{ name: 'Completed', value: 'COMPLETED' },
					{ name: 'Failed', value: 'FAILED' },
					{ name: 'Pending', value: 'PENDING' },
					{ name: 'Running', value: 'RUNNING' },
				],
			},
		],
	},
];

export const searchWebFields: INodeProperties[] = [
	{
		displayName: 'Query',
		name: 'searchQuery',
		type: 'string',
		default: '',
		required: true,
		placeholder: 'web automation tools',
		description:
			'Search query. Supports search operators such as site:example.com and -site:example.com.',
		displayOptions: {
			show: {
				operation: ['searchWeb'],
			},
		},
	},
	{
		displayName: 'Options',
		name: 'searchOptions',
		type: 'collection',
		placeholder: 'Add Option',
		default: {},
		displayOptions: {
			show: {
				operation: ['searchWeb'],
			},
		},
		options: [
			{
				displayName: 'Language',
				name: 'language',
				type: 'string',
				default: '',
				placeholder: 'en',
				description: 'Language code for result language, e.g. en, fr, or de',
			},
			{
				displayName: 'Location',
				name: 'location',
				type: 'string',
				default: '',
				placeholder: 'US',
				description: 'Country code for geo-targeted results, e.g. US, GB, FR, or DE',
			},
			{
				displayName: 'Page',
				name: 'page',
				type: 'number',
				default: 0,
				description: 'Page number for pagination, starting from 0',
				typeOptions: {
					minValue: 0,
					maxValue: 10,
				},
			},
		],
	},
];

export const fetchContentFields: INodeProperties[] = [
	{
		displayName: 'URLs',
		name: 'fetchUrls',
		type: 'string',
		typeOptions: { rows: 4 },
		default: '',
		required: true,
		placeholder: 'https://example.com\nhttps://docs.tinyfish.ai',
		description: 'URLs to fetch, one per line. Maximum 10 URLs per request.',
		displayOptions: {
			show: {
				operation: ['fetchContent'],
			},
		},
	},
	{
		displayName: 'Options',
		name: 'fetchOptions',
		type: 'collection',
		placeholder: 'Add Option',
		default: {},
		displayOptions: {
			show: {
				operation: ['fetchContent'],
			},
		},
		options: [
			{
				displayName: 'Format',
				name: 'format',
				type: 'options',
				default: 'markdown',
				description: 'Output format for the extracted text field',
				options: [
					{ name: 'HTML', value: 'html' },
					{ name: 'JSON', value: 'json' },
					{ name: 'Markdown', value: 'markdown' },
				],
			},
			{
				displayName: 'Include Image Links',
				name: 'imageLinks',
				type: 'boolean',
				default: false,
				description: 'Whether to include all image URLs found on each page',
			},
			{
				displayName: 'Include Links',
				name: 'links',
				type: 'boolean',
				default: false,
				description: 'Whether to include all links found on each page',
			},
			{
				displayName: 'Proxy Country',
				name: 'proxyCountryCode',
				type: 'options',
				default: '',
				description: 'Optional country code for routing fetch requests through a TinyFish proxy',
				options: [
					{ name: 'Australia', value: 'AU' },
					{ name: 'Canada', value: 'CA' },
					{ name: 'France', value: 'FR' },
					{ name: 'Germany', value: 'DE' },
					{ name: 'Japan', value: 'JP' },
					{ name: 'None', value: '' },
					{ name: 'United Kingdom', value: 'GB' },
					{ name: 'United States', value: 'US' },
				],
			},
		],
	},
];

export const createBrowserSessionFields: INodeProperties[] = [
	{
		displayName: 'URL',
		name: 'browserUrl',
		type: 'string',
		default: '',
		placeholder: 'https://example.com',
		description: 'Optional URL to navigate to when the browser session starts',
		displayOptions: {
			show: {
				operation: ['createBrowserSession'],
			},
		},
	},
	{
		displayName: 'Options',
		name: 'browserOptions',
		type: 'collection',
		placeholder: 'Add Option',
		default: {},
		displayOptions: {
			show: {
				operation: ['createBrowserSession'],
			},
		},
		options: [
			{
				displayName: 'Timeout Seconds',
				name: 'timeoutSeconds',
				type: 'number',
				default: 300,
				description: 'Inactivity timeout in seconds. Plan limits may cap this value.',
				typeOptions: {
					minValue: 5,
					maxValue: 86400,
				},
			},
		],
	},
];

export const terminateBrowserSessionFields: INodeProperties[] = [
	{
		displayName: 'Session ID',
		name: 'sessionId',
		type: 'string',
		default: '',
		required: true,
		placeholder: 'br-a1b2c3d4-e5f6-7890-abcd-ef1234567890',
		description: 'The browser session ID to terminate',
		displayOptions: {
			show: {
				operation: ['terminateBrowserSession'],
			},
		},
	},
];
