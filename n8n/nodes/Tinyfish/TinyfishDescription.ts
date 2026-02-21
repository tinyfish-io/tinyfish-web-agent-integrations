import type { INodeProperties } from 'n8n-workflow';

export const operationField: INodeProperties = {
	displayName: 'Operation',
	name: 'operation',
	type: 'options',
	default: 'runSse',
	options: [
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
			description: 'Execute and wait for the complete result in a single response. Use for quick extractions under 60 seconds.',
		},
		{
			name: 'Run (Async)',
			value: 'runAsync',
			action: 'Run automation asynchronously',
			description: 'Returns a run ID immediately without waiting. Use with Get Run to poll for results. Best for batch processing multiple URLs in parallel.',
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
			description: 'List past automation runs with optional status filter. Useful for monitoring or retrieving results.',
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
		description: 'The website URL to navigate to. Must include https://. The AI browser will load this page and execute the goal.',
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
		placeholder: 'Extract all product names and prices. Return as JSON array with keys: name, price.',
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
				description: 'Browser profile to use for execution. Start with Lite for speed; switch to Stealth if you get blocked.',
				options: [
					{
						name: 'Lite (Standard)',
						value: 'lite',
						description:
							'Fast standard browser for sites without bot protection',
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
				description: 'Whether to route the browser through a geographic proxy. Recommended when using Stealth mode for geo-restricted or bot-protected sites.',
			},
			{
				displayName: 'Proxy Country',
				name: 'proxyCountryCode',
				type: 'options',
				default: 'US',
				description: 'Geographic location for the proxy. Choose the country closest to the target site\'s expected region.',
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
			{
				displayName: 'Timeout (Seconds)',
				name: 'timeout',
				type: 'number',
				default: 300,
				description:
					'Maximum time to wait for automation to complete (30-600s). Most tasks complete within 60-120 seconds. Increase for complex multi-step workflows.',
				typeOptions: {
					minValue: 30,
					maxValue: 600,
				},
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
		default: 20,
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
