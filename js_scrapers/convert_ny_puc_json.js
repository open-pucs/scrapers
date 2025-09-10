const fs = require('fs');
const path = require('path');

function convertFile(inputPath, outputPath) {
  console.log(`Reading file from: ${inputPath}`);
  const rawData = fs.readFileSync(inputPath, 'utf-8');
  const data = JSON.parse(rawData);

  let convertedData;

  if (Array.isArray(data)) {
    convertedData = data.map(item => {
      if (item && item.case && item.documents && item.parties) {
        const { case: metadata, documents, parties } = item;
        metadata.filings = documents;
        metadata.case_parties = parties;
        return metadata;
      }
      return item; // Return as is if it doesn't match the format
    });
  } else if (data && data.case && data.documents && data.parties) {
    const { case: metadata, documents, parties } = data;
    metadata.filings = documents;
    metadata.case_parties = parties;
    convertedData = metadata;
  } else {
    console.log("File content does not seem to be in the expected format. No conversion performed.");
    convertedData = data;
  }

  fs.writeFileSync(outputPath, JSON.stringify(convertedData, null, 2), 'utf-8');
  console.log(`Successfully converted file and saved to: ${outputPath}`);
}

const inputFile = process.argv[2];
const outputFile = process.argv[3];

if (!inputFile || !outputFile) {
  console.error('Usage: node convert_ny_puc_json.js <inputFile> <outputFile>');
  process.exit(1);
}

const inputFilePath = path.resolve(inputFile);
const outputFilePath = path.resolve(outputFile);

convertFile(inputFilePath, outputFilePath);
