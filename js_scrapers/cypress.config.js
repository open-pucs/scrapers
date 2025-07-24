const { defineConfig } = require("cypress");
const fs = require("fs");

module.exports = defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      on("task", {
        log(message) {
          console.log(message);
          return null;
        },
        appendToCsv({ filename, data }) {
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