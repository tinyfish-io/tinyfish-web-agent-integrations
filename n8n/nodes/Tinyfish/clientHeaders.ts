import { version } from '../../package.json';

// Without these the server files every call as untagged `api`.
export const CLIENT_HEADERS: Record<string, string> = {
	'X-TF-Client-Name': 'tinyfish-n8n',
	'X-TF-Client-Version': version,
};
