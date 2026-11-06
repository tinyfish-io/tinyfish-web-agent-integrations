"""TinyFish Datasets tools: tables of many web entities with the same fields."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from . import rest_client
from .profile_tools import _required, _schema, _with_key, plain_error
from .research_tools import wait_until

PREVIEW_ROWS = 50
ROWS_LIMIT_DEFAULT = 100
ROWS_LIMIT_MAX = 500

_DATASET_ID = {
    "type": "string",
    "description": (
        "dataset_id returned by tinyfish_create_dataset or tinyfish_list_datasets."
    ),
}
_TARGET_ROWS = {
    "type": "integer",
    "minimum": 1,
    "maximum": 250,
    "description": (
        "Rows to fill the dataset to, 1 to 250. More rows take longer and cost more."
    ),
}
_PROMPT = {
    "type": "string",
    "description": (
        "What the dataset should contain, in plain English, with any scope the "
        "user gave."
    ),
}
_SPEC = {
    "type": "object",
    "description": (
        "Columns to use as is, such as the spec tinyfish_plan_dataset returned. "
        "When sending a spec, omit prompt; the spec decides the columns."
    ),
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "columns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "label": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["string", "number", "boolean", "url", "date"],
                    },
                    "is_primary_key": {
                        "type": "boolean",
                        "description": (
                            "Exactly one column: the one that names the entity. "
                            "Never a boolean."
                        ),
                    },
                    "is_unique": {
                        "type": "boolean",
                        "description": (
                            "A url or string column besides the key; at most three."
                        ),
                    },
                    "retrieval_hint": {"type": "string"},
                    "format": {"type": "string"},
                    "examples": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "type", "is_primary_key"],
            },
        },
        "keep_when": {
            "type": "object",
            "properties": {"column": {"type": "string"}},
            "description": "Keeps rows where this boolean column is true.",
        },
    },
    "required": ["name", "description", "columns"],
}
_CURSOR = {"type": "string", "description": "The previous page's next_cursor."}

CREATE_SCHEMA = _schema(
    "tinyfish_create_dataset",
    "Slow (minutes) and billed per row. Only use when the user asks for a dataset, "
    "table, or list of many entities with the same fields (companies, products, "
    "places, people), each row found on the web. Not for a single fact, one page, "
    "or a question web_search and web_extract can answer. Give a prompt, or a spec "
    "from tinyfish_plan_dataset when the user reviewed the columns; send one, not "
    "both. Returns dataset_id and run_id at once; then call tinyfish_get_dataset, "
    "which waits and returns the rows. Do not create a second dataset for the same "
    "request.",
    {
        "prompt": {
            **_PROMPT,
            "description": (
                "The user's request in plain English; TinyFish plans the columns "
                "from it. Omit when sending a spec."
            ),
        },
        "spec": _SPEC,
        "target_rows": {
            **_TARGET_ROWS,
            "description": (
                "Rows to fill the dataset to, 1 to 250; defaults to 100. More rows "
                "take longer and cost more."
            ),
        },
    },
    [],
)
PLAN_SCHEMA = _schema(
    "tinyfish_plan_dataset",
    "Designs the columns for a dataset prompt without creating anything. Use when "
    "the user wants to see or edit the columns first; pass the returned spec to "
    "tinyfish_create_dataset. Otherwise call tinyfish_create_dataset directly with "
    "the prompt.",
    {"prompt": _PROMPT},
    ["prompt"],
)
GET_SCHEMA = _schema(
    "tinyfish_get_dataset",
    "Waits up to about 25 seconds for a dataset started by tinyfish_create_dataset "
    "or tinyfish_populate_dataset, then returns its status, row count and the "
    "first rows. When output_ready is true the rows stand; call "
    "tinyfish_get_dataset_rows for more pages. While status is populating, call "
    "tinyfish_get_dataset again with the same dataset_id; filling usually takes a "
    "few minutes. Do not create another dataset or cancel because it is slow.",
    {
        "dataset_id": _DATASET_ID,
        "wait": {
            "type": "boolean",
            "description": (
                "Wait up to about 25 seconds for the run to finish before "
                "answering. Defaults to true."
            ),
        },
    },
    ["dataset_id"],
)
ROWS_SCHEMA = _schema(
    "tinyfish_get_dataset_rows",
    "One page of rows from a dataset, in column order. Use after "
    "tinyfish_get_dataset reports output_ready, or to read past the first rows; "
    "pass the previous next_cursor as after.",
    {
        "dataset_id": _DATASET_ID,
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": ROWS_LIMIT_MAX,
            "description": f"Rows per page, 1 to {ROWS_LIMIT_MAX}; defaults to 100.",
        },
        "after": _CURSOR,
    },
    ["dataset_id"],
)
LIST_SCHEMA = _schema(
    "tinyfish_list_datasets",
    "The caller's datasets, newest first, with status and row counts. Use to find "
    "a dataset_id the user refers to by name.",
    {
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "description": "Datasets per page, 1 to 100; defaults to 20.",
        },
        "cursor": _CURSOR,
    },
    [],
)
POPULATE_SCHEMA = _schema(
    "tinyfish_populate_dataset",
    "Fills an existing dataset again, to add rows up to a new target_rows or to "
    "rebuild it with reset. Refused while a run is live. Returns run_id; then call "
    "tinyfish_get_dataset.",
    {
        "dataset_id": _DATASET_ID,
        "reset": {
            "type": "boolean",
            "description": "Empty the dataset before filling it.",
        },
        "target_rows": _TARGET_ROWS,
    },
    ["dataset_id"],
)
CANCEL_SCHEMA = _schema(
    "tinyfish_cancel_dataset_run",
    "Only use when the user explicitly asks to stop a dataset run. Never cancel "
    "because filling is slow or tinyfish_get_dataset returned without "
    "output_ready; keep polling instead. Rows already landed stay.",
    {
        "dataset_id": _DATASET_ID,
        "run_id": {"type": "string", "description": "run_id from the dataset's run."},
    },
    ["dataset_id", "run_id"],
)
DELETE_SCHEMA = _schema(
    "tinyfish_delete_dataset",
    "Permanently deletes a dataset and its rows. Only when the user explicitly "
    "asks. Refused while a run is live: cancel it first.",
    {"dataset_id": _DATASET_ID},
    ["dataset_id"],
)


def _poll_again(dataset_id: str) -> str:
    return (
        f"Call tinyfish_get_dataset again with dataset_id={dataset_id}; filling "
        "usually takes a few minutes. Do not create another dataset or cancel "
        "because it is slow."
    )


def dataset_error_json(exc: rest_client.TinyFishRestError) -> str:
    payload = plain_error(exc)
    dataset_id = (exc.details or {}).get("dataset_id")
    named = isinstance(dataset_id, str)
    if named:
        payload["dataset_id"] = dataset_id
    run_id = (exc.details or {}).get("run_id")
    if named and isinstance(run_id, str):
        # The run started before the readback failed; populating again bills twice.
        payload["run_id"] = run_id
        payload["next_action"] = (
            f"The run started as run_id={run_id}. Call tinyfish_get_dataset with "
            f"dataset_id={dataset_id}; do not call tinyfish_populate_dataset or "
            "tinyfish_create_dataset again."
        )
    elif exc.status == 429:
        payload["next_action"] = (
            "Run limit reached: too many runs are in progress. The dataset exists as "
            f"dataset_id={dataset_id}. Tell the user to wait for a run to finish, "
            f"then call tinyfish_populate_dataset with dataset_id={dataset_id}; do "
            "not call tinyfish_create_dataset again."
            if named
            else "Run limit reached: too many runs are in progress. Tell the user to "
            "wait for one to finish; do not call tinyfish_populate_dataset or "
            "tinyfish_create_dataset again until then."
        )
    elif named:
        payload["next_action"] = (
            f"The dataset exists as dataset_id={dataset_id}. Call "
            "tinyfish_populate_dataset with that id to start filling it; do not call "
            "tinyfish_create_dataset again."
        )
    if exc.retry_after:
        payload["retry_after_seconds"] = exc.retry_after
    return json.dumps(payload)


def summary(dataset: dict[str, Any]) -> dict[str, Any]:
    spec = dataset.get("spec") or {}
    columns = [c for c in spec.get("columns") or [] if isinstance(c, dict)]
    return {
        "dataset_id": dataset.get("id"),
        "name": dataset.get("name"),
        "status": dataset.get("status"),
        "target_rows": dataset.get("target_rows"),
        "row_count": dataset.get("row_count"),
        "run": dataset.get("run"),
        "created_at": dataset.get("created_at"),
        "columns": [
            {
                "name": c.get("name"),
                **({"label": c["label"]} if c.get("label") else {}),
                "type": c.get("type"),
                "is_primary_key": c.get("is_primary_key"),
                **({"is_unique": True} if c.get("is_unique") else {}),
            }
            for c in columns
        ],
    }


def _started(dataset: dict[str, Any]) -> dict[str, Any]:
    dataset_id = str(dataset.get("id") or "")
    return {
        "dataset_id": dataset_id,
        "run_id": (dataset.get("run") or {}).get("id"),
        "status": dataset.get("status"),
        "target_rows": dataset.get("target_rows"),
        "output_ready": False,
        "next_action": _poll_again(dataset_id),
    }


def _create(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    prompt = str(args.get("prompt") or "").strip()
    spec = args.get("spec")
    if bool(prompt) == bool(spec):
        raise ValueError("Send exactly one of prompt or spec.")
    fields: dict[str, Any] = {"prompt": prompt} if prompt else {"spec": spec}
    if args.get("target_rows") is not None:
        fields["target_rows"] = args["target_rows"]
    return _started(rest_client.create_dataset(fields, api_key=api_key))


def _plan(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    return rest_client.plan_dataset(_required(args, "prompt"), api_key=api_key)


def _landed(dataset: dict[str, Any]) -> str:
    count = dataset.get("row_count") or 0
    return (
        f" The {count} rows that landed are in tinyfish_get_dataset_rows."
        if count
        else ""
    )


def _outcome(dataset: dict[str, Any], api_key: str) -> dict[str, Any]:
    dataset_id = str(dataset.get("id") or "")
    status = dataset.get("status")
    if status == "ready":
        preview = rest_client.get_dataset_rows(
            dataset_id, {"limit": PREVIEW_ROWS}, api_key=api_key
        )
        return {
            "output_ready": True,
            "rows": preview.get("rows"),
            "next_cursor": preview.get("next_cursor"),
        }
    if status == "populating":
        return {"output_ready": False, "next_action": _poll_again(dataset_id)}
    if status == "failed":
        return {
            "output_ready": False,
            "error": (dataset.get("run") or {}).get("error") or "The run failed",
            "next_action": (
                f"Call tinyfish_populate_dataset with dataset_id={dataset_id} and "
                "reset=true to fill it again, or tell the user." + _landed(dataset)
            ),
        }
    if status == "cancelled":
        return {
            "output_ready": False,
            "error": "The run was cancelled",
            "next_action": (
                "The run was cancelled at the user's request. Report the "
                f"{dataset.get('row_count') or 0} rows that landed and wait for the "
                "user; do not call tinyfish_populate_dataset unless asked."
                + _landed(dataset)
            ),
        }
    return {
        "output_ready": False,
        "next_action": (
            "No rows yet and no run is live; call tinyfish_populate_dataset with "
            f"dataset_id={dataset_id}."
        ),
    }


def _get(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    dataset_id = _required(args, "dataset_id")

    def read() -> dict[str, Any]:
        return rest_client.get_dataset(dataset_id, api_key=api_key)

    if args.get("wait", True) is False:
        dataset = read()
    else:
        dataset = wait_until(read, lambda d: d.get("status") != "populating")
    return {**summary(dataset), **_outcome(dataset, api_key)}


def _rows(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    dataset_id = _required(args, "dataset_id")
    limit = int(args.get("limit") or ROWS_LIMIT_DEFAULT)
    # Every row lands in the model's context, so pages stay smaller than the API's.
    params: dict[str, Any] = {"limit": max(1, min(limit, ROWS_LIMIT_MAX))}
    if args.get("after"):
        params["after"] = args["after"]
    return rest_client.get_dataset_rows(dataset_id, params, api_key=api_key)


def _list(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    params = {k: args[k] for k in ("limit", "cursor") if args.get(k) not in (None, "")}
    page = rest_client.list_datasets(params, api_key=api_key)
    pagination = page.get("pagination") or {}
    return {
        "datasets": [summary(d) for d in page.get("data") or [] if isinstance(d, dict)],
        "next_cursor": pagination.get("next_cursor"),
        "has_more": bool(pagination.get("has_more")),
    }


def _populate(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    fields: dict[str, Any] = {"reset": bool(args.get("reset"))}
    if args.get("target_rows") is not None:
        fields["target_rows"] = args["target_rows"]
    return _started(
        rest_client.populate_dataset(
            _required(args, "dataset_id"), fields, api_key=api_key
        )
    )


def _cancel(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    dataset_id = _required(args, "dataset_id")
    result = rest_client.cancel_dataset_run(
        dataset_id, _required(args, "run_id"), api_key=api_key
    )
    return {"dataset_id": dataset_id, **result}


def _delete(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    dataset_id = _required(args, "dataset_id")
    rest_client.delete_dataset(dataset_id, api_key=api_key)
    return {"dataset_id": dataset_id, "deleted": True}


DATASET_TOOLS: tuple[tuple[dict[str, Any], Callable[..., str]], ...] = tuple(
    (schema, _with_key(handler, dataset_error_json))
    for schema, handler in (
        (CREATE_SCHEMA, _create),
        (PLAN_SCHEMA, _plan),
        (GET_SCHEMA, _get),
        (ROWS_SCHEMA, _rows),
        (LIST_SCHEMA, _list),
        (POPULATE_SCHEMA, _populate),
        (CANCEL_SCHEMA, _cancel),
        (DELETE_SCHEMA, _delete),
    )
)
