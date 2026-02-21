import type {
	IDataObject,
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
} from 'n8n-workflow';
import { NodeOperationError } from 'n8n-workflow';

import {
	operationField,
	runFields,
	getRunFields,
	listRunsFields,
} from './TinyfishDescription';
import {
	tinyfishApiRequest,
	buildAutomationPayload,
	consumeSseStream,
} from './GenericFunctions';

const MAX_PAGINATION_ITEMS = 10_000;

export class Tinyfish implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'TinyFish Web Agent',
		name: 'tinyfish',
		icon: 'file:tinyfish.svg',
		group: ['output'],
		version: 1,
		subtitle: '={{$parameter["operation"]}}',
		description:
			'Extract data, fill forms, and automate multi-step browser workflows using natural language',
		defaults: {
			name: 'TinyFish Web Agent',
		},
		inputs: ['main'],
		outputs: ['main'],
		usableAsTool: true,
		credentials: [
			{
				name: 'tinyfishApi',
				required: true,
			},
		],
		properties: [operationField, ...runFields, ...getRunFields, ...listRunsFields],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];
		const operation = this.getNodeParameter('operation', 0) as string;

		for (let i = 0; i < items.length; i++) {
			try {
				let responseData: IDataObject;

				if (operation === 'runSse') {
					const payload = buildAutomationPayload.call(this, i);
					responseData = await consumeSseStream.call(
						this,
						payload,
					);
				} else if (operation === 'runSync') {
					const payload = buildAutomationPayload.call(this, i);
					responseData = await tinyfishApiRequest.call(
						this,
						'POST',
						'/v1/automation/run',
						payload,
					);
				} else if (operation === 'runAsync') {
					const payload = buildAutomationPayload.call(this, i);
					responseData = await tinyfishApiRequest.call(
						this,
						'POST',
						'/v1/automation/run-async',
						payload,
					);
				} else if (operation === 'getRun') {
					const runId = this.getNodeParameter('runId', i) as string;
					responseData = await tinyfishApiRequest.call(
						this,
						'GET',
						`/v1/runs/${runId}`,
					);
				} else if (operation === 'listRuns') {
					const returnAll = this.getNodeParameter('returnAll', i) as boolean;
					const filters = this.getNodeParameter(
						'filters',
						i,
						{},
					) as IDataObject;
					const qs: IDataObject = {};

					if (filters.status) {
						qs.status = filters.status;
					}

					if (returnAll) {
						const allRuns: IDataObject[] = [];
						let cursor: string | undefined;

						do {
							if (cursor) qs.cursor = cursor;
							qs.limit = 100;

							const page = await tinyfishApiRequest.call(
								this,
								'GET',
								'/v1/runs',
								{},
								qs,
							);

							const data = (page.data as IDataObject[]) || [];
							allRuns.push(...data);

							if (allRuns.length >= MAX_PAGINATION_ITEMS) {
								break;
							}

							const pagination = page.pagination as IDataObject | undefined;
							cursor = pagination?.has_more
								? (pagination.next_cursor as string)
								: undefined;
						} while (cursor);

						for (const run of allRuns.slice(0, MAX_PAGINATION_ITEMS)) {
							returnData.push({ json: run, pairedItem: { item: i } });
						}
						continue;
					} else {
						const limit = this.getNodeParameter('limit', i) as number;
						qs.limit = limit;

						const page = await tinyfishApiRequest.call(
							this,
							'GET',
							'/v1/runs',
							{},
							qs,
						);

						const data = (page.data as IDataObject[]) || [];
						for (const run of data) {
							returnData.push({ json: run, pairedItem: { item: i } });
						}
						continue;
					}
				} else {
					throw new NodeOperationError(
						this.getNode(),
						`Unknown operation: ${operation}`,
						{ itemIndex: i },
					);
				}

				const executionData = this.helpers.constructExecutionMetaData(
					this.helpers.returnJsonArray(responseData),
					{ itemData: { item: i } },
				);
				returnData.push(...executionData);
			} catch (error) {
				if (this.continueOnFail()) {
					returnData.push({
						json: { error: (error as Error).message },
						pairedItem: { item: i },
					});
					continue;
				}

				if (error instanceof NodeOperationError) {
					throw error;
				}

				throw new NodeOperationError(this.getNode(), error as Error, {
					itemIndex: i,
				});
			}
		}

		return [returnData];
	}
}
