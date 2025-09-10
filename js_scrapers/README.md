# NY PUC Scraper

A Node.js/TypeScript web scraper for the New York Public Utilities Commission (NY PUC) website that extracts case information, documents, and party details with parallel processing and task queuing.

## Features

- **Multiple Scraping Modes**: Extract full case details, metadata only, documents only, or parties only
- **Parallel Processing**: Process multiple cases simultaneously with configurable concurrency (default: 4 browser windows)
- **Task Queue Management**: Intelligent queuing system prevents resource overload
- **Flexible Input**: Support for comma-separated IDs, file input, or date-based scraping
- **JSON Output**: Save results to structured JSON files or display in console
- **Browser Automation**: Uses Playwright with Chromium for reliable data extraction

## Installation

```bash
npm install
# or
pnpm install
```

## Usage

### Basic Command Structure

```bash
npx ts-node playwright/ny_puc_scraper.spec.ts [OPTIONS]
```

### Command Line Options

| Flag | Long Form | Description | Example |
|------|-----------|-------------|---------|
| `--mode` | | Scraping mode (required) | `--mode full-extraction` |
| `--gov-ids` | | Comma-separated government IDs | `--gov-ids "14-M-0094,18-M-0084"` |
| `--from-file` | | Read government IDs from file | `--from-file gov_ids.txt` |
| `--date` | | Scrape cases for specific date | `--date "09/10/2025"` |
| `-o` | `--outfile` | Save results to JSON file | `-o results.json` |

### Scraping Modes

| Mode | Description | Output |
|------|-------------|--------|
| `full` | Complete case details with documents and parties | Full RawGenericDocket objects |
| `meta` | Case metadata only | Basic case information |
| `docs` | Documents and filings only | Array of RawGenericFiling objects |
| `parties` | Case parties only | Array of RawGenericParty objects |
| `dates` | Cases filed on specific date | Basic case information for date |
| `full-extraction` | All data organized separately | Object with case, documents, and parties |

## Examples

### 1. Full Case Details with File Input

Extract complete information for all cases listed in `gov_ids.txt`:

```bash
npx ts-node playwright/ny_puc_scraper.spec.ts --mode full --from-file gov_ids.txt -o full_cases.json
```

### 2. Documents Only for Specific Cases

Extract only documents for specific government IDs:

```bash
npx ts-node playwright/ny_puc_scraper.spec.ts --mode docs --gov-ids "14-M-0094,18-M-0084,24-E-0165" -o documents.json
```

### 3. Parties Information

Get party information for cases in file:

```bash
npx ts-node playwright/ny_puc_scraper.spec.ts --mode parties --from-file gov_ids.txt -o parties.json
```

### 4. Metadata Only (Quick Overview)

Get basic case information without heavy document/party extraction:

```bash
npx ts-node playwright/ny_puc_scraper.spec.ts --mode meta --gov-ids "20-E-0197,18-E-0071" -o metadata.json
```

### 5. Full Extraction (Organized Output)

Extract all data but organize it separately for each case:

```bash
npx ts-node playwright/ny_puc_scraper.spec.ts --mode full-extraction --from-file gov_ids.txt -o organized_results.json
```

### 6. Date-Based Scraping

Get all cases filed on a specific date:

```bash
npx ts-node playwright/ny_puc_scraper.spec.ts --mode dates --date "09/10/2025" -o date_cases.json
```

### 7. Console Output (No File)

Display results in console without saving to file:

```bash
npx ts-node playwright/ny_puc_scraper.spec.ts --mode meta --gov-ids "15-E-0751"
```

## Input File Format

Create a `gov_ids.txt` file with one government ID per line:

```text
# NY PUC government IDs for scraping
# Lines starting with # are ignored
14-M-0094
18-M-0084
18-E-0130
24-E-0165
20-E-0197
18-E-0071
15-E-0751
21-E-0629
```

## Performance & Concurrency

The scraper uses intelligent task queuing with a default maximum of 4 concurrent browser windows:

- **Resource Management**: Prevents system overload by limiting concurrent browsers
- **Dynamic Queue**: New tasks start automatically as others complete
- **Progress Tracking**: Real-time logging of task progress
- **Error Handling**: Failed tasks don't stop the entire process

### Example Progress Output:
```
Scraping documents for 8 cases with max 4 concurrent browsers
Starting task 1/8 (4 running, max: 4)
Starting task 2/8 (4 running, max: 4)
Starting task 3/8 (4 running, max: 4)
Starting task 4/8 (4 running, max: 4)
Completed task 1/8 (3 still running)
Starting task 5/8 (4 running, max: 4)
```

## Output Examples

### Console Success Output:
```
✅ Successfully saved 8 results to results.json
📊 Mode: full-extraction, File size: 245.67 KB
```

### JSON Structure (full-extraction mode):
```json
[
  {
    "case": {
      "case_govid": "14-M-0094",
      "case_name": "Matter Name",
      "opened_date": "2014-03-15T00:00:00.000Z",
      "case_type": "Matter Type",
      "petitioner": "Petitioner Name"
    },
    "documents": [
      {
        "name": "Document Title",
        "filed_date": "2014-03-20T00:00:00.000Z",
        "filing_type": "Filing Type",
        "attachments": [...]
      }
    ],
    "parties": [
      {
        "name": "Party Name",
        "contact_email": "email@example.com",
        "contact_phone": "555-1234"
      }
    ]
  }
]
```

## Error Handling

- **Network Issues**: Automatic retry and graceful degradation
- **File Operations**: Clear error messages for file read/write issues
- **Invalid Arguments**: Helpful validation messages
- **Browser Crashes**: Individual task failures don't stop the entire process

## Legacy Compatibility

The scraper maintains backward compatibility with the original CLI runner:

```bash
# Original format still works
npx ts-node playwright/ny_puc_scraper.spec.ts '[{"case_govid":"14-M-0094"}]'
```

## Troubleshooting

### Common Issues:

1. **Permission Denied**: Ensure write permissions for output directory
2. **Network Timeouts**: NY PUC website may be slow; scraper has 30-second timeouts
3. **Too Many Browsers**: Reduce concurrency if system resources are limited
4. **Invalid Government IDs**: Check ID format (e.g., "14-M-0094", "18-E-0130")

### Debug Mode:

The scraper runs in non-headless mode by default, so you can see browser windows and debug navigation issues.

## Contributing

1. Follow existing code patterns
2. Add error handling for new features  
3. Update this README for any new command-line options
4. Test with various government ID formats

## License

[Add your license information here]