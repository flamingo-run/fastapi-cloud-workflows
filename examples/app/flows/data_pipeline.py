"""Example data pipeline workflow with error handling and retries."""

from __future__ import annotations

from datetime import timedelta

from pydantic import BaseModel

from fastapi_cloudflow import (
    Context,
    HttpStep,
    RetryPolicy,
    TryCatchStep,
    step,
    workflow,
)


class DataSource(BaseModel):
    source_id: str
    endpoint: str
    format: str = "json"


class RawData(BaseModel):
    data: list[dict]
    source_id: str
    record_count: int


class ProcessedData(BaseModel):
    processed_records: int
    failed_records: int
    source_id: str
    status: str


class PipelineResult(BaseModel):
    total_processed: int
    total_failed: int
    sources_processed: list[str]
    status: str


# Data extraction with retries for unreliable sources
@step(
    name="extract-data",
    retry=RetryPolicy(
        max_retries=3,
        initial_delay_s=5.0,
        max_delay_s=60.0,
        multiplier=2.0,
        predicate="http.default_retry_predicate",
    ),
    timeout=timedelta(seconds=120),
)
async def extract_data(ctx: Context, data: DataSource) -> RawData:
    """Extract data from source with automatic retries."""
    # Simulate data extraction
    import random

    # Simulate occasional extraction failures
    if random.random() < 0.2:
        raise Exception(f"Failed to extract from {data.source_id}")

    # Mock extracted data
    mock_data = [{"id": i, "value": f"record_{i}", "source": data.source_id} for i in range(10)]

    return RawData(data=mock_data, source_id=data.source_id, record_count=len(mock_data))


@step(name="validate-data")
async def validate_data(ctx: Context, data: RawData) -> RawData:
    """Validate extracted data."""
    # Filter out invalid records
    valid_data = [record for record in data.data if record.get("id") is not None and record.get("value") is not None]

    if not valid_data:
        raise ValueError(f"No valid records found in {data.source_id}")

    return RawData(data=valid_data, source_id=data.source_id, record_count=len(valid_data))


@step(
    name="transform-data",
    retry=RetryPolicy(
        max_retries=2, initial_delay_s=1.0, max_delay_s=5.0, multiplier=2.0, predicate="http.default_retry_predicate"
    ),
)
async def transform_data(ctx: Context, data: RawData) -> ProcessedData:
    """Transform and enrich data."""
    processed_count = 0
    failed_count = 0

    for record in data.data:
        try:
            # Simulate transformation
            record["transformed"] = True
            record["timestamp"] = "2024-01-01T00:00:00Z"
            processed_count += 1
        except Exception:
            failed_count += 1

    return ProcessedData(
        processed_records=processed_count, failed_records=failed_count, source_id=data.source_id, status="transformed"
    )


# External data quality service
data_quality_check = HttpStep(
    name="quality-check",
    input_model=ProcessedData,
    output_model=ProcessedData,
    method="POST",
    url="https://jsonplaceholder.typicode.com/posts",  # Mock endpoint
    retry=RetryPolicy.idempotent_http(),
    timeout=timedelta(seconds=30),
)


@step(name="load-data")
async def load_data(ctx: Context, data: ProcessedData) -> PipelineResult:
    """Load data to destination."""
    # Simulate data loading
    return PipelineResult(
        total_processed=data.processed_records,
        total_failed=data.failed_records,
        sources_processed=[data.source_id],
        status="loaded",
    )


@step(name="handle-extraction-error")
async def handle_extraction_error(ctx: Context, data: DataSource) -> RawData:
    """Handle extraction errors by returning empty dataset."""
    return RawData(data=[], source_id=data.source_id, record_count=0)


@step(name="handle-transform-error")
async def handle_transform_error(ctx: Context, data: RawData) -> ProcessedData:
    """Handle transformation errors."""
    return ProcessedData(
        processed_records=0, failed_records=data.record_count, source_id=data.source_id, status="transform_failed"
    )


@step(name="cleanup-on-error")
async def cleanup_on_error(ctx: Context, data: DataSource) -> PipelineResult:
    """Cleanup resources on pipeline failure."""
    return PipelineResult(total_processed=0, total_failed=0, sources_processed=[], status="pipeline_failed_cleaned")


def build_data_pipeline():
    """Build a resilient data pipeline with multiple try/catch blocks."""

    # Extract phase with error handling
    extract_try = workflow("extract-phase") >> extract_data >> validate_data
    extract_with_recovery = TryCatchStep(
        name="extract-with-recovery",
        input_model=DataSource,
        output_model=RawData,
        try_steps=extract_try.nodes,
        except_steps=[handle_extraction_error],
        error_var="extract_error",
        raise_on_error=False,
    )

    # Transform phase with error handling
    transform_try = workflow("transform-phase") >> transform_data >> data_quality_check
    transform_with_recovery = TryCatchStep(
        name="transform-with-recovery",
        input_model=RawData,
        output_model=ProcessedData,
        try_steps=transform_try.nodes,
        except_steps=[handle_transform_error],
        error_var="transform_error",
        raise_on_error=False,
    )

    # Complete pipeline with outer try/catch
    pipeline_steps = [extract_with_recovery, transform_with_recovery, load_data]

    pipeline_with_cleanup = TryCatchStep(
        name="pipeline-with-cleanup",
        input_model=DataSource,
        output_model=PipelineResult,
        try_steps=pipeline_steps,
        except_steps=[cleanup_on_error],
        error_var="pipeline_error",
        raise_on_error=False,
    )

    return (workflow("data-pipeline-flow") >> pipeline_with_cleanup).build()


# Export workflow
DATA_PIPELINE_FLOW = build_data_pipeline()
