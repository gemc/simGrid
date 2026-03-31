//Multiplication (https://stackoverflow.com/questions/21223164/multiplying-two-inputs-with-javascript-displaying-in-text-box)
function calculate() {
	var myBox1 = document.getElementById('box1').value;
	var myBox2 = document.getElementById('box2').value;
	var result = document.getElementById('result');
	var myResult = myBox1 * myBox2;
	document.getElementById('result').value = myResult / 1000000;

}

window.onscroll = function () {
	myFunction();
};

var navbar = document.getElementById("nav");
var sticky = navbar ? navbar.offsetTop : 0;

function myFunction() {
	if (!navbar) return;

	if (window.pageYOffset >= sticky) {
		navbar.classList.add("sticky");
	} else {
		navbar.classList.remove("sticky");
	}
}

function formatNumber(value, digits = 1) {
	var num = Number(value);
	if (!isFinite(num)) return "";
	return num.toFixed(digits);
}

function formatAgeDays(value) {
	var num = Number(value);
	if (!isFinite(num)) return "";
	return num.toFixed(2);
}

function genSelected(val) {
	var generator = document.getElementById("generator").value;

	if (generator == "clasdis") {
		document.getElementById("generatorLink").getElementsByTagName('a')[0].href = 'https://github.com/JeffersonLab/clasdis-nocernlib/blob/master/README.md';
		document.getElementById("generatorLink").getElementsByTagName('a')[0].innerHTML = '<br/> → clasdis options';

	} else if (generator == "claspyth") {
		document.getElementById("generatorLink").getElementsByTagName('a')[0].href = 'https://github.com/JeffersonLab/claspyth/blob/master/README.md';
		document.getElementById("generatorLink").getElementsByTagName('a')[0].innerHTML = '<br/> → claspyth options';

	} else if (generator == "dvcsgen") {
		document.getElementById("generatorLink").getElementsByTagName('a')[0].href = 'https://github.com/JeffersonLab/dvcsgen/blob/master/README.md';
		document.getElementById("generatorLink").getElementsByTagName('a')[0].innerHTML = '<br/> → dvcsgen options';

	} else if (generator == "genKYandOnePion") {
		document.getElementById("generatorLink").getElementsByTagName('a')[0].href = 'https://github.com/ValeriiKlimenko/genKYandOnePion/blob/master/README.md';
		document.getElementById("generatorLink").getElementsByTagName('a')[0].innerHTML = '<br/> → genKYandOnePion options';

	} else if (generator == "MCEGENpiN_radcorr") {
		document.getElementById("generatorLink").getElementsByTagName('a')[0].href = 'https://github.com/Maksaska/MCEGENpiN_radcorr#readme';
		document.getElementById("generatorLink").getElementsByTagName('a')[0].innerHTML = '<br/> → MCEGENpiN_radcorr options';

	} else if (generator == "inclusive-dis-rad") {
		document.getElementById("generatorLink").getElementsByTagName('a')[0].href = 'https://github.com/JeffersonLab/inclusive-dis-rad/blob/master/README.md';
		document.getElementById("generatorLink").getElementsByTagName('a')[0].innerHTML = '<br/> → disrad options';

	} else if (generator == "JPsiGen") {
		document.getElementById("generatorLink").getElementsByTagName('a')[0].href = 'https://github.com/JeffersonLab/JPsiGen/blob/master/README.md';
		document.getElementById("generatorLink").getElementsByTagName('a')[0].innerHTML = '<br/> → JPsiGen options';

	} else if (generator == "TCSGen") {
		document.getElementById("generatorLink").getElementsByTagName('a')[0].href = 'https://github.com/JeffersonLab/TCSGen/blob/master/README.md';
		document.getElementById("generatorLink").getElementsByTagName('a')[0].innerHTML = '<br/> → TCSGen options';

	} else if (generator == "twopeg") {
		document.getElementById("generatorLink").getElementsByTagName('a')[0].href = 'https://github.com/skorodumina/twopeg/blob/main/README.md';
		document.getElementById("generatorLink").getElementsByTagName('a')[0].innerHTML = '<br/> → twopeg options';

	} else if (generator == "clas12-elSpectro") {
		document.getElementById("generatorLink").getElementsByTagName('a')[0].href = 'https://github.com/dglazier/clas12-elSpectro/wiki/Running-on-OSG';
		document.getElementById("generatorLink").getElementsByTagName('a')[0].innerHTML = '<br/> → clas12-elSpectro options';

	} else if (generator == "deep-pipi-gen") {
		document.getElementById("generatorLink").getElementsByTagName('a')[0].href = 'https://github.com/jeffersonlab/deep-pipi-gen/';
		document.getElementById("generatorLink").getElementsByTagName('a')[0].innerHTML = '<br/> → deep-pipi-gen options';

	} else if (generator == "genepi") {
		document.getElementById("generatorLink").getElementsByTagName('a')[0].href = 'https://github.com/N-Plx/genepi/tree/OSG';
		document.getElementById("generatorLink").getElementsByTagName('a')[0].innerHTML = '<br/> → genepi options';

	} else if (generator == "onepigen") {
		document.getElementById("generatorLink").getElementsByTagName('a')[0].href = 'https://github.com/tylern4/onepigen';
		document.getElementById("generatorLink").getElementsByTagName('a')[0].innerHTML = '<br/> → onepigen options';

	} else if (generator == "gibuu") {
		document.getElementById("generatorLink").getElementsByTagName('a')[0].href = 'https://github.com/JeffersonLab/clas12-mcgen/tree/main/gibuu';
		document.getElementById("generatorLink").getElementsByTagName('a')[0].innerHTML = '<br/> → gibuu options';

	} else if (generator == "clas-stringspinner") {
		document.getElementById("generatorLink").getElementsByTagName('a')[0].href = 'https://jeffersonlab.github.io/clas-stringspinner/';
		document.getElementById("generatorLink").getElementsByTagName('a')[0].innerHTML = '<br/> → clas-stringspinner generator options';

	} else if (generator == "gemc") {
		document.getElementById("generatorLink").getElementsByTagName('a')[0].href = 'https://gemc.jlab.org/gemc/html/documentation/generator/internal.html';
		document.getElementById("generatorLink").getElementsByTagName('a')[0].innerHTML = '<br/> → gemc generator options';
	}

}

