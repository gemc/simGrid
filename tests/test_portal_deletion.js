// Run offline with: node --test tests/test_portal_deletion.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const {test} = require("node:test");
const source = fs.readFileSync(path.join(__dirname, "../web_portal/main.js"), "utf8");

function portal(confirm, response) {
    const message = {textContent: ""};
    const calls = [];
    const context = vm.createContext({
        window: {confirm}, URLSearchParams,
        document: {getElementById(id) { return id === "jobDeletionMessage" ? message : null; }},
        fetch: async (...args) => { calls.push(args); return response; },
    });
    vm.runInContext(source, context);
    return {context, message, calls};
}

const data = {requested_id: 42, osg_id: 1234, can_delete: true, csrf_token: "token"};

test("button is rendered only with explicit owner permission and a request token", () => {
    const {context} = portal();
    assert.match(context.renderJobDetails(data), /DELETE JOB/);
    for (const changed of [{can_delete: false}, {can_delete: "true"}, {csrf_token: ""}]) {
        assert.doesNotMatch(context.renderJobDetails({...data, ...changed}), /DELETE JOB/);
    }
});

test("canceling confirmation sends no deletion request", async () => {
    const {context, calls} = portal(() => false);
    const button = {disabled: false};
    await context.deleteJob(data, button);
    assert.equal(calls.length, 0);
    assert.equal(button.disabled, false);
});

test("confirmed deletion sends a POST with ID and token, then hides the button", async () => {
    const {context, message, calls} = portal(text => {
        assert.match(text, /OSG ID 1234/);
        assert.match(text, /permanently deletes/);
        return true;
    }, {ok: true, json: async () => ({message: "Deletion scheduled.", queued: true})});
    const button = {};
    await context.deleteJob(data, button);
    assert.equal(calls[0][0], "delete_submission.php");
    assert.equal(calls[0][1].method, "POST");
    assert.equal(calls[0][1].body, "id=42&csrf_token=token");
    assert.equal(button.hidden, true);
    assert.match(message.textContent, /Deletion scheduled/);
});

test("rejected request reports the error and re-enables retry", async () => {
    const {context, message} = portal(() => true, {
        ok: false, json: async () => ({error: "Only the submitting user can delete this job."}),
    });
    const button = {};
    await context.deleteJob(data, button);
    assert.equal(button.disabled, false);
    assert.match(message.textContent, /Only the submitting user/);
});
