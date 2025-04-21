"""Test Illinois ICC pipeline."""

import json
import os
import pytest
from pathlib import Path

from openpuc_scrapers.pipelines.il import IllinoisICCPipeline

def test_pipeline_output_structure():
    """Test that pipeline output follows expected structure."""
    # Initialize pipeline
    pipeline = IllinoisICCPipeline(output_dir="test_output")
    
    # Process a test case
    pipeline.process_case("25-0274")
    
    # Check output directory exists
    output_dir = Path("test_output")
    assert output_dir.exists()
    
    # Find the most recent output subdirectory
    output_subdirs = [d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith("illinois_")]
    assert len(output_subdirs) > 0
    latest_output = max(output_subdirs, key=lambda x: x.stat().st_mtime)
    
    # Check intermediate case data
    intermediate_file = latest_output / "intermediate_25-0274.json"
    assert intermediate_file.exists()
    with open(intermediate_file) as f:
        intermediate_data = json.load(f)
        assert "case_id" in intermediate_data
        assert "case_details" in intermediate_data
        assert "docket_sheet" in intermediate_data
        assert "service_list" in intermediate_data
        assert "schedule" in intermediate_data
        assert "documents" in intermediate_data
        
    # Check generic case data
    generic_file = latest_output / "generic_case_25-0274.json"
    assert generic_file.exists()
    with open(generic_file) as f:
        generic_data = json.load(f)
        assert "case_id" in generic_data
        assert "title" in generic_data
        assert "category" in generic_data
        assert "status" in generic_data
        assert "filing_date" in generic_data
        assert "judge_names" in generic_data
        assert "docket_sheet" in generic_data
        assert "service_list" in generic_data
        assert "schedule" in generic_data
        assert "documents" in generic_data
        
    # Clean up
    for file in latest_output.glob("*"):
        file.unlink()
    latest_output.rmdir()
    output_dir.rmdir()

def test_pipeline_document_processing():
    """Test that pipeline correctly processes documents."""
    # Initialize pipeline
    pipeline = IllinoisICCPipeline(output_dir="test_output")
    
    # Process a test case
    pipeline.process_case("25-0274")
    
    # Find the most recent output subdirectory
    output_dir = Path("test_output")
    output_subdirs = [d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith("illinois_")]
    latest_output = max(output_subdirs, key=lambda x: x.stat().st_mtime)
    
    # Check intermediate filing data
    intermediate_file = latest_output / "intermediate_filing_25-0274.json"
    assert intermediate_file.exists()
    with open(intermediate_file) as f:
        intermediate_data = json.load(f)
        assert "case_id" in intermediate_data
        assert "filing_date" in intermediate_data
        assert "filing_type" in intermediate_data
        assert "filing_party" in intermediate_data
        assert "filing_description" in intermediate_data
        assert "filing_documents" in intermediate_data
        
    # Check generic filing data
    generic_file = latest_output / "generic_filing_25-0274.json"
    assert generic_file.exists()
    with open(generic_file) as f:
        generic_data = json.load(f)
        assert "case_id" in generic_data
        assert "filing_date" in generic_data
        assert "filing_type" in generic_data
        assert "filing_party" in generic_data
        assert "filing_description" in generic_data
        assert "documents" in generic_data
        
    # Clean up
    for file in latest_output.glob("*"):
        file.unlink()
    latest_output.rmdir()
    output_dir.rmdir()

def test_pipeline_error_handling():
    """Test that pipeline handles errors gracefully."""
    # Initialize pipeline
    pipeline = IllinoisICCPipeline(output_dir="test_output")
    
    # Process an invalid case ID
    pipeline.process_case("invalid_case")
    
    # Check that output directory was not created
    output_dir = Path("test_output")
    assert not output_dir.exists() 