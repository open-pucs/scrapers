import * as fs from "fs";
import * as path from "path";

interface Filing {
  filed_date: string;
  filling_govid: string;
  name: string;
  organization_author_blob: string[];
  individual_author_blob: string[];
  filing_type: string;
  description: string;
  attachments: any[];
  extra_metadata: {
    doc_location: string;
    permitID: string;
  };
}

interface MineData {
  case_govid: string;
  opened_date: string | null;
  case_name: string;
  case_url: string;
  case_type: string;
  case_subtype: string;
  description: string;
  industry: string;
  petitioner: string;
  hearing_officer: string;
  closed_date: string | null;
  filings: Filing[];
  case_parties: any[];
  extra_metadata: {
    county?: string;
  };
}

interface MineMetadata {
  case_govid: string;
  case_name: string;
  petitioner: string;
  county: string;
  total_filings: number;
  first_filing_date: string | null;
  last_filing_date: string | null;
  last_filing_name: string | null;
  case_url: string;
}

interface FilingRecord {
  case_govid: string;
  case_name: string;
  petitioner: string;
  county: string;
  filed_date: string;
  filing_name: string;
  doc_from: string;
  doc_to: string;
  doc_location: string;
}

function parseDate(dateStr: string): Date | null {
  if (!dateStr || dateStr.trim() === "" || dateStr === "null" || dateStr === "undefined") {
    return null;
  }
  try {
    return new Date(dateStr);
  } catch {
    return null;
  }
}

function formatDate(date: Date | null): string {
  if (!date) return "";
  return date.toISOString().split('T')[0];
}

function analyzeMineData(inputDirectory: string): { mineMetadata: MineMetadata[], filingRecords: FilingRecord[] } {
  const mineMetadata: MineMetadata[] = [];
  const filingRecords: FilingRecord[] = [];

  const files = fs.readdirSync(inputDirectory).filter(file => file.endsWith('.json'));

  console.log(`Analyzing ${files.length} mine files...`);

  for (const file of files) {
    try {
      const filePath = path.join(inputDirectory, file);
      const content = fs.readFileSync(filePath, 'utf-8');
      const mineData: MineData = JSON.parse(content);

      const filings = mineData.filings || [];
      const validFilings = filings.filter(filing =>
        filing.filed_date &&
        filing.filed_date.trim() !== "" &&
        filing.filed_date !== "null" &&
        filing.filed_date !== "undefined"
      );

      let firstFilingDate: Date | null = null;
      let lastFilingDate: Date | null = null;
      let lastFilingName: string | null = null;

      if (validFilings.length > 0) {
        const sortedFilings = validFilings
          .map(filing => ({ ...filing, parsedDate: parseDate(filing.filed_date) }))
          .filter(filing => filing.parsedDate !== null)
          .sort((a, b) => a.parsedDate!.getTime() - b.parsedDate!.getTime());

        if (sortedFilings.length > 0) {
          firstFilingDate = sortedFilings[0].parsedDate;
          lastFilingDate = sortedFilings[sortedFilings.length - 1].parsedDate;
          lastFilingName = sortedFilings[sortedFilings.length - 1].name;
        }
      }

      const metadata: MineMetadata = {
        case_govid: mineData.case_govid,
        case_name: mineData.case_name,
        petitioner: mineData.petitioner || "Unknown",
        county: mineData.extra_metadata?.county || "Unknown",
        total_filings: validFilings.length,
        first_filing_date: formatDate(firstFilingDate),
        last_filing_date: formatDate(lastFilingDate),
        last_filing_name: lastFilingName,
        case_url: mineData.case_url
      };

      mineMetadata.push(metadata);

      for (const filing of validFilings) {
        const filingRecord: FilingRecord = {
          case_govid: mineData.case_govid,
          case_name: mineData.case_name,
          petitioner: mineData.petitioner || "Unknown",
          county: mineData.extra_metadata?.county || "Unknown",
          filed_date: filing.filed_date,
          filing_name: filing.name,
          doc_from: filing.individual_author_blob?.join("; ") || "",
          doc_to: filing.organization_author_blob?.join("; ") || "",
          doc_location: filing.extra_metadata?.doc_location || ""
        };

        filingRecords.push(filingRecord);
      }

    } catch (error) {
      console.error(`Error processing file ${file}:`, error);
    }
  }

  console.log(`Processed ${mineMetadata.length} mines with ${filingRecords.length} total filings`);
  return { mineMetadata, filingRecords };
}

function generateCSV<T>(data: T[], filename: string): void {
  if (data.length === 0) {
    console.log(`No data to write for ${filename}`);
    return;
  }

  const headers = Object.keys(data[0] as any);
  const csvContent = [
    headers.join(','),
    ...data.map(row =>
      headers.map(header => {
        const value = (row as any)[header];
        const stringValue = value === null || value === undefined ? '' : String(value);
        return `"${stringValue.replace(/"/g, '""')}"`;
      }).join(',')
    )
  ].join('\n');

  fs.writeFileSync(filename, csvContent, 'utf-8');
  console.log(`Generated ${filename} with ${data.length} rows`);
}

async function main() {
  const inputDirectory = "outputs/utah_coal_mines";
  const outputDirectory = "outputs";

  if (!fs.existsSync(inputDirectory)) {
    console.error(`Input directory ${inputDirectory} does not exist`);
    process.exit(1);
  }

  fs.mkdirSync(outputDirectory, { recursive: true });

  console.log("Analyzing Utah coal mine data...");
  const { mineMetadata, filingRecords } = analyzeMineData(inputDirectory);

  console.log("\nGenerating spreadsheets...");

  generateCSV(mineMetadata, path.join(outputDirectory, "utah_coal_mines_metadata.csv"));
  generateCSV(filingRecords, path.join(outputDirectory, "utah_coal_mines_filings.csv"));

  console.log("\nSummary statistics:");
  console.log(`Total mines: ${mineMetadata.length}`);
  console.log(`Total filings: ${filingRecords.length}`);
  console.log(`Mines with filings: ${mineMetadata.filter(m => m.total_filings > 0).length}`);
  console.log(`Mines without filings: ${mineMetadata.filter(m => m.total_filings === 0).length}`);

  const counties = [...new Set(mineMetadata.map(m => m.county))];
  console.log(`Unique counties: ${counties.length}`);

  const petitioners = [...new Set(mineMetadata.map(m => m.petitioner))];
  console.log(`Unique petitioners: ${petitioners.length}`);

  console.log("\nFiles generated:");
  console.log(`- ${path.join(outputDirectory, "utah_coal_mines_metadata.csv")}`);
  console.log(`- ${path.join(outputDirectory, "utah_coal_mines_filings.csv")}`);
}

main().catch(console.error);