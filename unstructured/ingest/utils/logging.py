import json


def hide_sensitive_fields(data: dict) -> dict:
    sensitive_fields = [
        "account_name",
        "client_id",
    ]
    sensitive_triggers = ["key", "cred", "token"]
    new_data = data.copy()
    for k, v in new_data.items():
        if (
            v
            and any([s in k.lower() for s in sensitive_triggers])  # noqa: C419
            or k.lower() in sensitive_fields
        ):
            new_data[k] = "*******"
        if isinstance(v, dict):
            new_data[k] = hide_sensitive_fields(v)
        if isinstance(v, str):
            try:
                json_data = json.loads(v)
                if isinstance(json_data, dict):
                    updated_data = hide_sensitive_fields(json_data)
                    new_data[k] = json.dumps(updated_data)
            except json.JSONDecodeError:
                pass

    return new_data
