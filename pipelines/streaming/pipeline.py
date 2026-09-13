import argparse
import json
import logging
from datetime import datetime, timezone

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.transforms.window import FixedWindows

REQUIRED_FIELDS = ["event_id", "event_type", "event_timestamp"]

VALID_EVENT_TYPES = {"order_placed", "order_filled", "order_cancelled"}

OUTPUT_FIELDS = [
    "event_id", "event_type", "event_timestamp", "order_id", "account_id",
    "ticker", "side", "quantity", "order_type", "limit_price_usd",
    "fill_price_usd", "fee_usd", "reason", "ingested_at",
]


class ParseAndValidate(beam.DoFn):
    """Parse JSON and validate. Good records to main output, bad to 'dlq' tag."""

    def process(self, element):
        raw = element.decode("utf-8") if isinstance(element, bytes) else element

        try:
            record = json.loads(raw)
        except Exception as e:
            yield beam.pvalue.TaggedOutput("dlq", {
                "raw_payload": raw[:5000],
                "error_type": "JSON_PARSE_ERROR",
                "error_message": str(e)[:1000],
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            })
            return

        missing = [f for f in REQUIRED_FIELDS if not record.get(f)]
        if missing:
            yield beam.pvalue.TaggedOutput("dlq", {
                "raw_payload": raw[:5000],
                "error_type": "MISSING_REQUIRED_FIELD",
                "error_message": f"missing: {','.join(missing)}",
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            })
            return

        if record["event_type"] not in VALID_EVENT_TYPES:
            yield beam.pvalue.TaggedOutput("dlq", {
                "raw_payload": raw[:5000],
                "error_type": "UNKNOWN_EVENT_TYPE",
                "error_message": record["event_type"][:1000],
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            })
            return

        try:
            if record.get("quantity") is not None:
                record["quantity"] = int(record["quantity"])
            for f in ["limit_price_usd", "fill_price_usd", "fee_usd"]:
                if record.get(f) is not None:
                    record[f] = float(record[f])
        except (ValueError, TypeError) as e:
            yield beam.pvalue.TaggedOutput("dlq", {
                "raw_payload": raw[:5000],
                "error_type": "TYPE_COERCION_ERROR",
                "error_message": str(e)[:1000],
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            })
            return

        record["ingested_at"] = datetime.now(timezone.utc).isoformat()
        yield {k: record.get(k) for k in OUTPUT_FIELDS}


def dedupe_key(record):
    return (record["event_id"], record)


def take_first(kv):
    _, records = kv
    yield next(iter(records))


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--subscription", required=True)
    parser.add_argument("--events_table", required=True)
    parser.add_argument("--dlq_table", required=True)
    known, pipeline_args = parser.parse_known_args(argv)

    options = PipelineOptions(pipeline_args, project=known.project, save_main_session=True)
    options.view_as(StandardOptions).streaming = True

    with beam.Pipeline(options=options) as p:
        parsed = (
            p
            | "ReadPubSub" >> beam.io.ReadFromPubSub(subscription=known.subscription)
            | "Window" >> beam.WindowInto(FixedWindows(60))
            | "ParseValidate" >> beam.ParDo(ParseAndValidate()).with_outputs("dlq", main="good")
        )

        deduped = (
            parsed.good
            | "KeyByEventId" >> beam.Map(dedupe_key)
            | "GroupByEventId" >> beam.GroupByKey()
            | "TakeFirst" >> beam.FlatMap(take_first)
        )

        deduped | "WriteEvents" >> beam.io.WriteToBigQuery(
            table=known.events_table,
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
            create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
        )

        parsed.dlq | "WriteDLQ" >> beam.io.WriteToBigQuery(
            table=known.dlq_table,
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
            create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
        )


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    run()