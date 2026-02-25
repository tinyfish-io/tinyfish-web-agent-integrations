import type {
	IAuthenticateGeneric,
	ICredentialTestRequest,
	ICredentialType,
	INodeProperties,
} from 'n8n-workflow';

export class TinyfishApi implements ICredentialType {
	name = 'tinyfishApi';

	displayName = 'TinyFish Web Agent API';

	icon = 'file:tinyfish.svg' as const;

	documentationUrl = 'https://docs.mino.ai';

	properties: INodeProperties[] = [
		{
			displayName: 'API Key',
			name: 'apiKey',
			type: 'string',
			typeOptions: { password: true },
			default: '',
			required: true,
			description:
				'Your TinyFish Web Agent API key. Get one at https://agent.tinyfish.ai/api-keys.',
		},
	];

	authenticate: IAuthenticateGeneric = {
		type: 'generic',
		properties: {
			headers: {
				'X-API-Key': '={{$credentials.apiKey}}',
			},
		},
	};

	test: ICredentialTestRequest = {
		request: {
			baseURL: 'https://agent.tinyfish.ai',
			url: '/v1/runs',
			method: 'GET',
			qs: { limit: '1' },
		},
	};
}
