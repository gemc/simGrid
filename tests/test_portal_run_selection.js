// Run with: node tests/test_portal_run_selection.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const elements = {};
for (const id of ["configuration", "fields", "fields-row", "runs-row", "user-runs-row",
                  "run_number", "user_runs"]) {
    elements[id] = {value: "", innerHTML: "", disabled: false, style: {}};
}
// Model the browser clearing a select's value when its options are replaced.
let runOptions = "";
Object.defineProperty(elements.run_number, "innerHTML", {
    get() { return runOptions; },
    set(value) { runOptions = value; this.value = ""; },
});

const setup = {
    rgk_spring2024: {
        runs: {19324: {title: "RGK Spring24", torus: "+1.00", solenoid: "-1.00"}},
    },
    rgk_fall2018_FTOn: {"tor+1.00_sol-1.00": []},
};
const context = vm.createContext({
    window: {},
    document: {getElementById(id) { return elements[id] || null; }},
    XMLHttpRequest: class {
        open() {}
        send() {
            this.readyState = 4;
            this.status = 200;
            this.responseText = JSON.stringify(setup);
            this.onreadystatechange();
        }
    },
});
vm.runInContext(fs.readFileSync(path.join(__dirname, "../web_portal/main.js"), "utf8"), context);

elements.configuration.value = "rgk_spring2024";
context.fieldSelected();
assert.equal(elements.run_number.disabled, false);
assert.match(elements.run_number.innerHTML, /19324/);
elements.run_number.value = "19324";
elements.user_runs.value = "19324, 19359";

elements.configuration.value = "rgk_fall2018_FTOn";
context.fieldSelected();
assert.equal(elements.run_number.value, "");
assert.equal(elements.run_number.disabled, true);
assert.equal(elements.user_runs.value, "");
assert.equal(elements.user_runs.disabled, true);
assert.equal(elements["runs-row"].style.display, "none");
assert.match(elements.fields.innerHTML, /tor\+1.00_sol-1.00/);

elements.configuration.value = "rgk_spring2024";
context.fieldSelected();
assert.equal(elements.run_number.disabled, false);
assert.equal(elements.user_runs.disabled, false);
assert.match(elements.run_number.innerHTML, /19324/);
console.log("Portal run controls reset on configuration changes and re-enable for run selection.");