// The configuration is read from data/xrootd
function configurationSelected() {
	var text = "<option selected hidden value=\"\"></option>";
	var xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function () {
		if (this.readyState == 4 && this.status == 200) {
			var myObj = JSON.parse(this.responseText);
			for (experiments in myObj) {
				text += "<option value=\"" + experiments + "\">" + experiments + "</option>";
			}
			document.getElementById("configuration").innerHTML = text;
		}
	};
	xmlhttp.open("GET", "data/setup.json", true);
	xmlhttp.send();
}


function fieldSelected() {
	var selected_experiment = document.getElementById("configuration").value;

	var text = "<option selected hidden value=\"\"></option>";
	var xmlhttp = new XMLHttpRequest();

	xmlhttp.onreadystatechange = function () {
		if (this.readyState == 4 && this.status == 200) {
			var myObj = JSON.parse(this.responseText);

			if (selected_experiment in myObj) {

				var keys_field = Object.keys(myObj[selected_experiment]);

				for (key in keys_field) {
					if (keys_field[key].includes("tor")) {
						text += "<option value=\"" + keys_field[key] + "\">" + keys_field[key] + "</option>";
					}
				}
			}
			document.getElementById("fields").innerHTML = text;
		}
	};
	xmlhttp.open("GET", "data/setup.json", true);
	xmlhttp.send();
}


