// Run offline with: node --test tests/test_portal_estimates.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const {test} = require("node:test");

const source = fs.readFileSync(path.join(__dirname, "../web_portal/main.js"), "utf8");

function portal() {
    const elements = {};
    for (const id of ["osgLog", "osgLog_summary"]) {
        elements[id] = {innerHTML: "", dataset: {}, addEventListener() {}};
    }
    const context = vm.createContext({
        window: {},
        document: {getElementById(id) { return elements[id] || null; }},
    });
    vm.runInContext(source, context);
    context.ensureJobDetailsModal = function () {};
    return {context, elements};
}

const {context} = portal();

test("total includes the slowest user's processing and queue delay", () => {
    const user = context.calculateEstimatedTimeRemaining(
        4, 1, 10000, 0, 100, 10, 1000, 100, 10000, 1
    );
    assert.equal(user.days, 20);
    const total = context.calculateTotalEstimatedTimeRemaining(10, 20000, 0, 10000, 10, 1, [user]);
    assert.equal(total.days, 20);
});

test("a queued-only user's first arrival is not the total completion time", () => {
    const user = context.calculateEstimatedTimeRemaining(10, 0, 0, 0, 0, 1, 100, 100, 10000, 1);
    assert.equal(user.queueOnly, true);
    assert.equal(user.days, 1);
    const total = context.calculateTotalEstimatedTimeRemaining(10, 0, 0, 10000, 10, 1, [user]);
    assert.equal(total.days, 11);
});

test("processing can overlap queue waiting", () => {
    const total = context.calculateTotalEstimatedTimeRemaining(10, 100000, 0, 10000, 10, 1, []);
    assert.equal(total.days, 20);
});

test("a slow queue includes processing after the last arrival", () => {
    const total = context.calculateTotalEstimatedTimeRemaining(2, 0, 0, 10000, 2, 0.1, []);
    assert.equal(total.days, 21);
});

test("without pending submissions the total still respects slower users", () => {
    const total = context.calculateTotalEstimatedTimeRemaining(0, 20000, 10000, 10000, 0, null,
        [{days: 3}]);
    assert.equal(total.days, 3);
});

test("missing rates, priorities or active user estimates leave completion unknown", () => {
    for (const rate of [null, undefined, 0, -1, NaN, Infinity]) {
        assert.equal(context.calculateTotalEstimatedTimeRemaining(1, 0, 0, rate, 1, 1, []).days, null);
        assert.equal(context.calculateTotalEstimatedTimeRemaining(1, 0, 0, 10000, 1, rate, []).days, null);
    }
    assert.equal(context.calculateTotalEstimatedTimeRemaining(1, 0, 0, 10000, 0, 1, []).days, null);
    assert.equal(context.calculateTotalEstimatedTimeRemaining(0, 10, 0, 10000, 0, null,
        [{days: null}]).days, null);
    assert.equal(context.calculateTotalEstimatedTimeRemaining(NaN, 0, 0, 10000, 0, 1, []).days, null);
});

test("finished work needs no completion rate", () => {
    assert.equal(context.calculateTotalEstimatedTimeRemaining(0, 100, 100, null, 0, null, []).days, 0);
});

function submitted(user, jobs, done, run) {
    return {user, jobs, done, run, idle: jobs - done - run, mysql_status: "Submitted to OSG"};
}

function pending(user, priority) {
    return {user, priority, jobs: null, done: null, run: null, idle: null, mysql_status: "Not Submitted"};
}

async function render(results, mode = "production") {
    const {context, elements} = portal();
    context.fetch = async function () {
        const database = mode === "devel" ? "CLAS12TEST" : "CLAS12OCR";
        return {json: async () => ({[database]: {results, average_completions_per_day: 10000}})};
    };
    context.osgLogtoTable(mode);
    await new Promise(resolve => setImmediate(resolve));
    const html = elements.osgLog_summary.innerHTML;
    assert.notEqual(html, "", "The summary must render successfully");
    return html;
}

function estimateCell(html, user) {
    const row = html.match(new RegExp("<tr><td>" + user + "</td>(.*?)</tr>"));
    assert.ok(row, "Missing summary row for " + user);
    return row[1].match(/<td[^>]*>([^<]*)<\/td>$/)[1];
}

test("the rendered total cannot finish before a user with a queue delay", async () => {
    const rows = [submitted("alice", 10000, 0, 100), submitted("bob", 10000, 9000, 900)];
    for (let priority = 1; priority <= 10; priority++) {
        rows.push(pending(priority <= 6 ? "bob" : "alice", priority));
    }
    const html = await render(rows);
    assert.match(estimateCell(html, "alice"), /12\.0 days$/);
    assert.match(estimateCell(html, "totals"), /12\.0 days$/);
});

test("the rendered total waits for a queued-only user's last submission", async () => {
    const html = await render([submitted("alice", 10000, 10000, 0),
        pending("bob", 1), pending("bob", 2), pending("bob", 3)], "devel");
    assert.equal(estimateCell(html, "bob"), "to osg: 1.0 days");
    assert.match(estimateCell(html, "totals"), /4\.0 days$/);
});

test("a terminal pre-submission failure does not make active work unknown", async () => {
    const html = await render([submitted("alice", 10000, 0, 100),
        {...pending("bob", 0), mysql_status: "Failed to Read Directory"}]);
    assert.match(estimateCell(html, "totals"), /1\.0 days$/);
});

test("the rendered total is unknown when pending queue positions are missing", async () => {
    const html = await render([submitted("alice", 10000, 0, 100), pending("bob", null)]);
    assert.match(estimateCell(html, "totals"), /N\/A$/);
});
