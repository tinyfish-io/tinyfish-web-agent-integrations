import { version } from '../../package.json';

// Without these, telemetry cannot tell the node from raw curl.
export const CLIENT_HEADERS = {
	'X-TF-Client-Name': 'n8n',
	'X-TF-Client-Version': version,
};