function softwareVersionSelected() {
	const selected_experiment = document.getElementById("configuration").value;

	let text = '<option selected hidden value=""></option>';
	const xmlhttp = new XMLHttpRequest();

	xmlhttp.onreadystatechange = function () {
		if (this.readyState === 4 && this.status === 200) {
			const data = JSON.parse(this.responseText);

			if (data[selected_experiment]) {
				const versions = data[selected_experiment].software_versions;
				for (const key in versions) {
					if (Object.hasOwnProperty.call(versions, key) && versions[key].includes("gemc/")) {
						text += `<option value="${versions[key]}">${versions[key]}</option>`;
					}
				}
			}

			document.getElementById("softwarev").innerHTML = text;
		}
	};

	xmlhttp.open("GET", "data/setup.json", true);
	xmlhttp.send();
}


function vertexSelected() {

	var selected_experiment = document.getElementById("configuration").value;
	var textz = "";
	var textr = "";
	var texts = "";

	var selected_softwareversion = document.getElementById("softwarev").value;
	// exit if selected_softwareversion is "gemc/4.4.2 coatjava/6.5.9 (pass1 rgb)"


	var xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function () {
		if (this.readyState == 4 && this.status == 200) {

			var myObj = JSON.parse(this.responseText);

			if (selected_experiment in myObj) {

				var zpos = myObj[selected_experiment]["z-position"];
				var rast = myObj[selected_experiment]["raster"];
				var bspot = myObj[selected_experiment]["beam_spot"];

				if (document.getElementById("zposition-check").checked) {
					textz = zpos[0];
				} else {
					textz = "";
				}
				if (document.getElementById("raster-check").checked) {
					textr = rast[0];
				} else {
					textr = "";
				}
				if (document.getElementById("beamspot-check").checked) {
					texts = bspot[0];
				} else {
					texts = "";
				}

			} else {
				text = "";
			}
			document.getElementById("zposition-show").value = textz;
			document.getElementById("raster-show").value = textr;
			document.getElementById("beamspot-show").value = texts;


			// if textz textr texts are empty, hide the vertex radio buttons
			if (textz == "" && textr == "" && texts == "") {
				document.getElementById("vertex_user_selection").style.display = "none";
			} else {
				document.getElementById("vertex_user_selection").style.display = "block";
			}

			if (selected_softwareversion == "gemc/4.4.2 coatjava/6.5.9" || selected_softwareversion == "gemc/4.4.2 coatjava/6.5.6.1") {
				document.getElementById("zposition-check").style.display = "none";
				document.getElementById("raster-check").style.display = "none";
				document.getElementById("beamspot-check").style.display = "none";
				document.getElementById("vertex_user_selection").style.display = "none";
				document.getElementById("zposition-show").value = "n/a";
				document.getElementById("raster-show").value = "n/a";
				document.getElementById("beamspot-show").value = "n/a";

			} else {
				document.getElementById("zposition-check").style.display = "inline";
				document.getElementById("raster-check").style.display = "inline";
				document.getElementById("beamspot-check").style.display = "inline";
				document.getElementById("vertex_user_selection").style.display = "inline";
			}
			if (textz == "") {
				document.getElementById("zposition-show").value = "n/a";
			}
			if (textr == "") {
				document.getElementById("raster-show").value = "n/a";
			}
			if (texts == "") {
				document.getElementById("beamspot-show").value = "n/a";
			}
		}
	};
	xmlhttp.open("GET", "data/setup.json", true);
	xmlhttp.send();


}


function update_mcgen_versions() {
	var default_val = "3.18";
	var text = "<option selected  value=\" " + default_val + "\">" + default_val + "</option>";
	var xmlhttp = new XMLHttpRequest();

	xmlhttp.onreadystatechange = function () {
		if (this.readyState == 4 && this.status == 200) {

			var myObj = JSON.parse(this.responseText);
			var vals = myObj["mcgen_versions"];

			for (val in vals) {
				if (vals[val] == default_val) continue;
				text += "<option  value=\"" + vals[val] + "\">" + vals[val] + "</option>";
			}

			document.getElementById("mcgenv").innerHTML = text;
		}
	};
	xmlhttp.open("GET", "data/software_versions.json", true);
	xmlhttp.send();
}

