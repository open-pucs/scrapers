import { defineConfig } from "cypress";
import * as fs from "fs";

export default defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      on("task", {
        log(message: string) {
          console.log(message);
          return null;
        },
        appendToCsv({ filename, data }: { filename: string; data: string[][] }) {
          const dataString = data.map(row => row.join(",")).join("\n") + "\n";
          if (!fs.existsSync(filename)) {
            const headers = ["API Well Number", "Well Name", "Operator", "Lease / Unit", "Log Category", "Log Type", "Date Posted", "PDF"];
            fs.writeFileSync(filename, headers.join(",") + "\n");
          }
          fs.appendFileSync(filename, dataString, "utf8");
          return null;
        },
      });
    },
    specPattern: "cypress/e2e/**/*.cy.ts",
  },
});