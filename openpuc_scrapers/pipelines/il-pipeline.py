"""Pipeline for Illinois ICC data processing."""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Union

from openpuc_scrapers.models.generic import GenericCase, GenericFiling
from openpuc_scrapers.scrapers.il import (
    IllinoisICCScraper,
    ILICCIntermediateCaseData,
    ILICCIntermediateFilingData
)

class IllinoisICCPipeline:
    """Pipeline for processing Illinois ICC data."""
    
    def __init__(self, output_dir: str = "output"):
        """Initialize the pipeline.
        
        Args:
            output_dir: Directory to save output files
        """
        self.output_dir = output_dir
        self.scraper = IllinoisICCScraper()
        
    def _save_json(self, data: Union[Dict, List], filename: str) -> None:
        """Save data to a JSON file.
        
        Args:
            data: Data to save
            filename: Name of the file to save to
        """
        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    def _convert_to_generic_case(self, case_data: ILICCIntermediateCaseData) -> GenericCase:
        """Convert intermediate case data to generic case format.
        
        Args:
            case_data: Intermediate case data
            
        Returns:
            Generic case data
        """
        return GenericCase(
            case_id=case_data.case_id,
            title=case_data.case_details.title,
            category=case_data.case_details.category,
            status=case_data.case_details.status,
            filing_date=case_data.case_details.filing_date,
            judge_names=case_data.case_details.judge_names,
            docket_sheet=[
                {
                    "date": entry.action_date,
                    "title": entry.title,
                    "description": entry.description
                }
                for entry in case_data.docket_sheet
            ],
            service_list=[
                {
                    "name": entry.name,
                    "role": entry.role,
                    "organization": entry.organization,
                    "address": entry.address,
                    "email": entry.email,
                    "phone": entry.phone,
                    "party_type": entry.party_type,
                    "party_status": entry.party_status
                }
                for entry in case_data.service_list
            ],
            schedule=[
                {
                    "date": entry.date,
                    "time": entry.time,
                    "type": entry.type,
                    "description": entry.description,
                    "location": entry.location
                }
                for entry in case_data.schedule
            ],
            documents=[
                {
                    "url": doc.url,
                    "type": doc.type,
                    "filed_by": doc.filed_by,
                    "filed_for": doc.filed_for,
                    "date_filed": doc.date_filed,
                    "means_received": doc.means_received,
                    "description": doc.description,
                    "attachments": [
                        {
                            "url": att.url,
                            "description": att.description,
                            "file_size": att.file_size,
                            "file_type": att.file_type
                        }
                        for att in doc.attachments
                    ]
                }
                for doc in case_data.documents
            ]
        )
        
    def _convert_to_generic_filing(self, filing_data: ILICCIntermediateFilingData) -> GenericFiling:
        """Convert intermediate filing data to generic filing format.
        
        Args:
            filing_data: Intermediate filing data
            
        Returns:
            Generic filing data
        """
        return GenericFiling(
            case_id=filing_data.case_id,
            filing_date=filing_data.filing_date,
            filing_type=filing_data.filing_type,
            filing_party=filing_data.filing_party,
            filing_description=filing_data.filing_description,
            documents=[
                {
                    "url": doc.url,
                    "type": doc.type,
                    "filed_by": doc.filed_by,
                    "filed_for": doc.filed_for,
                    "date_filed": doc.date_filed,
                    "means_received": doc.means_received,
                    "description": doc.description,
                    "attachments": [
                        {
                            "url": att.url,
                            "description": att.description,
                            "file_size": att.file_size,
                            "file_type": att.file_type
                        }
                        for att in doc.attachments
                    ]
                }
                for doc in filing_data.filing_documents
            ]
        )
        
    def process_case(self, case_id: str) -> None:
        """Process a single case.
        
        Args:
            case_id: Case ID to process
        """
        # Create output directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(self.output_dir, f"illinois_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Get case data
        case_data = self.scraper.get_case_data(case_id)
        if not case_data:
            print(f"Failed to get case data for {case_id}")
            return
            
        # Save intermediate data
        self._save_json(case_data.model_dump(), f"intermediate_{case_id}.json")
        
        # Convert to generic format
        generic_case = self._convert_to_generic_case(case_data)
        
        # Save generic data
        self._save_json(generic_case.model_dump(), f"generic_case_{case_id}.json")
        
        # Process filings
        for doc in case_data.documents:
            filing_data = self.scraper.get_filing_data(case_id, doc.url)
            if not filing_data:
                print(f"Failed to get filing data for {doc.url}")
                continue
                
            # Save intermediate filing data
            self._save_json(filing_data.model_dump(), f"intermediate_filing_{case_id}.json")
            
            # Convert to generic format
            generic_filing = self._convert_to_generic_filing(filing_data)
            
            # Save generic filing data
            self._save_json(generic_filing.model_dump(), f"generic_filing_{case_id}.json")
            
    def run(self, case_ids: List[str]) -> None:
        """Run the pipeline on a list of cases.
        
        Args:
            case_ids: List of case IDs to process
        """
        for case_id in case_ids:
            try:
                self.process_case(case_id)
            except Exception as e:
                print(f"Error processing case {case_id}: {str(e)}")
                continue

def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Run Illinois ICC pipeline")
    parser.add_argument("case_ids", nargs="+", help="Case IDs to process")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    args = parser.parse_args()

    pipeline = IllinoisICCPipeline(args.output_dir)
    pipeline.run(args.case_ids)

if __name__ == "__main__":
    main() 