function bkmergingSelected() {
	var experiments = document.getElementById("configuration").value;
	var fields = document.getElementById("fields").value;
	var text = "<option selected  value=\"no\"> Not Available </option>";
	var xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function () {
		if (this.readyState == 4 && this.status == 200) {
			var myObj = JSON.parse(this.responseText);
			if (experiments in myObj) {
				var vals = myObj[experiments][fields];
				text = "<option selected  value=\"no\"> No </option>";
				for (val in vals) {
					text += "<option value=\"" + vals[val] + "\">" + vals[val] + "</option>";
				}
			}
			document.getElementById("bkmerging").innerHTML = text;
		}
	};
	xmlhttp.open("GET", "data/setup.json", true);
	xmlhttp.send();
}

function escapeHtml(value) {
	if (value === null || value === undefined) return "";
	return String(value)
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;");
}

function ensureJobDetailsModal() {
	if (document.getElementById("jobDetailsModal")) return;

	const style = document.createElement("style");
	style.textContent = `
		#jobDetailsModal {
			display: none;
			position: fixed;
			z-index: 9999;
			left: 0;
			top: 0;
			width: 100%;
			height: 100%;
			background: rgba(0,0,0,0.45);
		}
		#jobDetailsModal .modal-content {
			background: #fff;
			margin: 4% auto;
			padding: 20px;
			width: 80%;
			max-width: 950px;
			max-height: 82vh;
			overflow-y: auto;
			border-radius: 8px;
			box-shadow: 0 8px 30px rgba(0,0,0,0.25);
			font-family: Arial, sans-serif;
		}
		#jobDetailsModal .modal-close {
			float: right;
			font-size: 26px;
			font-weight: bold;
			cursor: pointer;
			margin-top: -6px;
		}
		#jobDetailsModal h3 {
			margin-top: 0;
			margin-bottom: 14px;
		}
		#jobDetailsModal table {
			width: 100%;
			border-collapse: collapse;
			margin-top: 10px;
		}
		#jobDetailsModal th,
		#jobDetailsModal td {
			border: 1px solid #d9d9d9;
			padding: 8px 10px;
			text-align: left;
			vertical-align: top;
		}
		#jobDetailsModal th {
			background: #f4f4f4;
			width: 220px;
		}
		#jobDetailsModal pre {
			margin: 0;
			white-space: pre-wrap;
			word-break: break-word;
			font-family: Menlo, Consolas, monospace;
			font-size: 13px;
		}
		.job-id-link {
			cursor: pointer;
			color: #0b5ed7;
			text-decoration: underline;
		}
	`;
	document.head.appendChild(style);

	const modal = document.createElement("div");
	modal.id = "jobDetailsModal";
	modal.innerHTML = `
		<div class="modal-content">
			<span class="modal-close" id="jobDetailsModalClose">&times;</span>
			<div id="jobDetailsBody">Loading...</div>
		</div>
	`;
	document.body.appendChild(modal);

	document.getElementById("jobDetailsModalClose").onclick = function () {
		modal.style.display = "none";
	};

	window.addEventListener("click", function (event) {
		if (event.target === modal) {
			modal.style.display = "none";
		}
	});
}

function renderJobDetails(data) {
	let html = `<h3>Submission Details for Job ${escapeHtml(data.requested_id || "")}</h3>`;

	if (data.error) {
		html += `<div style="color:#b00020;font-weight:bold;">${escapeHtml(data.error)}</div>`;
		return html;
	}

	html += `<table>`;

	if (data.user) {
		html += `<tr><th>User</th><td>${escapeHtml(data.user)}</td></tr>`;
	}
	if (data.user_submission_id) {
		html += `<tr><th>Job ID</th><td>${escapeHtml(data.user_submission_id)}</td></tr>`;
	}
	if (data.status) {
		html += `<tr><th>Status</th><td>${escapeHtml(data.status)}</td></tr>`;
	}

	if (data.details && Array.isArray(data.details) && data.details.length > 0) {
		for (const item of data.details) {
			html += `
				<tr>
					<th>${escapeHtml(item.key)}</th>
					<td><pre>${escapeHtml(item.value)}</pre></td>
				</tr>
			`;
		}
	} else if (data.raw_scard) {
		html += `
			<tr>
				<th>Details</th>
				<td><pre>${escapeHtml(data.raw_scard)}</pre></td>
			</tr>
		`;
	}

	html += `</table>`;
	return html;
}

