"""Pratica 1 (console) - a menor Lambda possivel ligada ao S3.

Cole este codigo no editor do console da Lambda, ligue um gatilho S3 e
suba qualquer arquivo. O objetivo e so ENXERGAR o evento no CloudWatch.
"""

import json
import urllib.parse


def lambda_handler(event, context):
    print("EVENTO BRUTO:")
    print(json.dumps(event, indent=2))

    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        raw_key = record["s3"]["object"]["key"]
        key = urllib.parse.unquote_plus(raw_key)
        size = record["s3"]["object"].get("size", 0)

        print(f"evento:  {record['eventName']}")
        print(f"bucket:  {bucket}")
        print(f"key crua: {raw_key}")
        print(f"key real: {key}")
        print(f"tamanho: {size} bytes")

    print(f"tempo restante: {context.get_remaining_time_in_millis()} ms")
    return {"ok": True}
