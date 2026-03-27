<!DOCTYPE html>
<html lang="english">
<?php require_once __DIR__ . '/head.php'; ?>
<body>
<?php require_once __DIR__ . '/header.php'; ?>

<div class="w3-row-padding w3-rest" id="contact">

	<h2>Submitting Jobs</h2>
	<p style="margin-left: 40px">
		When you click the "Submit" button:<br/>
		<li style="margin-left: 60px"><b>1</b>: Your submission is saved in our mysql db</li>
		<li style="margin-left: 60px"><b>2</b>: Within a few minutes your jobs will be submitted to OSG and visible in this
			portal.
		</li>
		<li style="margin-left: 60px"><b>3</b>: When the jobs are completed, the job will be delisted from the portal.</li>
		<li style="margin-left: 60px"><b>4</b>: The output directory is synced every hour on /volatile/clas12/osg2</li>
	</p>
	<p>
		<b tyle="margin-left: 60px">Notes:</b>:
		<li style="margin-left: 60px; background-color: gold">The number of events per job are limited to 5,000,
			corresponding to a time on the OSG between 4-10 hours depending on the node CPU
		</li>
		<li style="margin-left: 60px; background-color: gold">The number of jobs per submission are
			limited to 10,000
		</li>
	</p>
	<p style="margin-left: 40px">
		See also:<br/>
		<li style="margin-left: 60px"> Submit Jobs to OSG
			<a href="https://clasweb.jlab.org/wiki/index.php/Submit_Jobs_to_OSG"> CLAS12 Software Center </a></li>

		<br/>


	<h2> Experiment Configurations, Gcards and Yaml Files</h2>
	The job workflow and steering cards are maintained in the <a href="https://github.com/JeffersonLab/clas12-config">clas12-config</a> repo.<br/>

	<br/>
	<br/>


	<h2> Background Merging </h2>
	<p style="margin-left: 40px">
		The user choice of experiment and magnetic fieds enable the possibility of backgrond merging
		in the dropdown menu.<br/>
		If selected, a random file among the available pool (files of 10k events each) is merged
		to the simulated events before reconstruction.
	</p>
	<br/>

	<h2> Output </h2>
	<p style="margin-left: 40px">
		The output is synced hourly on
	</p>
	<pre style="font-size: 20px">	/volatile/clas12/osg/"username"/OSGID </pre>
	<p style="margin-left: 40px">
		where "<b>username</b>" is your jlab account name and <b>OSGID</b> is the OSG submission ID.<br/>
		The optional string identifier STRINGID, the OSG JOB ID and the JOBINDEX are used to form the filenames:

		<li style="margin-left: 40px"><b>STRINGID-OSGID-JOBINDEX.hipo</b> for type 1 submissions</li>
		<li style="margin-left: 40px"><b>STRINGID-LUNDFILENAME-OSGID-JOBINDEX.hipo</b> for type 2 submissions</li>
	<p style="margin-left: 40px">
		STRINGID may be set by users on the submission form. If you submit 500 jobs, JOBINDEX will run from 0 to 499.
	</p>
	</p>
	<br/>


	<h2> Priority </h2>
	<p style="margin-left: 40px">
		A priority system is in place to ensure that the resources are shared among all submissions.<br/>
		Analysis groups can submit the <a href="OSG_Priority_Request_Form.pdf"> Priority Permission Increase
		Form </a>
		to increase an account priority.<br/>
	</p>
	<br/>

	<h2> Job Status </h2>
	<p style="margin-left: 40px">
		Log files can be browsed on the submit node:<br/>
	<pre style="font-size: 20px; background-color: #ececec">

	ssh scosg2202
	ls -l /home/gemc/osgOutput/&lt;username&gt;/job_OSGID
	</pre>
	<ul>
		<li>You will see the script used on the OSG (nodeScript.sh).</li>
		<li>The file condorSubmissionError.txt will show a log in case of submission problem.</li>
		<li>The log submdir contains, for each subjob, the condor (.log), and the std out/err (.out, .err) logs.</li>

	</ul>
	<br/>
	On the node, you can also used the <b>condor_q</b> or our wrapper around it <b>condor-probe.py</b> for general/more details:
	<pre style="font-size: 20px; background-color: #ececec">

	condor_q
	/home/gemc/condor-probe.py
	</pre>
	</p>

	<br/>

	<h2> Generators </h2>
	<p style="margin-left: 40px">

		The generators available on the portal are collected in the <a href="https://github.com/JeffersonLab/clas12-mcgen">clas12-mcgen</a> repo.<br/>
		The generators are not linked with any reconstruction pass versions, and usually fix previous bugs or add features. We advise to always
		use the latest mcgen version.

		This is the preferred way of submitting jobs:
		<li style="margin-left: 60px"><b>Vetted Generators:</b> Using a generator developed on a repository, tagged, available to, vetted and
			developed by CLAS12 users, ensures analyses robustness. LUND submissions uses files whose provenience is not vetted (sometimes unknown).
		</li>
		<li style="margin-left: 60px"><b> Data reproducibility:</b> all generators are tagged, and the submission parameters are saved in a MYSQL database.
			A generator submission is completely reproducible. LUND files are usually not permanently stored and are lost after a submission.
		</li>
		<li style="margin-left: 60px"><b> Efficiency:</b> Using LUND submissions add a network and disk allocation which may cause issue and inefficiencies</li>
	</p>
	<br/>

	<section id="gen-test"><br/>
		<h2> Test Generators </h2>
		<p style="margin-left: 40px">
			Before submitting large scale jobs to OSG it is recommended to test the generator. This can be done on the JLab cue machines.<br/>
			To test mcgen version X (2.33 for example):
		</p>

		<pre>
	module load clas12
	module switch mcgen/X
	clasdis --t 20 25
	dvcsgen --beam 10.604 --x 0.05 0.85 --trig 100 --q2 0.9 14 --t 0 0.79 --gpd 101 --y 0.15 0.9 --w 3.61 --zpos -3 --zwidth 5 --raster 0.025
		</pre>
		<p style="margin-left: 40px">
			Notice on the portal the additional arguments will be given:
		</p>

		<pre style="margin-left: 40px">
	--trig  #nevents
	--docker
	--seed #seed
	</pre>
		<br/>
	</section>

	<h2> Versions </h2>
	<p style="margin-left: 40px">

		The <a href="https://github.com/JeffersonLab/clas12-config">software versions of gemc, coatjava</a> and <a target="_blank"
																												   href="https://github.com/JeffersonLab/clas12-mcgen#readme">mcgen</a>
		are
		selectable by dropdown menu. <br/> Please check the corresponding README for details.
	</p>


	<br/>
	<br/>
	<h2> Container for Interactive Use </h2>

	<p style="margin-left: 40px">
		The docker container used on OSG is also available for interactive use, see
		the <a href="https://clasweb.jlab.org/clas12/clas12SoftwarePage/html/index.html"> docker distribution </a> page
		for details.
	</p>

	<br/>
	<hr>

	<table style=" width:70%; text-align:center; border: 0px; border-collapse: collapse;">
		<tr>
			<th style="border-collapse:collapse; border: 0px;"></th>
			<th style="border-collapse:collapse; border: 0px;"><h2> Contacts and Support </h2></th>
			<th style="border-collapse:collapse; border: 0px;"></th>
		</tr>
		<tr>
			<th style="border-collapse:collapse; border: 0px;"><h3> JLab </h3>
				<a href="mailto:baltzell@jlab.org">Nathan Baltzell</a><br/>
				<a href="mailto:ungaro@jlab.org">Maurizo Ungaro</a>
			</th>
			<th style="border-collapse:collapse; border: 0px;"><h3></h3>
			<th style="border-collapse:collapse; border: 0px;"><h3> Additional Resources </h3>
				<a href="https://clas12.discourse.group/c/simulation/9">Discourse</a><br/>
				<a href="https://clasweb.jlab.org/clas12/clas12SoftwarePage/html/index.html">Docker Distribution</a><br/>
				<a href="https://github.com/JeffersonLab/clas12-mcgen">clas12-mcgen Repo</a><br/>
				<a href="https://clasweb.jlab.org/wiki/index.php/CLAS12_Software_Center#tab=Simulation">CLAS12
					Software Center </a><br/>

			</th>

		</tr>

	</table>
	<br/>
	<br/>

</div>

</body>
<script src="main.js"></script>
</html>