function showJobDetails(jobId) {
	ensureJobDetailsModal();

	const modal = document.getElementById("jobDetailsModal");
	const body = document.getElementById("jobDetailsBody");
	body.innerHTML = `<h3>Submission Details for Job ${escapeHtml(jobId)}</h3><div>Loading...</div>`;
	modal.style.display = "block";

	fetch("get_submission_details.php?id=" + encodeURIComponent(jobId))
		.then(response => response.json())
		.then(data => {
			body.innerHTML = renderJobDetails(data);
		})
		.catch(error => {
			body.innerHTML = `
				<h3>Submission Details for Job ${escapeHtml(jobId)}</h3>
				<div style="color:#b00020;font-weight:bold;">Failed to load submission details.</div>
				<pre>${escapeHtml(error)}</pre>
			`;
		});
}

function osgLogtoTable(mode) {
	var logFile = "data/osgLog.json";
	var dictionaryName = null;

	if (mode === "production") {
		logFile = "data/osg-production.json";
		dictionaryName = "CLAS12OCR";
	} else if (mode === "devel") {
		logFile = "data/osg-devel.json";
		dictionaryName = "CLAS12TEST";
	}

	fetch(logFile)
		.then(function (r) {
			return r.json();
		})
		.then(function (myObj) {

			var selectedBlock = null;

			if (dictionaryName && myObj[dictionaryName]) {
				selectedBlock = myObj[dictionaryName];
			} else if (myObj.user_data) {
				// backward compatibility with old format
				selectedBlock = {
					results: myObj.user_data,
					update_timestamp: {},
					database: "",
					owner: "",
					count: myObj.user_data.length
				};
			}

			if (!selectedBlock || !Array.isArray(selectedBlock.results)) {
				document.getElementById("osgLog").innerHTML =
					"<div style=\"color:#b00020;font-weight:bold;\">Invalid OSG log format.</div>";
				document.getElementById("osgLog_summary").innerHTML = "";
				return;
			}

			var userData = selectedBlock.results;

			var txt = "<table align=\"center\" style=\"width:80%;text-align:center\"><caption align=\"bottom\">";
			var txt_summary = "<table align=\"center\" style=\"width:50%;text-align:center\"><tr>";

			var footer = "";
			if (selectedBlock.update_timestamp && selectedBlock.update_timestamp.time) {
				footer += "Updated: " + escapeHtml(selectedBlock.update_timestamp.time);
			}
			if (selectedBlock.database) {
				if (footer) footer += " | ";
				footer += "Database: " + escapeHtml(selectedBlock.database);
			}
			if (selectedBlock.owner) {
				if (footer) footer += " | ";
				footer += "Owner: " + escapeHtml(selectedBlock.owner);
			}
			if (selectedBlock.count !== undefined && selectedBlock.count !== null) {
				if (footer) footer += " | ";
				footer += "Count: " + escapeHtml(selectedBlock.count);
			}

			txt += footer;
			txt += "</caption>";

			if (!userData.length) {
				txt += "<tr><td>No entries found.</td></tr></table>";
				document.getElementById("osgLog").innerHTML = txt;
				document.getElementById("osgLog_summary").innerHTML = "";
				return;
			}

			var data_summary = {
				"user": [],
				"submission": [],
				"total": [],
				"done": [],
				"run": [],
				"idle": []
			};

			var keys = Object.keys(userData[0]);

			keys = keys.filter(function (key) {
				return ![
					"mysql_status",
					"mysql_client_time",
					"priority",
					"pool_node",
					"user_submission_id"
				].includes(key);
			});

			var jobIdKey = null;
			for (var k = 0; k < keys.length; k++) {
				if (String(keys[k]).toLowerCase().replace(/\s+/g, "") === "jobid") {
					jobIdKey = keys[k];
					break;
				}
			}

			txt += "<tr>";
			for (var i = 0; i < keys.length; i++) {
				txt += "<th>" + escapeHtml(keys[i]) + "</th>";
			}
			txt += "<th>order</th></tr>";

			for (var s in Object.keys(data_summary)) {
				txt_summary += "<th>" + escapeHtml(Object.keys(data_summary)[s]) + "</th>";
			}

			for (var row = 0; row < userData.length; row++) {
				var val = userData[row];
				txt += "<tr>";

				for (var col = 0; col < keys.length; col++) {
					var key = keys[col];
					txt += "<td>";

					if (key === jobIdKey) {
						txt += "<a href=\"#\" class=\"job-id-link\" data-job-id=\"" +
							escapeHtml(val[key]) + "\">" + escapeHtml(val[key]) + "</a>";
					} else {
						txt += escapeHtml(val[key]);
					}

					txt += "</td>";
				}

				txt += "<td></td></tr>";

				if (data_summary.user.includes(val.user)) {
					var idx = data_summary.user.indexOf(val.user);
					data_summary.total[idx] += Number(val.total || 0);
					data_summary.done[idx] += Number(val.done || 0);
					data_summary.run[idx] += Number(val.run || 0);
					data_summary.idle[idx] += Number(val.idle || 0);
					data_summary.submission[idx] += 1;
				} else {
					data_summary.user.push(val.user || "");
					data_summary.submission.push(1);
					data_summary.total.push(Number(val.total || 0));
					data_summary.done.push(Number(val.done || 0));
					data_summary.run.push(Number(val.run || 0));
					data_summary.idle.push(Number(val.idle || 0));
				}
			}

			txt += "</table>";

			for (var u = 0; u < data_summary.user.length; u++) {
				txt_summary += "</tr><tr>";
				txt_summary += "<td>" + escapeHtml(data_summary.user[u]) + "</td>";
				txt_summary += "<td>" + escapeHtml(data_summary.submission[u]) + "</td>";
				txt_summary += "<td>" + escapeHtml(data_summary.total[u]) + "</td>";
				txt_summary += "<td>" + escapeHtml(data_summary.done[u]) + "</td>";
				txt_summary += "<td>" + escapeHtml(data_summary.run[u]) + "</td>";
				txt_summary += "<td>" + escapeHtml(data_summary.idle[u]) + "</td>";
			}

			txt_summary += "</tr><tr><td>total</td>";
			txt_summary += "<td>" + data_summary.submission.reduce(function (a, b) {
				return Number(a) + Number(b);
			}, 0) + "</td>";
			txt_summary += "<td>" + data_summary.total.reduce(function (a, b) {
				return Number(a) + Number(b);
			}, 0) + "</td>";
			txt_summary += "<td>" + data_summary.done.reduce(function (a, b) {
				return Number(a) + Number(b);
			}, 0) + "</td>";
			txt_summary += "<td>" + data_summary.run.reduce(function (a, b) {
				return Number(a) + Number(b);
			}, 0) + "</td>";
			txt_summary += "<td>" + data_summary.idle.reduce(function (a, b) {
				return Number(a) + Number(b);
			}, 0) + "</td>";
			txt_summary += "</tr></table>";

			document.getElementById("osgLog").innerHTML = txt;
			document.getElementById("osgLog_summary").innerHTML = txt_summary;

			var osgLogEl = document.getElementById("osgLog");
			if (!osgLogEl.dataset.jobClickBound) {
				osgLogEl.addEventListener("click", function (e) {
					var link = e.target.closest(".job-id-link");
					if (!link) return;
					e.preventDefault();
					showJobDetails(link.dataset.jobId);
				});
				osgLogEl.dataset.jobClickBound = "1";
			}

			ensureJobDetailsModal();

			fetch("data/submission_priorities.json")
				.then(function (r) {
					return r.json();
				})
				.then(function (priorityObj) {
					var priorities = (priorityObj && priorityObj.priorities) ? priorityObj.priorities : [];
					var priorityMap = {};

					for (var p = 0; p < priorities.length; p++) {
						var entry = priorities[p];
						if (entry.user_submission_id != null) {
							priorityMap[String(entry.user_submission_id).trim()] = entry.priority;
						}
					}

					var rows = document.querySelectorAll("#osgLog table tr");
					for (var r = 1; r < rows.length; r++) {
						var cells = rows[r].querySelectorAll("td");
						if (!cells.length) continue;

						var lastCell = cells[cells.length - 1];
						var link = rows[r].querySelector(".job-id-link");
						var jobId = link ? link.dataset.jobId : "";

						var osgIdCell = null;
						var headerCells = rows[0] ? rows[0].querySelectorAll("th") : [];
						for (var h = 0; h < headerCells.length; h++) {
							if (headerCells[h].textContent.trim() === "osg id") {
								osgIdCell = cells[h];
								break;
							}
						}

						var osgIdVal = osgIdCell ? osgIdCell.textContent.trim() : "";
						if ((osgIdVal === "null" || osgIdVal === "" || osgIdVal === "Not Submitted") &&
							priorityMap.hasOwnProperty(jobId)) {
							lastCell.textContent = priorityMap[jobId];
						}
					}
				})
				.catch(function (e) {
					console.warn("priorities fetch failed:", e);
				});
		})
		.catch(function (e) {
			document.getElementById("osgLog").innerHTML =
				"<div style=\"color:#b00020;font-weight:bold;\">Failed to load OSG log data.</div>";
			document.getElementById("osgLog_summary").innerHTML = "";
			console.warn("osg log fetch failed:", e);
		});
}

function fairshareToTable() {
	var fairshareEl = document.getElementById("fairshare");
	var fairshareSummaryEl = document.getElementById("fairshare_summary");
	var fairshareUserSummaryEl = document.getElementById("fairshare_user_summary");

	if (!fairshareEl || !fairshareSummaryEl || !fairshareUserSummaryEl) {
		return;
	}

	var xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function () {
		if (this.readyState == 4) {
			if (this.status != 200) {
				fairshareEl.innerHTML = "<div style=\"color:#b00020;font-weight:bold;\">Failed to load fairshare data.</div>";
				fairshareSummaryEl.innerHTML = "";
				fairshareUserSummaryEl.innerHTML = "";
				return;
			}

			var myObj = JSON.parse(this.responseText);

			var priorities = [];
			if (myObj.priorities && Array.isArray(myObj.priorities)) {
				priorities = myObj.priorities;
			}

			var jobsPerUser = [];
			if (myObj.jobs_per_user && Array.isArray(myObj.jobs_per_user)) {
				jobsPerUser = myObj.jobs_per_user;
			}

			var daysConsidered = "all";
			if (myObj.days_considered !== null && myObj.days_considered !== undefined) {
				daysConsidered = "last " + myObj.days_considered;
			}

			// Settings summary table
			var summaryTxt = "<table align=\"center\" style=\"width:60%;text-align:center\">";
			summaryTxt += "<tr><th>Setting</th><th>Value</th></tr>";
			summaryTxt += "<tr><td>Algorithm</td><td>" + escapeHtml(myObj.priority_algorithm || "") + "</td></tr>";
			summaryTxt += "<tr><td>Aging Half-life (days)</td><td>" + escapeHtml(myObj.half_life_days == null ? "n/a" : myObj.half_life_days) + "</td></tr>";
			summaryTxt += "<tr><td>History half-life (days)</td><td>" + escapeHtml(myObj.history_half_life_days == null ? "n/a" : myObj.history_half_life_days) + "</td></tr>";
			summaryTxt += "<tr><td>Days considered</td><td>" + escapeHtml(daysConsidered) + "</td></tr>";
			summaryTxt += "<tr><td>Number of Submissions</td><td>" + escapeHtml(myObj.total_submissions || 0) + "</td></tr>";
			summaryTxt += "<tr><td>Total users</td><td>" + escapeHtml(myObj.total_users || 0) + "</td></tr>";
			summaryTxt += "<tr><td>Not Submitted</td><td>" + escapeHtml(myObj.total_not_submitted_jobs || 0) + "</td></tr>";
			summaryTxt += "</table>";

			// Per-user summary table
			var userSummaryTxt = "<table align=\"center\" style=\"width:60%;text-align:center\">";
			userSummaryTxt += "<tr><th>user</th><th>submissions</th><th>history weight</th><th>pending</th></tr>";
			for (var i = 0; i < jobsPerUser.length; i++) {
				userSummaryTxt += "<tr>";
				userSummaryTxt += "<td>" + escapeHtml(jobsPerUser[i].user) + "</td>";
				userSummaryTxt += "<td>" + escapeHtml(jobsPerUser[i].jobs) + "</td>";
				userSummaryTxt += "<td>" + escapeHtml(formatNumber(jobsPerUser[i].submitted_load * 100, 2)) + "</td>";
				userSummaryTxt += "<td>" + escapeHtml(jobsPerUser[i].pending_jobs) + "</td>";
				userSummaryTxt += "</tr>";
			}
			if (jobsPerUser.length === 0) {
				userSummaryTxt += "<tr><td colspan=\"4\">No summary entries found.</td></tr>";
			}
			userSummaryTxt += "</table>";

			// Per-job priorities table
			var txt = "<table align=\"center\" style=\"width:90%;text-align:center\"><tr>";
			var headers = [
				"user",
				"user_submission_id",
				"date",
				"order",
				"wait_time (h)",
				"pending",
				"score",
				"age_days"
			];

			for (var j = 0; j < headers.length; j++) {
				txt += "<th>" + headers[j] + "</th>";
			}
			txt += "</tr>";

			for (var rowIndex = 0; rowIndex < priorities.length; rowIndex++) {
				var row = priorities[rowIndex];

				var waitTime = "";
				var clientMs = Date.parse(row.client_time ? row.client_time.replace(" ", "T") : "");
				if (!isNaN(clientMs)) {
					var hours = (Date.now() - clientMs) / 3600000;
					if (hours >= 0) waitTime = hours.toFixed(1);
				}

				txt += "<tr>";
				txt += "<td>" + escapeHtml(row.user) + "</td>";
				txt += "<td>" + escapeHtml(row.user_submission_id) + "</td>";
				txt += "<td>" + escapeHtml(row.client_time) + "</td>";
				txt += "<td>" + escapeHtml(row.priority) + "</td>";
				txt += "<td>" + escapeHtml(waitTime) + "</td>";
				txt += "<td>" + escapeHtml(row.pending_jobs_for_user) + "</td>";
				txt += "<td>" + escapeHtml(formatNumber(row.score)) + "</td>";
				txt += "<td>" + escapeHtml(row.age_days == null ? "n/a" : formatAgeDays(row.age_days)) + "</td>";
				txt += "</tr>";
			}

			if (priorities.length === 0) {
				txt += "<tr><td colspan=\"8\">No fairshare entries found.</td></tr>";
			}

			txt += "</table>";

			fairshareSummaryEl.innerHTML = summaryTxt;
			fairshareUserSummaryEl.innerHTML = userSummaryTxt;
			fairshareEl.innerHTML = txt;
		}
	};

	xmlhttp.open("GET", "data/submission_priorities.json", true);
	xmlhttp.send();
}


function max_events(checkboxElem) {
	var jobs = document.getElementById('box1');
	if (document.getElementById('gemcEvioOUT').checked || document.getElementById('generatorOUT').checked || document.getElementById('gemcHipoOUT').checked || document.getElementById('reconstructionOUT').checked)
		jobs.max = "100";
	else jobs.removeAttribute('max')
}

function resizable(el, factor) {
	var int = Number(factor) || 7.7;

	function resize() {
		if (el) {
			el.style.width = ((el.value.length + 1) * int) + 'px'
		}
	}

	var e = 'keyup,keypress,focus,blur,change'.split(',');


	for (var i in e) {
		if (el) {
			el.addEventListener(e[i], resize, false);
		}

	}


	resize();
}

resizable(document.getElementById('genOptions'), 7);